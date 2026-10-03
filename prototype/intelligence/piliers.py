"""ESCALADE VERS DES MEMBRES « PILIERS » VOLONTAIRES (P3 n°15).

Un membre peut se déclarer pilier (et se retirer) : journal PILIER / PILIER_RETRAIT. Un pilier voit les demandes
BLOQUÉES (sans réponse depuis SEUIL_BLOQUEE jours ou plus) pour les relayer dans son propre réseau — jamais qui a été
sollicité, jamais qui a dit non. Le secrétariat ne voit que le nombre de piliers (« < 3 » en entreprises). Le routage
d'une demande reste par catégorie : un pilier ne reçoit rien de plus, il VOIT ce qui coince."""
from __future__ import annotations

from typing import TYPE_CHECKING

from plateforme.affirmations import Statut

from . import anonymat, club_cherche
from .erreurs import Interdit
from .tableau_bord import SEUIL_BLOQUEE

if TYPE_CHECKING:
    from .club_pulse import ClubPulse


def actuels(c: "ClubPulse") -> set[str]:
    res: set[str] = set()
    for e in c.journal.evenements("PILIER", "PILIER_RETRAIT"):
        (res.add if e.type == "PILIER" else res.discard)(e.acteurs[0])
    return {m for m in res if c.coffre.identite(m) is not None}


def declarer(c: "ClubPulse", pid: str, actif: bool) -> dict:
    if actif and pid not in actuels(c):
        c.banc._ecrire("PILIER", [pid], Statut.DECLARE)
    elif not actif and pid in actuels(c):
        c.banc._ecrire("PILIER_RETRAIT", [pid], Statut.DECLARE)
    return {"pilier": pid in actuels(c)}


def escalades(c: "ClubPulse", pid: str) -> list[dict]:
    if pid not in actuels(c):
        raise Interdit("réservé aux membres piliers volontaires")
    return _bloquees(c)


def pour_membre(c: "ClubPulse", pid: str) -> dict:
    """Pour la route : un non-pilier reçoit « pilier : non » et rien d'autre (pas d'erreur : il est bien authentifié)."""
    p = pid in actuels(c)
    return {"pilier": p, "escalades": _bloquees(c) if p else []}


def _bloquees(c: "ClubPulse") -> list[dict]:
    return [{"titre": d["titre"], "piece": d["piece"], "metier": g["libelle"], "age_jours": d["age_jours"]}
            for g in club_cherche.calculer(c)["metiers"] for d in g["demandes"] if d["age_jours"] >= SEUIL_BLOQUEE]


def agregats(c: "ClubPulse") -> dict:
    p = actuels(c)
    return {"piliers": anonymat.seuil(c, p, len(p)), "seuil_bloquee_jours": SEUIL_BLOQUEE}
