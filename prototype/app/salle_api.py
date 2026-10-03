"""Routes du MODE SALLE (interrupteur HACKVS_SALLE, allumé par défaut) — adaptateur mince autour de intelligence/salle.
L'état vit au niveau du PROCESSUS (une séance de pitch), hors du journal du Club : réinitialiser la démonstration ne le
touche pas ; la purge l'efface entièrement. Débit limité par passe et globalement — jamais par adresse IP."""
from __future__ import annotations

import os
from typing import Callable, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from intelligence.erreurs import ErreurMetier
from intelligence.salle import Salle

from .urls import base_publique


class Entree(BaseModel):
    jeton: str = Field(max_length=80)


class Capacite(BaseModel):
    capacite: str = Field(max_length=20)
    consentement: bool


class Vue(BaseModel):
    vue: Literal["salle", "bilan"]


class Choix(BaseModel):
    choix: Literal["oui", "non", "pas cette fois"]


def ajouter_routes(r: APIRouter, console: Callable, secret: Callable[[], bytes], *, limiter: Callable, nouveau_limiteur: Callable,
                   qr: Callable[[str], str]) -> tuple[Callable[[Request], Optional[str]], Callable[[], Optional[dict]]]:
    """Ajoute les routes ; renvoie l'URL courante de la salle (None si fermée) — pour le QR servi EN DIRECT à la racine
    (/qr/salle.svg, app/main.py), qui suit l'adresse publique du moment (PUBLIC_BASE_URL : l'adresse du tunnel) — et
    l'aperçu de l'écran géant (None : salle jamais créée depuis le lancement), pour la check-list locale /preflight."""
    etat: dict[str, Optional[Salle]] = {"salle": None}
    limite_entree = nouveau_limiteur(600, 60.0)        # 80 téléphones qui scannent en même temps, avec de la marge
    limite_passe = nouveau_limiteur(120, 60.0)         # un téléphone qui relit toutes les 2 s, plus ses gestes

    def actif() -> bool:
        return os.environ.get("HACKVS_SALLE", "1") == "1" and os.environ.get("HACKVS_VISITE") != "1"   # jamais dans le monde « visite »

    def salle() -> Salle:
        if not actif():
            raise HTTPException(404, "Mode salle désactivé (HACKVS_SALLE=0).")
        if etat["salle"] is None:
            etat["salle"] = Salle(secret(), plafond=int(os.environ.get("HACKVS_SALLE_PLAFOND", "80")),
                                  minimum=int(os.environ.get("HACKVS_SALLE_MIN", "5")),
                                  k=max(1, int(os.environ.get("HACKVS_K_ANONYMAT", "3"))))
        assert etat["salle"] is not None
        return etat["salle"]

    def faire(f: Callable[[Salle], dict]) -> dict:
        try:
            return f(salle())
        except ErreurMetier as e:
            raise HTTPException(e.statut_http, str(e)) from None

    def participant(x_pulse_salle: Optional[str] = Header(None)) -> str:
        limiter(limite_passe, "salle|" + (x_pulse_salle or "")[:40])
        faire(lambda s: s.moi(x_pulse_salle or "") and {})
        return x_pulse_salle or ""

    def lien(request: Request, s: Salle) -> dict:
        o = s.ouvrir() if s.ouverte_le is not None else None
        if o is None:
            return {}
        url = base_publique(request) + "/salle#s=" + o["jeton_salle"]
        return {"url": url, "qr": qr(url)}

    def url_courante(request: Request) -> Optional[str]:
        s = etat["salle"]
        if not actif() or s is None or s.ouverte_le is None:
            return None
        return base_publique(request) + "/salle#s=" + s.ouvrir()["jeton_salle"]

    def apercu() -> Optional[dict]:
        s = etat["salle"]
        return None if not actif() or s is None else s.ecran()

    # ------------------------------------------------------------------ téléphones (public : seulement entrer)
    @r.post("/salle/entrer")
    def entrer(x: Entree) -> dict:
        limiter(limite_entree, "salle-entree")
        return faire(lambda s: s.entrer(x.jeton))

    @r.get("/salle/moi")
    def moi(passe: str = Depends(participant)) -> dict:
        return faire(lambda s: s.moi(passe))

    @r.post("/salle/declarer")
    def declarer(x: Capacite, passe: str = Depends(participant)) -> dict:
        return faire(lambda s: s.declarer(passe, x.capacite, x.consentement))

    @r.post("/salle/repondre")
    def repondre(x: Choix, passe: str = Depends(participant)) -> dict:
        return faire(lambda s: s.repondre(passe, x.choix))

    @r.post("/salle/retirer")
    def retirer(passe: str = Depends(participant)) -> dict:
        return faire(lambda s: s.retirer(passe))

    # ------------------------------------------------------------------ écran géant et télécommande (console)
    @r.get("/console/salle/etat", dependencies=[Depends(console)])
    def etat_salle() -> dict:
        return {"actif": actif()}

    @r.post("/console/salle/ouvrir", dependencies=[Depends(console)])
    def ouvrir(request: Request) -> dict:
        return faire(lambda s: (s.ouvrir() and {}) | lien(request, s) | {"plafond": s.plafond})

    @r.get("/console/salle", dependencies=[Depends(console)])
    def ecran(request: Request) -> dict:
        return faire(lambda s: s.ecran() | lien(request, s))

    @r.post("/console/salle/inviter", dependencies=[Depends(console)])
    def inviter() -> dict:
        return faire(lambda s: s.inviter())

    @r.post("/console/salle/lancer", dependencies=[Depends(console)])
    def lancer() -> dict:
        return faire(lambda s: s.lancer())

    @r.post("/console/salle/retrait", dependencies=[Depends(console)])
    def retrait() -> dict:
        return faire(lambda s: s.declencher_retrait())

    @r.post("/console/salle/afficher", dependencies=[Depends(console)])
    def afficher(x: Vue) -> dict:
        return faire(lambda s: s.afficher(x.vue))

    @r.get("/console/salle/bilan", dependencies=[Depends(console)])
    def bilan() -> dict:
        return faire(lambda s: s.bilan())

    @r.post("/console/salle/purger", dependencies=[Depends(console)])
    def purger() -> dict:
        return faire(lambda s: s.purger())

    return url_courante, apercu
