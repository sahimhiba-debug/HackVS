"""ANNÉE 1 · LOT 1 — Sauvegarde et restauration du journal, indépendantes du moteur (SQLite ↔ PostgreSQL).

Format v2 : JSON Lines, séparées par « \\n » SEULEMENT (un texte de membre peut contenir U+2028, U+0085… : jamais une
fin de ligne). Ligne 1 : l'en-tête (`format`, `version`, `nombre`, `empreinte`, `empreinte_journal` =
`Memoire.empreinte`). Puis un fait par ligne, dans l'ordre,
AVEC son numéro `seq` (les références des reçus en dépendent). L'empreinte est un SHA-256 de toutes les lignes de faits,
octet pour octet : un fait altéré (statut compris), ajouté, retiré, déplacé ou renuméroté change l'empreinte.

Sauvegarder : écrit un fichier provisoire, le force sur le disque, le RELIT et le vérifie, puis seulement lui donne
son nom. Restaurer : seulement dans un journal VIDE, en une transaction, revérifiée AVANT validation. Tout ou rien."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .memoire import Evt, Memoire

FORMAT, VERSION = "clubpulse-journal", 2


class SauvegardeInvalide(ValueError):
    """Fichier altéré, incomplet, d'un autre format — ou cible non vide."""


def _empreinte(lignes: list[str]) -> str:
    h = hashlib.sha256()
    for x in lignes:
        h.update(x.encode("utf-8") + b"\n")
    return h.hexdigest()


def _lignes(m: Memoire) -> list[str]:
    return [e.model_dump_json() for e in m.evenements()]


def sauvegarder(m: Memoire, chemin: Path | str) -> dict:
    lignes = _lignes(m)
    entete = {"format": FORMAT, "version": VERSION, "nombre": len(lignes), "empreinte": _empreinte(lignes),
              "empreinte_journal": m.empreinte()}
    p = Path(chemin)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".part")
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(entete, ensure_ascii=False) + "\n")
            for x in lignes:
                f.write(x + "\n")
            f.flush()
            os.fsync(f.fileno())
        relu, _ = lire(tmp)                            # jamais « réussie » sans avoir été relue
        if relu != entete:
            raise SauvegardeInvalide("la sauvegarde relue diffère de ce qui a été écrit")
        tmp.replace(p)                                 # jamais une sauvegarde à moitié écrite sous le bon nom
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return entete


def _verifier(entete: dict, lignes: list[str]) -> None:
    if len(lignes) != entete.get("nombre"):
        raise SauvegardeInvalide(f"incomplet : {len(lignes)} faits lus, {entete.get('nombre')} annoncés")
    if _empreinte(lignes) != entete.get("empreinte"):
        raise SauvegardeInvalide("empreinte différente : fichier altéré")


def lire(chemin: Path | str) -> tuple[dict, list[Evt]]:
    entete, lignes = _lire(chemin)
    return entete, [Evt.model_validate_json(x) for x in lignes]


def _lire(chemin: Path | str) -> tuple[dict, list[str]]:
    with open(chemin, encoding="utf-8", newline="") as f:
        brut = f.read()
    if not brut:
        raise SauvegardeInvalide("fichier vide")
    if not brut.endswith("\n"):
        raise SauvegardeInvalide("fichier tronqué (pas de fin de ligne finale)")
    tete, *lignes = brut[:-1].split("\n")
    try:
        entete = json.loads(tete)
        evts = [Evt.model_validate_json(x) for x in lignes]
    except ValueError as e:
        raise SauvegardeInvalide(f"fichier illisible : {e}") from None
    if not isinstance(entete, dict) or entete.get("format") != FORMAT or entete.get("version") != VERSION:
        v = entete.get("version") if isinstance(entete, dict) else "?"
        raise SauvegardeInvalide(f"format inconnu (v{v}) : seul le format {FORMAT} v{VERSION} se restaure")
    _verifier(entete, lignes)
    if len({e.id for e in evts}) != len(evts):
        raise SauvegardeInvalide("un même fait apparaît deux fois")
    if any(b.seq <= a.seq for a, b in zip(evts, evts[1:], strict=False)) or any(e.seq < 1 for e in evts):
        raise SauvegardeInvalide("numéros des faits dans le désordre")
    if any(Evt.model_validate_json(x).model_dump_json() != x for x in lignes):
        raise SauvegardeInvalide("ligne non canonique")
    return entete, lignes


def restaurer(m: Memoire, chemin: Path | str) -> dict:
    entete, lignes = _lire(chemin)                     # tout vérifier AVANT d'écrire
    try:
        def verifier(relues: list[str]) -> None:
            _verifier(entete, relues)
            ids = "".join(Evt.model_validate_json(x).id for x in relues)
            if hashlib.sha256(ids.encode()).hexdigest() != entete.get("empreinte_journal"):
                raise SauvegardeInvalide("empreinte du journal restauré différente de la sauvegarde")
        m.charger_sauvegarde(lignes, verifier)
    except SauvegardeInvalide:
        raise
    except ValueError as e:
        raise SauvegardeInvalide(str(e)) from None
    return entete
