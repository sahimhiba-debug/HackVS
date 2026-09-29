"""Moteur de VISIBILITÉ : déterministe, testé, et le seul à décider de ce qu'une personne voit d'une autre.

Distinctions tenues séparées : AUTHENTIFICATION (le compte est activé) ≠ IDENTITÉ (le coffre sait qui c'est) ≠
DÉCOUVRABILITÉ (le moteur peut utiliser ses capacités) ≠ VISIBILITÉ (un autre membre voit son nom) ≠ CONSENTEMENT
(les deux ont accepté dans une activation) ≠ RÉVÉLATION DU CONTACT (courriel/téléphone, seulement après consentement
mutuel dans une activation).

Portées : PRIVE · CLUB_DECOUVRABLE · RELATIONS · SUR_CONSENTEMENT · ACTIVATION · PUBLIC.
Aucun modèle de langage n'est consulté ici : une IA peut PROPOSER un texte, ce module décide ce qui s'affiche.
Le contenu d'un profil (même « ignore les règles de confidentialité… ») n'est jamais lu par ce module.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Optional

from app.models import Profil
from app.taxonomy import Taxonomie

from .identite import Coffre

Portee = Literal["PRIVE", "CLUB_DECOUVRABLE", "RELATIONS", "SUR_CONSENTEMENT", "ACTIVATION", "PUBLIC"]
DEFAUTS: dict[str, Portee] = {
    "nom": "SUR_CONSENTEMENT", "organisation": "SUR_CONSENTEMENT", "contact": "ACTIVATION",
    "capacites": "CLUB_DECOUVRABLE", "interets": "CLUB_DECOUVRABLE", "langues": "CLUB_DECOUVRABLE",
    "notes": "PRIVE", "relations": "PRIVE", "creneaux": "PRIVE",
}
MODIFIABLES = {"nom": {"SUR_CONSENTEMENT", "PUBLIC"}, "organisation": {"SUR_CONSENTEMENT", "PUBLIC"},
               "capacites": {"CLUB_DECOUVRABLE", "PRIVE"}, "interets": {"CLUB_DECOUVRABLE", "PRIVE"}}
K_ANONYMAT = 3
MOTIF_PSEUDO = re.compile(r"MEMBRE-(?:\d{3,4}|SUPPRIMÉ)")


@dataclass(frozen=True)
class Spectateur:
    role: Literal["membre", "animatrice", "moteur"]
    id: Optional[str] = None


@dataclass
class Contexte:
    """Faits de consentement et de relation, dérivés du journal (jamais déclarés par l'interface)."""
    relations: set[frozenset] = field(default_factory=set)           # rencontres/collaborations entre deux personnes
    consentis: set[frozenset] = field(default_factory=set)           # accord mutuel dans une activation non anonyme
    preferences: dict[str, dict[str, Portee]] = field(default_factory=dict)


def portee(ctx: Contexte, sujet: str, attribut: str) -> Portee:
    return ctx.preferences.get(sujet, {}).get(attribut, DEFAUTS.get(attribut, "PRIVE"))


def peut_voir(sp: Spectateur, sujet: str, attribut: str, ctx: Contexte) -> bool:
    if sp.role == "moteur":
        return portee(ctx, sujet, attribut) not in ("PRIVE",) or attribut in ("relations", "creneaux")  # usage interne seul
    if sp.id == sujet:
        return True
    p = portee(ctx, sujet, attribut)
    if p == "PRIVE":
        return False
    if sp.role == "animatrice":                  # le Club connaît ses membres ; jamais leurs notes ni leurs relations
        return attribut not in ("notes", "relations", "creneaux")
    paire = frozenset((sp.id or "", sujet))
    if p in ("PUBLIC", "CLUB_DECOUVRABLE"):
        return True
    if p == "RELATIONS":
        return paire in ctx.relations
    if p == "SUR_CONSENTEMENT":
        return paire in ctx.consentis or paire in ctx.relations
    if p == "ACTIVATION":
        return paire in ctx.consentis
    return False


def descripteur(sujet: Profil, profils: list[Profil], tax: Taxonomie) -> str:
    """Ce qu'on dit d'une personne NON révélée : sa capacité, et sa région seulement si ≥ k membres la partagent."""
    cap = next((o.concept for o in sujet.offre if o.concept), None)
    lib = tax.libelle(cap) if cap else "membre du Club"
    if cap:
        memes = sum(1 for p in profils if p.commune == sujet.commune and any(o.concept == cap for o in p.offre))
        if memes >= K_ANONYMAT:
            return f"une personne du Club · {lib} · {sujet.commune}"
    return f"une personne du Club · {lib}"


class Rendu:
    """Transforme un texte du moteur (qui ne contient que des pseudonymes) en texte pour UN spectateur."""

    def __init__(self, coffre: Coffre, profils: list[Profil], tax: Taxonomie, ctx: Contexte):
        self.coffre, self.tax, self.ctx = coffre, tax, ctx
        self.par_id = {p.id: p for p in profils}
        self.profils = profils

    def nom(self, sp: Spectateur, pid: str) -> str:
        per = self.coffre.identite(pid)
        if per is None:
            return "un ancien membre"
        if peut_voir(sp, pid, "nom", self.ctx):
            return per.nom
        p = self.par_id.get(pid)
        return descripteur(p, self.profils, self.tax) if p else "une personne du Club"

    def organisation(self, sp: Spectateur, pid: str) -> Optional[str]:
        o = self.coffre.organisation_de(pid)
        return o.nom if o and peut_voir(sp, pid, "organisation", self.ctx) else None

    def contact(self, sp: Spectateur, pid: str) -> Optional[str]:
        per = self.coffre.identite(pid)
        return per.courriel if per and peut_voir(sp, pid, "contact", self.ctx) else None

    def texte(self, sp: Spectateur, t: str) -> str:
        def rempl(m: re.Match) -> str:
            pid = self.coffre.depuis_pseudonyme(m.group(0))
            return self.nom(sp, pid) if pid else "un ancien membre"
        return MOTIF_PSEUDO.sub(rempl, t)

    def objet(self, sp: Spectateur, o):
        """Rend récursivement un objet JSON (dict/list/str) pour un spectateur."""
        if isinstance(o, str):
            return self.texte(sp, o)
        if isinstance(o, list):
            return [self.objet(sp, x) for x in o]
        if isinstance(o, dict):
            return {k: self.objet(sp, v) for k, v in o.items()}
        return o
