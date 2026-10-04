"""ANNÉE 1 · LOT 7 — Suivi du taux d'acceptation des propositions (interrupteur HACKVS_SUIVI_IA, éteint par défaut).

Ce que le Club a compris d'une demande (par le modèle, ou par les règles en repli) est PROPOSÉ au membre ; il confirme,
ou non. Deux faits, sans contenu : PROPOSITION (identifiant, source) et PROPOSITION_ACCEPTEE (identifiant). Le taux se
lit par source — décomptes seulement, « < k » compté en entreprises distinctes (anonymat.seuil)."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from plateforme.affirmations import Statut

from . import anonymat

if TYPE_CHECKING:
    from .club_pulse import ClubPulse


def allume() -> bool:
    return os.environ.get("HACKVS_SUIVI_IA") == "1"


def source(ia: dict) -> str:
    """« modele » : la sortie du modèle a été retenue ; « regles » : le repli déterministe (ou aucun modèle)."""
    return "modele" if ia.get("statut") in ("MODEL_CALLED", "CACHE_REPLAY") and not ia.get("repli") else "regles"


def noter_proposition(c: "ClubPulse", pid: str, prop: dict) -> None:
    if allume():
        c.banc._ecrire("PROPOSITION", [pid], Statut.OBSERVE, id=prop["id"], source=source(prop.get("ia") or {}))


def noter_acceptation(c: "ClubPulse", pid: str, prop: dict) -> None:
    if allume():
        c.banc._ecrire("PROPOSITION_ACCEPTEE", [pid], Statut.OBSERVE, id=prop["id"])


def taux(c: "ClubPulse") -> dict:
    acceptees = {e.donnees["id"] for e in c.journal.evenements("PROPOSITION_ACCEPTEE")}
    res = {}
    for src in ("modele", "regles"):
        props = [e for e in c.journal.evenements("PROPOSITION") if e.donnees["source"] == src]
        qui = {e.acteurs[0] for e in props}
        ok = [e for e in props if e.donnees["id"] in acceptees]
        qui_ok = {e.acteurs[0] for e in ok}                # audit des lots 6-8, I1 : le seuil des acceptations se compte
        qui_non = {e.acteurs[0] for e in props if e not in ok}   # sur CEUX QUI ONT ACCEPTÉ (et le reste, sur les autres)
        k = c.reglages.k_anonymat
        assez = all(anonymat.entreprises(c, g) >= k for g in (qui_ok, qui_non) if g)
        res[src] = {"proposees": anonymat.seuil(c, qui, len(props)), "acceptees": anonymat.seuil(c, qui_ok, len(ok)),
                    "taux": round(100 * len(ok) / len(props)) if props and assez else None}
    return {"par_source": res, "regle": "décomptes seulement ; moins de 3 entreprises : « < 3 », taux non dit",
            "note": "« modele » : la compréhension d'Apertus a été retenue ; « regles » : le repli déterministe"}
