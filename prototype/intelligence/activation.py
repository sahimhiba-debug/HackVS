"""ACTIVER : transformer une opportunité en action humaine réelle, sous consentement, et survivre aux imprévus.

Une activation est une MACHINE À ÉTATS dérivée d'un journal d'événements (rien n'est stocké deux fois) :

    DETECTEE → EVALUEE → PLANIFIEE → EN_ATTENTE_ACCORD → ACTIVEE → TERMINEE → RESULTAT_{CONFIRME,PARTIEL,NEGATIF,INCONNU}
                                         │    ▲
                        refus / silence  ▼    │ alternative sollicitée
                                      BLOQUEE → REPLANIFICATION → ALTERNATIVE_PROPOSEE
                                                       │
                                                       └→ ABANDONNEE (aucune alternative : dit pourquoi, s'arrête)

Chaque transition est écrite par un « agent » nommé — un SERVICE DÉTERMINISTE avec une responsabilité, une entrée,
une sortie, une condition de passage et un journal ; aucun n'est un modèle de langage :
- Garde         : re-vérifie les règles dures au moment d'agir (un profil a pu changer depuis la détection) ;
- Planificateur : séquence d'étapes, une personne par capacité, alternatives classées ;
- Coordinateur  : sollicitations PRIVÉES, délais, budget d'attention (2 sollicitations ouvertes par membre) ;
- Vérificateur  : résultat déclaré par le bénéficiaire — jamais déduit, jamais fabriqué ;
- Mémoire       : un résultat confirmé devient un motif vérifié (`intelligence.apprentissage`).
Les gestes humains (accepter, décliner, contribuer, confirmer) viennent de l'extérieur ; en démonstration ils sont
JOUÉS par la présentation et marqués comme tels.
"""
from __future__ import annotations

import functools
import hashlib
from datetime import date
from typing import Callable, Optional, TypeVar, cast

from app import agenda
from app.models import Profil
from app.taxonomy import Taxonomie
from plateforme.affirmations import Statut
from plateforme.memoire import Evt

from . import apprentissage
from .detection import Detecteur
from .erreurs import Conflit, ErreurMetier, Interdit, Introuvable, Invalide
from .modele import Opportunite, Reseau

ETATS = ("DETECTEE", "EVALUEE", "PLANIFIEE", "EN_ATTENTE_ACCORD", "ACTIVEE", "TERMINEE", "BLOQUEE", "REPLANIFICATION",
         "ALTERNATIVE_PROPOSEE", "ABANDONNEE", "REJETEE", "RESULTAT_CONFIRME", "RESULTAT_PARTIEL", "RESULTAT_NEGATIF",
         "RESULTAT_INCONNU", "EN_PAUSE", "ANNULEE")
PAUSABLES = {"PLANIFIEE", "EN_ATTENTE_ACCORD", "ACTIVEE"}
TRANSITIONS: dict[str, set[str]] = {
    "": {"DETECTEE"},
    "DETECTEE": {"EVALUEE", "REJETEE"},
    "EVALUEE": {"PLANIFIEE", "REJETEE"},
    "PLANIFIEE": {"EN_ATTENTE_ACCORD", "REJETEE", "PLANIFIEE"},
    "EN_ATTENTE_ACCORD": {"ACTIVEE", "BLOQUEE", "ABANDONNEE"},
    "BLOQUEE": {"REPLANIFICATION"},
    "REPLANIFICATION": {"ALTERNATIVE_PROPOSEE", "ABANDONNEE"},
    "ALTERNATIVE_PROPOSEE": {"EN_ATTENTE_ACCORD"},
    "ACTIVEE": {"TERMINEE", "BLOQUEE"},
    "TERMINEE": {"RESULTAT_CONFIRME", "RESULTAT_PARTIEL", "RESULTAT_NEGATIF", "RESULTAT_INCONNU"},
    "RESULTAT_INCONNU": {"RESULTAT_CONFIRME", "RESULTAT_PARTIEL", "RESULTAT_NEGATIF"},
    "EN_PAUSE": set(PAUSABLES) | {"ANNULEE"},
}
for _e in PAUSABLES | {"BLOQUEE", "REPLANIFICATION", "ALTERNATIVE_PROPOSEE", "EVALUEE", "DETECTEE"}:
    TRANSITIONS[_e] = TRANSITIONS[_e] | {"ANNULEE"} | ({"EN_PAUSE"} if _e in PAUSABLES else set())
FINAUX = {"ABANDONNEE", "REJETEE", "RESULTAT_CONFIRME", "RESULTAT_PARTIEL", "RESULTAT_NEGATIF", "ANNULEE"}
DELAI_REPONSE_JOURS = 4        # sans réponse après 4 jours : on n'insiste pas, on passe à l'alternative
DELAI_RESULTAT_JOURS = 21      # pas de confirmation 21 jours après la fin : RÉSULTAT INCONNU (jamais « réussi »)
MAX_REMPLACEMENTS = 3          # garde-fou : une étape ne boucle pas indéfiniment sur des alternatives
BUDGET_ATTENTION = 2           # sollicitations ouvertes au plus par membre, toutes activations confondues
NATURES = ("ressource", "rencontre", "conseil", "validation", "introduction", "document", "seance")
VERDICTS = {"debloque": "RESULTAT_CONFIRME", "partiel": "RESULTAT_PARTIEL", "non": "RESULTAT_NEGATIF"}


ErreurActivation = ErreurMetier        # nom historique : tout refus du moteur (sous-classes typées ci-dessous)


F = TypeVar("F", bound=Callable)


def atomique(f: F) -> F:
    """Une commande du moteur écrit plusieurs faits (transition, plan, sollicitations…) : tous ou aucun.
    Sans cela, une erreur au milieu (budget d'attention, règle métier) laissait une activation dans un état partiel."""
    @functools.wraps(f)
    def enveloppe(self: "Moteur", *a, **k):
        with self.m.transaction():
            return f(self, *a, **k)
    return cast(F, enveloppe)


def _aid(opp_id: str, n: int) -> str:
    return "a" + hashlib.sha256(f"{opp_id}|{n}".encode()).hexdigest()[:8]


class Moteur:
    """Toutes les activations d'un réseau. L'horloge est un PARAMÈTRE (`le`) : jamais `date.today()` dans la logique."""

    def __init__(self, reseau: Reseau, tax: Taxonomie, statut: Statut = Statut.SIMULE):
        self.r, self.tax, self.statut = reseau, tax, statut
        self.m = reseau.memoire
        self.exclus: set[str] = set()                # retirés du réseau (départ, capacité supprimée…)

    # ------------------------------------------------------------------ journal
    def _ecrire(self, type_: str, le: date, acteurs: list[str], **donnees) -> None:
        self.m.ajouter(Evt(type=type_, le=le, acteurs=acteurs, statut=self.statut,
                           donnees=donnees | {"n": len(self.m.evenements())}))   # n : deux gestes identiques restent deux faits

    def _evs(self, aid: str, *types: str) -> list[Evt]:
        return [e for e in self.m.evenements(*types) if e.donnees.get("aid") == aid]

    def etat(self, aid: str) -> str:
        t = self._evs(aid, "ACTIVATION")
        return t[-1].donnees["etat"] if t else ""

    def _transition(self, aid: str, le: date, vers: str, agent: str, raison: str, **details) -> None:
        de = self.etat(aid)
        if vers not in TRANSITIONS.get(de, set()):
            raise Conflit(f"transition interdite : {de or 'rien'} → {vers}")
        self._ecrire("ACTIVATION", le, [], aid=aid, de=de, etat=vers, agent=agent, raison=raison, details=details)

    def plan(self, aid: str) -> dict:
        p = self._evs(aid, "ACTIVATION_PLAN")
        if not p:
            raise Introuvable("activation inconnue")
        return p[-1].donnees

    def opportunite(self, aid: str) -> Opportunite:
        return Opportunite(**self.plan(aid)["opportunite"])

    def activations(self) -> list[str]:
        return list(dict.fromkeys(e.donnees["aid"] for e in self.m.evenements("ACTIVATION_PLAN")))

    # ------------------------------------------------------------------ Détecteur → Garde → Planificateur
    @atomique
    def creer(self, opp: Opportunite, le: date, anonyme: bool = False, langue: Optional[str] = None) -> str:
        if opp.type == "LACUNE":
            raise Invalide("une lacune ne s'active pas en sollicitant des membres : elle se signale à l'animatrice")
        aid = _aid(opp.id, len(self.activations()))
        self._transition(aid, le, "DETECTEE", "Détecteur", f"{opp.type} : {opp.declencheur}", opportunite=opp.id)
        probleme = self._garde(opp)
        # le plan est écrit AVANT l'évaluation : c'est lui qui porte l'opportunité (et donc ce qui sera refusé)
        etapes = self._planifier(opp, langue)
        self._ecrire("ACTIVATION_PLAN", le, [], aid=aid, opportunite=opp.model_dump(), etapes=etapes, anonyme=anonyme,
                     langue=langue, version=1)
        if probleme:
            self._transition(aid, le, "REJETEE", "Garde", probleme)
            return aid
        self._transition(aid, le, "EVALUEE", "Garde",
                         f"règles dures re-vérifiées pour {len(opp.roles)} personne(s) : consentement, disponibilité, "
                         "organisation, langue, profil récent, refus antérieur")
        self._transition(aid, le, "PLANIFIEE", "Planificateur",
                         f"{sum(1 for e in etapes if e['type'] in ('contribution', 'animation'))} contribution(s), "
                         f"{sum(len(e.get('alternatives', [])) for e in etapes)} alternative(s) en réserve"
                         + (f", {len([e for e in etapes if e['type'] == 'hors_club'])} manque(s) signalé(s)" if opp.manque else ""))
        return aid

    def _garde(self, opp: Opportunite) -> Optional[str]:
        par_id = self.r.par_id()
        for r in opp.roles:
            p = par_id.get(r.membre)
            if p is None or r.membre in self.exclus:
                return "une personne de l'opportunité n'est plus dans le réseau"
            if r.role in ("bénéficiaire", "participant", "demandeur bloqué"):
                continue
            if not p.accepte_introductions or not p.disponible:
                return "une personne sollicitée n'accepte plus les sollicitations ou n'est plus disponible"
        return None

    def _alternatives(self, beneficiaire: Profil, concept: Optional[str], deja: set[str], langue: Optional[str],
                      texte: str = "") -> list[str]:
        if not concept:
            return []
        d = Detecteur(self.r, self.tax, exclus=self.exclus | deja)
        return [x["id"] for x in d.fournisseurs(beneficiaire, concept, texte=texte)
                if not langue or langue in self.r.par_id()[x["id"]].langues][:MAX_REMPLACEMENTS]

    def _planifier(self, opp: Opportunite, langue: Optional[str]) -> list[dict]:
        par_id, tax = self.r.par_id(), self.tax
        benef = par_id.get(opp.beneficiaire or "")
        dans_plan = {r.membre for r in opp.roles}
        etapes: list[dict] = []
        if benef:
            etapes.append({"id": "e0", "type": "accord_beneficiaire", "membre": benef.id, "libelle": "Accord du bénéficiaire",
                           "demande": "Est-ce utile pour vous maintenant ? Rien n'est transmis à personne avant votre accord."})
        for r in opp.roles:
            if r.membre == (benef.id if benef else None):
                continue
            if r.role == "participant":
                etapes.append({"id": f"e{len(etapes)}", "type": "accord_participant", "membre": r.membre,
                               "libelle": "Participation à la séance", "demande": "Souhaitez-vous participer à une séance commune ?"})
                continue
            contact = r.role.startswith("partenaire")
            concept = r.concept
            if contact:                                # un partenaire apporte SA capacité (pas le produit du bénéficiaire)
                concept = next((o.concept for o in par_id[r.membre].offre if o.concept), r.concept)
            libelle = tax.libelle(concept) if concept else "contribution"
            typ = "animation" if r.role.startswith("animatrice") else "contribution"
            texte = next((s.extrait for s in opp.signaux if s.membre == (benef.id if benef else None) and s.source in ("recherche", "besoin")), "")
            alt = [] if contact or not benef else [
                x for x in self._alternatives(benef, r.concept, dans_plan, langue, texte) if x not in dans_plan]
            etapes.append({"id": f"e{len(etapes)}", "type": typ, "membre": r.membre, "concept": concept,
                           "libelle": ("Rencontre : " + libelle) if contact else libelle,
                           "demande": ("Rendez-vous de 20 minutes" + (" sur place" if opp.evenement else "") if contact
                                       else f"Votre aide sur : {libelle} (20 minutes ou une ressource écrite)"),
                           "alternatives": alt, "remplacements": 0})
        for m_ in opp.manque:
            etapes.append({"id": f"e{len(etapes)}", "type": "hors_club", "membre": None, "libelle": m_,
                           "demande": "Aucun membre éligible : signalé à l'animatrice (manque du Club)"})
        if benef:
            etapes.append({"id": f"e{len(etapes)}", "type": "confirmation", "membre": benef.id,
                           "libelle": "Le bénéficiaire confirme l'effet", "demande": "Votre prochaine étape est-elle débloquée ?"})
        if langue:
            for e in etapes:
                if e["type"] in ("contribution", "animation") and langue not in par_id[e["membre"]].langues:
                    e["incompatible"] = f"ne parle pas {langue}"
        return etapes

    # ------------------------------------------------------------------ Coordinateur
    def ouvertes(self, le: Optional[date] = None) -> dict[str, int]:
        """Sollicitations sans réponse, par membre (budget d'attention)."""
        repondues = {(e.donnees["aid"], e.donnees["etape"], e.acteurs[0]) for e in self.m.evenements("REPONSE")}
        res: dict[str, int] = {}
        for e in self.m.evenements("SOLLICITATION_PRIVEE"):
            k = (e.donnees["aid"], e.donnees["etape"], e.acteurs[0])
            if k not in repondues and self.etat(e.donnees["aid"]) not in FINAUX:
                res[e.acteurs[0]] = res.get(e.acteurs[0], 0) + 1
        return res

    def _solliciter(self, aid: str, le: date, etape: dict, question: Optional[str] = None) -> None:
        if self.ouvertes().get(etape["membre"], 0) >= BUDGET_ATTENTION:
            raise Conflit("budget d'attention atteint pour cette personne")
        self._ecrire("SOLLICITATION_PRIVEE", le, [etape["membre"]], aid=aid, etape=etape["id"],
                     demande=etape["demande"] + (f" — {question}" if question else ""))

    def _sollicitations(self, aid: str) -> dict[tuple[str, str], Evt]:
        return {(e.donnees["etape"], e.acteurs[0]): e for e in self._evs(aid, "SOLLICITATION_PRIVEE")}

    def _reponses(self, aid: str) -> dict[tuple[str, str], Evt]:
        return {(e.donnees["etape"], e.acteurs[0]): e for e in self._evs(aid, "REPONSE")}

    @atomique
    def lancer(self, aid: str, le: date) -> None:
        """Première sollicitation : le BÉNÉFICIAIRE d'abord (personne d'autre n'est exposé avant son accord)."""
        if self.etat(aid) != "PLANIFIEE":
            raise Conflit("seule une activation planifiée peut être lancée")
        etapes = self.plan(aid)["etapes"]
        if any(e.get("incompatible") for e in etapes):
            raise Conflit("le plan viole une contrainte : replanifier d'abord")
        premiere = [e for e in etapes if e["type"] == "accord_beneficiaire"] or \
                   [e for e in etapes if e["type"] in ("contribution", "animation", "accord_participant")]
        self._transition(aid, le, "EN_ATTENTE_ACCORD", "Coordinateur",
                         f"{len(premiere)} sollicitation(s) privée(s) envoyée(s)")
        for e in premiere:
            self._solliciter(aid, le, e)

    @atomique
    def repondre(self, aid: str, le: date, membre: str, accepte: bool) -> None:
        """Geste HUMAIN : seule une personne sollicitée répond, une seule fois."""
        etapes = self.plan(aid)["etapes"]
        sol = self._sollicitations(aid)
        rep = self._reponses(aid)
        ouvertes = [e for e in etapes if (e["id"], membre) in sol and (e["id"], membre) not in rep]
        if not ouvertes:
            if any(k[1] == membre for k in sol):
                raise Conflit("vous avez déjà répondu à cette sollicitation")     # nouvel essai, double clic
            raise Interdit("seule une personne sollicitée peut répondre")
        if self.etat(aid) != "EN_ATTENTE_ACCORD":
            raise Conflit("cette activation n'attend pas de réponse")
        e = ouvertes[0]
        self._ecrire("REPONSE", le, [membre], aid=aid, etape=e["id"], accepte=accepte, geste="humain")
        if not accepte:
            self._bloquer(aid, le, e, "une personne sollicitée a décliné")
            return
        self._avancer_accords(aid, le)

    def _avancer_accords(self, aid: str, le: date) -> None:
        etapes = self.plan(aid)["etapes"]
        rep, sol = self._reponses(aid), self._sollicitations(aid)
        benef = next((e for e in etapes if e["type"] == "accord_beneficiaire"), None)
        suivantes = [e for e in etapes if e["type"] in ("contribution", "animation", "accord_participant")]
        if benef and (benef["id"], benef["membre"]) in rep and suivantes and not any((e["id"], e["membre"]) in sol for e in suivantes):
            for e in suivantes:                            # après l'accord du bénéficiaire : les contributeurs, en privé
                self._solliciter(aid, le, e, e.get("question"))
            return
        attendues = [e for e in etapes if e["type"] in ("accord_beneficiaire", "contribution", "animation", "accord_participant")]
        if all((e["id"], e["membre"]) in rep and rep[(e["id"], e["membre"])].donnees["accepte"] for e in attendues):
            self._transition(aid, le, "ACTIVEE", "Coordinateur", f"{len(attendues)} accord(s) : les personnes sont mises en relation")

    def _bloquer(self, aid: str, le: date, etape: dict, raison: str) -> None:
        self._transition(aid, le, "BLOQUEE", "Coordinateur", raison, etape=etape["id"])
        if etape["type"] == "accord_beneficiaire":
            self._transition(aid, le, "REPLANIFICATION", "Planificateur", "le bénéficiaire ne souhaite pas donner suite")
            self._transition(aid, le, "ABANDONNEE", "Planificateur", "sans l'accord du bénéficiaire, rien n'est fait ; personne d'autre n'a été exposé")
            return
        self.replanifier(aid, le, etape["id"], raison)

    @atomique
    def replanifier(self, aid: str, le: date, etape_id: str, raison: str) -> None:
        """Planificateur : remplacer UNE étape par la meilleure alternative encore éligible — ou s'arrêter proprement."""
        if self.etat(aid) == "BLOQUEE":
            self._transition(aid, le, "REPLANIFICATION", "Planificateur", f"recherche d'une alternative ({raison})")
        p = self.plan(aid)
        etapes = [dict(e) for e in p["etapes"]]
        e = next(x for x in etapes if x["id"] == etape_id)
        par_id = self.r.par_id()
        opp = Opportunite(**p["opportunite"])
        benef = par_id.get(opp.beneficiaire or "")
        refuses = {k[1] for k, v in self._reponses(aid).items() if k[0] == etape_id and not v.donnees["accepte"]}
        refuses |= {k[1] for k in self._sollicitations(aid) if k[0] == etape_id and k not in self._reponses(aid)}
        dans_plan = {x["membre"] for x in etapes if x.get("membre")}
        texte = next((s.extrait for s in opp.signaux if benef and s.membre == benef.id and s.source in ("recherche", "besoin")), "")
        candidats = [x for x in (e.get("alternatives") or []) if x not in refuses | self.exclus and x not in dans_plan]
        if benef:                                      # les alternatives sont recalculées : le réseau a pu changer
            frais = self._alternatives(benef, e.get("concept"), dans_plan | refuses, p.get("langue"), texte)
            candidats = [x for x in candidats if x in frais] + [x for x in frais if x not in candidats]
        ouvertes = self.ouvertes()
        candidats = [x for x in candidats if ouvertes.get(x, 0) < BUDGET_ATTENTION]
        if not candidats or e.get("remplacements", 0) >= MAX_REMPLACEMENTS:
            levee = self._levee(benef, e.get("concept"), dans_plan | refuses) if benef else {}
            self._transition(aid, le, "ABANDONNEE", "Planificateur",
                             "aucune alternative éligible pour : " + e["libelle"] + (" — " + levee["texte"] if levee else ""),
                             etape=etape_id, levee=levee)
            return
        alt = candidats[0]
        verif = self.verifier_candidat(benef, par_id[alt], e.get("concept"), opp) if benef else {"ok": [], "a_verifier": []}
        question = ("merci de confirmer : " + " ; ".join(verif["a_verifier"])) if verif["a_verifier"] else None
        e.update(membre=alt, alternatives=[x for x in candidats[1:]], remplacements=e.get("remplacements", 0) + 1,
                 question=question)
        self._ecrire("ACTIVATION_PLAN", le, [], **(p | {"etapes": etapes, "version": p["version"] + 1}))
        total = len(verif["ok"]) + len(verif["a_verifier"])
        self._transition(aid, le, "ALTERNATIVE_PROPOSEE", "Planificateur",
                         f"alternative pour « {e['libelle']} » : {len(verif['ok'])}/{total} conditions satisfaites"
                         + (f" ; à vérifier : {', '.join(verif['a_verifier'])}" if verif["a_verifier"] else ""),
                         etape=etape_id, alternative=alt, ok=verif["ok"], a_verifier=verif["a_verifier"],
                         prochaine_action=("Demander à la personne sa disponibilité avant de l'engager" if verif["a_verifier"]
                                           else "Solliciter la personne en privé"))
        self._transition(aid, le, "EN_ATTENTE_ACCORD", "Coordinateur", "alternative sollicitée en privé")
        benef_ok = not any(x["type"] == "accord_beneficiaire" for x in etapes) or any(
            k[0] == "e0" and v.donnees["accepte"] for k, v in self._reponses(aid).items())
        if benef_ok:
            self._solliciter(aid, le, e, question)

    def verifier_candidat(self, benef: Profil, p: Profil, concept: Optional[str], opp: Opportunite) -> dict:
        """Conditions d'une alternative : les DURES sont garanties par la détection ; les SOUPLES sont dites."""
        ok = [f"déclare : {self.tax.libelle(concept)}" if concept else "déclare la capacité",
              "accepte d'être sollicitée", "profil récent", "langue commune", "aucun refus antérieur"]
        a_verifier = []
        if p.note_disponibilite:
            a_verifier.append(f"disponibilité ({p.note_disponibilite})")
        if opp.evenement and not agenda.communs(benef.creneaux, p.creneaux, self.r.aujourd_hui):
            a_verifier.append("aucun créneau commun déclaré dans les 14 prochains jours")
        return {"ok": ok, "a_verifier": a_verifier}

    def _levee(self, benef: Profil, concept: Optional[str], exclus: set[str]) -> dict:
        if not concept:
            return {}
        d = Detecteur(self.r, self.tax, exclus=self.exclus)
        r = d.raisons_blocage(benef, concept, None)
        restants = [x for x in d.fournisseurs(benef, concept) if x["id"] not in exclus]
        if restants:
            return {"texte": f"{len(restants)} personne(s) éligible(s) déjà sollicitée(s) ou au budget d'attention atteint"}
        if r["absente"]:
            return {"texte": "personne d'autre ne déclare cette capacité : manque du Club, signalé à l'animatrice"}
        return {"texte": "d'autres la déclarent mais une règle dure les écarte : " + ", ".join(f"{k} ({v})" for k, v in r["raisons"].items())}

    # ------------------------------------------------------------------ perturbations (le réseau change pendant l'action)
    @atomique
    def retirer_membre(self, membre: str, le: date, raison: str = "capacité retirée du réseau") -> list[str]:
        """Un membre quitte le réseau ou retire sa capacité : chaque activation en cours qui comptait sur lui se replanifie."""
        self.exclus.add(membre)
        touchees = []
        for aid in self.activations():
            etat = self.etat(aid)
            if etat in FINAUX or etat in ("TERMINEE", "RESULTAT_INCONNU"):
                continue
            for e in self.plan(aid)["etapes"]:
                if e.get("membre") == membre and e["type"] in ("contribution", "animation"):
                    touchees.append(aid)
                    if etat in ("EN_ATTENTE_ACCORD", "ACTIVEE"):
                        self._bloquer(aid, le, e, raison)
                    elif etat == "PLANIFIEE":
                        self._replanifier_avant_lancement(aid, le, e["id"])
        return touchees

    @atomique
    def changer_contraintes(self, aid: str, le: date, langue: Optional[str] = None, anonyme: Optional[bool] = None) -> None:
        """Le jury change une contrainte AVANT le lancement : le plan est recalculé (version suivante), jamais bricolé."""
        if self.etat(aid) != "PLANIFIEE":
            raise Conflit("les contraintes se changent avant les premières sollicitations")
        p = self.plan(aid)
        opp = Opportunite(**p["opportunite"])
        etapes = self._planifier(opp, langue)
        for e in etapes:
            if e.get("incompatible") and e.get("alternatives"):
                ok = [x for x in e["alternatives"] if langue in self.r.par_id()[x].langues]
                if ok:
                    e.update(membre=ok[0], alternatives=ok[1:], remplacement_par_contrainte=True)
                    del e["incompatible"]
        self._ecrire("ACTIVATION_PLAN", le, [], **(p | {"etapes": etapes, "version": p["version"] + 1, "langue": langue,
                                                         "anonyme": p["anonyme"] if anonyme is None else anonyme}))
        bloquantes = [e["libelle"] for e in etapes if e.get("incompatible")]
        self._transition(aid, le, "PLANIFIEE", "Planificateur",
                         "contraintes modifiées : " + ", ".join(x for x in (f"langue {langue}" if langue else "",
                                                                           "demande anonyme" if anonyme else "") if x)
                         + (f" ; impossible pour : {', '.join(bloquantes)}" if bloquantes else " ; plan recalculé"))

    def _replanifier_avant_lancement(self, aid: str, le: date, etape_id: str) -> None:
        p = self.plan(aid)
        etapes = [dict(e) for e in p["etapes"]]
        e = next(x for x in etapes if x["id"] == etape_id)
        alt = [x for x in e.get("alternatives", []) if x not in self.exclus]
        if alt:
            e.update(membre=alt[0], alternatives=alt[1:])
        else:
            e.update(incompatible="plus personne d'éligible")
        self._ecrire("ACTIVATION_PLAN", le, [], **(p | {"etapes": etapes, "version": p["version"] + 1}))
        self._transition(aid, le, "PLANIFIEE", "Planificateur", f"un membre du plan a quitté le réseau : « {e['libelle']} » "
                         + ("réattribuée" if alt else "sans alternative"))

    # ------------------------------------------------------------------ contrôle du Club et du membre
    @atomique
    def mettre_en_pause(self, aid: str, le: date, par: str = "animatrice") -> None:
        if self.etat(aid) not in PAUSABLES:
            raise Conflit("seule une activation planifiée ou en cours peut être mise en pause")
        self._transition(aid, le, "EN_PAUSE", "Club", f"mise en pause par {par}", reprise=self.etat(aid))

    @atomique
    def reprendre(self, aid: str, le: date) -> None:
        if self.etat(aid) != "EN_PAUSE":
            raise Conflit("cette activation n'est pas en pause")
        vers = self._evs(aid, "ACTIVATION")[-1].donnees["details"]["reprise"]
        self._transition(aid, le, vers, "Club", "reprise")

    @atomique
    def annuler(self, aid: str, le: date, par: str = "animatrice") -> None:
        if self.etat(aid) in FINAUX or self.etat(aid) in ("TERMINEE", "RESULTAT_INCONNU"):
            raise Conflit("activation déjà terminée")
        self._transition(aid, le, "ANNULEE", "Club", f"annulée par {par} ; les personnes sollicitées sont libérées")

    @atomique
    def retirer_consentement(self, aid: str, le: date, membre: str) -> None:
        """Un membre qui avait accepté se retire : l'étape repart en replanification ; sa visibilité est retirée."""
        if self.etat(aid) not in ("EN_ATTENTE_ACCORD", "ACTIVEE"):
            raise Conflit("retrait possible tant que l'activation est en cours")
        e = next((x for x in self.plan(aid)["etapes"] if x.get("membre") == membre and x["type"] in ("contribution", "animation")), None)
        if e is None or not (self._reponses(aid).get((e["id"], membre)) and self._reponses(aid)[(e["id"], membre)].donnees["accepte"]):
            raise Interdit("seule une personne qui a accepté peut retirer son accord")
        self._ecrire("RETRAIT_CONSENTEMENT", le, [membre], aid=aid, etape=e["id"], geste="humain")
        self._bloquer(aid, le, e, "une personne a retiré son accord")

    @atomique
    def retirer_capacite(self, membre: str, concept: str, le: date) -> list[str]:
        """Un membre retire une capacité de son profil : les plans qui comptaient dessus se replanifient."""
        touchees = []
        for aid in self.activations():
            etat = self.etat(aid)
            for e in self.plan(aid)["etapes"]:
                if e.get("membre") == membre and e.get("concept") == concept and e["type"] in ("contribution", "animation"):
                    if etat in ("EN_ATTENTE_ACCORD", "ACTIVEE"):
                        touchees.append(aid)
                        self._bloquer(aid, le, e, "la capacité sollicitée a été retirée du profil")
                    elif etat == "PLANIFIEE":
                        touchees.append(aid)
                        self._replanifier_avant_lancement(aid, le, e["id"])
        return touchees

    @atomique
    def echeances(self, le: date) -> list[str]:
        """Coordinateur : silence au-delà du délai = « sans réponse » (on n'insiste pas) ; résultat non confirmé = INCONNU."""
        faits = []
        for aid in self.activations():
            etat = self.etat(aid)
            if etat == "EN_ATTENTE_ACCORD":
                rep = self._reponses(aid)
                for (etape, membre), s in self._sollicitations(aid).items():
                    if (etape, membre) not in rep and (le - s.le).days >= DELAI_REPONSE_JOURS and self.etat(aid) == "EN_ATTENTE_ACCORD":
                        e = next(x for x in self.plan(aid)["etapes"] if x["id"] == etape)
                        if e.get("membre") != membre:
                            continue
                        self._ecrire("REPONSE", le, [membre], aid=aid, etape=etape, accepte=False, geste="sans_reponse")
                        self._bloquer(aid, le, e, f"sans réponse après {DELAI_REPONSE_JOURS} jours")
                        faits.append(aid)
            elif etat == "TERMINEE":
                fin = self._evs(aid, "ACTIVATION")[-1].le
                if (le - fin).days >= DELAI_RESULTAT_JOURS:
                    self._transition(aid, le, "RESULTAT_INCONNU", "Vérificateur",
                                     f"aucune confirmation {DELAI_RESULTAT_JOURS} jours après la fin : on ne présume pas d'un succès")
                    faits.append(aid)
        return faits

    # ------------------------------------------------------------------ contributions, résultat, mémoire
    @atomique
    def contribuer(self, aid: str, le: date, membre: str, nature: str, titre: str, contenu: str,
                   reutilisable: bool = False, attribution: bool = False) -> None:
        if self.etat(aid) != "ACTIVEE":
            raise Conflit("on contribue à une activation dont tous les accords sont donnés")
        e = next((x for x in self.plan(aid)["etapes"] if x.get("membre") == membre and x["type"] in ("contribution", "animation")), None)
        if e is None:
            raise Interdit("seule une personne engagée dans le plan contribue")
        if nature not in NATURES:
            raise Invalide("nature de contribution inconnue")
        if not titre.strip():
            raise Invalide("une contribution a un titre")
        if any(x.donnees["etape"] == e["id"] for x in self._evs(aid, "CONTRIBUTION_RECUE")):
            raise Conflit("contribution déjà reçue pour cette étape")
        self._ecrire("CONTRIBUTION_RECUE", le, [membre], aid=aid, etape=e["id"], nature=nature, titre=titre.strip()[:120],
                     contenu=contenu.strip()[:4000], reutilisable=reutilisable, attribution=attribution, geste="humain")
        benef = self.opportunite(aid).beneficiaire
        if benef and benef != membre:                  # le réseau change : une collaboration réelle crée une relation
            self._ecrire("COLLABORATION", le, sorted([benef, membre]), aid=aid, nature=nature)
        attendues = {x["id"] for x in self.plan(aid)["etapes"] if x["type"] in ("contribution", "animation")}
        recues = {x.donnees["etape"] for x in self._evs(aid, "CONTRIBUTION_RECUE")}
        if attendues <= recues:
            self._transition(aid, le, "TERMINEE", "Coordinateur", f"{len(recues)} contribution(s) reçue(s)")

    @atomique
    def confirmer(self, aid: str, le: date, membre: str, verdict: str, etape_suivante: bool, preuve: str = "") -> dict:
        """Vérificateur : SEUL le bénéficiaire déclare l'effet. Un effet confirmé devient un motif vérifié (Mémoire)."""
        opp = self.opportunite(aid)
        if opp.beneficiaire != membre:
            raise Interdit("seul le bénéficiaire confirme l'effet")
        if verdict not in VERDICTS:
            raise Invalide("verdict inconnu")
        if self.etat(aid) not in ("TERMINEE", "RESULTAT_INCONNU"):
            raise Conflit("on confirme l'effet d'une activation terminée")
        self._ecrire("RESULTAT_DECLARE", le, [membre], aid=aid, verdict=verdict, etape_suivante=etape_suivante,
                     preuve=preuve[:300], geste="humain")
        self._transition(aid, le, VERDICTS[verdict], "Vérificateur", f"déclaré par le bénéficiaire : {verdict}"
                         + (" ; prochaine étape débloquée" if etape_suivante else ""))
        if verdict in ("debloque", "partiel"):
            p = self.plan(aid)
            contribs = [x for x in self._evs(aid, "CONTRIBUTION_RECUE")]
            par_id = self.r.par_id()
            benef = par_id.get(membre)
            if opp.motif:
                apprentissage.confirmer_reutilisation(self.m, le, opp.motif, aid, verdict, self.statut)
            else:
                apprentissage.enregistrer(
                    self.m, le, type_=opp.type, secteur=benef.secteurs[0] if benef and benef.secteurs else None,
                    concepts=sorted({e["concept"] for e in p["etapes"] if e.get("concept") and e["type"] in ("contribution", "animation")}
                                    or {c for c in opp.capacites if c}), contributeurs=[x.acteurs[0] for x in contribs],
                    sequence=[e["libelle"] for e in p["etapes"]],
                    contributions=[{"nature": x.donnees["nature"], "titre": x.donnees["titre"], "contenu": x.donnees["contenu"],
                                    "reutilisable": x.donnees["reutilisable"], "attribution": x.donnees.get("attribution", False),
                                    "auteur": x.acteurs[0], "concept": next(
                                        (e.get("concept") for e in p["etapes"] if e["id"] == x.donnees["etape"]), None)}
                                   for x in contribs if x.donnees["reutilisable"]],
                    resultat=verdict, activation=aid, statut=self.statut)
        return self.resultat(aid)

    @atomique
    def reutiliser(self, aid: str, le: date) -> None:
        """Opportunité MÉMOIRE : la ressource vérifiée est transmise ; personne n'est sollicité."""
        opp = self.opportunite(aid)
        if opp.type != "MEMOIRE" or self.etat(aid) != "ACTIVEE":
            raise Conflit("seule une opportunité mémoire acceptée par son bénéficiaire se réutilise")
        self._transition(aid, le, "TERMINEE", "Mémoire", "ressource vérifiée transmise ; aucune personne sollicitée")

    # ------------------------------------------------------------------ lecture
    def resultat(self, aid: str) -> dict:
        etat = self.etat(aid)
        contribs = self._evs(aid, "CONTRIBUTION_RECUE")
        dec = self._evs(aid, "RESULTAT_DECLARE")
        attendues = [e for e in self.plan(aid)["etapes"] if e["type"] in ("contribution", "animation")]
        return {"contribution": f"{len(contribs)}/{len(attendues)} reçue(s)",
                "confirmation": ("oui" if dec and dec[-1].donnees["verdict"] != "non" else "non" if dec else "en attente"),
                "etape_suivante": ("débloquée" if dec and dec[-1].donnees["etape_suivante"] else "non" if dec else "inconnue"),
                "preuve": [x.donnees["titre"] for x in contribs] + ([dec[-1].donnees["preuve"]] if dec and dec[-1].donnees["preuve"] else []),
                "statut": {"RESULTAT_CONFIRME": "DEMANDE DÉBLOQUÉE", "RESULTAT_PARTIEL": "PARTIELLEMENT DÉBLOQUÉE",
                           "RESULTAT_NEGATIF": "NON DÉBLOQUÉE", "RESULTAT_INCONNU": "RÉSULTAT INCONNU"}.get(etat, "EN COURS")}

    def journal(self, aid: str) -> list[dict]:
        """Vue ANIMATRICE (coulisses) : chaque transition, son agent et sa raison."""
        return [{"le": e.le.isoformat(), "de": e.donnees["de"], "etat": e.donnees["etat"], "agent": e.donnees["agent"],
                 "raison": e.donnees["raison"], "details": e.donnees.get("details", {})} for e in self._evs(aid, "ACTIVATION")]

    def vue_membre(self, aid: str, membre: str) -> dict:
        """Ce que voit une personne SOLLICITÉE : sa seule étape. Qui demande n'est nommé qu'après SON accord, et jamais si
        la demande est anonyme. Jamais les autres personnes, les autres étapes, les refus, ni l'opportunité complète."""
        p = self.plan(aid)
        mes = [e for e in p["etapes"] if (e["id"], membre) in self._sollicitations(aid)]
        if not mes:
            raise Interdit("vous n'êtes pas sollicité(e) pour cette activation")
        par_id = self.r.par_id()
        opp = Opportunite(**p["opportunite"])
        benef = par_id.get(opp.beneficiaire or "")
        rep = self._reponses(aid)
        accepte = any(rep.get((e["id"], membre)) and rep[(e["id"], membre)].donnees["accepte"] for e in mes)
        est_benef = benef is not None and benef.id == membre
        if est_benef or benef is None:
            qui = None
        elif accepte and not p["anonyme"]:
            qui = benef.nom
        else:
            qui = f"Une personne du Club (secteur : {self.tax.libelle(benef.secteurs[0]) if benef.secteurs else 'non précisé'})"
        creneaux = (agenda.communs(benef.creneaux, par_id[membre].creneaux, self.r.aujourd_hui)
                    if accepte and benef and not est_benef and not p["anonyme"] else [])
        vue = {"qui_demande": qui, "votre_part": [{"libelle": e["libelle"], "demande": e["demande"]
                                                   + (f" — {e['question']}" if e.get("question") and e["membre"] == membre else "")}
                                                  for e in mes],
               "accepte": accepte, "creneaux_communs": creneaux}
        if est_benef:
            vue["pourquoi"] = "Le Club a repéré une occasion qui correspond à ce que vous cherchez ; rien n'est transmis sans votre accord."
            vue["ce_qui_serait_fait"] = [e["libelle"] for e in p["etapes"] if e["type"] in ("contribution", "animation", "hors_club")]
        return vue

    def vue_beneficiaire(self, aid: str, membre: str) -> dict:
        """Ce que voit le bénéficiaire : l'avancement ; une personne n'est nommée qu'après avoir ACCEPTÉ ; un refus ou
        un silence ne sont jamais attribués (« une autre personne est sollicitée »)."""
        opp = self.opportunite(aid)
        if opp.beneficiaire != membre:
            raise Interdit("seul le bénéficiaire voit le suivi")
        par_id = self.r.par_id()
        rep, sol = self._reponses(aid), self._sollicitations(aid)
        lignes = []
        for e in self.plan(aid)["etapes"]:
            if e["type"] not in ("contribution", "animation", "hors_club"):
                continue
            if e["type"] == "hors_club":
                lignes.append({"etape": e["libelle"], "statut": "à trouver hors du Club"})
                continue
            k = (e["id"], e["membre"])
            a_accepte = k in rep and rep[k].donnees["accepte"]
            deja = any(kk[0] == e["id"] and kk[1] != e["membre"] for kk in sol)
            statut = ("a accepté : " + par_id[e["membre"]].nom if a_accepte else
                      ("une autre personne est sollicitée" if deja else "sollicitation privée en attente") if k in sol else "pas encore sollicitée")
            lignes.append({"etape": e["libelle"], "statut": statut})
        return {"etat": self.etat(aid), "etapes": lignes, "resultat": self.resultat(aid)}

