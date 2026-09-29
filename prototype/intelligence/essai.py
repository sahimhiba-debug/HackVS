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
import re
from datetime import date, timedelta
from typing import Callable, Literal, Optional

from pydantic import BaseModel, Field

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
}
FINAUX = {"ANNULE", "EXPIRE", "IMPOSSIBLE", "OBSERVEE"}
AVANT_LANCEMENT = {"BROUILLON", "PROPOSE", "AUTORISE", "A_ADAPTER"}
# une part À REDEMANDER (réponse attendue, portée changée) n'est pas une part PERDUE (refus, retrait, offre qui ne
# couvre plus) : la première attend une décision, la seconde exige une adaptation ou un arrêt
A_REDEMANDER = {"en attente de sa réponse", "à confirmer", "sa part a changé depuis son accord",
                "le protocole a changé depuis votre confirmation"}
DELAI_OBSERVATION_JOURS = 14                          # sans observation 14 j après l'échéance : RÉSULTAT INCONNU
PARTAGE = ("Si vous acceptez : votre nom et votre organisation sont communiqués au porteur et aux autres participants "
           "qui ont accepté ; l'observation reste entre participants, sauf droit de réutilisation donné par CHACUN.")


# ---------------------------------------------------------------------- objets (validés à la frontière)
class Etape(BaseModel):
    id: str = Field(max_length=8)
    nature: Nature
    geste: str = Field(min_length=3, max_length=200)                  # ce que la personne fait concrètement
    duree_min: int = Field(ge=1, le=120)
    contributeur: Optional[str] = Field(default=None, max_length=32)
    offre_id: Optional[str] = Field(default=None, max_length=32)


class Protocole(BaseModel):
    question: str = Field(min_length=3, max_length=300)               # ce que nous essayons de savoir
    objet: str = Field(default="", max_length=120)                    # l'objet, le support ou l'usage concerné
    pourquoi: str = Field(default="", max_length=300)                 # contexte (modifiable sans redemander d'accord)
    critere: str = Field(default="", max_length=300)                  # ce qu'on observera, et comment on le lira
    echeance: date
    etapes: list[Etape] = Field(default_factory=list, max_length=4)


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
            "gestes": [e.model_dump(mode="json", include={"nature", "geste", "duree_min", "offre_id"}) for e in p.etapes if e.contributeur == membre]}


class Banc:
    """Commandes (atomiques) et lectures (replis purs) du banc d'essai. Aucune règle d'accès aux NOMS ici : les vues."""

    def __init__(self, memoire: Memoire, aujourd_hui: Callable[[], date], organisation: Callable[[str], str]):
        self.m, self._jour, self._org = memoire, aujourd_hui, organisation

    # ------------------------------------------------------------------ journal
    def _ecrire(self, type_: str, acteurs: list[str], statut: Statut = Statut.DECLARE, **donnees) -> None:
        self.m.ajouter(Evt(type=type_, le=self._jour(), acteurs=acteurs, statut=statut,
                           donnees=donnees | {"n": len(self.m.evenements())}))    # deux gestes identiques restent deux faits

    def _evs(self, eid: str, *types: str) -> list[Evt]:
        return [e for e in self.m.evenements(*types) if e.donnees.get("essai") == eid]

    # ------------------------------------------------------------------ offres volontaires
    def publier_offre(self, auteur: str, nature: str, quoi: str, capacite: int, du: date, au: date,
                      duree_max_min: Optional[int] = None, conditions: str = "") -> str:
        if au < du:
            raise Invalide("la période de l'offre se termine avant de commencer")
        oid = "of-" + _empreinte([auteur, quoi, len(self.m.evenements())])[:8]
        o = OffreVolontaire(id=oid, auteur=auteur, nature=nature, quoi=quoi, capacite=capacite, du=du, au=au,  # type: ignore[arg-type]
                            duree_max_min=duree_max_min, conditions=conditions)
        self._ecrire("OFFRE", [auteur], offre=o.model_dump(mode="json"))
        return oid

    def offre(self, oid: str) -> OffreVolontaire:
        evs = [e for e in self.m.evenements("OFFRE") if e.donnees["offre"]["id"] == oid]
        if not evs:
            raise Introuvable("offre inconnue")
        return OffreVolontaire(**evs[-1].donnees["offre"])

    def offres(self) -> list[OffreVolontaire]:
        ids = list(dict.fromkeys(e.donnees["offre"]["id"] for e in self.m.evenements("OFFRE")))
        return [self.offre(i) for i in ids]

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
                if e.offre_id != oid or not e.contributeur:
                    continue
                recue = any(x.donnees["etape"] == e.id for x in self._evs(eid, "CONTRIBUTION"))
                if recue or (etat not in FINAUX and self._accord_donne(eid, e.contributeur, p, porteur)):
                    n += 1
        return n

    def offre_couvre(self, o: OffreVolontaire, e: Etape, echeance: date, sauf: Optional[str] = None) -> Optional[str]:
        """Pourquoi cette offre NE couvre PAS ce geste (None : elle le couvre). Aucune disponibilité n'est supposée."""
        etat = self.etat_offre(o.id)
        if etat != "active":
            return {"retiree": "offre retirée", "expiree": "offre expirée", "a_venir": "offre pas encore ouverte"}[etat]
        if o.nature != e.nature:
            return "nature différente"
        if o.duree_max_min is not None and e.duree_min > o.duree_max_min:
            return f"demande {e.duree_min} min, l'offre en accepte {o.duree_max_min}"
        if echeance > o.au:
            return f"l'essai se termine le {echeance.isoformat()}, l'offre le {o.au.isoformat()}"
        if self.reservations(o.id, sauf=sauf) >= o.capacite:
            return "capacité de l'offre atteinte"
        return None

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

    def couverture(self, eid: str) -> dict[str, Optional[str]]:
        """Pour chaque personne concernée par la version courante : None si son accord couvre ce qui lui est demandé
        MAINTENANT, sinon la raison (en clair). C'est ici qu'un accord périmé est reconnu comme tel."""
        p, porteur = self.protocole(eid), self.porteur(eid)
        res: dict[str, Optional[str]] = {}
        a = self._dernier_accord(eid, porteur)
        res[porteur] = None if self._accord_donne(eid, porteur, p, porteur) else (
            "le protocole a changé depuis votre confirmation" if a else "à confirmer")
        for e in p.etapes:
            if not e.contributeur:
                res[f"etape:{e.id}"] = "personne pour ce geste"
                continue
            if e.contributeur in res:
                continue
            if any(x.donnees["etape"] == e.id for x in self._evs(eid, "CONTRIBUTION")):
                res[e.contributeur] = None                    # déjà reçue : rien ne l'efface, pas même un retrait
                continue
            a = self._dernier_accord(eid, e.contributeur)
            if a is None:
                res[e.contributeur] = "en attente de sa réponse"
            elif a.type == "RETRAIT":
                res[e.contributeur] = "a retiré sa participation"
            elif not a.donnees["accepte"]:
                res[e.contributeur] = "a décliné"
            elif not self._accord_donne(eid, e.contributeur, p, porteur):
                res[e.contributeur] = "sa part a changé depuis son accord"
            else:
                raison = self.offre_couvre(self.offre(e.offre_id), e, p.echeance, sauf=eid) if e.offre_id else "aucune offre"
                res[e.contributeur] = f"son offre ne couvre plus ce geste : {raison}" if raison else None
        return res

    # ------------------------------------------------------------------ transitions
    def _transition(self, eid: str, vers: str, par: str, raison: str) -> None:
        de = self.etat(eid)
        if vers not in TRANSITIONS.get(de, set()):
            raise Conflit(f"transition interdite : {de or 'rien'} → {vers}")
        self._ecrire("ESSAI_ETAT", [par] if par else [], Statut.OBSERVE, essai=eid, de=de, vers=vers, raison=raison)

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
        touches = []
        for eid in self.essais():
            if self.etat(eid) in FINAUX or not any(e.offre_id == oid for e in self.protocole(eid).etapes):
                continue
            avant = self.etat(eid)
            self._reevaluer(eid, cause)
            if self.etat(eid) != avant:
                touches.append(eid)
        return touches

    # ------------------------------------------------------------------ alternatives (déterministes, jamais inventées)
    def candidats(self, eid: str, e: Etape, echeance: date) -> list[OffreVolontaire]:
        """Offres ADMISSIBLES pour ce geste : publiées, actives, couvrantes, capacité restante ; ni le porteur, ni sa
        propre organisation, ni quelqu'un qui a déjà décliné cet essai, ni quelqu'un déjà engagé sur un autre geste."""
        porteur = self.porteur(eid)
        retraits = {x.acteurs[0] for x in self._evs(eid, "RETRAIT")}
        exclus = self.refus(eid) | retraits | {porteur} | {x.contributeur for x in self.protocole(eid).etapes if x.contributeur and x.id != e.id}
        res = [o for o in self.offres() if o.auteur not in exclus and self._org(o.auteur) != self._org(porteur)
               and self.offre_couvre(o, e, echeance, sauf=eid) is None]
        mots = _mots(e.geste)                                   # l'offre la plus proche du geste, puis la plus durable
        return sorted(res, key=lambda o: (-len(mots & _mots(o.quoi)), -o.au.toordinal(), o.id))

    def alternatives(self, eid: str) -> list[dict]:
        p = self.protocole(eid)
        cov = self.couverture(eid)
        res: list[dict] = []
        for e in p.etapes:
            raison = cov.get(e.contributeur or f"etape:{e.id}")
            if raison is None or raison in A_REDEMANDER:
                continue
            for o in self.candidats(eid, e, p.echeance)[:2]:
                res.append({"id": f"remplacer:{e.id}:{o.id}", "type": "remplacer", "etape": e.id, "offre": o.id, "membre": o.auteur,
                            "texte": f"Garder l'essai tel quel ; demander ce geste à une autre personne qui l'offre : « {o.quoi} »"
                                     + (f" ({o.duree_max_min} min au plus)" if o.duree_max_min else ""),
                            "a_decider": ["porteur", o.auteur]})
            if e.contributeur and e.offre_id and raison.startswith("son offre ne couvre plus"):
                o = self.offre(e.offre_id)
                if self.etat_offre(o.id) == "active" and o.duree_max_min and o.duree_max_min < e.duree_min:
                    res.append({"id": f"raccourcir:{e.id}:{o.duree_max_min}", "type": "raccourcir", "etape": e.id, "duree": o.duree_max_min,
                                "membre": e.contributeur,
                                "texte": f"Garder la même personne ; raccourcir ce geste de {e.duree_min} à {o.duree_max_min} min. "
                                         "L'objectif reste le vôtre : vérifiez que le critère reste mesurable.",
                                "a_decider": ["porteur", e.contributeur]})
        return res

    def _manques(self, eid: str) -> list[str]:
        p = self.protocole(eid)
        cov = self.couverture(eid)
        return [f"{NATURES[e.nature]} pour « {e.geste} » ({e.duree_min} min) : aucune autre offre active, couvrante et disponible"
                for e in p.etapes if cov.get(e.contributeur or f"etape:{e.id}") not in (None, *A_REDEMANDER)]

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

    def proposer(self, porteur: str, eid: str, attendue: int, choix: Optional[dict[str, str]] = None) -> int:
        """Le porteur publie SA proposition. Pour chaque geste, il CHOISIT une offre parmi les offres admissibles
        (`choix` : geste → offre) ; à défaut, la première admissible est proposée. Une offre non admissible est refusée,
        jamais substituée. Sa publication vaut son accord sur CETTE version."""
        self._exiger_porteur(eid, porteur)
        self._verifier_version(eid, attendue)
        if self.etat(eid) != "BROUILLON":
            raise Conflit("déjà proposé")
        p = self.protocole(eid)
        if len(p.critere.strip()) < 3 or not p.etapes:
            raise Invalide("un critère d'observation et au moins un geste sont nécessaires")
        if p.echeance < self._jour():
            raise Invalide("échéance passée")
        etapes: list[Etape] = []
        manquants = []
        for e in p.etapes:
            if not e.contributeur:
                c = [o for o in self.candidats(eid, e, p.echeance) if o.auteur not in {x.contributeur for x in etapes}]
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

    def modifier(self, porteur: str, eid: str, attendue: int, **champs) -> dict:
        """Modification par le porteur (question, critère, geste, durée, échéance…) : nouvelle version ; seuls les accords
        dont la PORTÉE a changé sont à redonner ; les autres restent valables (dit en clair)."""
        self._exiger_porteur(eid, porteur)
        self._verifier_version(eid, attendue)
        if self.etat(eid) not in {"PROPOSE", "AUTORISE", "A_ADAPTER"}:
            raise Conflit("l'essai ne peut plus être modifié dans cet état")
        avant = self.protocole(eid)
        apres = Protocole(**(avant.model_dump() | {k: v for k, v in champs.items() if v is not None}))
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
                "champs": sorted(k for k in ("question", "objet", "pourquoi", "critere", "echeance")
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
            if e.id == alt["etape"]:
                e = (e.model_copy(update={"contributeur": alt["membre"], "offre_id": alt["offre"]}) if alt["type"] == "remplacer"
                     else e.model_copy(update={"duree_min": alt["duree"]}))
            etapes.append(e)
        apres = avant.model_copy(update={"etapes": etapes})
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

    def constater(self, porteur: str, eid: str, etape: str) -> None:
        """Le porteur CONSTATE qu'une contribution a été reçue. Ce n'est pas un résultat, encore moins un succès."""
        self._exiger_porteur(eid, porteur)
        if self.etat(eid) != "EN_COURS":
            raise Conflit("l'essai n'est pas en cours")
        e = next((x for x in self.protocole(eid).etapes if x.id == etape), None)
        if e is None:
            raise Introuvable("geste inconnu")
        if any(x.donnees["etape"] == etape for x in self._evs(eid, "CONTRIBUTION")):
            raise Conflit("contribution déjà constatée")
        with self.m.transaction():
            self._ecrire("CONTRIBUTION", [porteur], essai=eid, etape=etape, contributeur=e.contributeur)
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
        p = self.protocole(eid)
        pt = portee(p, self.porteur(eid), membre)
        self._ecrire("ACCORD", [membre], essai=eid, version=self.version(eid), accepte=accepte, empreinte=_empreinte(pt), portee=pt)

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
                    raison = self.offre_couvre(self.offre(e.offre_id), e, p.echeance, sauf=eid) if e.offre_id else "aucune offre"
                    if raison:
                        raise Conflit(f"votre offre ne couvre pas ce geste : {raison}")
            self._accord(eid, membre, accepte)
            self._reevaluer(eid, "une personne a accepté" if accepte else "une personne a décliné")

    def retirer(self, membre: str, eid: str) -> dict:
        """Retrait de sa participation. Ce qui est déjà reçu ne s'efface pas : on dit ce qui était encore évitable."""
        if membre not in self.personnes(eid) or membre == self.porteur(eid):
            raise Introuvable("essai inconnu") if membre not in self.personnes(eid) else Interdit("le porteur annule, il ne se retire pas")
        if self.etat(eid) in FINAUX:
            raise Conflit("essai terminé")
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

    # ------------------------------------------------------------------ horloge
    def echeances(self) -> list[str]:
        """Rien ne se déduit du silence : sans accords à l'échéance → EXPIRE ; sans observation 14 j après → INCONNU."""
        touches = []
        j = self._jour()
        for eid in self.essais():
            etat, p = self.etat(eid), self.protocole(eid)
            if etat in ("PROPOSE", "AUTORISE", "A_ADAPTER") and p.echeance < j:
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
