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

import threading
import time
from datetime import date, timedelta
from typing import Optional

from app.models import Offre, Profil
from app.parser_rules import extraire_profil
from app.taxonomy import Taxonomie
from plateforme.affirmations import Statut
from plateforme.memoire import Evt

from . import monde_demo as md
from .acces import Sessions
from .activation import ErreurActivation, Moteur
from .detection import Detecteur
from .erreurs import Conflit, ErreurMetier, Interdit, Introuvable, Invalide, NonAuthentifie
from .ia import AppelIA, Intelligence, besoin_de
from .identite import AdhesionsSynthetiques, Coffre
from .modele import BesoinActif, Opportunite
from .politique import MODIFIABLES, Contexte, Rendu, Spectateur, descripteur
from .reglages import Reglages
from .vues import Vues

ErreurPulse = ErreurMetier             # nom historique : tout refus du service (sous-classes typées)


class ClubPulse:
    def __init__(self, tax: Taxonomie, ia: Optional[Intelligence] = None, reglages: Optional[Reglages] = None):
        self.tax = tax
        self.reglages = reglages or Reglages.depuis_env()
        # Un seul verrou par monde : chaque requête HTTP s'exécute entière dessous (pas de lecture-puis-écriture
        # entrelacée entre deux requêtes). Réentrant : une commande peut en appeler une autre.
        self.verrou = threading.RLock()
        brut = md.construire(sophie_profilee=False)
        self.coffre = Coffre(AdhesionsSynthetiques(brut.profils).importer(), secret=self.reglages.secret)
        self.sessions = Sessions(self.reglages.secret, self.reglages.duree_session_s)
        brut.profils = [self.coffre.pseudonymiser(p) for p in brut.profils]    # le moteur ne voit que des pseudonymes
        self.r = brut
        self.moteur = Moteur(self.r, tax)
        self.ia = ia or Intelligence.depuis_environnement(tax, journal=self._tracer_ia,
                                                          notes_privees_autorisees=self.reglages.notes_privees_vers_ia)
        self.ia.journal = self._tracer_ia
        self.vues = Vues(self)
        self.notes: dict[str, list[dict]] = {}
        self.preferences: dict[str, dict] = {}
        self.ecartees: set[str] = set()
        self.explications: dict[tuple[str, str], dict] = {}
        self.messages: dict[tuple[str, str, str], dict] = {}   # (activation, étape, membre) → message de sollicitation rédigé
        self._scan: Optional[dict] = None
        self._version_scan: tuple = ()
        self._revision_profils = 0            # incrémentée à chaque modification de profil (invalide l'analyse)
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
            raise Introuvable("membre inconnu")
        return p

    def _remplacer_profil(self, p: Profil) -> None:
        self.r.profils = [p if q.id == p.id else q for q in self.r.profils]
        self._revision_profils += 1
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
        return self.sessions.emettre(pid)

    def verifier_session(self, jeton: str) -> str:
        pid = self.sessions.verifier(jeton)
        if pid not in self.coffre.actives:                    # compte désactivé ou identité effacée depuis
            raise NonAuthentifie("session invalide")
        return pid

    def activer_compte(self, code: str) -> dict:
        pid = self.coffre.activer(code)
        if not pid:
            raise NonAuthentifie("code d'invitation inconnu ou adhésion inactive")
        per = self.coffre.identite(pid)
        org = self.coffre.organisation_de(pid)
        assert per is not None
        return {"session": self.session(pid), "nom": per.nom, "organisation": org.nom if org else None,
                "role": per.role, "profil_complet": bool(self.profil(pid).offre or self.profil(pid).recherche)}

    def proposer(self, texte: str, sens: str) -> list[dict]:
        """Étape 2/3 de l'accueil : le texte libre est analysé ; le membre CONFIRME ou REJETTE chaque proposition."""
        if sens not in ("aide", "cherche") or not texte.strip():
            raise Invalide("texte vide ou sens inconnu")
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
                    raise Invalide(f"capacité inconnue : {c}")
                if str(x.get("texte", "")).strip():
                    res.append(Offre(concept=c, texte=str(x["texte"]).strip()[:200]))
            return res
        p = self.profil(pid)
        offres, recherches = items(aide), items(cherche)
        self._remplacer_profil(p.model_copy(update={"offre": offres, "recherche": recherches,
                                                     "secteurs": [o.concept for o in offres if o.concept][:1],
                                                     "accepte_introductions": visible, "maj": self.jour.isoformat()}))
        return self.vues.vue_profil(pid)

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
                    raise Invalide(f"visibilité non modifiable : {k} → {v}")
        # Tout ou rien : profil, préférences et replanifications qu'ils déclenchent. Le journal est transactionnel ;
        # l'état en mémoire (profils, préférences) est restauré si le moteur refuse.
        profils_avant, prefs_avant = self.r.profils, {k: dict(v) for k, v in self.preferences.items()}
        try:
            with self.r.memoire.transaction():
                if visibilite:
                    self.preferences.setdefault(pid, {}).update(visibilite)
                self._remplacer_profil(p.model_copy(update=maj))
                if retirer_capacite:
                    self.moteur.retirer_capacite(pid, retirer_capacite, self.jour)
                if (disponible is False or accepte is False) and any(
                        self.moteur.etat(a) in ("EN_ATTENTE_ACCORD", "PLANIFIEE") and any(
                            e.get("membre") == pid and e["type"] in ("contribution", "animation") for e in self.moteur.plan(a)["etapes"])
                        for a in self.moteur.activations()):
                    self.moteur.retirer_membre(pid, self.jour, "la personne a suspendu les sollicitations")
                    self.moteur.exclus.discard(pid)       # la pause vaut pour les plans en cours ; le profil dit la suite
        except Exception:
            self.r.profils, self.preferences = profils_avant, prefs_avant
            self._revision_profils += 1
            raise
        return self.vues.vue_profil(pid)



    # ------------------------------------------------------------------ mémoire privée : capture d'une rencontre
    def capturer(self, pid: str, texte: str, evenement: Optional[str] = None) -> dict:
        if not texte.strip() or len(texte) > 2000:
            raise Invalide("note vide ou trop longue")
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
        return self.vues._vue_note(pid, note)

    def partager(self, pid: str, note_id: str, index: int) -> dict:
        """Le membre choisit explicitement ce qui quitte sa note privée (et rien d'autre)."""
        note = next((n for n in self.notes.get(pid, []) if n["id"] == note_id), None)
        if note is None or not 0 <= index < len(note["propositions"]):
            raise Introuvable("note ou proposition inconnue")
        prop = note["propositions"][index]
        if prop["type"] == "ajouter_recherche":
            self.modifier_profil(pid, ajouter_recherche=prop["texte"].rstrip("."))
        note["partagee"].append(index)
        return self.vues._vue_note(pid, note)



    # ------------------------------------------------------------------ demande explicite (jury ou membre)
    def demander(self, pid: str, texte: str) -> dict:
        if not 3 <= len(texte.strip()) <= 600:
            raise Invalide("demande vide ou trop longue")
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
                "opportunites": [self.vues.vue_opportunite(o, Spectateur("membre", pid)) for o in miennes],
                "sans_solution": [self.vues._vue_blocage(x) for x in bloques]}


    # ------------------------------------------------------------------ OBSERVER → DÉTECTER
    def scanner(self, force: bool = False) -> dict:
        # l'analyse est une fonction de (journal, besoins, profils, date) : sa version se lit sans hachage ni heuristique
        version = (len(self.r.memoire.evenements()), len(self.r.besoins), self._revision_profils, self.jour)
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
        """Pour AGIR sur une opportunité ouverte : déjà activée → Conflit (double clic, nouvel essai réseau)."""
        o, aid = self.trouver_opportunite(oid)
        if aid is not None:
            raise Conflit("cette opportunité est déjà activée")
        return o

    def trouver_opportunite(self, oid: str) -> tuple[Opportunite, Optional[str]]:
        """Pour LIRE : une opportunité devenue activation n'est pas une erreur, c'est un état plus avancé. Renvoie
        l'opportunité (telle qu'elle a été activée) et l'activation qui la porte, s'il y en a une. (Défaut réel : une
        lecture tardive recevait 409 — un écran rafraîchi juste après l'activation affichait une erreur.)"""
        o = next((x for x in self.scanner()["opportunites"] if x.id == oid), None)
        if o is not None:
            return o, None
        for a in self.moteur.activations():
            p = self.moteur.plan(a)
            if p["opportunite"]["id"] == oid:
                return Opportunite(**p["opportunite"]), a
        raise Introuvable("opportunité inconnue")

    # ------------------------------------------------------------------ vues d'opportunité (par spectateur)

    def expliquer(self, oid: str, sp: Spectateur) -> dict:
        """L'IA reformule le « pourquoi » à partir de faits PSEUDONYMISÉS ; le texte est contrôlé puis rendu pour le spectateur."""
        o, _ = self.trouver_opportunite(oid)
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
            raise Interdit("seul le bénéficiaire (ou le Club) peut activer cette opportunité")
        with self.r.memoire.transaction():                     # créer + lancer + accord du demandeur : tout ou rien
            aid = self.moteur.creer(o, self.jour, anonyme=anonyme, langue=langue)
            if self.moteur.etat(aid) == "PLANIFIEE" and not (par.role == "animatrice" and langue):
                self.moteur.lancer(aid, self.jour)
                if par.role == "membre" and par.id is not None and par.id == o.beneficiaire:
                    self.moteur.repondre(aid, self.jour, par.id, True)    # c'est lui qui le demande : son accord est donné
        self._scan = None
        return aid

    def lancer(self, aid: str) -> None:
        self.moteur.lancer(aid, self.jour)

    def repondre(self, aid: str, pid: str, accepte: bool) -> None:
        self.moteur.repondre(aid, self.jour, pid, accepte)
        self._scan = None

    def contribuer(self, aid: str, pid: str, nature: str, titre: str, contenu: str, reutilisable: bool = False,
                   attribution: bool = False) -> None:
        self.moteur.contribuer(aid, self.jour, pid, nature, titre, contenu, reutilisable, attribution)

    def confirmer(self, aid: str, pid: str, verdict: str, etape_suivante: bool, pourquoi: str = "") -> dict:
        return self.moteur.confirmer(aid, self.jour, pid, verdict, etape_suivante, pourquoi)

    def reutiliser(self, aid: str, pid: Optional[str] = None) -> None:
        """Recevoir la ressource vérifiée d'une opportunité MÉMOIRE — geste du bénéficiaire (ou de la démonstration)."""
        if pid is not None and self.moteur.opportunite(aid).beneficiaire != pid:
            raise Interdit("seul le bénéficiaire reçoit la ressource vérifiée")
        self.moteur.reutiliser(aid, self.jour)

    def retirer_consentement(self, aid: str, pid: str) -> None:
        self.moteur.retirer_consentement(aid, self.jour, pid)

    def ecarter(self, oid: str) -> None:
        """L'animatrice écarte une opportunité (elle ne réapparaît plus dans l'analyse de ce monde)."""
        self.opportunite(oid)
        self.ecartees.add(oid)
        self._scan = None

    def piloter(self, aid: str, action: str) -> None:
        """Contrôle du Club sur une activation : lancer, mettre en pause, reprendre, annuler."""
        commandes = {"lancer": self.moteur.lancer, "pause": self.moteur.mettre_en_pause,
                     "reprendre": self.moteur.reprendre, "annuler": self.moteur.annuler}
        if action not in commandes:
            raise Invalide("action inconnue")
        commandes[action](aid, self.jour)

    def changer_contraintes(self, aid: str, langue: Optional[str], anonyme: Optional[bool]) -> None:
        self.moteur.changer_contraintes(aid, self.jour, langue=langue, anonyme=anonyme)

    # ------------------------------------------------------------------ vues d'activation




    # ------------------------------------------------------------------ ÉVOLUTION DU RÉSEAU (preuve secondaire)

    # ------------------------------------------------------------------ mémoire vérifiée (anonymisée)


    # ------------------------------------------------------------------ POULS (membre) et TOUR DE CONTRÔLE (Club)


    # ------------------------------------------------------------------ temps
    def avancer(self, jours: int) -> list[str]:
        if not 1 <= jours <= 60:
            raise Invalide("avance de 1 à 60 jours")
        self.r.aujourd_hui = self.jour + timedelta(days=jours)
        self.r.memoire.ajouter(Evt(type="HORLOGE", le=self.jour, statut=Statut.SIMULE, donnees={"avance_jours": jours}))
        self._scan = None
        return self.moteur.echeances(self.jour)


__all__ = ["ClubPulse", "ErreurPulse", "ErreurActivation", "descripteur"]
