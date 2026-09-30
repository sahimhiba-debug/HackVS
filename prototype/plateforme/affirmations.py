"""Registre d'affirmations (Claim Ledger) : ce que le système affirme, d'où ça vient, avec quel statut.

Règles :
- une affirmation a un identifiant DÉTERMINISTE (empreinte de son contenu) : même donnée ⇒ même identifiant ;
- un statut ne change JAMAIS en silence : `changer_statut` exige une raison et respecte la table des transitions ;
- une donnée SYNTHÉTIQUE ou SIMULÉE ne peut jamais devenir VÉRIFIÉE ;
- une affirmation INFÉRÉE ne devient VÉRIFIÉE que par une confirmation humaine ou une source de vérification.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import Enum
from typing import Iterable, Optional

from pydantic import BaseModel, Field


class Statut(str, Enum):
    VERIFIE = "VERIFIE"
    DECLARE = "DECLARE"
    OBSERVE = "OBSERVE"
    INFERE = "INFERE"
    SYNTHETIQUE = "SYNTHETIQUE"
    SIMULE = "SIMULE"
    JOUE = "JOUE"                      # fait par l'équipe (console) à la place d'un personnage absent de la scène
    PROPOSE = "PROPOSE"
    PERIME = "PERIME"
    REJETE = "REJETE"


# Transitions autorisées (toute autre est refusée). PERIME et REJETE sont atteignables depuis tout statut « vivant ».
TRANSITIONS: dict[Statut, set[Statut]] = {
    Statut.PROPOSE: {Statut.INFERE, Statut.DECLARE, Statut.REJETE},
    Statut.INFERE: {Statut.VERIFIE, Statut.REJETE, Statut.PERIME},
    Statut.DECLARE: {Statut.VERIFIE, Statut.REJETE, Statut.PERIME},
    Statut.OBSERVE: {Statut.VERIFIE, Statut.PERIME, Statut.REJETE},
    Statut.VERIFIE: {Statut.PERIME, Statut.REJETE},
    Statut.SYNTHETIQUE: {Statut.REJETE},   # jamais vérifiable : ce n'est pas le monde réel
    Statut.SIMULE: {Statut.REJETE},
    Statut.JOUE: {Statut.REJETE},
    Statut.PERIME: {Statut.DECLARE, Statut.OBSERVE},  # ré-observé
    Statut.REJETE: set(),
}
VERS_VERIFIE_EXIGE = {"confirmation_humaine", "source_de_verification"}


class TransitionInterdite(ValueError):
    pass


class Affirmation(BaseModel):
    sujet: str
    predicat: str
    objet: str
    source: str                       # ex. « profil:p20#offre[0] »
    type_source: str                  # ex. « profil_declaratif », « generateur_synthetique », « modele »
    statut: Statut
    confiance: Optional[float] = Field(default=None, ge=0, le=1)
    extrait: Optional[str] = None     # texte cité mot pour mot, si la source est textuelle
    observe_le: Optional[date] = None
    valide_du: Optional[date] = None
    valide_au: Optional[date] = None
    confirme_par_humain: bool = False
    historique: list[dict] = []

    @property
    def id(self) -> str:
        cle = json.dumps([self.sujet, self.predicat, self.objet, self.source], ensure_ascii=False)
        return "a_" + hashlib.sha256(cle.encode()).hexdigest()[:16]


class Registre:
    def __init__(self, affirmations: Iterable[Affirmation] = ()):
        self._a: dict[str, Affirmation] = {}
        for a in affirmations:
            self.ajouter(a)

    def ajouter(self, a: Affirmation) -> str:
        if a.id in self._a and self._a[a.id].statut != a.statut:
            raise TransitionInterdite(f"{a.id} existe déjà avec le statut {self._a[a.id].statut.value} : "
                                      "utiliser changer_statut, jamais un écrasement silencieux")
        self._a[a.id] = a
        return a.id

    def __len__(self) -> int:
        return len(self._a)

    def get(self, aid: str) -> Affirmation:
        return self._a[aid]

    def __contains__(self, aid: str) -> bool:
        return aid in self._a

    def toutes(self) -> list[Affirmation]:
        return [self._a[k] for k in sorted(self._a)]

    def chercher(self, sujet: Optional[str] = None, predicat: Optional[str] = None, objet: Optional[str] = None) -> list[Affirmation]:
        return [a for a in self.toutes() if (sujet is None or a.sujet == sujet) and (predicat is None or a.predicat == predicat)
                and (objet is None or a.objet == objet)]

    def changer_statut(self, aid: str, nouveau: Statut, raison: str, par: str) -> Affirmation:
        a = self._a[aid]
        if nouveau not in TRANSITIONS[a.statut]:
            raise TransitionInterdite(f"{a.statut.value} → {nouveau.value} interdit ({aid})")
        if nouveau is Statut.VERIFIE and raison not in VERS_VERIFIE_EXIGE:
            raise TransitionInterdite(f"VÉRIFIÉ exige {sorted(VERS_VERIFIE_EXIGE)}, reçu « {raison} »")
        nouvelle = a.model_copy(update={"statut": nouveau, "confirme_par_humain": a.confirme_par_humain or raison == "confirmation_humaine",
                                        "historique": a.historique + [{"de": a.statut.value, "vers": nouveau.value, "raison": raison, "par": par}]})
        self._a[aid] = nouvelle
        return nouvelle

    def perimees(self, jour: date, age_max_jours: int) -> list[str]:
        """Affirmations dont la validité est dépassée ou l'observation trop ancienne."""
        res = []
        for a in self.toutes():
            if a.statut in (Statut.REJETE, Statut.PERIME):
                continue
            if (a.valide_au and a.valide_au < jour) or (a.observe_le and (jour - a.observe_le).days > age_max_jours):
                res.append(a.id)
        return res

    def comptes(self, ids: Optional[Iterable[str]] = None) -> dict[str, int]:
        sel = [self._a[i] for i in ids] if ids is not None else self.toutes()
        c: dict[str, int] = {}
        for a in sel:
            c[a.statut.value] = c.get(a.statut.value, 0) + 1
        return dict(sorted(c.items()))

    def empreinte(self) -> str:
        """Empreinte de l'instantané complet (identique ⇔ mêmes affirmations et statuts)."""
        contenu = json.dumps([a.model_dump(mode="json") | {"id": a.id} for a in self.toutes()], ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(contenu.encode()).hexdigest()

    def exporter(self) -> list[dict]:
        return [a.model_dump(mode="json") for a in self.toutes()]

    @classmethod
    def importer(cls, donnees: list[dict]) -> "Registre":
        return cls(Affirmation(**d) for d in donnees)
