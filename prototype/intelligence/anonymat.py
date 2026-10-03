"""ANONYMAT À PETITE ÉCHELLE (Foire 2026, C) — k = 3.

Dans un club d'une cinquantaine de membres, nommer un RÔLE peut suffire à désigner une personne : si une seule
personne du Club a jamais tenu le rôle « transport », « transport : ce composant n'est plus disponible » la nomme.
Règle : un rôle tenu par MOINS de k membres (Reglages.k_anonymat, 3 par défaut) n'est jamais dit dans un avis de
retrait ou de perte. Le système ne nomme jamais et ne demande jamais pourquoi ; dans un petit club, on peut parfois
deviner — c'est dit tel quel (CLAIMS), pas promis.

Qui « tient » un rôle, POUR UNE CAPACITÉ : toute personne qui a, un jour, donné son consentement pour une pièce de ce rôle (journal,
ACCORD — retraits compris : un ancien porteur reste un porteur connu), ou qui déclare aujourd'hui une compétence du
concept attendu par ce rôle. Un décompte, jamais une liste ; calculé à la lecture, rien n'est écrit."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

MASQUE = "un composant n'est plus disponible"


def porteurs(c: "ClubPulse", finalite: str) -> dict[str, int]:
    """Pour UNE capacité : nombre de membres DISTINCTS connus pour chacun de ses rôles (emplacements) — un rôle se compte
    là où il est tenu (le « transport » d'une délégation n'est pas celui d'une livraison frigorifique)."""
    p = c.capacites.patron(finalite)
    jour = c.jour
    res = {}
    for e in p.emplacements:
        qui = {x.acteurs[0] for x in c.journal.evenements("ACCORD")
               if x.acteurs and x.donnees.get("finalite") == finalite and x.donnees.get("emplacement") == e.id}
        if e.concept:
            qui |= {x.membre for x in c.claims() if x.concept == e.concept and x.superseded_at is None and x.valable(jour)}
        res[e.role] = len(qui)
    return res


def masquer_avis(c: "ClubPulse", finalite: str, avis: list[str]) -> tuple[list[str], int]:
    """« rôle : ce composant n'est plus disponible[…] » → « un composant n'est plus disponible[…] » sous le seuil."""
    if not avis:
        return avis, 0
    k, nb = c.reglages.k_anonymat, porteurs(c, finalite)
    sortie, masques = [], 0
    for a in avis:
        role, _, reste = a.partition(" : ")
        if reste and nb.get(role, 0) < k:
            suite = reste.split("ce composant n'est plus disponible", 1)
            sortie.append(MASQUE + (suite[1] if len(suite) == 2 else ""))
            masques += 1
        else:
            sortie.append(a)
    return sortie, masques
