"""Routes du REGISTRE DES CAPACITÉS : un adaptateur mince (valider, authentifier, appeler le service, traduire l'erreur),
branché sur le routeur Club Pulse (mêmes sessions, même verrou par monde, mêmes erreurs typées). Aucune règle ici."""
from __future__ import annotations

from typing import Annotated, Callable, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field


class Reponse(BaseModel):
    oui: bool                                           # « non » et « pas cette fois » : même effet, sans justification
    attributs: dict[Annotated[str, Field(max_length=24)], Annotated[int, Field(ge=0, le=1000)]] = Field(default_factory=dict,
                                                                                                        max_length=4)
    quoi: Optional[str] = Field(default=None, min_length=3, max_length=200)


def ajouter_routes(r: APIRouter, au_monde: Callable, membre: Callable, console: Callable) -> None:
    @r.get("/console/capacites", dependencies=[Depends(console)])
    def registre() -> dict:
        return au_monde(lambda c: c.vues_capacites.console())

    @r.post("/console/capacites/{finalite}/relancer", dependencies=[Depends(console)])
    def relancer(finalite: str) -> dict:
        return au_monde(lambda c: c.vues_capacites.instance(c.relancer_recherche(finalite[:40])))

    @r.post("/console/capacites/{finalite}/acquitter", dependencies=[Depends(console)])
    def acquitter(finalite: str) -> dict:
        return au_monde(lambda c: c.vues_capacites.instance(c.acquitter_recherche(finalite[:40])))

    @r.get("/console/pulse", dependencies=[Depends(console)])
    def pulse(depuis: int = 0, jusqu_a: Optional[int] = None) -> dict:
        return au_monde(lambda c: c.pulse(depuis, jusqu_a))

    @r.get("/moi/asks")
    def mes_asks(pid: str = Depends(membre)) -> list[dict]:
        return au_monde(lambda c: c.vues_capacites.asks(pid))

    @r.post("/moi/asks/{ask_id}/reponse")
    def repondre(ask_id: str, x: Reponse, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.vues_capacites.apres_reponse(c.repondre_ask(pid, ask_id[:120], x.oui, x.attributs, x.quoi)))

    @r.get("/moi/consentements")
    def recus(pid: str = Depends(membre)) -> list[dict]:
        return au_monde(lambda c: c.capacites.recus(pid))

    @r.post("/moi/capacites/{finalite}/retrait")
    def retirer(finalite: str, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.vues_capacites.instance(c.retirer_consentement(pid, finalite[:40])))

    @r.get("/moi/donnees")
    def donnees(pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.vues_capacites.mes_donnees(pid))

    @r.post("/moi/capacites/{finalite}/consentement")
    def consentir(finalite: str, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.vues_capacites.instance(c.consentir_capacite(pid, finalite[:40])))
