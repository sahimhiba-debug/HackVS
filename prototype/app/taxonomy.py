"""Chargement de la taxonomie et utilitaires de normalisation du texte."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_SPECIAUX = {"œ": "oe", "Œ": "oe", "æ": "ae", "’": "'", "‘": "'", "–": "-", "—": "-", "ß": "ss"}


def normaliser(texte: str) -> tuple[str, list[int]]:
    """Minuscules sans accents + table de correspondance vers les positions d'origine.

    La table permet de retrouver l'extrait exact du texte saisi par l'utilisateur,
    pour que chaque critère affiché pointe vers ses propres mots.
    """
    sortie: list[str] = []
    positions: list[int] = []
    for i, c in enumerate(unicodedata.normalize("NFC", texte)):
        remplacement = _SPECIAUX.get(c)
        if remplacement is None:
            decompose = unicodedata.normalize("NFKD", c)
            remplacement = "".join(x for x in decompose if not unicodedata.combining(x))
        for r in remplacement.lower():
            sortie.append(r)
            positions.append(i)
    return "".join(sortie), positions


def norm(texte: str) -> str:
    return normaliser(texte)[0]


@lru_cache(maxsize=None)
def motif(expression: str) -> re.Pattern:
    return re.compile(r"(?<![a-z0-9])" + re.escape(expression) + r"(?![a-z0-9])")


@dataclass(frozen=True)
class Concept:
    id: str
    libelle: str
    parent: str | None
    expressions: tuple[str, ...]


_MOTS_OUTILS = {"de", "du", "des", "la", "le", "les", "a", "au", "aux", "en", "et", "pour", "sur", "d", "l"}


def _pluriel(mot: str) -> str:
    if mot in _MOTS_OUTILS or len(mot) <= 2 or mot.endswith(("s", "x", "z")) or "'" in mot[-2:]:
        return mot
    return mot + "s"


def _singulier(mot: str) -> str:
    return mot[:-1] if len(mot) > 3 and mot.endswith("s") and mot not in _MOTS_OUTILS else mot


def variantes(expr: str) -> set[str]:
    """Formes singulier/pluriel d'une expression (« panneau solaire » ↔ « panneaux solaires » partiellement,
    « audit énergétique » → « audits énergétiques »). Générées au chargement : la taxonomie reste lisible."""
    mots = expr.split()
    formes = {expr, " ".join(_pluriel(m) for m in mots), " ".join(_singulier(m) for m in mots),
              " ".join([_pluriel(mots[0])] + mots[1:])}
    if len(mots) > 1:
        formes.add(" ".join(mots[:-1] + [_pluriel(mots[-1])]))
    return {f for f in formes if len(f) >= 3}


class Taxonomie:
    def __init__(self, brut: dict):
        self.concepts: dict[str, Concept] = {
            cid: Concept(cid, c["libelle"], c.get("parent"),
                         tuple(sorted({v for e in c["expressions"] for v in variantes(norm(e))})))
            for cid, c in brut["concepts"].items()
        }
        self.ambigus: dict[str, dict] = brut.get("ambigus", {})
        self.zones: dict[str, tuple[str, ...]] = {z: tuple(norm(e) for e in v) for z, v in brut["zones"].items()}
        self.langues: dict[str, dict] = brut["langues"]
        self.marqueurs_souples = tuple(norm(m) for m in brut.get("marqueurs_souples", []))
        self.marqueurs_concurrents = tuple(norm(m) for m in brut.get("marqueurs_concurrents", []))
        self.marqueurs_forts = tuple(norm(m) for m in brut.get("marqueurs_forts", []))
        self.mots_generiques = frozenset(norm(m) for m in brut.get("mots_generiques", []))
        self.composes_trompeurs = tuple(sorted({norm(e) for e in brut.get("composes_trompeurs", {}).get("expressions", [])},
                                               key=len, reverse=True))
        self.contextes_trompeurs: dict[str, tuple[str, ...]] = {
            cid: tuple(norm(e) for e in v) for cid, v in brut.get("contextes_trompeurs", {}).items() if not cid.startswith("_")}
        for c in self.concepts.values():
            if c.parent and c.parent not in self.concepts:
                raise ValueError(f"Parent inconnu pour {c.id}: {c.parent}")

    def zone_de_commune(self, commune: str) -> str | None:
        """Zone d'IMPLANTATION déduite de la commune (différente des zones d'intervention)."""
        n = norm(commune)
        for zone, exprs in self.zones.items():
            if any(motif(e).search(n) for e in exprs):
                return zone
        return None

    def libelle(self, cid: str) -> str:
        return self.concepts[cid].libelle if cid in self.concepts else cid

    def ancetres(self, cid: str) -> list[str]:
        res, cur = [], self.concepts.get(cid)
        while cur and cur.parent:
            res.append(cur.parent)
            cur = self.concepts.get(cur.parent)
        return res

    def couvre(self, offert: str, demande: str) -> bool:
        """Une offre couvre une demande si elle est identique ou plus spécifique."""
        return offert == demande or demande in self.ancetres(offert)

    def meme_famille(self, a: str, b: str) -> bool:
        return self.couvre(a, b) or self.couvre(b, a)

    def concepts_dans(self, texte_norm: str) -> set[str]:
        """Concepts présents dans un texte normalisé, expression la plus longue d'abord.

        « sécurité informatique » compte comme cybersécurité, pas comme informatique générale.
        """
        if not hasattr(self, "_triees"):
            self._triees = sorted(((e, c.id) for c in self.concepts.values() for e in c.expressions), key=lambda x: -len(x[0]))
        pris: list[tuple[int, int]] = [(m.start(), m.end()) for e in self.composes_trompeurs for m in motif(e).finditer(texte_norm)]
        trouves: set[str] = set()
        for expr, cid in self._triees:
            for m in motif(expr).finditer(texte_norm):
                if not any(m.start() < f and d < m.end() for d, f in pris):
                    pris.append((m.start(), m.end()))
                    trouves.add(cid)
        return {c for c in trouves if not any(motif(t).search(texte_norm) for t in self.contextes_trompeurs.get(c, ()))}

    def descendants(self, cid: str) -> list[str]:
        """Le concept lui-même et toutes ses sous-catégories."""
        return [cid] + [c.id for c in self.concepts.values() if cid in self.ancetres(c.id)]

    def expressions_de(self, cid: str) -> list[str]:
        """Expressions du concept et de ses descendants (pour l'inférence depuis un texte libre)."""
        res = list(self.concepts[cid].expressions)
        for c in self.concepts.values():
            if cid in self.ancetres(c.id):
                res.extend(c.expressions)
        return res


@lru_cache(maxsize=1)
def charger_taxonomie() -> Taxonomie:
    with open(DATA_DIR / "taxonomie.json", encoding="utf-8") as f:
        return Taxonomie(json.load(f))
