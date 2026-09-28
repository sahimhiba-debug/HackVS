"""Spécification de décision : le problème formel, typé et inspectable AVANT toute exécution.

Le cœur est générique : les objectifs et contraintes AUTORISÉS sont déclarés par l'adaptateur de domaine
(`Domaine`). Une spécification qui cite un terme inconnu est refusée (L0), jamais « interprétée ».
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .affirmations import Statut


class Terme(BaseModel):
    nom: str
    description: str


class Domaine(BaseModel):
    """Vocabulaire formel d'un domaine, fourni par un adaptateur."""
    nom: str
    objectifs: dict[str, Terme]
    contraintes: dict[str, Terme]
    contraintes_obligatoires: list[str] = []      # la politique les impose : impossible de les retirer
    parametres: dict[str, tuple[int, int]] = {}   # nom → (min, max)


class Objectif(BaseModel):
    nom: str
    sens: Literal["maximiser"] = "maximiser"
    poids: float = Field(1.0, ge=0, le=10)


class PolitiquePreuve(BaseModel):
    statuts_admis: list[Statut] = [Statut.VERIFIE, Statut.DECLARE]
    preuves_minimum_par_proposition: int = Field(1, ge=1)
    age_max_jours: int = Field(365, ge=1)


class SpecDecision(BaseModel):
    intention: str
    domaine: str
    objectifs: list[Objectif]
    contraintes_dures: list[str]
    parametres: dict[str, int] = {}
    politique_preuve: PolitiquePreuve = PolitiquePreuve()
    revue_humaine_pour: list[str] = ["information_privee", "affirmation_non_soutenue", "conflit_objectifs"]
    sortie_attendue: Literal["plan", "frontiere_pareto"] = "frontiere_pareto"

    @model_validator(mode="after")
    def _non_vide(self):
        if not self.objectifs:
            raise ValueError("au moins un objectif")
        return self


class ErreurSpec(ValueError):
    pass


def valider(spec: SpecDecision, domaine: Domaine) -> SpecDecision:
    """L0 : conformité au vocabulaire du domaine et à la politique (contraintes obligatoires présentes)."""
    if spec.domaine != domaine.nom:
        raise ErreurSpec(f"domaine {spec.domaine!r} ≠ {domaine.nom!r}")
    inconnus = [o.nom for o in spec.objectifs if o.nom not in domaine.objectifs]
    inconnus += [c for c in spec.contraintes_dures if c not in domaine.contraintes]
    if inconnus:
        raise ErreurSpec(f"termes inconnus du domaine : {inconnus}")
    manquantes = [c for c in domaine.contraintes_obligatoires if c not in spec.contraintes_dures]
    if manquantes:
        raise ErreurSpec(f"contraintes imposées par la politique, non retirables : {manquantes}")
    for k, v in spec.parametres.items():
        if k not in domaine.parametres:
            raise ErreurSpec(f"paramètre inconnu : {k}")
        lo, hi = domaine.parametres[k]
        if not lo <= v <= hi:
            raise ErreurSpec(f"{k}={v} hors de [{lo}, {hi}]")
    return spec


def resume(spec: SpecDecision) -> dict:
    return {"objectifs": {o.nom: o.poids for o in spec.objectifs}, "contraintes_dures": spec.contraintes_dures,
            "parametres": spec.parametres, "statuts_admis": [s.value for s in spec.politique_preuve.statuts_admis]}


Decision = Literal["AGIR", "S_ABSTENIR", "DEMANDER_PLUS_DE_PREUVES", "ESCALADER_A_L_HUMAIN"]


class ResultatCompilation(BaseModel):
    decision: Decision
    spec: Optional[SpecDecision] = None
    reconnu: list[str] = []
    non_reconnu: list[str] = []
    raison: str = ""
    compilateur: str = "grammaire"
