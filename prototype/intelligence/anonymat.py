"""ANONYMAT À PETITE ÉCHELLE (Foire 2026, C) — k = 3.

Dans un club de 145 entreprises, nommer un RÔLE peut suffire à désigner une personne : si une seule
personne du Club a jamais tenu le rôle « transport », « transport : ce composant n'est plus disponible » la nomme.
Règle : un rôle tenu par MOINS de k ENTREPRISES distinctes (liste du Club, 3 octobre : 145 entreprises, 173 représentants —
deux représentants d'une même entreprise ne comptent qu'une fois) (Reglages.k_anonymat, 3 par défaut) n'est jamais dit dans un avis de
retrait ou de perte. Le système ne nomme jamais et ne demande jamais pourquoi ; dans un petit club, on peut parfois
deviner — c'est dit tel quel (CLAIMS), pas promis.

Qui « tient » un rôle, POUR UNE CAPACITÉ : toute personne qui a, un jour, donné son consentement pour une pièce de ce rôle (journal,
ACCORD — retraits compris : un ancien porteur reste un porteur connu), ou qui déclare aujourd'hui une compétence du
concept attendu par ce rôle. Un décompte, jamais une liste ; calculé à la lecture, rien n'est écrit."""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Union

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

MASQUE = "un composant n'est plus disponible"
Nombre = Union[int, str]


def entreprises(c: "ClubPulse", membres: Iterable[str]) -> int:
    """Nombre d'ENTREPRISES distinctes parmi des membres (le seuil se compte là, pas en personnes)."""
    return len({c.coffre.cle_entreprise(m) for m in membres})


def seuil(c: "ClubPulse", membres: Iterable[str], n: int) -> Nombre:
    """`n` (un décompte : personnes, réponses, reçus) n'est dit que si les membres concernés viennent d'au moins k
    entreprises distinctes ; sinon « < k ». 0 reste 0 : personne n'est désigné."""
    k = c.reglages.k_anonymat
    return f"< {k}" if n and entreprises(c, membres) < k else n


def porteurs(c: "ClubPulse", finalite: str) -> dict[str, int]:
    """Pour UNE capacité : nombre d'ENTREPRISES distinctes connues pour chacun de ses rôles (emplacements) — un rôle se
    compte là où il est tenu (le « transport » d'une délégation n'est pas celui d'une livraison frigorifique)."""
    return {role: entreprises(c, qui) for role, qui in porteurs_membres(c, finalite).items()}


def porteurs_membres(c: "ClubPulse", finalite: str) -> dict[str, set[str]]:
    """Les membres connus pour chaque rôle d'une capacité (interne : sert au décompte, jamais renvoyé par une vue)."""
    p = c.capacites.patron(finalite)
    jour = c.jour
    res = {}
    for e in p.emplacements:
        qui = {x.acteurs[0] for x in c.journal.evenements("ACCORD")
               if x.acteurs and x.donnees.get("finalite") == finalite and x.donnees.get("emplacement") == e.id}
        if e.concept:
            qui |= {x.membre for x in c.claims() if x.concept == e.concept and x.superseded_at is None and x.valable(jour)}
        res[e.role] = qui
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
