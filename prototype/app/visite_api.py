"""FEUILLE DE ROUTE VIVANTE et MONDE « VISITE » (Foire 2026 · §7).

- `GET /feuille-de-route` (page) et `GET /api/pulse/feuille-de-route` (public, lecture seule) : les chantiers de
  docs/roadmap/etat.yaml, trois statuts, FR / DE / EN ; QR « visite » construit depuis PUBLIC_BASE_URL.
- Le MONDE « VISITE » est un DEUXIÈME conteneur, même image, `HACKVS_VISITE=1` : journal à lui, mode salle éteint, IA
  éteinte, console ouverte sans jeton (bac à sable de données fictives, pour que le jury explore après le pitch). Les
  liens « Construit » y mènent (`PUBLIC_VISITE_URL`) ; sans elle, ils ne sont pas affichés.
- `GET /api/pulse/monde` (public) : dans quel monde on est — les écrans l'affichent."""
from __future__ import annotations

import os
from typing import Callable

from fastapi import APIRouter, Request

from intelligence import feuille_de_route

from .urls import base_publique


def visite() -> bool:
    return os.environ.get("HACKVS_VISITE") == "1"


def ajouter_routes(r: APIRouter, qr: Callable[[str], str]) -> None:
    @r.get("/monde")
    def monde() -> dict:
        return {"visite": visite(), "monde": "monde « visite » (bac à sable fictif)" if visite() else "monde de démonstration"}

    @r.get("/feuille-de-route")
    def feuille(request: Request) -> dict:
        url = base_publique(request) + "/feuille-de-route"
        base_visite = os.environ.get("PUBLIC_VISITE_URL") or (base_publique(request) if visite() else None)
        return {"chantiers": feuille_de_route.pour_la_page(base_visite), "qr": qr(url), "url": url,
                "visite_disponible": base_visite is not None}
