"""Le modèle du réseau : seulement les objets qui portent un comportement observable.

- `Reseau`      : l'état observé à une date (membres, besoins actifs, événements, journal des faits).
- `Signal`      : un fait daté et sourcé qui justifie une opportunité (jamais un score).
- `Opportunite` : ce que le réseau POURRAIT faire maintenant : déclencheur, preuves, personnes, capacités, manque,
                  action proposée, consentements requis, confiance expliquée.
Les essais, observations et confirmations sont des ÉVÉNEMENTS du journal du banc d'essai (`essai.Banc`) : leur état
et la mémoire du Club (`memoire_club`) en sont toujours dérivés, jamais stockés deux fois.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel

from app.models import Besoin, Profil
from plateforme.memoire import Memoire

TypeOpportunite = Literal["LATENTE", "SUIVI", "COMPOSITION", "COMPLEMENTARITE", "CONVERGENCE", "CAPACITE_DORMANTE", "LACUNE",
                          "MEMOIRE"]


@dataclass(frozen=True)
class BesoinActif:
    id: str
    auteur: str
    texte: str
    le: date
    besoin: Besoin
    anonyme: bool = False


@dataclass(frozen=True)
class Evenement:
    id: str
    nom: str
    le: date
    themes: tuple[str, ...]
    participants: tuple[str, ...]


@dataclass
class Reseau:
    profils: list[Profil]
    besoins: list[BesoinActif]
    evenements: list[Evenement]
    memoire: Memoire
    aujourd_hui: date
    nom: str = "Club fictif"
    fictif: bool = True
    _par_id: dict[str, Profil] = field(default_factory=dict, repr=False)
    _source: Optional[list] = field(default=None, repr=False)

    def par_id(self) -> dict[str, Profil]:
        """Index recalculé dès que la LISTE est remplacée (toute mise à jour de profil remplace la liste)."""
        if self._source is not self.profils or len(self._par_id) != len(self.profils):
            self._par_id = {p.id: p for p in self.profils}
            self._source = self.profils
        return self._par_id


class Signal(BaseModel):
    """Un fait qui fonde une opportunité : QUI, QUOI (extrait exact), D'OÙ (source), QUAND."""
    source: Literal["offre", "recherche", "besoin", "evenement", "relation", "memoire", "reseau"]
    membre: Optional[str] = None
    extrait: str
    le: Optional[str] = None


class Role(BaseModel):
    membre: str
    role: str                 # « bénéficiaire », « contributeur : Traduction », « participant »…
    concept: Optional[str] = None
    preuve: Optional[str] = None


class Contrainte(BaseModel):
    libelle: str
    statut: Literal["respectee", "a_verifier", "bloquante"]


class Opportunite(BaseModel):
    id: str
    type: TypeOpportunite
    titre: str
    declencheur: str
    pourquoi_maintenant: Optional[str] = None
    signaux: list[Signal]
    roles: list[Role]
    capacites: list[str]
    manque: list[str] = []
    contraintes: list[Contrainte] = []
    action: str
    raisonnement: list[str] = []       # « pourquoi » numéroté, construit UNIQUEMENT à partir des signaux et des règles
    risques: list[str] = []            # pourquoi cela pourrait échouer (dit avant d'agir)
    consentements: list[str]           # membres dont l'accord est requis AVANT toute exposition
    confiance: Literal["elevee", "moyenne", "faible"]
    confiance_raisons: list[str]
    demandes_servies: int
    personnes_a_solliciter: int
    besoin_id: Optional[str] = None
    beneficiaire: Optional[str] = None
    evenement: Optional[str] = None
    mecanismes: list[str] = []         # autres mécanismes qui ont trouvé la même opportunité (dédoublonnage)
