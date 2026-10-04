"""ANNÉE 1 · LOT 2 — Routes des comptes (/api/pulse/comptes/…), montées seulement si HACKVS_COMPTES=1.

Session : en-tête X-Pulse-Compte (jamais un cookie). CSRF : une requête qui annonce une Origin étrangère est refusée
(403) ; sans cookie, un autre site ne peut de toute façon pas faire porter la session par le navigateur. Limite par
session sur les écritures. Seule route publique : accepter une invitation (jeton signé, à usage unique)."""
from __future__ import annotations

import os
from typing import Callable, Literal, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from intelligence.comptes import Comptes
from intelligence.erreurs import ErreurMetier


class Acceptation(BaseModel):
    jeton: str = Field(max_length=200)
    appareil: str = Field(default="appareil", max_length=60)


class Invitation(BaseModel):
    role: Literal["membre", "invite", "secretariat", "administration"]
    etiquette: str = Field(min_length=1, max_length=60)
    duree_s: int = Field(default=7 * 24 * 3600, ge=60, le=30 * 24 * 3600)


class Code(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class Role(BaseModel):
    role: Literal["membre", "invite", "secretariat", "administration"]


def _origine_sure(request: Request) -> None:
    """CSRF : Origin absente (outil, même origine en GET) ou égale à l'hôte servi / à PUBLIC_BASE_URL."""
    origine = request.headers.get("origin")
    if not origine:
        return
    permises = {f"{request.url.scheme}://{request.url.netloc}"}
    if os.environ.get("PUBLIC_BASE_URL"):
        u = urlparse(os.environ["PUBLIC_BASE_URL"])
        permises.add(f"{u.scheme}://{u.netloc}")
    if origine.rstrip("/") not in permises:
        raise HTTPException(403, "origine refusée")


def creer_routeur_comptes(comptes: Callable[[], Comptes]) -> APIRouter:
    r = APIRouter(prefix="/api/pulse/comptes", dependencies=[Depends(_origine_sure)])

    def faire(f: Callable[[], object]) -> object:
        try:
            return f()
        except ErreurMetier as e:
            raise HTTPException(e.statut_http, str(e)) from None

    def session(x_pulse_compte: Optional[str] = Header(None)) -> str:
        if not x_pulse_compte:
            raise HTTPException(401, "session requise")
        faire(lambda: comptes().verifier(x_pulse_compte))
        return x_pulse_compte

    def ecriture(s: str = Depends(session)) -> str:
        faire(lambda: comptes().compter_ecriture(s))
        return s

    def admin(request: Request, s: str = Depends(session)) -> str:
        """ANNÉE 1 · audit des lots 6-8, I2 : les routes d'administration entrent au journal des accès."""
        route = request.scope.get("route")
        faire(lambda: comptes().tracer_acces(s, f"{request.method} {getattr(route, 'path', request.url.path)}"))
        return s

    @r.post("/invitations/accepter")
    def accepter(a: Acceptation) -> dict:
        return {"session": faire(lambda: comptes().accepter(a.jeton, a.appareil))}

    @r.get("/moi")
    def moi(s: str = Depends(session)) -> object:
        return faire(lambda: comptes().verifier(s))

    @r.get("/moi/appareils")
    def appareils(s: str = Depends(session)) -> object:
        return faire(lambda: comptes().mes_appareils(s))

    @r.post("/moi/deconnexion")
    def deconnexion(s: str = Depends(ecriture)) -> dict:
        faire(lambda: comptes().deconnecter(s))
        return {"ok": True}

    @r.post("/moi/appareils/{sid}/deconnexion")
    def deconnexion_appareil(sid: str, s: str = Depends(ecriture)) -> dict:
        faire(lambda: comptes().deconnecter_appareil(s, sid))
        return {"ok": True}

    @r.post("/moi/totp/preparer")
    def totp_preparer(s: str = Depends(ecriture)) -> object:
        return faire(lambda: comptes().preparer_totp(s))

    @r.post("/moi/totp/confirmer")
    def totp_confirmer(c: Code, s: str = Depends(ecriture)) -> dict:
        faire(lambda: comptes().confirmer_totp(s, c.code))
        return {"ok": True}

    @r.post("/moi/elever")
    def elever(c: Code, s: str = Depends(ecriture)) -> dict:
        faire(lambda: comptes().elever(s, c.code))
        return {"ok": True}

    @r.get("/console/moi")
    def console_moi(s: str = Depends(session)) -> object:
        return faire(lambda: comptes().exiger_console(s))

    @r.post("/admin/invitations")
    def inviter(i: Invitation, s: str = Depends(ecriture), _a: str = Depends(admin)) -> object:
        return faire(lambda: comptes().inviter(s, role=i.role, etiquette=i.etiquette, duree_s=i.duree_s))

    @r.post("/admin/comptes/{compte}/role")
    def role(compte: str, x: Role, s: str = Depends(ecriture), _a: str = Depends(admin)) -> dict:
        faire(lambda: comptes().attribuer_role(s, compte, x.role))
        return {"ok": True}

    @r.post("/admin/comptes/{compte}/revoquer")
    def revoquer(compte: str, s: str = Depends(ecriture), _a: str = Depends(admin)) -> dict:
        faire(lambda: comptes().revoquer(s, compte))
        return {"ok": True}

    @r.get("/admin/journal")
    def journal(s: str = Depends(session), _a: str = Depends(admin)) -> object:
        return faire(lambda: comptes().journal_admin(s))

    return r
