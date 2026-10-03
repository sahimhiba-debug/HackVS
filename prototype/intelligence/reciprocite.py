"""BALANCE DE RÉCIPROCITÉ PRIVÉE (P3 n°16) — visible par le membre SEUL : ce que j'ai donné, ce que j'ai reçu.

Donné : mes contributions livrées dans les essais des autres, et mes accords sur les capacités du Club. Reçu : les
contributions d'autres membres dans mes essais. Des décomptes, jamais des noms ; aucune route console, aucun agrégat,
aucun classement : ce n'est pas une note, c'est un miroir (« donner et recevoir », Reciprocity Ring)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .club_pulse import ClubPulse


def balance(c: "ClubPulse", pid: str) -> dict:
    contributions = c.journal.evenements("CONTRIBUTION")
    donne_essais = sum(1 for e in contributions if e.donnees.get("contributeur") == pid and e.acteurs[0] != pid)
    recu = sum(1 for e in contributions if e.acteurs[0] == pid and e.donnees.get("contributeur") not in (None, pid))
    accords = sum(1 for e in c.journal.evenements("ACCORD") if e.acteurs and e.acteurs[0] == pid and e.donnees.get("finalite"))
    return {"donne": donne_essais + accords, "recu": recu,
            "detail": {"contributions_donnees": donne_essais, "accords_au_club": accords, "contributions_recues": recu},
            "prive": "visible par vous seul — le Club ne voit pas cette balance, et rien ne la classe"}
