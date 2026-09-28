"""Routes de l'espace de décision (plateforme générique + adaptateur Club). Mode démo uniquement : les exécutions
contiennent des instantanés de profils, qui ne doivent pas être exposés sans authentification en mode réel."""
from __future__ import annotations

import json
from typing import Callable, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from adaptateurs.club.adaptateur import AdaptateurClub
from plateforme import action as ac
from plateforme import pipeline as pl
from plateforme.certificat import certificat
from plateforme.execution import Journal
from plateforme.specification import ErreurSpec

from .models import Profil
from .taxonomy import DATA_DIR, Taxonomie

ETATS_RELATION = ("acceptee", "rencontre_planifiee", "rencontre_faite", "cloturee")


class Demande(BaseModel):
    demande: str = Field(min_length=1, max_length=500)
    donnees: Literal["club", "synthetique"] = "club"


class Branche(BaseModel):
    retirer_contraintes: list[str] = []
    ajouter_contraintes: list[str] = []
    parametres: dict[str, int] = {}


class Stress(BaseModel):
    n: int = Field(2, ge=1, le=10)
    regle: Literal["articulation", "aleatoire"] = "articulation"
    graine: int = 0


def creer_routeur(profils_effectifs: Callable[[], list[Profil]], magasin, tax: Taxonomie, chemin_journal: str) -> APIRouter:
    r = APIRouter(prefix="/api/decisions", tags=["décisions"])
    journal = Journal(chemin_journal)

    def club():
        rel = [(x.auteur_id, x.aidant_id) for x in magasin.relations() if x.etat in ETATS_RELATION]
        return profils_effectifs(), magasin.besoins(), rel, "demo"

    def synthetique():
        brut = json.loads((DATA_DIR / "profils_synthetiques.json").read_text(encoding="utf-8"))
        return [Profil(**p) for p in brut["profils"]], [], [], "synthetique"

    adaptateurs = {"club": AdaptateurClub(club, tax), "synthetique": AdaptateurClub(synthetique, tax)}

    def ad_de(run_id: str) -> AdaptateurClub:
        try:
            run = journal.lire(run_id)
        except KeyError:
            raise HTTPException(404, "Exécution inconnue.") from None
        if not run.instantane_empreinte:          # abstention / escalade : aucun instantané consommé
            return adaptateurs["club"]
        source = journal.instantane(run.instantane_empreinte)["source"]
        return adaptateurs["synthetique" if source == "synthetique" else "club"]

    def vue(run, extra: dict | None = None) -> dict:
        return {"run": run.model_dump(), "certificat": certificat(run)} | (extra or {})

    @r.post("")
    def executer(d: Demande):
        run = pl.executer(adaptateurs[d.donnees], d.demande, journal)
        return vue(run)

    @r.get("")
    def lister():
        return journal.liste()

    @r.get("/{run_id}")
    def lire(run_id: str):
        ad_de(run_id)
        return vue(journal.lire(run_id))

    @r.get("/{run_id}/certificat")
    def cert(run_id: str):
        ad_de(run_id)
        return certificat(journal.lire(run_id))

    @r.post("/{run_id}/rejouer")
    def rejouer(run_id: str):
        return pl.rejouer(ad_de(run_id), journal, run_id)

    @r.post("/{run_id}/branche")
    def branche(run_id: str, b: Branche):
        ad = ad_de(run_id)
        if not journal.lire(run_id).spec:
            raise HTTPException(409, "Exécution sans spécification : rien à brancher.")
        try:
            enfant, d = pl.contrefactuel(ad, journal, run_id, b.model_dump())
        except ErreurSpec as e:
            raise HTTPException(422, str(e)) from None
        return vue(enfant, {"delta": d})

    @r.post("/{run_id}/stress")
    def stress(run_id: str, s: Stress):
        ad = ad_de(run_id)
        if not journal.lire(run_id).spec:
            raise HTTPException(409, "Exécution sans spécification : rien à éprouver.")
        enfant, d = pl.stress(ad, journal, run_id, s.n, s.regle, s.graine)
        return vue(enfant, {"stress": d})

    @r.post("/{run_id}/decision")
    def decision_humaine(run_id: str, d: ac.DecisionHumaine):
        ad_de(run_id)
        try:
            return vue(ac.decider(journal, run_id, d))
        except ac.ErreurAction as e:
            raise HTTPException(409, str(e)) from None

    @r.get("/{run_id}/action/apercu")
    def apercu_action(run_id: str):
        ad_de(run_id)
        run = journal.lire(run_id)
        return ac.apercu(run, ac.noms_depuis(journal, run))

    @r.post("/{run_id}/action")
    def executer_action(run_id: str):
        ad_de(run_id)
        run = journal.lire(run_id)
        try:
            return ac.executer(journal, run_id, ac.noms_depuis(journal, run))
        except ac.ErreurAction as e:
            raise HTTPException(409, str(e)) from None

    @r.get("/{run_id}/arbre")
    def arbre(run_id: str):
        ad_de(run_id)
        return journal.arbre(run_id)

    return r
