"""CLUB PULSE — le service qui fait vivre la boucle, entre les membres, le Club et l'intelligence du réseau.

    MEMBRE → CONTEXTE (note privée, IA) → RÉSEAU (observer, détecter) → OPPORTUNITÉ → CONSENTEMENT → ACTIVATION
    → ADAPTATION (refus, retrait, silence) → CONTRIBUTION → RÉSULTAT (confirmé par le bénéficiaire) → MÉMOIRE → suivante

Frontières tenues ici :
- le moteur (`Reseau`, `Detecteur`, `Moteur`) ne reçoit que des profils PSEUDONYMISÉS ; les identités sont au `Coffre` ;
- tout ce qui sort vers un humain passe par `Rendu` (politique de visibilité), pour CE spectateur ;
- l'IA (Apertus si configuré, sinon repli déterministe déclaré) comprend et rédige ; elle ne décide rien ;
- trois mémoires distinctes : NOTES PRIVÉES (propriétaire seul) · CONTEXTE PARTAGÉ (ce que le membre a choisi de mettre
  dans son profil) · MÉMOIRE VÉRIFIÉE (motifs issus d'un résultat confirmé, anonymisés sauf attribution consentie).
Monde de démonstration FICTIF ; gestes humains joués dans la démonstration et marqués comme tels.
"""
from __future__ import annotations

import hashlib
import hmac
import threading
import time
from datetime import date, timedelta
from typing import Optional

import networkx as nx

from app.models import Offre, Profil
from app.parser_rules import extraire_profil
from app.taxonomy import Taxonomie
from plateforme.affirmations import Statut
from plateforme.memoire import Evt

from . import apprentissage
from . import monde_demo as md
from .activation import FINAUX, ErreurActivation, Moteur
from .detection import Detecteur
from .ia import AppelIA, Intelligence, besoin_de
from .identite import AdhesionsSynthetiques, Coffre
from .modele import BesoinActif, Opportunite
from .politique import MODIFIABLES, Contexte, Rendu, Spectateur, descripteur

LIBELLES_TYPE = {"LATENTE": "Opportunité latente", "SUIVI": "Suite d'une rencontre", "COMPOSITION": "Composition",
                 "COMPLEMENTARITE": "Complémentarité", "CONVERGENCE": "Besoin émergent", "LACUNE": "Manque du Club",
                 "MEMOIRE": "Mémoire vérifiée", "CAPACITE_DORMANTE": "Capacité dormante"}
LIBELLES_ETAT = {"DETECTEE": "détectée", "EVALUEE": "évaluée", "PLANIFIEE": "planifiée", "EN_ATTENTE_ACCORD": "en attente d'accord",
                 "ACTIVEE": "activée", "TERMINEE": "contributions reçues", "BLOQUEE": "bloquée", "REPLANIFICATION": "replanification",
                 "ALTERNATIVE_PROPOSEE": "alternative proposée", "ABANDONNEE": "arrêtée faute d'alternative", "REJETEE": "rejetée",
                 "RESULTAT_CONFIRME": "demande débloquée", "RESULTAT_PARTIEL": "partiellement débloquée",
                 "RESULTAT_NEGATIF": "non débloquée", "RESULTAT_INCONNU": "résultat inconnu", "EN_PAUSE": "en pause", "ANNULEE": "annulée"}


class ErreurPulse(ValueError):
    pass


class ClubPulse:
    def __init__(self, tax: Taxonomie, ia: Optional[Intelligence] = None, secret: str = "demo-seulement"):
        self.tax = tax
        self.verrou = threading.RLock()
        brut = md.construire(sophie_profilee=False)
        self.coffre = Coffre(AdhesionsSynthetiques(brut.profils).importer(), secret=secret)
        self._secret = secret.encode()
        brut.profils = [self.coffre.pseudonymiser(p) for p in brut.profils]    # le moteur ne voit que des pseudonymes
        self.r = brut
        self.moteur = Moteur(self.r, tax)
        self.ia = ia or Intelligence.depuis_environnement(tax, journal=self._tracer_ia)
        self.ia.journal = self._tracer_ia
        self.notes: dict[str, list[dict]] = {}
        self.preferences: dict[str, dict] = {}
        self.ecartees: set[str] = set()
        self.explications: dict[tuple[str, str], dict] = {}
        self._scan: Optional[dict] = None
        self._version_scan = -1
        for pid in self.coffre._personnes:                   # tous ont activé leur compte, sauf la nouvelle venue
            if pid != md.SOPHIE:
                self.coffre.actives.add(pid)

    # ------------------------------------------------------------------ bases
    @property
    def jour(self) -> date:
        return self.r.aujourd_hui

    def _tracer_ia(self, a: AppelIA) -> None:
        # la latence reste dans `ia.appels` (mesure) ; le journal garde un contenu déterministe, donc rejouable à l'octet
        self.r.memoire.ajouter(Evt(type="APPEL_IA", le=self.jour, statut=Statut.SIMULE, donnees=a.model_dump(exclude={"latence_ms"})))

    def profil(self, pid: str) -> Profil:
        p = self.r.par_id().get(pid)
        if p is None:
            raise ErreurPulse("membre inconnu")
        return p

    def _remplacer_profil(self, p: Profil) -> None:
        self.r.profils = [p if q.id == p.id else q for q in self.r.profils]
        self._scan = None

    def contexte(self) -> Contexte:
        m = self.r.memoire
        relations = {frozenset(e.acteurs[:2]) for e in m.evenements("RENCONTRE", "COLLABORATION") if len(e.acteurs) >= 2}
        consentis: set[tuple[str, str]] = set()
        for aid in self.moteur.activations():
            p = self.moteur.plan(aid)
            opp = Opportunite(**p["opportunite"])
            rep = self.moteur._reponses(aid)
            acceptes = {k[1] for k, v in rep.items() if v.donnees["accepte"]}
            retires = {e.acteurs[0] for e in self.moteur._evs(aid, "RETRAIT_CONSENTEMENT")}
            b = opp.beneficiaire
            if not b or (b not in acceptes and any(e["type"] == "accord_beneficiaire" for e in p["etapes"])):
                continue
            for e in p["etapes"]:
                x = e.get("membre")
                if e["type"] in ("contribution", "animation") and x in acceptes and x not in retires:
                    consentis.add((b, x))                                   # le bénéficiaire voit qui a accepté
                    if not p["anonyme"]:
                        consentis.add((x, b))                               # et l'inverse, sauf demande anonyme
        prefs = {k: {a: v for a, v in d.items() if a in MODIFIABLES} for k, d in self.preferences.items()}
        return Contexte(relations=relations, consentis=consentis, preferences=prefs)  # type: ignore[arg-type]

    def rendu(self) -> Rendu:
        return Rendu(self.coffre, self.r.profils, self.tax, self.contexte())

    def pseudonymes(self) -> set[str]:
        return {self.coffre.pseudonyme(p) for p in self.coffre._personnes}

    # ------------------------------------------------------------------ accès et profil
    def session(self, pid: str) -> str:
        return pid + "." + hmac.new(self._secret, f"session|{pid}".encode(), hashlib.sha256).hexdigest()[:24]

    def verifier_session(self, jeton: str) -> str:
        pid, _, sig = (jeton or "").partition(".")
        if not pid or not hmac.compare_digest(self.session(pid), jeton) or pid not in self.coffre.actives:
            raise ErreurPulse("session invalide")
        return pid

    def activer_compte(self, code: str) -> dict:
        pid = self.coffre.activer(code)
        if not pid:
            raise ErreurPulse("code d'invitation inconnu ou adhésion inactive")
        per = self.coffre.identite(pid)
        org = self.coffre.organisation_de(pid)
        assert per is not None
        return {"session": self.session(pid), "nom": per.nom, "organisation": org.nom if org else None,
                "role": per.role, "profil_complet": bool(self.profil(pid).offre or self.profil(pid).recherche)}

    def proposer(self, texte: str, sens: str) -> list[dict]:
        """Étape 2/3 de l'accueil : le texte libre est analysé ; le membre CONFIRME ou REJETTE chaque proposition."""
        if sens not in ("aide", "cherche") or not texte.strip():
            raise ErreurPulse("texte vide ou sens inconnu")
        cle = "offre" if sens == "aide" else "recherche"
        prop = extraire_profil(("Nous proposons " if sens == "aide" else "Nous cherchons ") + texte.strip()[:300], self.tax)[cle]
        return [{"texte": texte.strip()[:200], "concept": o["concept"], "libelle": o["libelle"]} for o in prop[:3]] + [
            {"texte": texte.strip()[:200], "concept": None, "libelle": "garder tel quel (hors catalogue)"}]

    def onboarding(self, pid: str, aide: list[dict], cherche: list[dict], visible: bool) -> dict:
        """Étapes 2–4 : ce que je peux apporter, ce que je cherche (éléments CONFIRMÉS par le membre), visibilité."""
        def items(lst: list[dict]) -> list[Offre]:
            res = []
            for x in lst[:5]:
                c = x.get("concept")
                if c is not None and c not in self.tax.concepts:
                    raise ErreurPulse(f"capacité inconnue : {c}")
                if str(x.get("texte", "")).strip():
                    res.append(Offre(concept=c, texte=str(x["texte"]).strip()[:200]))
            return res
        p = self.profil(pid)
        offres, recherches = items(aide), items(cherche)
        self._remplacer_profil(p.model_copy(update={"offre": offres, "recherche": recherches,
                                                     "secteurs": [o.concept for o in offres if o.concept][:1],
                                                     "accepte_introductions": visible, "maj": self.jour.isoformat()}))
        return self.vue_profil(pid)

    def modifier_profil(self, pid: str, *, retirer_capacite: Optional[str] = None, ajouter_recherche: Optional[str] = None,
                        disponible: Optional[bool] = None, accepte: Optional[bool] = None,
                        visibilite: Optional[dict[str, str]] = None) -> dict:
        p = self.profil(pid)
        maj: dict = {"maj": self.jour.isoformat()}
        if retirer_capacite:
            maj["offre"] = [o for o in p.offre if o.concept != retirer_capacite]
        if ajouter_recherche:
            prop = extraire_profil(f"Nous cherchons {ajouter_recherche}", self.tax)["recherche"]
            c = prop[0]["concept"] if prop else None
            if not any(r.texte == ajouter_recherche for r in p.recherche):
                maj["recherche"] = [*p.recherche, Offre(concept=c, texte=ajouter_recherche[:200])]
        if disponible is not None:
            maj["disponible"] = disponible
        if accepte is not None:
            maj["accepte_introductions"] = accepte
        if visibilite:
            for k, v in visibilite.items():
                if k not in MODIFIABLES or v not in MODIFIABLES[k]:
                    raise ErreurPulse(f"visibilité non modifiable : {k} → {v}")
            self.preferences.setdefault(pid, {}).update(visibilite)
        self._remplacer_profil(p.model_copy(update=maj))
        if retirer_capacite:
            self.moteur.retirer_capacite(pid, retirer_capacite, self.jour)
        if disponible is False or accepte is False:
            for aid in self.moteur.activations():
                if self.moteur.etat(aid) in ("EN_ATTENTE_ACCORD", "PLANIFIEE") and any(
                        e.get("membre") == pid and e["type"] in ("contribution", "animation") for e in self.moteur.plan(aid)["etapes"]):
                    self.moteur.retirer_membre(pid, self.jour, "la personne a suspendu les sollicitations")
                    self.moteur.exclus.discard(pid)
        return self.vue_profil(pid)

    def _element(self, o: Offre) -> dict:
        return {"concept": o.concept, "libelle": self.tax.libelle(o.concept) if o.concept else "hors catalogue", "texte": o.texte}

    def vue_profil(self, pid: str) -> dict:
        p = self.profil(pid)
        per = self.coffre.identite(pid)
        org = self.coffre.organisation_de(pid)
        prefs = {**{k: "SUR_CONSENTEMENT" for k in ("nom", "organisation")}, **{k: "CLUB_DECOUVRABLE" for k in ("capacites", "interets")},
                 **{k: v for k, v in self.preferences.get(pid, {}).items()}}
        return {"nom": per.nom if per else None, "organisation": org.nom if org else None, "role": per.role if per else None,
                "adhesion": "carte entreprise" if per and self.coffre.adhesions[per.adhesion_id].formule == "entreprise" else "nominative",
                "je_peux_aider": [self._element(o) for o in p.offre], "je_cherche": [self._element(r) for r in p.recherche],
                "langues": p.langues, "disponible": p.disponible, "sollicitable": p.accepte_introductions, "visibilite": prefs,
                "note": "Votre nom et votre entreprise ne sont montrés qu'après votre accord ; vos notes restent privées."}

    # ------------------------------------------------------------------ mémoire privée : capture d'une rencontre
    def capturer(self, pid: str, texte: str, evenement: Optional[str] = None) -> dict:
        if not texte.strip() or len(texte) > 2000:
            raise ErreurPulse("note vide ou trop longue")
        rep = self.ia.capturer_rencontre(texte)
        c = rep.sortie
        # résolution de la personne mentionnée UNIQUEMENT parmi les relations du membre (jamais tout l'annuaire)
        avec = None
        if c.get("personne_mentionnee"):
            mien = [x for pair in self.contexte().relations if pid in pair for x in pair if x != pid]
            for x in sorted(mien):
                per = self.coffre.identite(x)
                if per and c["personne_mentionnee"].split()[0].lower() in per.nom.lower():
                    avec = x
                    break
        propositions = []
        if c.get("besoin_du_membre"):
            propositions.append({"type": "ajouter_recherche", "texte": c["besoin_du_membre"]["extrait"],
                                 "libelle": f"Ajouter à « je cherche » : {self.tax.libelle(c['besoin_du_membre']['concept'])}"})
        note = {"id": f"note{len(self.notes.get(pid, [])) + 1}", "le": self.jour.isoformat(), "texte": texte.strip(),
                "evenement": evenement, "avec": avec, "capture": c, "propositions": propositions, "partagee": [],
                "ia": {"fournisseur": rep.appel.fournisseur, "modele": rep.appel.modele, "statut": rep.appel.statut,
                       "repli": rep.appel.repli, "prompt": rep.appel.prompt}}
        self.notes.setdefault(pid, []).append(note)
        return self._vue_note(pid, note)

    def partager(self, pid: str, note_id: str, index: int) -> dict:
        """Le membre choisit explicitement ce qui quitte sa note privée (et rien d'autre)."""
        note = next((n for n in self.notes.get(pid, []) if n["id"] == note_id), None)
        if note is None or not 0 <= index < len(note["propositions"]):
            raise ErreurPulse("note ou proposition inconnue")
        prop = note["propositions"][index]
        if prop["type"] == "ajouter_recherche":
            self.modifier_profil(pid, ajouter_recherche=prop["texte"].rstrip("."))
        note["partagee"].append(index)
        return self._vue_note(pid, note)

    def _vue_note(self, pid: str, note: dict) -> dict:
        rendu = self.rendu()
        return note | {"avec_nom": rendu.nom(Spectateur("membre", pid), note["avec"]) if note["avec"] else None}

    def notes_de(self, pid: str) -> list[dict]:
        return [self._vue_note(pid, n) for n in self.notes.get(pid, [])]

    # ------------------------------------------------------------------ demande explicite (jury ou membre)
    def demander(self, pid: str, texte: str) -> dict:
        if not 3 <= len(texte.strip()) <= 600:
            raise ErreurPulse("demande vide ou trop longue")
        rep = self.ia.comprendre_demande(texte)
        b = besoin_de(rep)
        # sa PROPRE activité (« pour nos tisanes ») est du contexte, pas un besoin : on la retire et on relit le reste
        p = self.profil(pid)
        propres = {o.concept for o in p.offre if o.concept} | set(p.secteurs)
        exp = [c for c in b.criteres if c.type == "expertise"]
        if exp and all(c.valeur in propres for c in exp):
            reste = texte
            for c in exp:
                if c.extrait:
                    reste = reste.replace(c.extrait, " ")
            relu = besoin_de(self.ia.comprendre_demande(reste))
            if [c for c in relu.criteres if c.type in ("expertise", "texte_libre")]:
                relu.texte = texte
                relu.avertissements.insert(0, "« " + ", ".join(c.extrait or c.libelle for c in exp)
                                           + " » lu comme votre activité (contexte), pas comme un besoin.")
                b = relu
        self.r.besoins.append(BesoinActif(id=f"bj{len(self.r.besoins):05d}", auteur=pid, texte=texte.strip(), le=self.jour, besoin=b))
        self._scan = None
        scan = self.scanner()
        miennes = [o for o in scan["opportunites"]           # seulement ce que ce membre a le droit de voir : où il est aidé
                   if o.beneficiaire == pid or pid in {r.membre for r in o.roles if r.role == "participant"}]
        bloques = [x for x in scan["bloques"] if x["auteur"] == pid]
        return {"compris": [{"type": c.type, "libelle": c.libelle, "extrait": c.extrait, "obligatoire": c.obligatoire}
                            for c in b.criteres] + ([{"type": "contrainte", "libelle": "pas un concurrent direct", "extrait": None,
                                                      "obligatoire": True}] if b.exclure_concurrents else []),
                "incertain": [a.terme for a in b.ambiguites] + b.avertissements,
                "ia": rep.appel.model_dump(include={"fournisseur", "modele", "statut", "repli", "latence_ms"}),
                "opportunites": [self.vue_opportunite(o, Spectateur("membre", pid)) for o in miennes],
                "sans_solution": [self._vue_blocage(x) for x in bloques]}

    def _vue_blocage(self, x: dict) -> dict:
        lib = self.tax.libelle(x["concept"]) if x["concept"] in self.tax.concepts else x["concept"]
        if x["absente"]:
            pourquoi = f"Le Club ne compte aujourd'hui personne qui déclare : {lib}."
            suite = "Signalé à l'animatrice ; précisez si une autre compétence proche vous aiderait."
        else:
            pourquoi = f"Des membres déclarent « {lib} », mais une règle les écarte : " + ", ".join(f"{k} ({v})" for k, v in x["raisons"].items()) + "."
            suite = "La plus petite modification : lever cette contrainte, si elle n'est pas indispensable."
        return {"capacite": lib, "pourquoi": pourquoi, "prochaine_action": suite}

    # ------------------------------------------------------------------ OBSERVER → DÉTECTER
    def scanner(self, force: bool = False) -> dict:
        version = len(self.r.memoire.evenements()) + len(self.r.besoins) + hash(tuple(p.maj + str(len(p.offre)) + str(len(p.recherche))
                                                                                     + str(p.accepte_introductions) + str(p.disponible)
                                                                                     for p in self.r.profils))
        if self._scan is not None and self._version_scan == version and not force:
            return self._scan
        t0 = time.perf_counter()
        d = Detecteur(self.r, self.tax, exclus=set(self.moteur.exclus))
        res = d.detecter()
        en_cours = {self.moteur.plan(a)["opportunite"]["id"] for a in self.moteur.activations()}
        res["opportunites"] = [o for o in res["opportunites"] if o.id not in self.ecartees and o.id not in en_cours]
        m = res["mesures"]
        e = d.e
        res["phases"] = [
            {"etape": "Observer le réseau", "ms": m.get("membres_ms"),
             "detail": f"{len(self.r.profils)} membres, {sum(len(v) for v in e.offreurs.values())} capacités indexées"},
            {"etape": "Lire les relations et leur fraîcheur", "detail": f"{len(e.relies)} relations de moins d'un an", "ms": m.get("relations_ms")},
            {"etape": "Fenêtres d'événements", "detail": f"{len(e.evenements_proches)} événement(s) dans les 30 jours", "ms": None},
            {"etape": "Besoins actifs et complémentarités", "ms": m.get("besoins_ms"),
             "detail": f"{res['besoins']} besoins publiés, {len(res['bloques'])} capacité(s) introuvable(s)"},
            {"etape": "Intérêts latents, suites de rencontres, convergences", "ms": m.get("complementarite_ms"),
             "detail": f"{sum(len(v) for v in e.recherches.values())} intérêts déclarés"},
            {"etape": "Règles de consentement, fraîcheur, concurrence", "ms": None,
             "detail": f"{sum(res['ecartees'].values())} pistes écartées (sans nommer personne)"},
            {"etape": "Opportunités retenues", "detail": f"{len(res['opportunites'])}", "ms": round((time.perf_counter() - t0) * 1000, 1)}]
        self._scan, self._version_scan = res, version
        return res

    def opportunite(self, oid: str) -> Opportunite:
        o = next((x for x in self.scanner()["opportunites"] if x.id == oid), None)
        if o is None:
            raise ErreurPulse("opportunité inconnue ou déjà activée")
        return o

    # ------------------------------------------------------------------ vues d'opportunité (par spectateur)
    def vue_opportunite(self, o: Opportunite, sp: Spectateur) -> dict:
        rendu = self.rendu()
        t = lambda x: rendu.texte(sp, x)  # noqa: E731
        if sp.role == "membre" and sp.id != o.beneficiaire and sp.id not in {r.membre for r in o.roles if r.role == "participant"}:
            raise ErreurPulse("cette opportunité ne vous concerne pas (encore) : vous serez sollicité·e en privé si elle est activée")
        roles = [{"qui": rendu.nom(sp, r.membre), "role": r.role, "capacite": self.tax.libelle(r.concept) if r.concept else None,
                  "preuve": r.preuve if sp.role == "animatrice" or r.membre == sp.id else None}
                 for r in o.roles if r.membre != sp.id]
        return {"id": o.id, "type": o.type, "type_libelle": LIBELLES_TYPE.get(o.type, o.type), "titre": t(o.titre),
                "pourquoi_maintenant": t(o.pourquoi_maintenant or ""), "pourquoi": [t(x) for x in o.raisonnement],
                "manque": o.manque, "action": t(o.action), "risques": [t(x) for x in o.risques], "confiance": o.confiance,
                "confiance_raisons": o.confiance_raisons, "demandes_servies": o.demandes_servies,
                "personnes_a_solliciter": o.personnes_a_solliciter, "capacites": [self.tax.libelle(c) for c in o.capacites if c in self.tax.concepts],
                "roles": roles, "mecanismes": [t(x) for x in o.mecanismes],
                "evenement": next((e.nom for e in self.r.evenements if e.id == o.evenement), None),
                "partage": ("Avant tout accord : votre secteur et ce que vous cherchez, rien d'autre. Votre nom seulement aux personnes "
                            "qui acceptent ; vos coordonnées seulement après accord mutuel."),
                "activable": o.type != "LACUNE"}

    def expliquer(self, oid: str, sp: Spectateur) -> dict:
        """L'IA reformule le « pourquoi » à partir de faits PSEUDONYMISÉS ; le texte est contrôlé puis rendu pour le spectateur."""
        o = self.opportunite(oid)
        cle = (oid, sp.role + (sp.id or ""))
        if cle not in self.explications:
            faits = {"titre": o.titre, "raisonnement": o.raisonnement, "manque": o.manque, "action": o.action,
                     "risques": o.risques, "personnes_a_solliciter": o.personnes_a_solliciter}
            rep = self.ia.expliquer(faits, self.pseudonymes())
            self.explications[cle] = {"texte": rep.sortie["explication"], "appel": rep.appel.model_dump(
                include={"fournisseur", "modele", "prompt", "statut", "repli", "latence_ms", "trace"})}
        x = self.explications[cle]
        return {"texte": self.rendu().texte(sp, x["texte"]), "ia": x["appel"],
                "source": ("Apertus (texte contrôlé : fidèle aux faits)" if x["appel"]["fournisseur"] == "apertus" and not x["appel"]["repli"]
                           else "règles du moteur (aucun modèle génératif utilisé)")}

    # ------------------------------------------------------------------ ACTIVER
    def activer(self, oid: str, par: Spectateur, anonyme: bool = False, langue: Optional[str] = None) -> str:
        o = self.opportunite(oid)
        if par.role == "membre" and par.id != o.beneficiaire:
            raise ErreurPulse("seul le bénéficiaire (ou le Club) peut activer cette opportunité")
        aid = self.moteur.creer(o, self.jour, anonyme=anonyme, langue=langue)
        if self.moteur.etat(aid) == "PLANIFIEE" and not (par.role == "animatrice" and langue):
            self.moteur.lancer(aid, self.jour)
            if par.role == "membre" and par.id is not None and par.id == o.beneficiaire:      # c'est lui qui le demande : son accord est donné
                self.moteur.repondre(aid, self.jour, par.id, True)
        self._scan = None
        return aid

    def lancer(self, aid: str) -> None:
        self.moteur.lancer(aid, self.jour)

    def demandes_pour(self, pid: str) -> list[dict]:
        """Sollicitations privées ouvertes pour ce membre, avec un message rédigé (IA contrôlée ou gabarit)."""
        res = []
        rep = {k for a in self.moteur.activations() for k in self.moteur._reponses(a)}
        for ev in self.r.memoire.evenements("SOLLICITATION_PRIVEE"):
            aid = ev.donnees["aid"]
            if ev.acteurs[0] != pid or (ev.donnees["etape"], pid) in rep or self.moteur.etat(aid) in FINAUX:
                continue
            res.append(self.vue_demande(aid, pid))
        return res

    def vue_demande(self, aid: str, pid: str) -> dict:
        v = self.moteur.vue_membre(aid, pid)
        opp = self.moteur.opportunite(aid)
        sp = Spectateur("membre", pid)
        rendu = self.rendu()
        etape = next(e for e in self.moteur.plan(aid)["etapes"] if e.get("membre") == pid and (e["id"], pid) in self.moteur._sollicitations(aid))
        est_benef = opp.beneficiaire == pid
        benef = self.r.par_id().get(opp.beneficiaire or "")
        capa = next((o.texte for o in self.profil(pid).offre if o.concept == etape.get("concept")), None)
        message = None
        if not est_benef and benef:
            per = self.coffre.identite(benef.id)
            faits = {"capacite_declaree": capa or etape["libelle"], "demande": etape["demande"],
                     "secteur_demandeur": self.tax.libelle(benef.secteurs[0]) if benef.secteurs else "non précisé",
                     "partage": "votre nom et votre courriel à cette personne seulement si vous acceptez ; rien si vous refusez"}
            r_ = self.ia.rediger_sollicitation(faits, [per.nom if per else "", self.coffre.pseudonyme(benef.id)])
            message = {"texte": r_.sortie["message"], "ia": r_.appel.model_dump(include={"fournisseur", "modele", "statut", "repli"})}
        return {"activation": aid, "etat": self.moteur.etat(aid), "pour_vous": est_benef,
                "titre": ("Le Club a repéré une occasion pour vous" if est_benef else "Un membre du Club a une demande qui correspond à votre capacité"),
                "pourquoi_vous": (None if est_benef else f"Votre capacité déclarée : « {capa or etape['libelle']} »"),
                "qui_demande": rendu.texte(sp, v["qui_demande"]) if v["qui_demande"] else None,
                "votre_part": v["votre_part"], "accepte": v["accepte"], "creneaux_communs": v["creneaux_communs"],
                "ce_qui_serait_fait": v.get("ce_qui_serait_fait"),
                "visibilite": ("Votre identité reste cachée tant que vous n'avez pas accepté. Si vous refusez, personne ne le saura."
                               if not est_benef else "Rien n'est transmis à personne avant votre accord."),
                "message": message}

    def repondre(self, aid: str, pid: str, accepte: bool) -> None:
        self.moteur.repondre(aid, self.jour, pid, accepte)
        self._scan = None

    def contribuer(self, aid: str, pid: str, nature: str, titre: str, contenu: str, reutilisable: bool = False,
                   attribution: bool = False) -> None:
        self.moteur.contribuer(aid, self.jour, pid, nature, titre, contenu, reutilisable, attribution)

    def confirmer(self, aid: str, pid: str, verdict: str, etape_suivante: bool, pourquoi: str = "") -> dict:
        return self.moteur.confirmer(aid, self.jour, pid, verdict, etape_suivante, pourquoi)

    def reutiliser(self, aid: str) -> None:
        self.moteur.reutiliser(aid, self.jour)

    # ------------------------------------------------------------------ vues d'activation
    def vue_activation(self, aid: str, sp: Spectateur) -> dict:
        opp = self.moteur.opportunite(aid)
        participants = {e.get("membre") for e in self.moteur.plan(aid)["etapes"] if e.get("membre")}
        if sp.role == "membre" and sp.id not in participants:
            raise ErreurPulse("activation inconnue")
        rendu = self.rendu()
        etat = self.moteur.etat(aid)
        chrono = [{"etat": j["etat"], "libelle": LIBELLES_ETAT.get(j["etat"], j["etat"]), "le": j["le"],
                   "agent": j["agent"], "raison": rendu.texte(sp, j["raison"]) if sp.role == "animatrice" else self._raison_publique(j)}
                  for j in self.moteur.journal(aid)]
        contribs = [{"qui": rendu.nom(sp, e.acteurs[0]), "nature": e.donnees["nature"], "titre": e.donnees["titre"],
                     "contenu": e.donnees["contenu"], "le": e.le.isoformat()} for e in self.moteur._evs(aid, "CONTRIBUTION_RECUE")]
        vue = {"id": aid, "numero": self.moteur.activations().index(aid) + 1, "etat": etat, "etat_libelle": LIBELLES_ETAT.get(etat, etat),
               "objectif": rendu.texte(sp, opp.titre), "type": LIBELLES_TYPE.get(opp.type, opp.type), "chronologie": chrono,
               "resultat": self.moteur.resultat(aid), "contributions": contribs if sp.role == "animatrice" or sp.id == opp.beneficiaire else
               [c for c, e in zip(contribs, self.moteur._evs(aid, "CONTRIBUTION_RECUE"), strict=True) if e.acteurs[0] == sp.id],
               "anonyme": self.moteur.plan(aid)["anonyme"]}
        if sp.role == "animatrice":
            vue["etapes"] = []
            for e in self.moteur.plan(aid)["etapes"]:
                statut = self._statut_etape(aid, e)
                cache = statut == "a décliné"             # même le Club ne sait pas QUI a dit non
                vue["etapes"].append({"etape": e["libelle"], "type": e["type"], "statut": "une personne a décliné" if cache else statut,
                                      "qui": None if cache or not e.get("membre") else rendu.nom(sp, e["membre"]),
                                      "question": e.get("question"), "reserve": len(e.get("alternatives") or [])})
        elif sp.id is not None and sp.id == opp.beneficiaire:
            vb = self.moteur.vue_beneficiaire(aid, sp.id)
            vue["etapes"] = [{"etape": x["etape"], "statut": rendu.texte(sp, x["statut"])} for x in vb["etapes"]]
            vue["contacts"] = [{"qui": rendu.nom(sp, x), "contact": rendu.contact(sp, x)} for x in sorted(participants - {sp.id})
                               if rendu.contact(sp, x)]
            vue["a_confirmer"] = etat in ("TERMINEE", "RESULTAT_INCONNU")
            vue["reutilisation"] = opp.type == "MEMOIRE" and etat == "ACTIVEE"
        elif sp.id is not None:
            vue["etapes"] = [{"etape": x["libelle"], "statut": "votre part"} for x in self.moteur.vue_membre(aid, sp.id)["votre_part"]]
            vue["peut_contribuer"] = etat == "ACTIVEE" and not any(e.acteurs[0] == sp.id for e in self.moteur._evs(aid, "CONTRIBUTION_RECUE"))
        vue["evolution"] = self.evolution(aid, sp) if etat in ("TERMINEE", "RESULTAT_CONFIRME", "RESULTAT_PARTIEL", "RESULTAT_INCONNU") else None
        return vue

    @staticmethod
    def _raison_publique(j: dict) -> str:
        return {"BLOQUEE": "Une personne sollicitée n'est pas disponible : le Club cherche une alternative.",
                "REPLANIFICATION": "Le plan est recalculé.", "ALTERNATIVE_PROPOSEE": "Une alternative a été trouvée et sollicitée en privé.",
                "ABANDONNEE": "Aucune alternative éligible : l'activation s'arrête proprement.",
                }.get(j["etat"], LIBELLES_ETAT.get(j["etat"], j["etat"]).capitalize() + ".")

    def _statut_etape(self, aid: str, e: dict) -> str:
        if e["type"] == "hors_club":
            return "à trouver hors du Club"
        if not e.get("membre"):
            return ""
        rep, sol = self.moteur._reponses(aid), self.moteur._sollicitations(aid)
        k = (e["id"], e["membre"])
        if any(x.donnees["etape"] == e["id"] for x in self.moteur._evs(aid, "CONTRIBUTION_RECUE")):
            return "contribution reçue"
        if k in rep:
            return "a accepté" if rep[k].donnees["accepte"] else "a décliné"
        return "sollicité·e en privé" if k in sol else "pas encore sollicité·e"

    def activations_de(self, pid: str) -> list[dict]:
        sp = Spectateur("membre", pid)
        res = []
        for aid in self.moteur.activations():
            p = self.moteur.plan(aid)
            opp = Opportunite(**p["opportunite"])
            engage = opp.beneficiaire == pid or any(k[1] == pid and v.donnees["accepte"] for k, v in self.moteur._reponses(aid).items())
            if engage:
                res.append(self.vue_activation(aid, sp))
        return res

    # ------------------------------------------------------------------ ÉVOLUTION DU RÉSEAU (preuve secondaire)
    def evolution(self, aid: str, sp: Spectateur) -> dict:
        opp = self.moteur.opportunite(aid)
        noeuds = [r.membre for r in opp.roles]
        for e in self.moteur.plan(aid)["etapes"]:
            if e.get("membre") and e["membre"] not in noeuds:
                noeuds.append(e["membre"])
        limite = self.jour - timedelta(days=365)
        g_avant, g_apres = nx.Graph(), nx.Graph()
        for ev in self.r.memoire.evenements("RENCONTRE", "COLLABORATION"):
            if len(ev.acteurs) < 2 or ev.le < limite:
                continue
            g_apres.add_edge(*ev.acteurs[:2])
            if not (ev.type == "COLLABORATION" and ev.donnees.get("aid") == aid):
                g_avant.add_edge(*ev.acteurs[:2])
        b = opp.beneficiaire
        rendu = self.rendu()
        nouveaux = [(ev.acteurs[0], ev.acteurs[1]) for ev in self.r.memoire.evenements("COLLABORATION") if ev.donnees.get("aid") == aid]
        return {"noeuds": [{"cle": f"n{i}", "nom": rendu.nom(sp, x) if sp.role == "animatrice" or x == sp.id or x == b else
                            rendu.nom(sp, x), "beneficiaire": x == b} for i, x in enumerate(noeuds)],
                "liens_avant": [[f"n{noeuds.index(a)}", f"n{noeuds.index(c)}"] for a, c in g_avant.subgraph(noeuds).edges()],
                "liens_nouveaux": [[f"n{noeuds.index(a)}", f"n{noeuds.index(c)}"] for a, c in nouveaux if a in noeuds and c in noeuds],
                "relations_beneficiaire": {"avant": g_avant.degree(b) if b in g_avant else 0, "apres": g_apres.degree(b) if b in g_apres else 0},
                "reseau_atteignable": {"avant": len(nx.node_connected_component(g_avant, b)) if b in g_avant else 1,
                                       "apres": len(nx.node_connected_component(g_apres, b)) if b in g_apres else 1},
                "phrase": f"Cette activation a créé {len(nouveaux)} collaboration(s) confirmée(s) par une contribution reçue."}

    # ------------------------------------------------------------------ mémoire vérifiée (anonymisée)
    def memoire_club(self, sp: Spectateur) -> list[dict]:
        rendu = self.rendu()
        res = []
        for x in apprentissage.motifs(self.r.memoire, self.jour):
            res.append({"id": x["motif_id"], "capacites": [self.tax.libelle(c) for c in x["concepts"]],
                        "resultat": x["resultat"], "confirmations": x["confirmations"], "age_jours": x["age_jours"], "frais": x["frais"],
                        "secteur": self.tax.libelle(x["secteur"]) if x["secteur"] else None, "sequence": x["sequence"],
                        "ressources": [{"titre": c["titre"], "auteur": rendu.nom(sp, c["auteur"]) if c.get("attribution") and c.get("auteur") else "anonyme",
                                        "telecharger": f"/api/pulse/memoire/{x['motif_id']}/fiche"} for c in x["contributions"] if c.get("reutilisable")],
                        "statut": x["statut"],
                        "visibilite": "motif anonymisé : ni le bénéficiaire, ni les contributeurs sans leur accord"})
        return res

    def fiche(self, motif_id: str) -> str:
        x = next((m for m in apprentissage.motifs(self.r.memoire, self.jour) if m["motif_id"] == motif_id), None)
        c = next((c for c in (x or {}).get("contributions", []) if c.get("reutilisable")), None)
        if x is None or c is None:
            raise ErreurPulse("aucune ressource partageable pour ce motif")
        per = self.coffre.identite(c.get("auteur", "")) if c.get("attribution") else None
        return (f"{c['titre']}\n{'=' * len(c['titre'])}\n\n{c['contenu']}\n\n---\nProvenance : contribution de "
                f"{per.nom if per else 'un membre (anonyme à sa demande)'} ; effet confirmé par le bénéficiaire "
                f"({x['confirmations']} confirmation(s), la dernière il y a {x['age_jours']} jours). Le bénéficiaire n'est pas nommé.\n"
                f"DONNÉES FICTIVES — monde de démonstration Club Pulse, dates simulées. Statut : {x['statut']}.\n")

    # ------------------------------------------------------------------ POULS (membre) et TOUR DE CONTRÔLE (Club)
    def pouls_membre(self, pid: str) -> dict:
        sp = Spectateur("membre", pid)
        per = self.coffre.identite(pid)
        items = []
        for d in self.demandes_pour(pid):
            items.append({"type": "contribution" if not d["pour_vous"] else "accord", "titre": d["titre"], "cible": d["activation"],
                          "detail": d["pourquoi_vous"] or "Rien n'est transmis avant votre accord."})
        for o in self.scanner()["opportunites"]:
            if o.beneficiaire == pid:
                v = self.vue_opportunite(o, sp)
                items.append({"type": "opportunite", "titre": v["titre"], "cible": o.id, "detail": v["pourquoi_maintenant"],
                              "etiquette": v["type_libelle"]})
        for a in self.activations_de(pid):
            if a["etat"] not in FINAUX or a["etat"] in ("RESULTAT_CONFIRME", "RESULTAT_PARTIEL"):
                items.append({"type": "activation", "titre": f"Activation n°{a['numero']} : {a['etat_libelle']}", "cible": a["id"],
                              "detail": a["objectif"]})
        for ev in self.r.evenements:
            if pid in ev.participants and 0 <= (ev.le - self.jour).days <= 30:
                items.append({"type": "evenement", "titre": ev.nom, "cible": ev.id,
                              "detail": f"dans {(ev.le - self.jour).days} jours : préparez vos rencontres"})
        motifs = self.memoire_club(sp)
        if motifs:
            items.append({"type": "memoire", "titre": f"{len(motifs)} résultat(s) vérifié(s) dans la mémoire du Club", "cible": "memoire",
                          "detail": "ce qui a vraiment aidé, anonymisé"})
        return {"bonjour": per.nom.split()[0] if per else "", "date": self.jour.isoformat(), "items": items,
                "ia": self.ia.etat(), "fictif": True}

    def tour(self) -> dict:
        scan = self.scanner()
        acts = self.moteur.activations()
        etats = {a: self.moteur.etat(a) for a in acts}
        attention = [a for a, e in etats.items() if e in ("BLOQUEE", "ALTERNATIVE_PROPOSEE", "RESULTAT_INCONNU", "ABANDONNEE", "EN_PAUSE")]
        manques: dict[str, set[str]] = {}
        for o in scan["opportunites"]:
            for m_ in o.manque:
                manques.setdefault(m_, set()).update({o.beneficiaire or r.membre for r in o.roles})
        for x in scan["bloques"]:
            lib = self.tax.libelle(x["concept"]) if x["concept"] in self.tax.concepts else x["concept"]
            manques.setdefault(lib, set()).add(x["auteur"])
        intervention = max(manques.items(), key=lambda kv: (len(kv[1]), kv[0]), default=None)
        sp = Spectateur("animatrice")
        motifs = apprentissage.motifs(self.r.memoire, self.jour)
        return {
            "date": self.jour.isoformat(), "monde": self.r.nom, "ia": self.ia.etat(),
            "situation": [
                {"cle": "opportunites", "valeur": len(scan["opportunites"]), "libelle": "opportunités actives"},
                {"cle": "attention", "valeur": len(attention), "libelle": "demandent une attention humaine"},
                {"cle": "en_cours", "libelle": "activations en cours",
                 "valeur": sum(1 for e in etats.values() if e not in FINAUX and e not in ("TERMINEE", "RESULTAT_INCONNU"))},
                {"cle": "confirmees", "libelle": "demandes débloquées",
                 "valeur": sum(1 for e in etats.values() if e in ("RESULTAT_CONFIRME", "RESULTAT_PARTIEL"))},
                {"cle": "motifs", "valeur": sum(1 for x in motifs if x["frais"]), "libelle": "motifs vérifiés"},
                {"cle": "sans_solution", "valeur": len(scan["bloques"]), "libelle": "demandes sans solution dans le Club"}],
            "priorites": [self.vue_opportunite(o, sp) for o in scan["opportunites"][:3]],
            "toutes": [{"id": o.id, "type": LIBELLES_TYPE.get(o.type, o.type), "titre": self.rendu().texte(sp, o.titre),
                        "confiance": o.confiance, "demandes_servies": o.demandes_servies} for o in scan["opportunites"]],
            "intervention": ({"capacite": intervention[0], "demandes": len(intervention[1]),
                              "phrase": f"Trouver 1 compétence — {intervention[0]} — débloquerait {len(intervention[1])} demande(s) ou opportunité(s)."}
                             if intervention else None),
            "phases": scan["phases"], "ecartees": scan["ecartees"],
            "activations": [{"id": a, "numero": i + 1, "etat": etats[a], "etat_libelle": LIBELLES_ETAT.get(etats[a], etats[a]),
                             "objectif": self.rendu().texte(sp, self.moteur.opportunite(a).titre)} for i, a in enumerate(acts)],
            "adhesions": {"source": self.coffre.source, "synthetique": self.coffre.synthetique, "organisations": len(self.coffre.orgs),
                          "adhesions": len(self.coffre.adhesions),
                          "cartes_entreprise": sum(1 for a in self.coffre.adhesions.values() if a.formule == "entreprise"),
                          "personnes": len(self.coffre._personnes), "comptes_actives": len(self.coffre.actives),
                          "api_club": "non connectée (autorisation et accès technique du Club requis)"},
            "appels_ia": [a.model_dump(exclude={"controle"}) for a in self.ia.appels[-12:]]}

    # ------------------------------------------------------------------ temps
    def avancer(self, jours: int) -> list[str]:
        if not 1 <= jours <= 60:
            raise ErreurPulse("avance de 1 à 60 jours")
        self.r.aujourd_hui = self.jour + timedelta(days=jours)
        self.r.memoire.ajouter(Evt(type="HORLOGE", le=self.jour, statut=Statut.SIMULE, donnees={"avance_jours": jours}))
        self._scan = None
        return self.moteur.echeances(self.jour)


__all__ = ["ClubPulse", "ErreurPulse", "ErreurActivation", "descripteur"]
