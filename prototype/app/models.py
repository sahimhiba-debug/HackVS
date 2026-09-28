"""Schémas de données partagés par l'API, le moteur et l'évaluation."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Offre(BaseModel):
    concept: str
    texte: str


class Profil(BaseModel):
    id: str
    nom: str
    fonction: str
    entreprise: str
    commune: str
    type: Literal["membre_club", "exposant", "visiteur"]
    secteurs: list[str] = []
    offre: list[Offre] = []
    recherche: list[Offre] = []
    langues: list[str] = []
    zones_service: list[str] = []
    accepte_introductions: bool = False
    disponible: bool = True
    note_disponibilite: str = ""
    presentation: str = ""
    maj: str = ""


class ProfilPublic(BaseModel):
    """Ce qui peut être montré au demandeur (pas de coordonnées)."""
    id: str
    nom: str
    fonction: str
    entreprise: str
    commune: str
    type: str
    maj: str


class Critere(BaseModel):
    type: Literal["expertise", "langue", "zone"]
    valeur: str
    libelle: str
    obligatoire: bool = True
    extrait: Optional[str] = None  # passage du texte d'origine qui a produit ce critère
    note: Optional[str] = None     # ex. « interprété d'après l'indice : stand »


class OptionAmbiguite(BaseModel):
    valeur: str
    libelle: str


class Ambiguite(BaseModel):
    terme: str
    extrait: str
    options: list[OptionAmbiguite]


class Besoin(BaseModel):
    texte: str = ""
    criteres: list[Critere] = []
    exclure_concurrents: bool = False
    inclure_exposants: bool = False
    ambiguites: list[Ambiguite] = []
    contexte: list[str] = []  # éléments exprimés mais non vérifiables dans les profils
    analyseur: str = "regles"
    avertissements: list[str] = []


class Preuve(BaseModel):
    critere: str
    champ: Literal["offre", "presentation", "langues", "zones_service", "recherche"]
    extrait: str
    nature: Literal["declare", "deduit"]


class Suggestion(BaseModel):
    profil: ProfilPublic
    niveau: Literal["forte", "partielle"]
    preuves: list[Preuve]
    a_verifier: list[str] = []
    reciprocite: Optional[Preuve] = None
    score: float = Field(description="Score interne de classement, non affiché comme pourcentage")


class Ecart(BaseModel):
    raison: str
    nombre: int


class Resultat(BaseModel):
    mode: str
    suggestions: list[Suggestion]
    abstention: bool
    message: str = ""
    pistes_elargies: list[Suggestion] = []
    ecartes: list[Ecart] = []
    nb_profils_examines: int = 0
    duree_ms: float = 0.0
