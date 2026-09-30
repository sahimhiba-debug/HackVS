"""Ce qu'on MONTRE du registre des capacités. En RÔLES seulement : ni nom, ni texte d'offre (un texte d'offre peut
désigner quelqu'un — « le stand de la distillerie »), ni qui a consenti ou non. Un consentement perdu est dit par
l'emplacement (« salle : consentement retiré »), jamais par la personne."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .capacites import Instance

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

LIBELLES = {"ONE_AWAY": "il manque une pièce", "PROPOSED": "toutes les pièces existent — aucun consentement encore",
            "CONSENTED": "consentements en cours", "ACTIVE": "le Club peut le faire", "DEGRADED": "un consentement ne vaut plus",
            "EXTINCT": "la fenêtre est passée"}


class VuesCapacites:
    def __init__(self, club: "ClubPulse"):
        self.c = club

    def instance(self, i: Instance) -> dict:
        p = self.c.capacites.patron(i.finalite)
        pieces = []
        for e in p.emplacements:
            v, cons = i.liaisons.get(e.id), i.consentements.get(e.id)
            pieces.append({"emplacement": e.id, "role": e.role, "libelle": e.libelle, "presente": v is not None,
                           "consentement": None if v is None else ("donné" if cons is None else "à demander"),
                           "manquante": i.manquant == e.id})
        return {"finalite": i.finalite, "version": i.version, "titre": i.titre, "statut": i.statut,
                "statut_libelle": LIBELLES.get(i.statut or "", ""), "distance": i.distance,
                "creneau": i.creneau.texte() if i.creneau else None, "pieces": pieces,
                "ask": {"texte": i.ask.texte, "expire": i.ask.expire.isoformat()} if i.ask else None,
                "perdus": i.perdus, "hypotheses": i.hypotheses, "fictif": i.fictif}

    def console(self) -> dict:
        """Le registre : ce que le Club PEUT faire (distance 0) et ce qu'il lui manque une pièce pour faire (distance 1)."""
        return {"capacites": [self.instance(i) for i in self.c.capacites.projeter() if i.statut is not None],
                "date": self.c.jour.isoformat(), "fictif": True,
                "regle": "Une capacité n'existe que si chaque pièce est déclarée, valable à cette date et consentie pour "
                         "cette finalité. Rôles seulement : aucun nom."}

    def asks(self, pid: str) -> list[dict]:
        return [{"id": a, "titre": i.titre, "texte": i.ask.texte, "libelle": i.ask.libelle, "minimums": i.ask.minimums,  # type: ignore[union-attr]
                 "expire": i.ask.expire.isoformat(), "choix": ["oui", "non", "pas cette fois"]}  # type: ignore[union-attr]
                for i, a in self.c.asks_pour(pid)]

    def apres_reponse(self, i: Instance, pid: Optional[str] = None) -> dict:
        return self.instance(i) | {"vous": "votre pièce est enregistrée, avec votre consentement pour cette seule finalité"}
