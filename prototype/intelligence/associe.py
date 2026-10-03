"""STATUT « MEMBRE ASSOCIÉ » (P3 n°8, jalon « Grandir ») — une personne d'une organisation PARTENAIRE reçoit les demandes
du Club comme un membre ; le Club la compte à part, en agrégats.

Le partenaire est un EXEMPLE FICTIF : aucun partenaire réel n'est acquis (pistes « à contacter » : ROADMAP.md).
Journalisé (ASSOCIE / ASSOCIE_RETRAIT) ; rien de nominatif n'est montré au Club."""
from __future__ import annotations

from typing import TYPE_CHECKING

from plateforme.affirmations import Statut

from . import anonymat
from .erreurs import Introuvable

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

PARTENAIRE = {"id": "exemple-chambre-74", "nom": "Chambre partenaire (exemple fictif)", "zone": "Haute-Savoie", "exemple": True}


def _actuels(c: "ClubPulse") -> set[str]:
    res: set[str] = set()
    for e in c.journal.evenements("ASSOCIE", "ASSOCIE_RETRAIT"):
        (res.add if e.type == "ASSOCIE" else res.discard)(e.donnees["membre"])
    return {m for m in res if c.coffre.identite(m) is not None}


def declarer(c: "ClubPulse", pid: str) -> dict:
    c.profil(pid)                                        # Introuvable si inconnu
    if c.coffre.identite(pid) is None:
        raise Introuvable("membre inconnu")
    if pid not in _actuels(c):
        c.banc._ecrire("ASSOCIE", [pid], Statut.DECLARE, membre=pid, partenaire=PARTENAIRE["id"])
    return agregats(c)


def retirer(c: "ClubPulse", pid: str) -> dict:
    if pid in _actuels(c):
        c.banc._ecrire("ASSOCIE_RETRAIT", [pid], Statut.DECLARE, membre=pid, partenaire=PARTENAIRE["id"])
    return agregats(c)


def statut(c: "ClubPulse", pid: str) -> dict:
    a = pid in _actuels(c)
    return {"statut": "membre associé" if a else "membre", "partenaire": PARTENAIRE if a else None}


def agregats(c: "ClubPulse") -> dict:
    qui = _actuels(c)
    return {"associes": anonymat.seuil(c, qui, len(qui)), "partenaire": PARTENAIRE,
            "note": "partenaire : exemple fictif — aucun partenaire réel n'est acquis"}
