"""Magasin unique : besoins, mises en relation, consentements, journal. SQLite.

Toutes les vues (mon besoin, Bourse, suivi, scène) lisent ces mêmes données : les états
restent cohérents. Chaque règle métier est appliquée ICI, pas dans l'interface :
un appel direct à l'API ne peut pas contourner le consentement ou la machine à états.

Cycle de vie d'un BESOIN :
  brouillon ─publier→ publie ─(relation acceptée)→ en_cours ─cloturer→ resolu | retire
  modifier : version+1 (brouillon, publie, en_cours) ; depublier : publie → brouillon

Cycle de vie d'une MISE EN RELATION (initiée par l'auteur du besoin = « demande »,
ou par un membre qui peut aider = « offre ») :
  proposee ─accepter (destinataire)→ acceptee ─planifier→ rencontre_planifiee
           ─confirmer_rencontre→ rencontre_faite ─cloturer→ cloturee
  proposee ─decliner (destinataire)→ declinee ; ─retirer (initiateur)→ retiree
  annulee : par un participant, ou par le SYSTÈME (consentement retiré, besoin clos/dépublié)
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

from .models import Besoin

StatutBesoin = Literal["brouillon", "publie", "en_cours", "resolu", "retire"]
EtatRelation = Literal["proposee", "acceptee", "declinee", "retiree", "annulee",
                       "rencontre_planifiee", "rencontre_faite", "cloturee"]

LIBELLES_BESOIN = {
    "brouillon": "Brouillon (visible par vous seul·e)",
    "publie": "Publié dans la Bourse",
    "en_cours": "En cours : une mise en relation est acceptée",
    "resolu": "Résolu",
    "retire": "Clos sans suite",
}
LIBELLES_RELATION = {
    "proposee": "En attente de réponse",
    "acceptee": "Acceptée : coordonnées partagées",
    "declinee": "Déclinée",
    "retiree": "Retirée",
    "annulee": "Annulée",
    "rencontre_planifiee": "Rencontre planifiée",
    "rencontre_faite": "Rencontre faite : résultat à noter",
    "cloturee": "Clôturée",
}
# (état, action) → (nouvel état, rôle autorisé)
TRANSITIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("proposee", "accepter"): ("acceptee", "destinataire"),
    ("proposee", "decliner"): ("declinee", "destinataire"),
    ("proposee", "retirer"): ("retiree", "initiateur"),
    ("acceptee", "planifier"): ("rencontre_planifiee", "participant"),
    ("acceptee", "annuler"): ("annulee", "participant"),
    ("rencontre_planifiee", "confirmer_rencontre"): ("rencontre_faite", "participant"),
    ("rencontre_planifiee", "annuler"): ("annulee", "participant"),
    ("rencontre_faite", "cloturer"): ("cloturee", "participant"),
}
ETATS_ACTIFS = {"proposee", "acceptee", "rencontre_planifiee", "rencontre_faite"}
ETATS_PARTAGE = {"acceptee", "rencontre_planifiee", "rencontre_faite", "cloturee"}
RESULTATS_RELATION = {"utile", "affaire_en_cours", "pas_pertinent"}


class ErreurMetier(Exception):
    """Action refusée par une règle métier (→ HTTP 409)."""


class Interdit(Exception):
    """Action refusée pour ce membre (→ HTTP 403)."""


class Evenement(BaseModel):
    horodatage: str
    action: str
    acteur: str
    detail: str = ""


class BesoinEnregistre(BaseModel):
    id: str
    auteur_id: str
    besoin: Besoin
    anonyme: bool = False
    statut: StatutBesoin
    libelle_statut: str
    version: int = 1
    resolu_par: Optional[str] = None  # id de la mise en relation qui a résolu le besoin
    note_cloture: str = ""
    historique: list[Evenement]
    cree_le: str
    maj_le: str


class Relation(BaseModel):
    id: str
    besoin_id: str
    besoin_version: int
    auteur_id: str   # auteur du besoin
    aidant_id: str   # membre qui peut aider
    initiateur: Literal["auteur", "aidant"]
    message: str
    etat: EtatRelation
    libelle_etat: str
    coordonnees_partagees: bool = False
    date_rencontre: Optional[str] = None
    resultat: Optional[str] = None
    motif_fin: str = ""
    historique: list[Evenement]
    cree_le: str

    def initiateur_id(self) -> str:
        return self.auteur_id if self.initiateur == "auteur" else self.aidant_id

    def destinataire_id(self) -> str:
        return self.aidant_id if self.initiateur == "auteur" else self.auteur_id


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Magasin:
    def __init__(self, chemin: Path | str = ":memory:"):
        if chemin != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self._verrou = threading.RLock()
        self._db = sqlite3.connect(str(chemin), check_same_thread=False)
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS besoins (id TEXT PRIMARY KEY, donnees TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS relations (id TEXT PRIMARY KEY, donnees TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS consentements (membre_id TEXT PRIMARY KEY, accepte INTEGER NOT NULL, maj_le TEXT);
            CREATE TABLE IF NOT EXISTS profils (membre_id TEXT PRIMARY KEY, donnees TEXT NOT NULL, maj_le TEXT);
            CREATE TABLE IF NOT EXISTS journal (seq INTEGER PRIMARY KEY AUTOINCREMENT, horodatage TEXT,
                type TEXT, acteur TEXT, objet_id TEXT, message TEXT, concerne TEXT);
        """)
        self._db.commit()

    # ------------------------------------------------------------ bas niveau
    def _ecrire(self, table: str, obj: BaseModel) -> None:
        self._db.execute(f"INSERT OR REPLACE INTO {table} (id, donnees) VALUES (?, ?)", (obj.id, obj.model_dump_json()))

    def _journal(self, type_: str, acteur: str, objet_id: str, message: str, concerne: list[str]) -> None:
        self._db.execute("INSERT INTO journal (horodatage, type, acteur, objet_id, message, concerne) VALUES (?,?,?,?,?,?)",
                         (_maintenant(), type_, acteur, objet_id, message, json.dumps(concerne)))

    def journal(self, depuis: int = 0) -> list[dict]:
        with self._verrou:
            lignes = self._db.execute("SELECT seq, horodatage, type, acteur, objet_id, message, concerne FROM journal "
                                      "WHERE seq > ? ORDER BY seq", (depuis,)).fetchall()
        return [{"seq": l[0], "horodatage": l[1], "type": l[2], "acteur": l[3], "objet_id": l[4],
                 "message": l[5], "concerne": json.loads(l[6] or "[]")} for l in lignes]

    def dernier_seq(self) -> int:
        with self._verrou:
            return self._db.execute("SELECT COALESCE(MAX(seq), 0) FROM journal").fetchone()[0]

    # ------------------------------------------------------------ consentement
    def consentement(self, membre_id: str, defaut: bool) -> bool:
        with self._verrou:
            l = self._db.execute("SELECT accepte FROM consentements WHERE membre_id = ?", (membre_id,)).fetchone()
        return defaut if l is None else bool(l[0])

    def consentements(self) -> dict[str, bool]:
        with self._verrou:
            return {m: bool(a) for m, a in self._db.execute("SELECT membre_id, accepte FROM consentements").fetchall()}

    def changer_consentement(self, membre_id: str, accepte: bool) -> list[str]:
        """Retrait : annule les mises en relation EN ATTENTE où le membre est destinataire.
        Les relations déjà acceptées restent (consentement déjà donné) ; il peut les annuler lui-même."""
        annulees: list[str] = []
        with self._verrou:
            self._db.execute("INSERT OR REPLACE INTO consentements VALUES (?, ?, ?)", (membre_id, int(accepte), _maintenant()))
            if not accepte:
                for r in self._relations():
                    if r.etat == "proposee" and r.destinataire_id() == membre_id:
                        self._fin_systeme(r, "annulee", "La personne sollicitée a retiré son consentement aux introductions.")
                        annulees.append(r.id)
            self._journal("consentement", membre_id, membre_id,
                          "Consentement aux introductions " + ("activé" if accepte else "retiré"), [membre_id])
            self._db.commit()
        return annulees

    # ------------------------------------------------------------ profils modifiés par les membres
    def profils_modifies(self) -> dict[str, dict]:
        with self._verrou:
            return {m: json.loads(d) for m, d in self._db.execute("SELECT membre_id, donnees FROM profils").fetchall()}

    def modifier_profil(self, membre_id: str, champs: dict) -> None:
        with self._verrou:
            self._db.execute("INSERT OR REPLACE INTO profils VALUES (?, ?, ?)", (membre_id, json.dumps(champs, ensure_ascii=False), _maintenant()))
            self._journal("profil_modifie", membre_id, membre_id, "Profil mis à jour", [membre_id])
            self._db.commit()

    # ------------------------------------------------------------ besoins
    def _besoins(self) -> list[BesoinEnregistre]:
        return [BesoinEnregistre(**json.loads(l[0])) for l in self._db.execute("SELECT donnees FROM besoins").fetchall()]

    def besoins(self) -> list[BesoinEnregistre]:
        with self._verrou:
            return sorted(self._besoins(), key=lambda b: b.maj_le, reverse=True)

    def besoin(self, besoin_id: str) -> BesoinEnregistre:
        with self._verrou:
            l = self._db.execute("SELECT donnees FROM besoins WHERE id = ?", (besoin_id,)).fetchone()
        if not l:
            raise KeyError(besoin_id)
        return BesoinEnregistre(**json.loads(l[0]))

    def _verifier_auteur(self, b: BesoinEnregistre, membre_id: str) -> None:
        if b.auteur_id != membre_id:
            raise Interdit("Seul·e l'auteur·e du besoin peut faire cette action.")

    def creer_besoin(self, auteur_id: str, besoin: Besoin, publier: bool, anonyme: bool) -> BesoinEnregistre:
        if not any(c.type in ("expertise", "texte_libre") for c in besoin.criteres):
            raise ErreurMetier("Indiquez au moins la compétence recherchée avant d'enregistrer.")
        statut = "publie" if publier else "brouillon"
        t = _maintenant()
        b = BesoinEnregistre(id=uuid.uuid4().hex[:8], auteur_id=auteur_id, besoin=besoin, anonyme=anonyme,
                             statut=statut, libelle_statut=LIBELLES_BESOIN[statut], historique=[
                                 Evenement(horodatage=t, action="creer" + ("_et_publier" if publier else ""), acteur=auteur_id)],
                             cree_le=t, maj_le=t)
        with self._verrou:
            self._ecrire("besoins", b)
            if publier:
                self._journal("besoin_publie", auteur_id, b.id, "Nouveau besoin publié dans la Bourse", [auteur_id])
            self._db.commit()
        return b

    def modifier_besoin(self, besoin_id: str, membre_id: str, besoin: Besoin, anonyme: Optional[bool]) -> BesoinEnregistre:
        with self._verrou:
            b = self.besoin(besoin_id)
            self._verifier_auteur(b, membre_id)
            if b.statut in ("resolu", "retire"):
                raise ErreurMetier("Ce besoin est clos : créez-en un nouveau.")
            if not any(c.type in ("expertise", "texte_libre") for c in besoin.criteres):
                raise ErreurMetier("Indiquez au moins la compétence recherchée.")
            b.besoin, b.version, b.maj_le = besoin, b.version + 1, _maintenant()
            if anonyme is not None:
                b.anonyme = anonyme
            b.historique.append(Evenement(horodatage=b.maj_le, action="modifier", acteur=membre_id, detail=f"version {b.version}"))
            self._ecrire("besoins", b)
            self._journal("besoin_modifie", membre_id, b.id, f"Besoin modifié (version {b.version})", [membre_id])
            self._db.commit()
            return b

    def action_besoin(self, besoin_id: str, membre_id: str, action: str,
                      resolu_par: Optional[str] = None, note: str = "") -> BesoinEnregistre:
        with self._verrou:
            b = self.besoin(besoin_id)
            self._verifier_auteur(b, membre_id)
            if action == "publier":
                if b.statut != "brouillon":
                    raise ErreurMetier("Seul un brouillon peut être publié.")
                b.statut = "publie"
                msg = "Besoin publié dans la Bourse"
            elif action == "depublier":
                if b.statut != "publie":
                    raise ErreurMetier("Seul un besoin publié sans mise en relation acceptée peut être retiré de la Bourse.")
                b.statut = "brouillon"
                for r in self._relations():
                    if r.besoin_id == b.id and r.etat == "proposee" and r.initiateur == "aidant":
                        self._fin_systeme(r, "annulee", "Le besoin a été retiré de la Bourse.")
                msg = "Besoin retiré de la Bourse"
            elif action == "cloturer":
                if b.statut in ("resolu", "retire"):
                    raise ErreurMetier("Ce besoin est déjà clos.")
                if resolu_par:
                    r = self.relation(resolu_par)
                    if r.besoin_id != b.id or r.etat not in ETATS_PARTAGE:
                        raise ErreurMetier("Seule une mise en relation acceptée de ce besoin peut l'avoir résolu.")
                b.statut = "resolu" if resolu_par else "retire"
                b.resolu_par, b.note_cloture = resolu_par, note
                for r in self._relations():
                    if r.besoin_id == b.id and r.etat == "proposee":
                        self._fin_systeme(r, "annulee", "Le besoin a été clos.")
                msg = "Besoin résolu" if resolu_par else "Besoin clos sans suite"
            else:
                raise ErreurMetier(f"Action inconnue : {action}")
            b.libelle_statut, b.maj_le = LIBELLES_BESOIN[b.statut], _maintenant()
            b.historique.append(Evenement(horodatage=b.maj_le, action=action, acteur=membre_id, detail=note))
            self._ecrire("besoins", b)
            concernes = [membre_id] + [r.aidant_id for r in self._relations() if r.besoin_id == b.id]
            self._journal("besoin_" + action, membre_id, b.id, msg, concernes)
            self._db.commit()
            return b

    # ------------------------------------------------------------ mises en relation
    def _relations(self) -> list[Relation]:
        return [Relation(**json.loads(l[0])) for l in self._db.execute("SELECT donnees FROM relations").fetchall()]

    def relations(self, membre_id: Optional[str] = None) -> list[Relation]:
        with self._verrou:
            rs = self._relations()
        rs = [r for r in rs if membre_id is None or membre_id in (r.auteur_id, r.aidant_id)]
        return sorted(rs, key=lambda r: r.cree_le, reverse=True)

    def relation(self, relation_id: str) -> Relation:
        with self._verrou:
            l = self._db.execute("SELECT donnees FROM relations WHERE id = ?", (relation_id,)).fetchone()
        if not l:
            raise KeyError(relation_id)
        return Relation(**json.loads(l[0]))

    def creer_relation(self, besoin_id: str, initiateur_id: str, autre_id: str, message: str,
                       autre_accepte: bool, autre_eligible: bool) -> Relation:
        """Les conditions d'éligibilité (consentement, communauté, correspondance) sont vérifiées
        par l'appelant avec le moteur ; celles propres au cycle de vie sont vérifiées ici."""
        with self._verrou:
            b = self.besoin(besoin_id)
            if b.statut in ("resolu", "retire"):
                raise ErreurMetier("Ce besoin est clos.")
            if initiateur_id == b.auteur_id:
                initiateur, aidant_id = "auteur", autre_id
            else:
                if b.statut == "brouillon":
                    raise ErreurMetier("Ce besoin n'est pas publié.")
                if autre_id != b.auteur_id:
                    raise ErreurMetier("Une offre d'aide s'adresse à l'auteur·e du besoin.")
                initiateur, aidant_id = "aidant", initiateur_id
            if aidant_id == b.auteur_id:
                raise ErreurMetier("Impossible de se mettre en relation avec soi-même.")
            if not autre_eligible:
                raise ErreurMetier("Cette personne ne fait pas partie de la communauté du Club.")
            if not autre_accepte:
                raise ErreurMetier("Cette personne ne souhaite pas recevoir d'introductions.")
            if not message.strip():
                raise ErreurMetier("Le message ne peut pas être vide.")
            if any(r.besoin_id == b.id and r.aidant_id == aidant_id and r.etat in ETATS_ACTIFS for r in self._relations()):
                raise ErreurMetier("Une mise en relation est déjà en cours avec cette personne pour ce besoin.")
            t = _maintenant()
            r = Relation(id=uuid.uuid4().hex[:8], besoin_id=b.id, besoin_version=b.version, auteur_id=b.auteur_id,
                         aidant_id=aidant_id, initiateur=initiateur, message=message.strip(), etat="proposee",
                         libelle_etat=LIBELLES_RELATION["proposee"], cree_le=t,
                         historique=[Evenement(horodatage=t, action="proposer", acteur=initiateur_id)])
            self._ecrire("relations", r)
            texte = "Demande d'introduction envoyée" if initiateur == "auteur" else "Proposition d'aide envoyée"
            self._journal("relation_proposee", initiateur_id, r.id, texte, [b.auteur_id, aidant_id])
            self._db.commit()
            return r

    def transition(self, relation_id: str, action: str, membre_id: str,
                   date_rencontre: Optional[str] = None, resultat: Optional[str] = None) -> Relation:
        with self._verrou:
            r = self.relation(relation_id)
            if membre_id not in (r.auteur_id, r.aidant_id):
                raise Interdit("Vous ne participez pas à cette mise en relation.")
            cle = (r.etat, action)
            if cle not in TRANSITIONS:
                raise ErreurMetier(f"Action « {action} » impossible depuis l'état « {r.libelle_etat} ».")
            nouvel_etat, role = TRANSITIONS[cle]
            if role == "destinataire" and membre_id != r.destinataire_id():
                raise Interdit("Seule la personne sollicitée peut répondre.")
            if role == "initiateur" and membre_id != r.initiateur_id():
                raise Interdit("Seule la personne qui a fait la demande peut la retirer.")
            detail = ""
            if action == "planifier":
                if not date_rencontre:
                    raise ErreurMetier("Indiquez une date de rencontre.")
                r.date_rencontre = detail = date_rencontre
            if action == "cloturer":
                if resultat not in RESULTATS_RELATION:
                    raise ErreurMetier(f"Résultat attendu parmi : {', '.join(sorted(RESULTATS_RELATION))}.")
                r.resultat = detail = resultat
            r.etat, r.libelle_etat = nouvel_etat, LIBELLES_RELATION[nouvel_etat]
            r.coordonnees_partagees = nouvel_etat in ETATS_PARTAGE
            r.historique.append(Evenement(horodatage=_maintenant(), action=action, acteur=membre_id, detail=detail))
            self._ecrire("relations", r)
            if nouvel_etat == "acceptee":
                b = self.besoin(r.besoin_id)
                if b.statut == "publie" or b.statut == "brouillon":
                    b.statut, b.libelle_statut, b.maj_le = "en_cours", LIBELLES_BESOIN["en_cours"], _maintenant()
                    self._ecrire("besoins", b)
            self._journal("relation_" + action, membre_id, r.id, LIBELLES_RELATION[nouvel_etat], [r.auteur_id, r.aidant_id])
            self._db.commit()
            return r

    def _fin_systeme(self, r: Relation, etat: str, motif: str) -> None:
        r.etat, r.libelle_etat, r.motif_fin = etat, LIBELLES_RELATION[etat], motif
        r.coordonnees_partagees = False
        r.historique.append(Evenement(horodatage=_maintenant(), action="annulation_automatique", acteur="systeme", detail=motif))
        self._ecrire("relations", r)
        self._journal("relation_annulee", "systeme", r.id, motif, [r.auteur_id, r.aidant_id])

    # ------------------------------------------------------------ démo
    def retrodater(self, table: str, obj_id: str, cree_le: datetime, maj_le: Optional[datetime] = None) -> None:
        """Démo uniquement : place un objet de l'historique fictif dans le passé."""
        assert table in ("besoins", "relations")
        with self._verrou:
            l = self._db.execute(f"SELECT donnees FROM {table} WHERE id = ?", (obj_id,)).fetchone()
            d = json.loads(l[0])
            d["cree_le"] = cree_le.isoformat(timespec="seconds")
            if maj_le is not None and "maj_le" in d:
                d["maj_le"] = maj_le.isoformat(timespec="seconds")
            self._db.execute(f"UPDATE {table} SET donnees = ? WHERE id = ?", (json.dumps(d, ensure_ascii=False), obj_id))
            self._db.commit()

    def reinitialiser(self) -> None:
        with self._verrou:
            self._db.executescript("DELETE FROM besoins; DELETE FROM relations; DELETE FROM consentements; DELETE FROM profils; DELETE FROM journal;")
            self._journal("reinitialisation", "systeme", "", "Démo réinitialisée", [])
            self._db.commit()
