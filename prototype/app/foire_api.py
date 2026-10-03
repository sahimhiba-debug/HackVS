"""Routes FOIRE 2026 (interrupteur HACKVS_FOIRE) : Suivi, clôture de reçu, visibilité, passe découverte, « le Club
cherche ». Un adaptateur mince, comme capacites_api : valider, authentifier, appeler le service, traduire l'erreur.
Interrupteur éteint : chaque route répond 404 « désactivé » — le produit d'hier, à l'identique."""
from __future__ import annotations

from typing import Callable, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from intelligence import partenariats, suivi


class Cloture(BaseModel):
    resultat: Literal["signé", "test sans suite", "contact établi", "abandonné"]
    note: Optional[str] = Field(default=None, max_length=partenariats.NOTE_MAX)


class Visibilite(BaseModel):
    visible: bool


def ajouter_routes(r: APIRouter, au_monde: Callable, membre: Callable, console: Callable) -> None:
    def foire(f: Callable) -> Callable:
        def g(c):
            if not c.reglages.foire:
                raise HTTPException(404, "Fonction désactivée (HACKVS_FOIRE=0).")
            return f(c)
        return g

    @r.get("/console/suivi", dependencies=[Depends(console)])
    def lire_suivi(periode: str = "demo") -> dict:
        return au_monde(foire(lambda c: suivi.calculer(c, periode[:12])))

    @r.get("/console/recus", dependencies=[Depends(console)])
    def recus_console() -> list[dict]:
        """Les reçus du Club pour la clôture : référence, capacité, pièce, étape — JAMAIS le membre (sauf double accord,
        dans Suivi)."""
        return au_monde(foire(lambda c: [{"reference": x["reference"], "titre": x["titre"], "piece": x["piece"],
                                          "etape": x["etape"], "resultat": (x["cloture"] or {}).get("resultat"),
                                          "visible_club": partenariats.CLUB in x["visible"], "visible_membre": "membre" in x["visible"],
                                          "fictif": True}
                                         for x in partenariats.recus_du_club(c)]))

    @r.post("/console/recus/{reference}/cloture", dependencies=[Depends(console)])
    def cloturer(reference: str, x: Cloture) -> dict:
        return au_monde(foire(lambda c: partenariats.cloturer(c, reference[:40], x.resultat, x.note)))

    @r.post("/console/recus/{reference}/visible", dependencies=[Depends(console)])
    def visible_club(reference: str, x: Visibilite) -> dict:
        return au_monde(foire(lambda c: partenariats.rendre_visible(c, reference[:40], partenariats.CLUB, x.visible)))

    @r.post("/moi/recus/{reference}/visible")
    def visible_membre(reference: str, x: Visibilite, pid: str = Depends(membre)) -> dict:
        return au_monde(foire(lambda c: partenariats.rendre_visible(c, reference[:40], "membre", x.visible, membre=pid)))
