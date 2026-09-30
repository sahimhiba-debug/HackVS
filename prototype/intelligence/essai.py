"""Banc d'essai partagé — la tranche du pivot.

Une personne (le PORTEUR) pose une question concrète sur un objet. D'autres membres ont publié des OFFRES volontaires :
ce qu'ils acceptent éventuellement de fournir (quelques minutes, un lieu, un objet, une compétence), à quelles
conditions, pendant quelle période, combien de fois. Le système prépare un PROTOCOLE versionné (qui fait quel geste,
combien de temps, avec quel critère d'observation) ; chacun accepte SA part d'une version précise (ACCORD lié à une
empreinte de sa portée). Quand une condition change, ce qui n'est plus couvert est invalidé, ce qui l'est encore est
préservé, une alternative admissible est proposée au porteur — ou l'impossibilité est reconnue. L'essai a lieu ; la
contribution est CONSTATÉE (ce n'est pas un succès) ; une OBSERVATION est déclarée par une personne, avec sa portée,
confirmable ou contestable ; sa réutilisation dépend d'un DROIT explicite de chacun.

Invariants (testés, tests/test_essai.py) :
  - aucun lancement sans accord valable de chaque personne, pour la version courante, au moment du lancement ;
  - aucune disponibilité inventée : seules les offres publiées, actives à la date, avec capacité restante, servent ;
  - aucun accord déduit du silence ; aucun succès déduit du silence (échéance → EXPIRE ou RESULTAT_INCONNU) ;
  - aucune offre réservée au-delà de sa capacité ; un accord ne suit jamais une autre personne ni une autre portée ;
  - un refus n'est jamais redemandé à la même personne pour cet essai ;
  - aucune observation plus visible que ce que TOUS les participants concernés ont autorisé ;
  - le modèle de langage ne décide d'aucune transition (il ne fait que proposer un brouillon).

Source de vérité : le journal (ajout seul). L'état est le REPLI des événements : relire = reconstruire, sans effet.
Les notes privées n'y sont pas. Horloge : un paramètre (`aujourd_hui`), jamais `date.today()`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Callable, Iterator, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

from .erreurs import Conflit, Interdit, Introuvable, Invalide

Nature = Literal["temps", "lieu", "objet", "competence"]
NATURES: dict[str, str] = {"temps": "quelques minutes", "lieu": "un lieu", "objet": "un objet", "competence": "une compétence"}
Qualification = Literal["positif", "negatif", "mitige", "non_concluant"]
QUALIFICATIONS = ("positif", "negatif", "mitige", "non_concluant")
Niveau = Literal["moi", "participants", "club"]
NIVEAUX = ("moi", "participants", "club")
TRANSITIONS: dict[str, set[str]] = {
    "": {"BROUILLON"},
    "BROUILLON": {"PROPOSE", "ANNULE"},
    "PROPOSE": {"PROPOSE", "AUTORISE", "A_ADAPTER", "IMPOSSIBLE", "ANNULE", "EXPIRE"},
    "AUTORISE": {"PROPOSE", "EN_COURS", "A_ADAPTER", "IMPOSSIBLE", "ANNULE", "EXPIRE"},
    "A_ADAPTER": {"PROPOSE", "AUTORISE", "IMPOSSIBLE", "ANNULE", "EXPIRE"},
    "EN_COURS": {"CONTRIBUTION_RECUE", "A_ADAPTER", "IMPOSSIBLE", "ANNULE", "RESULTAT_INCONNU"},
    "CONTRIBUTION_RECUE": {"OBSERVEE", "RESULTAT_INCONNU"},
    "RESULTAT_INCONNU": {"OBSERVEE"},               # une observation tardive reste possible, et datée comme telle
    # BLOQUÉ, pas terminé : un fait nouveau sur une offre peut rouvrir une ADAPTATION — jamais un lancement direct. Le
    # porteur choisit, les personnes concernées reconfirment. À l'échéance, l'essai expire.
    "IMPOSSIBLE": {"A_ADAPTER", "ANNULE", "EXPIRE"},
}
FINAUX = {"ANNULE", "EXPIRE", "OBSERVEE"}
MAX_GESTES = 4                                         # un essai reste petit : au plus 4 gestes, donc 4 personnes sollicitées
AVANT_LANCEMENT = {"BROUILLON", "PROPOSE", "AUTORISE", "A_ADAPTER"}
# une part À REDEMANDER (réponse attendue, portée changée) n'est pas une part PERDUE (refus, retrait, offre qui ne
# couvre plus) : la première attend une décision, la seconde exige une adaptation ou un arrêt
CONDITIONS_A_RECONFIRMER = "les conditions de son offre ont changé : à reconfirmer"
A_REDEMANDER = {"en attente de sa réponse", "à confirmer", "sa part a changé depuis son accord",
                "le protocole a changé depuis votre confirmation", CONDITIONS_A_RECONFIRMER}
CONDITIONS_CHANGEES = "les conditions de son offre ont changé depuis son accord"
DELAI_OBSERVATION_JOURS = 14                          # sans observation 14 j après l'échéance : RÉSULTAT INCONNU
_journal = logging.getLogger("intelligence.essai")
PARTAGE = ("Si vous acceptez : votre nom et votre organisation sont communiqués au porteur et aux autres participants "
           "qui ont accepté ; l'observation reste entre participants, sauf droit de réutilisation donné par CHACUN.")


# ---------------------------------------------------------------------- le temps (créneaux au quart d'heure)
HEURE = r"^([01]\d|2[0-3]):[0-5]\d$"
PAS_MIN = 15                                           # recherche de créneaux : au quart d'heure


def minutes(h: str) -> int:
    return int(h[:2]) * 60 + int(h[3:])


def heure(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


class Plage(BaseModel):
    """Une disponibilité DÉCLARÉE : ce jour, de `debut` à `fin` (heure locale du Club)."""
    jour: date
    debut: str = Field(pattern=HEURE)
    fin: str = Field(pattern=HEURE)

    @model_validator(mode="after")
    def _ordre(self) -> "Plage":
        if minutes(self.fin) <= minutes(self.debut):
            raise ValueError("une plage se termine après avoir commencé")
        return self

    def contient(self, c: "Creneau") -> bool:
        return self.jour == c.jour and minutes(self.debut) <= minutes(c.debut) and minutes(c.debut) + c.duree_min <= minutes(self.fin)

    def texte(self) -> str:
        return f"{self.jour.strftime('%d.%m')} {self.debut}–{self.fin}"


class Creneau(BaseModel):
    """LE moment où l'action collective a lieu. Il fait partie de ce que chacun accepte : le déplacer redemande l'accord."""
    jour: date
    debut: str = Field(pattern=HEURE)
    duree_min: int = Field(ge=5, le=240)

    @property
    def fin(self) -> str:
        return heure(minutes(self.debut) + self.duree_min)

    def texte(self) -> str:
        return f"{self.jour.strftime('%d.%m')} {self.debut}–{self.fin}"


# ---------------------------------------------------------------------- objets (validés à la frontière)
class Etape(BaseModel):
    id: str = Field(max_length=8)
    nature: Nature
    geste: str = Field(min_length=3, max_length=200)                  # ce que la personne fait concrètement
    duree_min: int = Field(ge=1, le=120)
    contributeur: Optional[str] = Field(default=None, max_length=32)
    offre_id: Optional[str] = Field(default=None, max_length=32)
    # SUR INVITATION : la personne est nommée par une opportunité détectée, sans offre publiée. Aucune disponibilité
    # n'est supposée : c'est SON acceptation qui la déclare (une offre personnelle, pour ce seul essai, modifiable).
    invitation: bool = False
    # la CAPACITÉ demandée (catalogue du Club), quand le geste vient d'une opportunité détectée : seule une offre qui
    # déclare cette capacité peut le porter ou le remplacer (on ne remplace pas un conseil export par une fiduciaire).
    # None : un geste libre (« quelques minutes de regard neuf ») — toute offre de même nature convient.
    concept: Optional[str] = Field(default=None, max_length=64)
    # un résultat CONCRET que la personne transmet (ex. « Fiche produit en allemand ») ; reçu seulement quand le
    # destinataire (le porteur) en confirme la réception — jamais parce qu'il a été envoyé
    livrable: Optional[str] = Field(default=None, max_length=120)
    role: Optional[str] = Field(default=None, max_length=24)        # « voix », « lieu », « public »… : ce que le geste REMPLIT


class Protocole(BaseModel):
    question: str = Field(min_length=3, max_length=300)               # ce que nous essayons de savoir
    objet: str = Field(default="", max_length=120)                    # l'objet, le support ou l'usage concerné
    pourquoi: str = Field(default="", max_length=300)                 # contexte (modifiable sans redemander d'accord)
    critere: str = Field(default="", max_length=300)                  # ce qu'on observera, et comment on le lira
    echeance: date
    etapes: list[Etape] = Field(default_factory=list, max_length=MAX_GESTES)
    # d'où vient cet essai (opportunité détectée : identifiant, type, capacités) — sert la MÉMOIRE, jamais une décision
    origine: Optional[dict] = None
    # QUAND : la fenêtre acceptable pour le porteur, le créneau retenu (engageant), et la durée en dessous de laquelle
    # le résultat annoncé ne tient plus (une variante plus courte n'est jamais proposée sous ce seuil)
    fenetre: Optional[Plage] = None
    creneau: Optional[Creneau] = None
    duree_min_acceptable: Optional[int] = Field(default=None, ge=5, le=240)

    @model_validator(mode="after")
    def _coherence(self) -> "Protocole":
        if self.creneau is not None:
            if self.creneau.jour > self.echeance:
                raise ValueError("le créneau tombe après l'échéance")
            if any(e.duree_min > self.creneau.duree_min for e in self.etapes):
                raise ValueError("un geste dure plus longtemps que le créneau")
        return self


class OffreVolontaire(BaseModel):
    id: str
    auteur: str
    nature: Nature
    quoi: str = Field(min_length=3, max_length=200)
    duree_max_min: Optional[int] = Field(default=None, ge=1, le=240)  # None : sans durée (un objet, un lieu prêté)
    capacite: int = Field(ge=1, le=20)                                # nombre d'essais qu'elle peut servir au total
    du: date
    au: date
    conditions: str = Field(default="", max_length=300)
    version: int = 1
    pour_essai: Optional[str] = None                                  # offre personnelle déclarée EN acceptant un essai
    pour_etape: Optional[str] = None
    concept: Optional[str] = Field(default=None, max_length=64)       # capacité déclarée que l'offre met à disposition
    plages: list[Plage] = Field(default_factory=list, max_length=8)   # horaires DÉCLARÉS (vide : aucun horaire connu)


def _mots(t: str) -> set[str]:
    return set(re.findall(r"[a-zà-ÿ]{4,}", t.lower()))


def _empreinte(x: object) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]


def portee(p: Protocole, porteur: str, membre: str) -> dict:
    """Ce qu'une personne accepte. Le porteur : tout le protocole (sauf le « pourquoi », pure explication).
    Un contributeur : la question, l'objet, le critère, l'échéance, SES gestes et ce qui sera partagé. Une modification
    hors de sa portée (le geste d'un autre, un mot du contexte) ne lui redemande rien ; toute modification dedans, si."""
    if membre == porteur:
        return {"porteur": True, **p.model_dump(mode="json", exclude={"pourquoi"})}
    return {"question": p.question, "objet": p.objet, "critere": p.critere, "echeance": p.echeance.isoformat(), "partage": PARTAGE,
            "creneau": p.creneau.model_dump(mode="json") if p.creneau else None,
            "gestes": [e.model_dump(mode="json", include={"nature", "geste", "duree_min", "offre_id", "invitation", "concept", "livrable"})
                       for e in p.etapes if e.contributeur == membre]}


class Banc:
    """Commandes (atomiques) et lectures (replis purs) du banc d'essai. Aucune règle d'accès aux NOMS ici : les vues."""

    def __init__(self, memoire: Memoire, aujourd_hui: Callable[[], date], organisation: Callable[[str], str],
                 eligibilite: Optional[Callable[[str, str], Optional[str]]] = None):
        """`eligibilite(porteur, candidat)` : pourquoi ce candidat ne peut PAS être sollicité pour ce porteur (None : il
        peut l'être). Fournie par la composition à partir des règles dures du réseau (langue commune, refus des
        sollicitations, disponibilité, introduction déjà déclinée…) : une seule source de vérité pour ces règles."""
        self.m, self._jour, self._org = memoire, aujourd_hui, organisation
        self._eligibilite = eligibilite or (lambda porteur, candidat: None)
        self._origine: Statut = Statut.DECLARE

    # ------------------------------------------------------------------ journal
    @contextmanager
    def origine(self, statut: Statut) -> Iterator[None]:
        """D'où viennent les faits écrits dans ce bloc : SYNTHETIQUE (données préparées), JOUE (console de démonstration).
        Par défaut, DECLARE : saisi par la personne elle-même."""
        avant, self._origine = self._origine, statut
        try:
            yield
        finally:
            self._origine = avant

    def _ecrire(self, type_: str, acteurs: list[str], statut: Optional[Statut] = None, **donnees) -> None:
        statut = statut or self._origine                      # ESSAI_ETAT, ADAPTATION : calculés par le moteur (statut propre)
        self.m.ajouter(Evt(type=type_, le=self._jour(), acteurs=acteurs, statut=statut,
                           donnees=donnees | {"n": len(self.m.evenements())}))    # deux gestes identiques restent deux faits

    def _evs(self, eid: str, *types: str) -> list[Evt]:
        return [e for e in self.m.evenements(*types) if e.donnees.get("essai") == eid]

    # ------------------------------------------------------------------ offres volontaires
    def publier_offre(self, auteur: str, nature: str, quoi: str, capacite: int, du: date, au: date,
                      duree_max_min: Optional[int] = None, conditions: str = "", pour: Optional[tuple[str, str]] = None,
                      concept: Optional[str] = None, plages: Optional[list[Plage]] = None) -> str:
        if au < du:
            raise Invalide("la période de l'offre se termine avant de commencer")
        oid = "of-" + _empreinte([auteur, quoi, len(self.m.evenements())])[:8]
        o = OffreVolontaire(id=oid, auteur=auteur, nature=nature, quoi=quoi, capacite=capacite, du=du, au=au,  # type: ignore[arg-type]
                            duree_max_min=duree_max_min, conditions=conditions,
                            pour_essai=pour[0] if pour else None, pour_etape=pour[1] if pour else None, concept=concept,
                            plages=plages or [])
        with self.m.transaction():
            self._ecrire("OFFRE", [auteur], offre=o.model_dump(mode="json"))
            if not pour:                                      # une offre publique nouvelle peut débloquer un essai bloqué
                self._revoir_essais_de_l_offre(oid, f"{self._nom_offre(o)} : nouvelle offre publiée")
        return oid

    def offre(self, oid: str) -> OffreVolontaire:
        evs = [e for e in self.m.evenements("OFFRE") if e.donnees["offre"]["id"] == oid]
        if not evs:
            raise Introuvable("offre inconnue")
        return OffreVolontaire(**evs[-1].donnees["offre"])

    def offres(self, publiques: bool = False) -> list[OffreVolontaire]:
        """`publiques=True` : seulement les offres ouvertes à tout essai (pas celles déclarées pour un essai précis)."""
        dernieres: dict[str, dict] = {}                          # un seul passage : la dernière version de chaque offre
        for e in self.m.evenements("OFFRE"):
            dernieres[e.donnees["offre"]["id"]] = e.donnees["offre"]
        return [o for o in (OffreVolontaire(**d) for d in dernieres.values()) if not (publiques and o.pour_essai)]

    def offre_de(self, eid: str, e: Etape) -> Optional[OffreVolontaire]:
        """L'offre qui porte ce geste : l'offre choisie, ou — sur invitation — celle que la personne a déclarée EN
        acceptant (None tant qu'elle n'a pas accepté : sa disponibilité est alors INCONNUE)."""
        if e.offre_id:
            return self.offre(e.offre_id)
        if e.invitation and e.contributeur:
            miennes = [o for o in self.offres() if o.auteur == e.contributeur and o.pour_essai == eid and o.pour_etape == e.id]
            return miennes[-1] if miennes else None
        return None

    def etat_offre(self, oid: str) -> str:
        if any(e.donnees["offre"] == oid for e in self.m.evenements("OFFRE_RETIREE")):
            return "retiree"
        o, j = self.offre(oid), self._jour()
        return "expiree" if o.au < j else ("a_venir" if o.du > j else "active")

    def modifier_offre(self, auteur: str, oid: str, **champs) -> list[str]:
        """L'auteur change SES conditions (ex. « je n'ai plus que 5 minutes »). Renvoie les essais à adapter."""
        o = self.offre(oid)
        if o.auteur != auteur:
            raise Interdit("seul l'auteur modifie son offre")
        if self.etat_offre(oid) == "retiree":
            raise Conflit("offre retirée")
        nouvelle = OffreVolontaire(**(o.model_dump() | {k: v for k, v in champs.items() if v is not None} | {"version": o.version + 1}))
        with self.m.transaction():
            self._ecrire("OFFRE", [auteur], offre=nouvelle.model_dump(mode="json"))
            return self._revoir_essais_de_l_offre(oid, f"{self._nom_offre(nouvelle)} : conditions modifiées par son auteur")

    def retirer_offre(self, auteur: str, oid: str) -> list[str]:
        o = self.offre(oid)
        if o.auteur != auteur:
            raise Interdit("seul l'auteur retire son offre")
        with self.m.transaction():
            self._ecrire("OFFRE_RETIREE", [auteur], offre=oid)
            return self._revoir_essais_de_l_offre(oid, f"{self._nom_offre(o)} : offre retirée par son auteur")

    @staticmethod
    def _nom_offre(o: OffreVolontaire) -> str:
        return f"« {o.quoi} »"

    def reservations(self, oid: str, sauf: Optional[str] = None) -> int:
        """Essais qui utilisent cette offre avec un accord valable, ou dont la contribution a été reçue (consommée)."""
        n = 0
        for eid in self.essais():
            if eid == sauf:
                continue
            etat, p, porteur = self.etat(eid), self.protocole(eid), self.porteur(eid)
            for e in p.etapes:
                o = self.offre_de(eid, e) if e.contributeur else None
                if o is None or o.id != oid or e.contributeur is None:
                    continue
                recue = any(x.donnees["etape"] == e.id for x in self._evs(eid, "CONTRIBUTION"))
                if recue or (etat not in FINAUX and etat != "IMPOSSIBLE" and self._accord_donne(eid, e.contributeur, p, porteur)):
                    n += 1
        return n

    def offre_couvre(self, o: OffreVolontaire, e: Etape, echeance: date, sauf: Optional[str] = None,
                     creneau: Optional[Creneau] = None) -> Optional[str]:
        """Pourquoi cette offre NE couvre PAS ce geste (None : elle le couvre). Aucune disponibilité n'est supposée : avec
        un créneau, l'offre doit DÉCLARER une plage horaire qui le contient."""
        etat = self.etat_offre(o.id)
        if etat != "active":
            return {"retiree": "offre retirée", "expiree": "offre expirée", "a_venir": "offre pas encore ouverte"}[etat]
        if o.nature != e.nature:
            return "nature différente"
        if e.concept and o.concept != e.concept:
            return "capacité différente de celle demandée"
        if o.duree_max_min is not None and e.duree_min > o.duree_max_min:
            return f"demande {e.duree_min} min, l'offre en accepte {o.duree_max_min}"
        if echeance > o.au:
            return f"l'essai se termine le {echeance.isoformat()}, l'offre le {o.au.isoformat()}"
        if creneau is not None:
            if not o.plages:
                return "aucun horaire déclaré"
            if not any(pl.contient(creneau) for pl in o.plages):
                return f"pas disponible {creneau.texte()} (déclaré : {', '.join(pl.texte() for pl in o.plages)})"
            if any(self._chevauche(c, creneau) for c in self.occupations(o.auteur, sauf=sauf)):
                return "la personne est déjà engagée sur un créneau qui chevauche"
        if self.reservations(o.id, sauf=sauf) >= o.capacite:
            return "capacité de l'offre atteinte"
        return None

    def occupations(self, auteur: str, sauf: Optional[str] = None) -> list[Creneau]:
        """Créneaux où cette personne est DÉJÀ engagée (accord valable dans un autre essai vivant). On n'est pas à deux
        endroits à la fois, quelle que soit la capacité déclarée de l'offre (défaut trouvé par la revue « jury » : une
        offre de capacité 2 laissait autoriser deux actions au même créneau)."""
        res = []
        for eid in self.essais():
            if eid == sauf or self.etat(eid) in FINAUX or self.etat(eid) == "IMPOSSIBLE":
                continue
            p = self.protocole(eid)
            if p.creneau is not None and any(e.contributeur == auteur for e in p.etapes) \
                    and self._accord_donne(eid, auteur, p, self.porteur(eid)):
                res.append(p.creneau)
        return res

    @staticmethod
    def _chevauche(a: Creneau, b: Creneau) -> bool:
        return a.jour == b.jour and minutes(a.debut) < minutes(b.fin) and minutes(b.debut) < minutes(a.fin)

    # ------------------------------------------------------------------ lecture d'un essai (repli pur)
    def essais(self) -> list[str]:
        return list(dict.fromkeys(e.donnees["essai"] for e in self.m.evenements("ESSAI_VERSION")))

    def _versions(self, eid: str) -> list[Evt]:
        v = self._evs(eid, "ESSAI_VERSION")
        if not v:
            raise Introuvable("essai inconnu")
        return v

    def version(self, eid: str) -> int:
        return self._versions(eid)[-1].donnees["version"]

    def protocole(self, eid: str, version: Optional[int] = None) -> Protocole:
        vs = self._versions(eid)
        ev = vs[-1] if version is None else next((x for x in vs if x.donnees["version"] == version), None)
        if ev is None:
            raise Introuvable("version inconnue")
        return Protocole(**ev.donnees["protocole"])

    def porteur(self, eid: str) -> str:
        return self._versions(eid)[0].acteurs[0]

    def etat(self, eid: str) -> str:
        t = self._evs(eid, "ESSAI_ETAT")
        return t[-1].donnees["vers"] if t else ""

    def personnes(self, eid: str) -> set[str]:
        """Toute personne à qui une version de l'essai a été proposée (y compris qui a refusé ou été remplacé)."""
        res = {self.porteur(eid)}
        for v in self._versions(eid):
            res |= {e["contributeur"] for e in v.donnees["protocole"]["etapes"] if e.get("contributeur")}
        return res

    def participants(self, eid: str) -> set[str]:
        """Personnes de la version courante qui ont donné un accord (ou dont la contribution a été reçue)."""
        p, porteur = self.protocole(eid), self.porteur(eid)
        return {porteur} | {e.contributeur for e in p.etapes if e.contributeur and self._accord_donne(eid, e.contributeur, p, porteur)}

    def refus(self, eid: str) -> set[str]:
        return {e.acteurs[0] for e in self._evs(eid, "ACCORD") if not e.donnees["accepte"]}

    def _dernier_accord(self, eid: str, membre: str) -> Optional[Evt]:
        acc = [e for e in self._evs(eid, "ACCORD", "RETRAIT") if e.acteurs[0] == membre]
        return acc[-1] if acc else None

    def _accord_donne(self, eid: str, membre: str, p: Protocole, porteur: str) -> bool:
        """Accord POSITIF, non retiré, dont la portée est EXACTEMENT celle de la version donnée (sans juger l'offre)."""
        a = self._dernier_accord(eid, membre)
        return bool(a and a.type == "ACCORD" and a.donnees["accepte"] and a.donnees["empreinte"] == _empreinte(portee(p, porteur, membre)))

    @staticmethod
    def _materiel(o: Optional[OffreVolontaire]) -> Optional[str]:
        """Empreinte de ce qui, dans une offre, ne se vérifie PAS par un nombre : ce qui est offert, sa nature, sa
        capacité déclarée et ses conditions en texte libre. Durée, dates et capacité restent contrôlées numériquement."""
        return _empreinte([o.quoi, o.nature, o.concept, o.conditions]) if o else None

    def _offres_vues(self, eid: str, membre: str, p: Protocole, porteur: str) -> dict[str, Optional[str]]:
        """Les conditions d'offre sur lesquelles porte l'accord de `membre` (toutes pour le porteur, les siennes sinon)."""
        return {e.id: self._materiel(self.offre_de(eid, e)) for e in p.etapes
                if e.contributeur and (membre == porteur or e.contributeur == membre)}

    def apres_action(self, eid: str) -> bool:
        """L'action a eu lieu (ou est close) : son créneau est passé, ou l'essai est au-delà de EN_COURS."""
        etat, p = self.etat(eid), self.protocole(eid)
        return etat not in AVANT_LANCEMENT | {"EN_COURS", "IMPOSSIBLE"} or (
            etat == "EN_COURS" and p.creneau is not None and p.creneau.jour < self._jour())

    def raisons_gestes(self, eid: str) -> dict[str, Optional[str]]:
        """Pour CHAQUE geste de la version courante : None s'il est couvert (accord valable et offre qui le porte encore,
        aux mêmes conditions), sinon la raison. Chaque geste est vérifié — une personne peut en porter plusieurs."""
        p, porteur = self.protocole(eid), self.porteur(eid)
        recues = {x.donnees["etape"] for x in self._evs(eid, "CONTRIBUTION")}
        acc_porteur = self._dernier_accord(eid, porteur)
        vues_porteur = (acc_porteur.donnees.get("offres") or {}) if acc_porteur and acc_porteur.type == "ACCORD" else {}
        # APRÈS le moment de l'action (créneau passé, ou action close), l'état ACTUEL d'une offre ne requalifie plus un
        # accord : une disponibilité datée qui expire ensuite n'est pas un désistement (défaut trouvé : +30 jours
        # affichait « ne couvre plus » pour un lieu accepté et engagé)
        passe = self.apres_action(eid)
        res: dict[str, Optional[str]] = {}
        for e in p.etapes:
            if not e.contributeur:
                res[e.id] = "personne pour ce geste"
                continue
            if e.id in recues:
                res[e.id] = None                              # déjà reçue : rien ne l'efface, pas même un retrait
                continue
            a = self._dernier_accord(eid, e.contributeur)
            if a is None:
                res[e.id] = "en attente de sa réponse"
            elif a.type == "RETRAIT":
                res[e.id] = "a retiré sa participation"
            elif not a.donnees["accepte"]:
                res[e.id] = "a décliné"
            elif not self._accord_donne(eid, e.contributeur, p, porteur):
                res[e.id] = "sa part a changé depuis son accord"
            elif passe:
                res[e.id] = None                              # accord valable au moment engagé : il le reste
            else:
                o = self.offre_de(eid, e)
                raison = self.offre_couvre(o, e, p.echeance, sauf=eid, creneau=p.creneau) if o else "aucune disponibilité déclarée"
                vues = a.donnees.get("offres")               # absent : accord écrit avant ce contrôle (journal ancien)
                if raison:
                    res[e.id] = f"son offre ne couvre plus ce geste : {raison}"
                elif vues is not None and vues.get(e.id) != self._materiel(o):
                    # un texte libre ne se vérifie pas : l'accord ne vaut plus. Si le porteur a déjà accepté les
                    # nouvelles conditions (révision explicite), la personne doit reconfirmer ; sinon, à adapter.
                    res[e.id] = CONDITIONS_A_RECONFIRMER if vues_porteur.get(e.id) == self._materiel(o) else \
                        f"{CONDITIONS_CHANGEES} : « {o.conditions or o.quoi} »"  # type: ignore[union-attr]
                else:
                    res[e.id] = None
        return res

    def couverture(self, eid: str) -> dict[str, Optional[str]]:
        """Pour chaque personne concernée par la version courante : None si son accord couvre TOUT ce qui lui est
        demandé MAINTENANT, sinon la première raison (en clair). C'est ici qu'un accord périmé est reconnu comme tel."""
        p, porteur = self.protocole(eid), self.porteur(eid)
        res: dict[str, Optional[str]] = {}
        a = self._dernier_accord(eid, porteur)
        res[porteur] = None if self._accord_donne(eid, porteur, p, porteur) else (
            "le protocole a changé depuis votre confirmation" if a else "à confirmer")
        for e, raison in zip(p.etapes, self.raisons_gestes(eid).values(), strict=True):
            cle = e.contributeur or f"etape:{e.id}"
            if res.get(cle) is None:
                res[cle] = raison                             # un geste non couvert suffit : la personne n'est pas couverte
        return res

    # ------------------------------------------------------------------ transitions
    def _transition(self, eid: str, vers: str, par: str, raison: str) -> None:
        de = self.etat(eid)
        if vers not in TRANSITIONS.get(de, set()):
            raise Conflit(f"transition interdite : {de or 'rien'} → {vers}")
        self._ecrire("ESSAI_ETAT", [par] if par else [], Statut.OBSERVE, essai=eid, de=de, vers=vers, raison=raison)
        # identifiants techniques seulement : ni la raison (texte libre), ni qui (un identifiant de membre)
        _journal.info("transition", extra={"essai": eid, "de": de or None, "vers": vers, "agent": "personne" if par else "système"})

    def _nouvelle_version(self, eid: str, p: Protocole, par: str, motif: str, statut: Statut = Statut.DECLARE) -> int:
        v = self.version(eid) + 1
        self._ecrire("ESSAI_VERSION", [par], statut, essai=eid, version=v, protocole=p.model_dump(mode="json"), motif=motif)
        return v

    def _verifier_version(self, eid: str, attendue: int) -> None:
        if attendue != self.version(eid):
            raise Conflit(f"le protocole a changé (version {self.version(eid)}, vous avez vu la version {attendue}) : relisez-le")

    def _reevaluer(self, eid: str, cause: str) -> None:
        """Après tout fait nouveau : AUTORISE si tout est couvert, PROPOSE si des réponses manquent, A_ADAPTER si une part
        n'est plus couverte (refus, retrait, offre réduite ou retirée), IMPOSSIBLE si aucune alternative n'existe."""
        etat = self.etat(eid)
        if etat in FINAUX or etat in ("BROUILLON", "CONTRIBUTION_RECUE", "RESULTAT_INCONNU"):
            return
        cov = self.couverture(eid)
        perdus = {k: v for k, v in cov.items() if v and v not in A_REDEMANDER}
        if etat == "IMPOSSIBLE":                              # bloqué : seulement ROUVRIR une adaptation, que le porteur choisira
            alternatives = self.alternatives(eid)
            if alternatives:
                self._ecrire("ADAPTATION", [], Statut.PROPOSE, essai=eid, version=self.version(eid), cause=cause, perdus=perdus,
                             alternatives=alternatives)
                self._transition(eid, "A_ADAPTER", "", f"{cause} : une adaptation redevient possible (à choisir, puis à reconfirmer)")
            return
        if not perdus:
            if all(v is None for v in cov.values()):
                if etat in ("PROPOSE", "A_ADAPTER"):
                    self._transition(eid, "AUTORISE", "", "tous les accords couvrent la version courante")
            elif etat in ("AUTORISE", "A_ADAPTER"):
                self._transition(eid, "PROPOSE", "", cause + " : les personnes concernées doivent choisir à nouveau")
            return
        alternatives = self.alternatives(eid)
        if not alternatives:
            self._ecrire("ADAPTATION", [], Statut.PROPOSE, essai=eid, version=self.version(eid), cause=cause, perdus=perdus, alternatives=[])
            self._transition(eid, "IMPOSSIBLE", "", f"{cause} — aucune alternative admissible : " + " ; ".join(self._manques(eid)))
            return
        self._ecrire("ADAPTATION", [], Statut.PROPOSE, essai=eid, version=self.version(eid), cause=cause, perdus=perdus,
                     alternatives=alternatives)
        if etat != "A_ADAPTER":
            self._transition(eid, "A_ADAPTER", "", cause)

    def _revoir_essais_de_l_offre(self, oid: str, cause: str) -> list[str]:
        """Les essais qui reposent sur cette offre — et les essais BLOQUÉS, qu'une offre changée peut débloquer."""
        touches = []
        for eid in self.essais():
            if self.etat(eid) in FINAUX or (self.etat(eid) != "IMPOSSIBLE" and not any(
                    (o := self.offre_de(eid, e)) is not None and o.id == oid for e in self.protocole(eid).etapes)):
                continue
            avant = self.etat(eid)
            self._reevaluer(eid, cause)
            if self.etat(eid) != avant:
                touches.append(eid)
        return touches

    # ------------------------------------------------------------------ alternatives (déterministes, jamais inventées)
    def candidats(self, eid: str, e: Etape, echeance: date, creneau: Optional[Creneau] = None,
                  autres: Optional[set[str]] = None) -> list[OffreVolontaire]:
        """Offres ADMISSIBLES pour ce geste : publiées, actives, couvrantes, capacité restante ; ni le porteur, ni sa
        propre organisation, ni quelqu'un qui a déjà décliné cet essai, ni quelqu'un déjà engagé sur un autre geste."""
        porteur = self.porteur(eid)
        retraits = {x.acteurs[0] for x in self._evs(eid, "RETRAIT")}
        deja = autres if autres is not None else {x.contributeur for x in self.protocole(eid).etapes if x.contributeur and x.id != e.id}
        exclus = self.refus(eid) | retraits | {porteur} | {x for x in deja if x}
        res = [o for o in self.offres(publiques=True) if o.auteur not in exclus and self._org(o.auteur) != self._org(porteur)
               and self._eligibilite(porteur, o.auteur) is None and self.offre_couvre(o, e, echeance, sauf=eid, creneau=creneau) is None]
        mots = _mots(e.geste)                                   # l'offre la plus proche du geste, puis la plus durable
        return sorted(res, key=lambda o: (-len(mots & _mots(o.quoi)), -o.au.toordinal(), o.id))

    # ------------------------------------------------------------------ QUAND : recherche BORNÉE de créneaux
    def _composer(self, eid: str, p: Protocole, c: Creneau, garder: dict[str, Optional[OffreVolontaire]]) -> Optional[dict]:
        """Une équipe pour ce créneau : chaque geste garde son offre actuelle si elle le couvre, sinon la première offre
        admissible d'une AUTRE personne. None si un geste reste sans offre (rien n'est inventé)."""
        etapes = [e.model_copy(update={"duree_min": min(e.duree_min, c.duree_min)}) for e in p.etapes]   # variante courte : dite
        par_id = {e.id: e for e in etapes}
        gardees = {k: o for k, o in garder.items()
                   if o is not None and self.offre_couvre(o, par_id[k], p.echeance, sauf=eid, creneau=c) is None}
        choix: dict[str, Optional[str]] = {}
        auteurs: set[str] = set()
        remplaces = []
        for e in etapes:
            if e.invitation and e.contributeur and garder.get(e.id) is None:
                choix[e.id] = None                            # sur invitation, pas encore déclarée : à demander, jamais supposée
                continue
            o = gardees.get(e.id)
            if o is None or o.auteur in auteurs:
                autres = auteurs | {x.auteur for k, x in gardees.items() if k != e.id}
                cands = self.candidats(eid, e, p.echeance, c, autres=autres)
                if not cands:
                    return None
                o = cands[0]
                if e.contributeur:
                    remplaces.append(e.id)
            choix[e.id] = o.id
            auteurs.add(o.auteur)
        return {"creneau": c, "choix": choix, "remplaces": remplaces}

    def solutions(self, eid: str, p: Optional[Protocole] = None, maximum: int = 3) -> list[dict]:
        """Créneaux où TOUS les gestes sont couverts, dans la fenêtre du porteur : recherche exhaustive au quart d'heure
        (bornée : fenêtre × durées × gestes × offres). Une variante plus courte n'est proposée que si le porteur a fixé
        une durée minimale acceptable — jamais en dessous. Ordre : le moins de personnes changées, la durée entière,
        le plus proche du créneau actuel."""
        p = p or self.protocole(eid)
        fen = p.fenetre
        if fen is None or not p.etapes:
            return []
        duree = p.creneau.duree_min if p.creneau else max(e.duree_min for e in p.etapes)
        plancher = p.duree_min_acceptable or duree           # jamais sous le minimum que le porteur a fixé
        durees = list(range(duree, plancher - 1, -PAS_MIN)) or [duree]
        partis = self.refus(eid) | {x.acteurs[0] for x in self._evs(eid, "RETRAIT")}
        # on ne GARDE jamais quelqu'un qui a décliné ou s'est retiré (défaut trouvé : « même équipe » gardait un refus)
        garder = {e.id: self.offre_de(eid, e) if e.contributeur and e.contributeur not in partis else None for e in p.etapes}
        res = []
        for d in durees:
            for m in range(minutes(fen.debut), minutes(fen.fin) - d + 1, PAS_MIN):
                c = Creneau(jour=fen.jour, debut=heure(m), duree_min=d)
                if p.creneau and c == p.creneau:
                    continue                                  # le créneau actuel n'est pas une adaptation
                sol = self._composer(eid, p, c, garder)
                if sol:
                    res.append(sol | {"plus_court": d < duree})
        ref = minutes(p.creneau.debut) if p.creneau else minutes(fen.debut)
        res.sort(key=lambda x: (len(x["remplaces"]), x["plus_court"], abs(minutes(x["creneau"].debut) - ref), x["creneau"].debut))
        return res[:maximum]

    def assembler(self, porteur: str, eid: str) -> dict:
        """Ce qui rend la demande RÉALISABLE, sans rien écrire : pour chaque exigence, les offres qui existent (et leurs
        horaires déclarés) ; le premier créneau où elles se recouvrent toutes ; sinon, ce qui manque. Aucune offre
        isolée n'est présentée comme suffisante : la proposition n'existe que si chaque geste est couvert."""
        self._exiger_porteur(eid, porteur)
        p = self.protocole(eid)
        exigences: list[dict] = []
        for e in p.etapes:
            offres = self.candidats(eid, e, p.echeance, None, autres=set())
            if p.fenetre:
                offres = [o for o in offres if any(pl.jour == p.fenetre.jour for pl in o.plages)]
            exigences.append({"etape": e.id, "offres": [o.id for o in offres]})
        sol = self.solutions(eid, p, maximum=1)
        manque: list[str] = [str(x["etape"]) for x in exigences if not x["offres"]]
        return {"exigences": exigences, "solution": sol[0] if sol else None, "manque": manque,
                "blocage": None if sol else ("personne n'offre : " + ", ".join(manque) if manque else
                                             "les disponibilités déclarées ne se recouvrent sur aucun créneau de la fenêtre")}

    def alternatives(self, eid: str) -> list[dict]:
        p = self.protocole(eid)
        raisons = self.raisons_gestes(eid)
        res: list[dict] = []
        for e in p.etapes:
            raison = raisons[e.id]
            if raison is None or raison in A_REDEMANDER:
                continue
            o_ = self.offre_de(eid, e) if e.contributeur else None
            if o_ is not None and raison.startswith(CONDITIONS_CHANGEES) and self.offre_couvre(o_, e, p.echeance, sauf=eid, creneau=p.creneau) is None:
                res.append({"id": f"conditions:{e.id}:{o_.id}:{o_.version}", "type": "accepter_conditions", "etape": e.id,
                            "membre": e.contributeur, "offre": o_.id,
                            "texte": f"Garder la même personne AUX NOUVELLES CONDITIONS : « {o_.conditions or o_.quoi} ». Vérifiez "
                                     "qu'elles permettent encore ce geste ; elle devra reconfirmer.", "a_decider": ["porteur", e.contributeur]})
            for o in self.candidats(eid, e, p.echeance, p.creneau)[:2]:
                res.append({"id": f"remplacer:{e.id}:{o.id}", "type": "remplacer", "etape": e.id, "offre": o.id, "membre": o.auteur,
                            "texte": f"Garder l'essai tel quel ; demander ce geste à une autre personne qui l'offre : « {o.quoi} »"
                                     + (f" ({o.duree_max_min} min au plus)" if o.duree_max_min else ""),
                            "a_decider": ["porteur", o.auteur]})
            o_ = self.offre_de(eid, e) if e.contributeur else None
            if o_ is not None and raison.startswith("son offre ne couvre plus"):
                o = o_
                if self.etat_offre(o.id) == "active" and o.duree_max_min and o.duree_max_min < e.duree_min:
                    res.append({"id": f"raccourcir:{e.id}:{o.duree_max_min}", "type": "raccourcir", "etape": e.id, "duree": o.duree_max_min,
                                "membre": e.contributeur,
                                "texte": f"Garder la même personne ; raccourcir ce geste de {e.duree_min} à {o.duree_max_min} min. "
                                         "L'objectif reste le vôtre : vérifiez que le critère reste mesurable.",
                                "a_decider": ["porteur", e.contributeur]})
        if not any(r is not None and r not in A_REDEMANDER for r in raisons.values()) and self.etat(eid) in ("A_ADAPTER", "IMPOSSIBLE"):
            res.append({"id": f"reprendre:v{self.version(eid)}", "type": "reprendre", "texte": "Plus rien ne bloque : reprendre l'essai tel "
                        "quel. Chaque accord encore valable est conservé ; les autres sont redemandés.", "a_decider": ["porteur"]})
        if p.creneau and any(r is not None and r not in A_REDEMANDER for r in raisons.values()):
            for sol in self.solutions(eid, p):                # déplacer le moment commun : TOUT le monde reconfirme
                c = sol["creneau"]
                qui = [x for x in sol["remplaces"]]
                res.append({"id": f"decaler:{c.jour.isoformat()}:{c.debut}:{c.duree_min}:" + ",".join(f"{k}={v}" for k, v in sol["choix"].items()),
                            "type": "decaler", "creneau": c.model_dump(mode="json"), "choix": sol["choix"], "remplaces": qui,
                            "plus_court": sol["plus_court"],
                            "texte": (f"Déplacer à {c.texte()}" + (f" — variante plus courte ({c.duree_min} min ; votre minimum : "
                                                                    f"{p.duree_min_acceptable} min)" if sol["plus_court"] else "")
                                      + (" — même équipe" if not qui else " — " + " ; ".join(
                                          f"{next(x for x in p.etapes if x.id == k).role or k} : « {self.offre(sol['choix'][k]).quoi} »"
                                          " (une autre personne)" for k in qui))
                                      + ". Le moment change : chaque participant reconfirme."),
                            "a_decider": ["porteur", "chaque participant"]})
        return res

    def _manques(self, eid: str) -> list[str]:
        raisons = self.raisons_gestes(eid)
        return [f"{NATURES[e.nature]} pour « {e.geste} » ({e.duree_min} min) : aucune autre offre active, couvrante et disponible"
                for e in self.protocole(eid).etapes if raisons[e.id] not in (None, *A_REDEMANDER)]

    # ------------------------------------------------------------------ commandes du porteur
    def brouillon(self, porteur: str, p: Protocole) -> str:
        eid = "es-" + _empreinte([porteur, p.question, len(self.m.evenements())])[:8]
        with self.m.transaction():
            self._ecrire("ESSAI_VERSION", [porteur], essai=eid, version=0, protocole=p.model_dump(mode="json"), motif="brouillon")
            self._transition(eid, "BROUILLON", porteur, "brouillon créé par le porteur")
        return eid

    def _exiger_porteur(self, eid: str, qui: str) -> None:
        if self.porteur(eid) != qui:
            raise Interdit("réservé au porteur de l'essai")

    def modifier_brouillon(self, porteur: str, eid: str, attendue: int, p: Protocole) -> int:
        self._exiger_porteur(eid, porteur)
        self._verifier_version(eid, attendue)
        if self.etat(eid) != "BROUILLON":
            raise Conflit("l'essai n'est plus un brouillon : utilisez « modifier »")
        with self.m.transaction():
            return self._nouvelle_version(eid, p, porteur, "brouillon corrigé par le porteur")

    def proposer(self, porteur: str, eid: str, attendue: int, choix: Optional[dict[str, str]] = None,
                 creneau: Optional[Creneau] = None) -> int:
        """Le porteur publie SA proposition. Pour chaque geste, il CHOISIT une offre parmi les offres admissibles
        (`choix` : geste → offre) ; à défaut, la première admissible est proposée. Une offre non admissible est refusée,
        jamais substituée. Sa publication vaut son accord sur CETTE version."""
        self._exiger_porteur(eid, porteur)
        self._verifier_version(eid, attendue)
        if self.etat(eid) != "BROUILLON":
            raise Conflit("déjà proposé")
        p = self.protocole(eid)
        if creneau is not None:
            if p.fenetre and not p.fenetre.contient(creneau):
                raise Invalide("le créneau choisi sort de la fenêtre que vous avez fixée")
            p = Protocole(**(p.model_dump() | {"creneau": creneau.model_dump()}))
        if len(p.critere.strip()) < 3 or not p.etapes:
            raise Invalide("un critère d'observation et au moins un geste sont nécessaires")
        if p.echeance < self._jour():
            raise Invalide("échéance passée")
        etapes: list[Etape] = []
        manquants = []
        for e in p.etapes:
            if e.contributeur:                                # désignée par une opportunité : mêmes règles dures
                raison = ("vous-même" if e.contributeur == porteur else "même organisation" if self._org(e.contributeur) == self._org(porteur)
                          else "a déjà décliné cet essai" if e.contributeur in self.refus(eid) else self._eligibilite(porteur, e.contributeur))
                if raison:
                    raise Conflit(f"la personne proposée pour « {e.geste} » ne peut pas être sollicitée : {raison}")
            if not e.contributeur:
                c = [o for o in self.candidats(eid, e, p.echeance, p.creneau) if o.auteur not in {x.contributeur for x in etapes}]
                if not c:
                    manquants.append(f"{NATURES[e.nature]} pour « {e.geste} » ({e.duree_min} min)")
                    continue
                voulu = (choix or {}).get(e.id)
                o = next((x for x in c if x.id == voulu), None) if voulu else c[0]
                if o is None:
                    raise Conflit(f"l'offre choisie pour « {e.geste} » n'est pas (ou plus) admissible : relisez les offres")
                e = e.model_copy(update={"contributeur": o.auteur, "offre_id": o.id})
            etapes.append(e)
        if manquants:                                         # rien n'est inventé : on le dit, le porteur décide
            raise Conflit("personne n'offre aujourd'hui : " + " ; ".join(manquants) + ". Modifiez ou retirez ce geste.")
        with self.m.transaction():
            v = self._nouvelle_version(eid, p.model_copy(update={"etapes": etapes}), porteur, "proposition publiée", Statut.PROPOSE)
            self._accord(eid, porteur, True)
            self._transition(eid, "PROPOSE", porteur, "proposition publiée : chaque personne choisit sa part")
            self._reevaluer(eid, "proposition publiée")
        return v

    def modifier(self, porteur: str, eid: str, attendue: int, durees: Optional[dict[str, int]] = None, **champs) -> dict:
        """Modification par le porteur (question, critère, échéance, et `durees` : durée d'un geste) : nouvelle version ;
        seuls les accords dont la PORTÉE a changé sont à redonner ; les autres restent valables (dit en clair)."""
        self._exiger_porteur(eid, porteur)
        self._verifier_version(eid, attendue)
        if self.etat(eid) not in {"PROPOSE", "AUTORISE", "A_ADAPTER"}:
            raise Conflit("l'essai ne peut plus être modifié dans cet état")
        avant = self.protocole(eid)
        inconnus = set(durees or {}) - {e.id for e in avant.etapes}
        if inconnus:
            raise Invalide(f"geste inconnu : {', '.join(sorted(inconnus))}")
        etapes = [e.model_copy(update={"duree_min": (durees or {})[e.id]}) if e.id in (durees or {}) else e for e in avant.etapes]
        apres = Protocole(**(avant.model_dump() | {k: v for k, v in champs.items() if v is not None}
                             | {"etapes": [e.model_dump() for e in etapes]}))
        with self.m.transaction():
            self._nouvelle_version(eid, apres, porteur, "modifié par le porteur")
            self._accord(eid, porteur, True)
            diff = self.difference(eid, avant, apres)
            self._reevaluer(eid, "protocole modifié par le porteur")
        return diff

    def difference(self, eid: str, avant: Protocole, apres: Protocole) -> dict:
        porteur = self.porteur(eid)
        gens = {e.contributeur for e in apres.etapes if e.contributeur}
        a_redemander = sorted(m for m in gens if _empreinte(portee(avant, porteur, m)) != _empreinte(portee(apres, porteur, m)))
        return {"a_redemander": a_redemander, "preserves": sorted(gens - set(a_redemander)),
                "champs": sorted(k for k in ("question", "objet", "pourquoi", "critere", "echeance", "creneau")
                                 if getattr(avant, k) != getattr(apres, k))}

    def choisir_alternative(self, porteur: str, eid: str, attendue: int, alternative: str) -> dict:
        """Le PORTEUR choisit (le système ne remplace jamais silencieusement une personne ni un objectif)."""
        self._exiger_porteur(eid, porteur)
        self._verifier_version(eid, attendue)
        if self.etat(eid) != "A_ADAPTER":
            raise Conflit("aucune adaptation en attente")
        alt = next((a for a in self.alternatives(eid) if a["id"] == alternative), None)
        if alt is None:
            raise Conflit("cette alternative n'est plus admissible : relisez les propositions")
        avant = self.protocole(eid)
        etapes = []
        for e in avant.etapes:
            if alt["type"] != "reprendre" and e.id == alt.get("etape"):
                e = (e.model_copy(update={"contributeur": alt["membre"], "offre_id": alt["offre"], "invitation": False})
                     if alt["type"] == "remplacer"
                     else e.model_copy(update={"duree_min": alt["duree"]}) if alt["type"] == "raccourcir"
                     else e)                                  # accepter_conditions : même geste, nouvelle version à reconfirmer
            if alt["type"] == "decaler" and e.duree_min > alt["creneau"]["duree_min"]:
                e = e.model_copy(update={"duree_min": alt["creneau"]["duree_min"]})   # variante plus courte, choisie explicitement
            if alt["type"] == "decaler" and alt["choix"].get(e.id) and (self.offre_de(eid, e) is None or self.offre_de(eid, e).id != alt["choix"][e.id]):  # type: ignore[union-attr]
                o = self.offre(alt["choix"][e.id])
                e = e.model_copy(update={"contributeur": o.auteur, "offre_id": o.id, "invitation": False})
            etapes.append(e)
        apres = avant.model_copy(update={"etapes": etapes})
        if alt["type"] == "decaler":
            apres = Protocole(**(apres.model_dump() | {"creneau": alt["creneau"]}))   # revalidé (durées, échéance)
        with self.m.transaction():
            self._nouvelle_version(eid, apres, porteur, f"adaptation choisie par le porteur : {alt['texte']}")
            self._accord(eid, porteur, True)
            self._transition(eid, "PROPOSE", porteur, "nouvelle version : les personnes concernées choisissent")
            self._reevaluer(eid, "adaptation choisie")
        return self.difference(eid, avant, apres)

    def lancer(self, porteur: str, eid: str, attendue: int) -> None:
        """Moment où la décision est ENGAGÉE : tout est revérifié ici, sous le même verrou que l'écriture."""
        self._exiger_porteur(eid, porteur)
        self._verifier_version(eid, attendue)
        if self.etat(eid) != "AUTORISE":
            raise Conflit("tous les accords ne sont pas réunis pour cette version")
        if self.protocole(eid).echeance < self._jour():
            raise Conflit("échéance passée")
        with self.m.transaction():
            manque = {k: v for k, v in self.couverture(eid).items() if v}
            if manque:                                        # une condition a pu changer entre l'autorisation et le clic
                self._reevaluer(eid, "revérification au lancement")
            else:
                self._transition(eid, "EN_COURS", porteur, "lancé par le porteur : chacun réalise sa part")
        if manque:                                            # la réévaluation est écrite ; le lancement, lui, est refusé
            raise Conflit("un accord ne couvre plus l'essai : " + " ; ".join(v for v in manque.values() if v))

    def livraisons(self, eid: str, etape: str) -> list[Evt]:
        return [x for x in self._evs(eid, "LIVRAISON") if x.donnees["etape"] == etape]

    def livrer(self, membre: str, eid: str, etape: str, contenu: str) -> int:
        """La personne TRANSMET le résultat concret de son geste (ex. la fiche en allemand). Transmis n'est pas reçu : le
        destinataire confirme. Tant que ce n'est pas confirmé, une version corrigée peut être transmise."""
        if membre not in self.personnes(eid):
            raise Introuvable("essai inconnu")
        e = next((x for x in self.protocole(eid).etapes if x.id == etape), None)
        if e is None or e.contributeur != membre:
            raise Interdit("ce geste ne vous est pas confié")
        if not e.livrable:
            raise Conflit("ce geste n'a rien à transmettre")
        if self.etat(eid) != "EN_COURS":
            raise Conflit("l'action n'est pas engagée : rien ne se transmet avant que tous les accords soient réunis et l'essai lancé")
        if self.receptions(eid, etape):
            raise Conflit("réception déjà confirmée")
        if not 3 <= len(contenu.strip()) <= 3000:
            raise Invalide("contenu vide ou trop long")
        rev = len(self.livraisons(eid, etape)) + 1
        self._ecrire("LIVRAISON", [membre], essai=eid, etape=etape, revision=rev, contenu=contenu.strip(), empreinte=_empreinte(contenu.strip()))
        return rev

    def autoriser_projection(self, porteur: str, eid: str, oui: bool) -> None:
        """Le porteur, et lui seul, accepte que son action soit montrée sur un écran COMMUN (en rôles, sans noms) — ou
        le retire. Sans ce choix, rien n'est projeté : pas même un brouillon (défaut trouvé par la revue « jury »)."""
        self._exiger_porteur(eid, porteur)
        if self.etat(eid) in FINAUX and oui:
            raise Conflit("essai terminé")
        self._ecrire("PROJECTION", [porteur], essai=eid, oui=oui)

    def projetable(self, eid: str) -> bool:
        evs = self._evs(eid, "PROJECTION")
        return bool(evs) and bool(evs[-1].donnees["oui"])

    def enregistrer_redaction(self, eid: str, version: int, pour: str, texte: str, meta: dict) -> None:
        """Un texte RÉDIGÉ pour une personne (message d'invitation) : écrit une fois, par une commande ; les lectures et
        le rejeu le RELISENT — aucun modèle n'est rappelé en lisant."""
        self._ecrire("REDACTION", [], essai=eid, version=version, pour=pour, texte=texte, meta=meta)

    def redaction(self, eid: str, version: int, pour: str) -> Optional[Evt]:
        return next((x for x in reversed(self._evs(eid, "REDACTION"))
                     if x.donnees["version"] == version and x.donnees["pour"] == pour), None)

    def receptions(self, eid: str, etape: str) -> list[Evt]:
        return [x for x in self._evs(eid, "RECEPTION") if x.donnees["etape"] == etape]

    def recevoir(self, porteur: str, eid: str, etape: str) -> None:
        """Le destinataire confirme avoir REÇU le livrable transmis (sa dernière version). C'est un fait sur le LIVRABLE
        seulement : le geste au créneau (présenter, prêter, amener) n'est pas constaté pour autant, et un retrait
        ultérieur de la personne garde tout son effet (défaut trouvé : « reçu » valait pour la présentation entière)."""
        self._exiger_porteur(eid, porteur)
        if self.etat(eid) != "EN_COURS":
            raise Conflit("l'essai n'est pas en cours")
        e = next((x for x in self.protocole(eid).etapes if x.id == etape), None)
        if e is None or not e.livrable:
            raise Introuvable("aucun livrable pour ce geste")
        livres = self.livraisons(eid, etape)
        if not livres:
            raise Conflit("rien n'a encore été transmis pour ce geste")
        if self.receptions(eid, etape):
            raise Conflit("réception déjà confirmée")
        self._ecrire("RECEPTION", [porteur], essai=eid, etape=etape, contributeur=e.contributeur,
                     revision=livres[-1].donnees["revision"], empreinte=livres[-1].donnees["empreinte"])

    def constatable(self, eid: str, etape: str) -> Optional[str]:
        """Pourquoi la contribution de ce geste ne peut PAS encore être constatée (None : elle le peut)."""
        p = self.protocole(eid)
        e = next((x for x in p.etapes if x.id == etape), None)
        if e is None:
            return "geste inconnu"
        if self.etat(eid) != "EN_COURS":
            return "l'essai n'est pas en cours"
        if any(x.donnees["etape"] == etape for x in self._evs(eid, "CONTRIBUTION")):
            return "contribution déjà constatée"
        if e.livrable and not self.livraisons(eid, etape):
            return "rien n'a encore été transmis pour ce geste"
        if e.livrable and not self.receptions(eid, etape):
            return "la réception du livrable n'est pas encore confirmée"
        if p.creneau and self._jour() < p.creneau.jour:
            return f"le créneau ({p.creneau.texte()}) n'a pas encore eu lieu : rien ne peut être constaté"
        return None

    def constater(self, porteur: str, eid: str, etape: str) -> None:
        """Le porteur CONSTATE qu'une contribution a eu lieu : pour un geste au créneau, pas avant le jour du créneau ;
        pour un geste avec livrable, après en avoir confirmé la réception. Ce n'est pas un résultat, encore moins un succès."""
        self._exiger_porteur(eid, porteur)
        if self.etat(eid) != "EN_COURS":
            raise Conflit("l'essai n'est pas en cours")
        p = self.protocole(eid)
        e = next((x for x in p.etapes if x.id == etape), None)
        if e is None:
            raise Introuvable("geste inconnu")
        pourquoi = self.constatable(eid, etape)
        if pourquoi:
            raise Conflit(pourquoi)
        livres = self.livraisons(eid, etape)
        with self.m.transaction():
            self._ecrire("CONTRIBUTION", [porteur], essai=eid, etape=etape, contributeur=e.contributeur,
                         livraison=livres[-1].donnees["revision"] if livres else None)
            recues = {x.donnees["etape"] for x in self._evs(eid, "CONTRIBUTION")}
            if recues >= {x.id for x in self.protocole(eid).etapes}:
                self._transition(eid, "CONTRIBUTION_RECUE", porteur, "toutes les contributions sont reçues (aucun résultat en découle)")

    def observer(self, auteur: str, eid: str, texte: str, qualification: str, limites: str) -> int:
        """Observation DÉCLARÉE par le porteur, avec sa portée. Négative, mitigée ou non concluante : gardée telle quelle."""
        self._exiger_porteur(eid, auteur)
        if qualification not in QUALIFICATIONS:
            raise Invalide("qualification inconnue")
        if self.etat(eid) not in ("CONTRIBUTION_RECUE", "RESULTAT_INCONNU", "OBSERVEE"):
            raise Conflit("aucune contribution reçue : il n'y a rien à observer")
        if len(limites.strip()) < 3:
            raise Invalide("dites la portée de l'observation (combien de personnes, quelles conditions)")
        rev = len(self._evs(eid, "OBSERVATION")) + 1
        with self.m.transaction():
            self._ecrire("OBSERVATION", [auteur], essai=eid, revision=rev, texte=texte, qualification=qualification, limites=limites,
                         tardive=self.etat(eid) == "RESULTAT_INCONNU")
            if self.etat(eid) != "OBSERVEE":
                self._transition(eid, "OBSERVEE", auteur, "observation déclarée par le porteur (non vérifiée par le système)")
        return rev

    def annuler(self, par: str, eid: str, raison: str, console: bool = False) -> None:
        if not console:
            self._exiger_porteur(eid, par)
        if self.etat(eid) in FINAUX or self.etat(eid) in ("CONTRIBUTION_RECUE", "RESULTAT_INCONNU"):
            raise Conflit("essai terminé : il ne peut plus être annulé")
        self._transition(eid, "ANNULE", par, raison)

    # ------------------------------------------------------------------ commandes des participants
    def _accord(self, eid: str, membre: str, accepte: bool) -> None:
        p, porteur = self.protocole(eid), self.porteur(eid)
        pt = portee(p, porteur, membre)
        self._ecrire("ACCORD", [membre], essai=eid, version=self.version(eid), accepte=accepte, empreinte=_empreinte(pt), portee=pt,
                     offres=self._offres_vues(eid, membre, p, porteur))

    def decider(self, membre: str, eid: str, attendue: int, accepte: bool) -> None:
        """Accepter ou décliner SA part de la version vue. Un double clic est sans effet ; changer d'avis après avoir
        répondu passe par « retirer » (dit, daté), jamais par une réécriture."""
        p = self.protocole(eid)
        gestes = [e for e in p.etapes if e.contributeur == membre]
        if membre not in self.personnes(eid):
            raise Introuvable("essai inconnu")                # n'en révèle pas l'existence
        if not gestes:
            raise Interdit("aucune part ne vous est demandée dans la version courante")
        self._verifier_version(eid, attendue)
        if self.etat(eid) not in ("PROPOSE", "AUTORISE", "A_ADAPTER"):
            raise Conflit("l'essai n'attend plus de réponse")
        dernier = self._dernier_accord(eid, membre)
        if dernier and dernier.type == "ACCORD" and dernier.donnees["version"] == attendue:
            if dernier.donnees["accepte"] == accepte:
                return                                        # double clic, requête rejouée : idempotent
            raise Conflit("vous avez déjà répondu à cette version : retirez votre participation pour changer d'avis")
        if membre in self.refus(eid):
            raise Conflit("vous avez décliné cet essai : il ne vous sera pas redemandé")
        with self.m.transaction():
            if accepte:
                for e in gestes:                              # capacité et couverture revérifiées AU MOMENT d'accepter
                    o = self.offre_de(eid, e)
                    if o is None and e.invitation:            # accepter une invitation = déclarer SA disponibilité
                        oid = self.publier_offre(membre, e.nature, e.geste, 1, self._jour(), p.echeance, duree_max_min=e.duree_min,
                                                 conditions=f"déclarée en acceptant l'essai « {p.question[:80]} »", pour=(eid, e.id),
                                                 concept=e.concept,
                                                 plages=[Plage(jour=p.creneau.jour, debut=p.creneau.debut, fin=p.creneau.fin)] if p.creneau else None)
                        o = self.offre(oid)
                    raison = self.offre_couvre(o, e, p.echeance, sauf=eid, creneau=p.creneau) if o else "aucune offre"
                    if raison:
                        raise Conflit(f"votre disponibilité déclarée ne couvre pas ce geste : {raison} — mettez-la à jour d'abord")
            self._accord(eid, membre, accepte)
            self._reevaluer(eid, "une personne a accepté" if accepte else "une personne a décliné")

    def retirer(self, membre: str, eid: str) -> dict:
        """Retrait de sa participation. Ce qui est déjà reçu ne s'efface pas : on dit ce qui était encore évitable."""
        if membre not in self.personnes(eid) or membre == self.porteur(eid):
            raise Introuvable("essai inconnu") if membre not in self.personnes(eid) else Interdit("le porteur annule, il ne se retire pas")
        if self.etat(eid) in FINAUX:
            raise Conflit("essai terminé")
        if self.apres_action(eid):                            # défaut trouvé à l'enregistrement : « retirer » 30 jours après
            raise Conflit("l'action a déjà eu lieu : un retrait n'a plus d'objet")
        recues = {x.donnees["etape"] for x in self._evs(eid, "CONTRIBUTION") if x.donnees["contributeur"] == membre}
        with self.m.transaction():
            self._ecrire("RETRAIT", [membre], essai=eid, version=self.version(eid))
            self._reevaluer(eid, "une personne a retiré sa participation")
        return {"deja_fait": sorted(recues), "evite": "aucune nouvelle demande ne vous sera faite pour cet essai ; votre nom ne sera "
                "associé à aucune réutilisation", "irreversible": "une contribution déjà reçue reste reçue" if recues else None}

    def aviser(self, membre: str, eid: str, revision: int, avis: str, raison: str = "") -> None:
        """Un participant CONFIRME ou CONTESTE l'observation. Une contestation reste visible ; rien n'est effacé."""
        if avis not in ("confirme", "conteste"):
            raise Invalide("avis inconnu")
        if membre not in self.participants(eid) or membre == self.porteur(eid):
            raise Interdit("seuls les autres participants donnent leur avis")
        obs = self._evs(eid, "OBSERVATION")
        if not obs or obs[-1].donnees["revision"] != revision:
            raise Conflit("l'observation a été corrigée : relisez-la")
        if avis == "conteste" and len(raison.strip()) < 3:
            raise Invalide("dites ce que vous contestez")
        self._ecrire("AVIS", [membre], essai=eid, revision=revision, avis=avis, raison=raison)

    def reutilisation(self, membre: str, eid: str, niveau: str, mention: str) -> None:
        if niveau not in NIVEAUX or mention not in ("nom", "anonyme"):
            raise Invalide("niveau ou mention inconnus")
        if membre not in self.participants(eid):
            raise Interdit("réservé aux participants")
        if not self._evs(eid, "OBSERVATION"):
            raise Conflit("aucune observation à réutiliser")
        self._ecrire("REUTILISATION", [membre], essai=eid, niveau=niveau, mention=mention)

    def droits(self, eid: str) -> dict[str, dict]:
        res: dict[str, dict] = {}
        for e in self._evs(eid, "REUTILISATION"):
            res[e.acteurs[0]] = {"niveau": e.donnees["niveau"], "mention": e.donnees["mention"]}
        return res

    def niveau_partage(self, eid: str) -> str:
        """Le niveau le PLUS RESTRICTIF parmi les participants : un seul « moi » ou une seule absence de choix suffit."""
        d = self.droits(eid)
        ordre = {"moi": 0, "participants": 1, "club": 2}
        niveaux = [d[m]["niveau"] if m in d else "participants" for m in self.participants(eid)]
        return min(niveaux, key=lambda x: ordre[x]) if niveaux else "participants"

    def etat_canonique(self) -> dict:
        """L'état CALCULÉ du banc (offres et essais), sous une forme canonique : ce que `empreinte_etat` compare."""
        return {"jour": self._jour().isoformat(),
                "offres": {o.id: o.model_dump(mode="json") | {"etat": self.etat_offre(o.id), "reservees": self.reservations(o.id)}
                           for o in self.offres()},
                "essais": {eid: {"etat": self.etat(eid), "version": self.version(eid), "porteur": self.porteur(eid),
                                 "protocole": self.protocole(eid).model_dump(mode="json"), "couverture": self.couverture(eid),
                                 "projetable": self.projetable(eid), "droits": self.droits(eid)} for eid in self.essais()}}

    # ------------------------------------------------------------------ horloge
    def echeances(self) -> list[str]:
        """Rien ne se déduit du silence : sans accords à l'échéance → EXPIRE ; sans observation 14 j après → INCONNU."""
        touches = []
        j = self._jour()
        for eid in self.essais():
            etat, p = self.etat(eid), self.protocole(eid)
            if etat in ("PROPOSE", "AUTORISE", "A_ADAPTER", "IMPOSSIBLE") and p.echeance < j:
                self._transition(eid, "EXPIRE", "", "échéance passée sans lancement : aucun accord n'est supposé")
                touches.append(eid)
            elif etat in ("EN_COURS", "CONTRIBUTION_RECUE") and p.echeance + timedelta(days=DELAI_OBSERVATION_JOURS) < j:
                self._transition(eid, "RESULTAT_INCONNU", "", "aucune observation déclarée : le résultat reste inconnu")
                touches.append(eid)
            elif etat in ("PROPOSE", "AUTORISE"):
                avant = etat
                self._reevaluer(eid, "une offre a expiré")
                if self.etat(eid) != avant:
                    touches.append(eid)
        return touches
