"""« NOUVEAUX LIENS TISSÉS » (Suivi, P3 n°4) — ce que le Club ne voyait pas : des entreprises qui font quelque chose
ensemble pour la première fois.

Un LIEN = deux ENTREPRISES distinctes qui portent chacune un accord (journal, ACCORD) sur la même capacité. Il naît le
jour où le second des deux accords est donné. « Nouveau » dans une période = né dans la période et jamais né avant.
Calculé à la lecture, depuis le journal ; un décompte, jamais une liste ; seuil « < 3 » en entreprises distinctes.
Les retraits ne défont pas un lien déjà tissé : ils ont travaillé ensemble (un retrait se lit ailleurs)."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from . import anonymat

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

ROUTAGE = ("Hypothèse, non branché : favoriser, pour une même demande, les membres qui n'ont encore jamais travaillé "
           "avec le demandeur (les liens faibles font bouger — Science, 2022). Aujourd'hui une demande va à une "
           "catégorie, jamais à une personne choisie par le système ; changer cela demande l'accord du Club.")


def _naissances(c: "ClubPulse") -> dict[frozenset, tuple[date, set[str]]]:
    """Chaque paire d'entreprises → (jour de naissance, membres concernés)."""
    premiers: dict[tuple[str, str], tuple[date, str]] = {}            # (finalité, entreprise) → (premier accord, membre)
    for e in c.journal.evenements("ACCORD"):
        f = e.donnees.get("finalite")
        if not f or not e.acteurs:
            continue
        cle = (f, c.coffre.cle_entreprise(e.acteurs[0]))
        if cle not in premiers or e.le < premiers[cle][0]:
            premiers[cle] = (e.le, e.acteurs[0])
    res: dict[frozenset, tuple[date, set[str]]] = {}
    par_finalite: dict[str, list[tuple[str, date, str]]] = {}
    for (f, ent), (le, membre) in premiers.items():
        par_finalite.setdefault(f, []).append((ent, le, membre))
    for liste in par_finalite.values():
        for i, (a, la, ma) in enumerate(liste):
            for b, lb, mb in liste[i + 1:]:
                paire, ne = frozenset((a, b)), max(la, lb)
                if paire not in res or ne < res[paire][0]:
                    res[paire] = (ne, {ma, mb})
    return res


def paires(c: "ClubPulse", debut: Optional[date]) -> int:
    return sum(1 for ne, _ in _naissances(c).values() if debut is None or ne >= debut)


def nouveaux(c: "ClubPulse", debut: Optional[date]) -> dict:
    neuves = [m for ne, m in _naissances(c).values() if debut is None or ne >= debut]
    membres = set().union(*neuves) if neuves else set()
    return {"nouveaux": anonymat.seuil(c, membres, len(neuves)),
            "definition": "deux entreprises distinctes qui portent chacune un accord sur la même capacité, pour la première fois",
            "routage": ROUTAGE}
