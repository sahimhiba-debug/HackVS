"""Demandes d'introduction : machine à états contrôlée par le code, stockage SQLite.

Double consentement : la personne sollicitée accepte ou refuse ; les coordonnées
ne sont partagées qu'après acceptation. En mode démo, la réponse de la personne
sollicitée est SIMULÉE par un bouton explicitement étiqueté. Aucun message n'est envoyé.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

Etat = Literal["demandee", "acceptee", "refusee", "annulee", "rencontre_planifiee", "rencontre_faite", "cloturee"]
Acteur = Literal["demandeur", "cible"]

# (état courant, action) -> (nouvel état, acteur autorisé)
TRANSITIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("demandee", "accepter"): ("acceptee", "cible"),
    ("demandee", "refuser"): ("refusee", "cible"),
    ("demandee", "annuler"): ("annulee", "demandeur"),
    ("acceptee", "planifier"): ("rencontre_planifiee", "demandeur"),
    ("acceptee", "annuler"): ("annulee", "demandeur"),
    ("rencontre_planifiee", "confirmer_rencontre"): ("rencontre_faite", "demandeur"),
    ("rencontre_planifiee", "annuler"): ("annulee", "demandeur"),
    ("rencontre_faite", "cloturer"): ("cloturee", "demandeur"),
}
ETATS_ACTIFS = {"demandee", "acceptee", "rencontre_planifiee", "rencontre_faite"}
RESULTATS = {"utile", "affaire_en_cours", "pas_pertinent"}
LIBELLES = {
    "demandee": "En attente de réponse",
    "acceptee": "Acceptée : coordonnées partagées",
    "refusee": "Déclinée",
    "annulee": "Annulée",
    "rencontre_planifiee": "Rencontre planifiée",
    "rencontre_faite": "Rencontre faite : résultat à noter",
    "cloturee": "Clôturée",
}


class Evenement(BaseModel):
    horodatage: str
    action: str
    acteur: str
    etat: str
    detail: str = ""


class Introduction(BaseModel):
    id: str
    demandeur_id: str
    cible_id: str
    besoin_texte: str
    criteres: list[dict]
    message: str
    etat: Etat
    libelle_etat: str
    coordonnees_partagees: bool
    date_rencontre: Optional[str] = None
    resultat: Optional[str] = None
    historique: list[Evenement]
    simulation: bool = True


class ErreurTransition(Exception):
    pass


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Registre:
    def __init__(self, chemin: Path | str = ":memory:"):
        if chemin != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self._verrou = threading.Lock()
        self._db = sqlite3.connect(str(chemin), check_same_thread=False)
        self._db.execute("""CREATE TABLE IF NOT EXISTS intros (
            id TEXT PRIMARY KEY, donnees TEXT NOT NULL, cree_le TEXT NOT NULL)""")
        self._db.commit()

    def _sauver(self, intro: Introduction, nouveau: bool = False) -> None:
        with self._verrou:
            if nouveau:
                self._db.execute("INSERT INTO intros VALUES (?, ?, ?)", (intro.id, intro.model_dump_json(), _maintenant()))
            else:
                self._db.execute("UPDATE intros SET donnees = ? WHERE id = ?", (intro.model_dump_json(), intro.id))
            self._db.commit()

    def lister(self, demandeur_id: Optional[str] = None) -> list[Introduction]:
        with self._verrou:
            lignes = self._db.execute("SELECT donnees FROM intros ORDER BY cree_le DESC, rowid DESC").fetchall()
        res = [Introduction(**json.loads(l[0])) for l in lignes]
        return [i for i in res if demandeur_id is None or i.demandeur_id == demandeur_id]

    def obtenir(self, intro_id: str) -> Introduction:
        with self._verrou:
            l = self._db.execute("SELECT donnees FROM intros WHERE id = ?", (intro_id,)).fetchone()
        if not l:
            raise KeyError(intro_id)
        return Introduction(**json.loads(l[0]))

    def creer(self, demandeur_id: str, cible_id: str, besoin_texte: str, criteres: list[dict],
              message: str, cible_accepte: bool, cible_eligible: bool) -> Introduction:
        # Garde-fous indépendants de l'interface : même un appel API direct est refusé.
        if demandeur_id == cible_id:
            raise ErreurTransition("Impossible de se présenter à soi-même.")
        if not cible_eligible:
            raise ErreurTransition("Cette personne ne fait pas partie de la communauté du Club.")
        if not cible_accepte:
            raise ErreurTransition("Cette personne ne souhaite pas recevoir d'introductions.")
        if any(i.cible_id == cible_id and i.etat in ETATS_ACTIFS for i in self.lister(demandeur_id)):
            raise ErreurTransition("Une introduction est déjà en cours avec cette personne.")
        if not message.strip():
            raise ErreurTransition("Le message ne peut pas être vide.")
        intro = Introduction(
            id=uuid.uuid4().hex[:10], demandeur_id=demandeur_id, cible_id=cible_id,
            besoin_texte=besoin_texte, criteres=criteres, message=message.strip(),
            etat="demandee", libelle_etat=LIBELLES["demandee"], coordonnees_partagees=False,
            historique=[Evenement(horodatage=_maintenant(), action="demander", acteur="demandeur", etat="demandee")],
        )
        self._sauver(intro, nouveau=True)
        return intro

    def transition(self, intro_id: str, action: str, acteur: str,
                   date_rencontre: Optional[str] = None, resultat: Optional[str] = None) -> Introduction:
        intro = self.obtenir(intro_id)
        cle = (intro.etat, action)
        if cle not in TRANSITIONS:
            raise ErreurTransition(f"Action « {action} » impossible depuis l'état « {intro.libelle_etat} ».")
        nouvel_etat, acteur_autorise = TRANSITIONS[cle]
        if acteur != acteur_autorise:
            raise ErreurTransition(f"Seul·e le/la {acteur_autorise} peut « {action} ».")
        detail = ""
        if action == "planifier":
            if not date_rencontre:
                raise ErreurTransition("Indiquez une date de rencontre.")
            intro.date_rencontre = date_rencontre
            detail = date_rencontre
        if action == "cloturer":
            if resultat not in RESULTATS:
                raise ErreurTransition(f"Résultat attendu parmi : {', '.join(sorted(RESULTATS))}.")
            intro.resultat = resultat
            detail = resultat
        intro.etat = nouvel_etat
        intro.libelle_etat = LIBELLES[nouvel_etat]
        intro.coordonnees_partagees = nouvel_etat in {"acceptee", "rencontre_planifiee", "rencontre_faite", "cloturee"}
        intro.historique.append(Evenement(horodatage=_maintenant(), action=action, acteur=acteur, etat=nouvel_etat, detail=detail))
        self._sauver(intro)
        return intro

    def reinitialiser(self) -> None:
        with self._verrou:
            self._db.execute("DELETE FROM intros")
            self._db.commit()
