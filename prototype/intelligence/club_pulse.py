"""CLUB PULSE — le service qui compose la boucle, entre les membres, le Club et l'intelligence du réseau.

    MEMBRE → BESOIN → SIGNAUX → DÉCOUVERTE (+ pourquoi) → ESSAI (consentements, versions) → PERTURBATION → ADAPTATION
    → CONTRIBUTION → OBSERVATION → MÉMOIRE (bornée, contestable) → DÉCOUVERTE SUIVANTE

Frontières tenues ici :
- NETWORK INTELLIGENCE (`Detecteur`, `expliquer`) : détecte et explique ; ne sollicite personne ;
- ACTIVATION ENGINE (`Banc`) : essais, accords par version, adaptation, observation ; ses règles « qui peut être
  sollicité » sont celles du réseau (une seule source : `Etat.exclusion`) ;
- la PASSERELLE est le seul pont entre les deux, et seule la personne aidée l'emprunte ;
- le moteur ne reçoit que des profils PSEUDONYMISÉS ; les identités sont au `Coffre` ; tout ce qui sort vers un
  humain passe par la politique (`Rendu`, vues) pour CE spectateur ;
- l'IA (Apertus si configuré, sinon repli déterministe déclaré) comprend et rédige ; elle ne décide rien ;
- trois mémoires distinctes : NOTES PRIVÉES (propriétaire seul) · PROFIL (ce que le membre a choisi de déclarer) ·
  MÉMOIRE DU CLUB (projection des essais observés, confirmés ou contestés, bornée par les droits de chacun).
Monde de démonstration FICTIF ; gestes humains joués dans la démonstration et marqués comme tels.
"""
from __future__ import annotations

import threading
from datetime import date, timedelta
from typing import Optional

from app.models import Offre, Profil
from app.parser_rules import extraire_profil
from app.taxonomy import Taxonomie
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

from . import memoire_club
from . import monde_demo as md
from .acces import Sessions
from .detection import Detecteur
from .erreurs import Conflit, ErreurMetier, Interdit, Introuvable, Invalide, NonAuthentifie
from .essai import Banc, Etape, Plage, Protocole
from .ia import AppelIA, Intelligence, besoin_de
from .identite import AdhesionsSynthetiques, Coffre, nettoyer
from .modele import BesoinActif, Opportunite
from .observateur import Etat, observer
from .passerelle import CRITERE_SUGGERE, brouillon, essai_existant
from .politique import MODIFIABLES, Contexte, Rendu, Spectateur, descripteur
from .reglages import Reglages
from .vues_essai import VuesEssai
from .vues_intelligence import VuesIntelligence

ErreurPulse = ErreurMetier             # nom historique : tout refus du service (sous-classes typées)
# ce qu'on considérera comme RÉALISÉ : une suggestion que le porteur adopte ou remplace (jamais écrite à sa place)
CRITERE_ACTION = ("La présentation a lieu au créneau convenu et la fiche promise est remise ; "
                  "je dirai ce que les acheteurs en ont retenu.")


class ClubPulse:
    def __init__(self, tax: Taxonomie, ia: Optional[Intelligence] = None, reglages: Optional[Reglages] = None):
        self.tax = tax
        self.reglages = reglages or Reglages.depuis_env()
        # Un seul verrou par monde : chaque requête HTTP s'exécute entière dessous (pas de lecture-puis-écriture
        # entrelacée entre deux requêtes). Réentrant : une commande peut en appeler une autre.
        self.verrou = threading.RLock()
        brut = md.construire(sophie_profilee=False, recherches_autres=md.BESOINS_SUIVANTS)
        self.coffre = Coffre(AdhesionsSynthetiques(brut.profils).importer(), secret=self.reglages.secret)
        self.sessions = Sessions(self.reglages.secret, self.reglages.duree_session_s)
        brut.profils = [self.coffre.pseudonymiser(p) for p in brut.profils]    # le moteur ne voit que des pseudonymes
        self.r = brut
        self.ia = ia or Intelligence.depuis_environnement(tax, journal=self._tracer_ia,
                                                          notes_privees_autorisees=self.reglages.notes_privees_vers_ia)
        self.ia.journal = self._tracer_ia
        self.vues = VuesIntelligence(self)
        # ACTIVATION ENGINE : son propre journal — fichier si HACKVS_ESSAIS_DB (survit au redémarrage), sinon en mémoire.
        # Qui peut être sollicité pour qui : les règles DURES du réseau (langue commune, consentement, disponibilité,
        # profil récent, introduction déjà déclinée), lues dans l'état observé courant — une seule source de vérité.
        self.banc = Banc(Memoire(self.reglages.essais_db), lambda: self.jour, self.organisation_de, self._non_sollicitable)
        self.vues_essai = VuesEssai(self)
        self.notes: dict[str, list[dict]] = {}
        self.preferences: dict[str, dict] = {}
        self.explications: dict[tuple[str, str], dict] = {}
        self.messages: dict[tuple[str, int, str], dict] = {}   # (essai, version, invité) → message d'invitation rédigé
        self.joues: list[dict] = []                            # gestes JOUÉS par l'équipe depuis la console (démonstration)
        self._scan: Optional[dict] = None
        self._etat: Optional[Etat] = None
        self._version_etat: tuple = ()
        self._version_scan: tuple = ()
        self._revision_profils = 0            # incrémentée à chaque modification de profil (invalide l'analyse)
        for pid in self.coffre._personnes:                   # tous ont activé leur compte, sauf la nouvelle venue
            if pid != md.SOPHIE:
                self.coffre.actives.add(pid)

    # ------------------------------------------------------------------ bases
    @property
    def jour(self) -> date:
        return self.r.aujourd_hui

    def organisation_de(self, pid: str) -> str:
        o = self.coffre.organisation_de(pid)
        return o.id if o else f"org-{pid}"

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
        """Faits de relation (journal du Club) et de CONSENTEMENT (accords donnés dans un essai) : le porteur et chaque
        contributeur qui a accepté se voient nommés l'un l'autre ; qui décline ou se tait, jamais."""
        m = self.r.memoire
        relations = {frozenset(e.acteurs[:2]) for e in m.evenements("RENCONTRE", "COLLABORATION") if len(e.acteurs) >= 2}
        consentis: set[tuple[str, str]] = set()
        for eid in self.banc.essais():
            porteur = self.banc.porteur(eid)
            for x in self.banc.participants(eid) - {porteur}:
                consentis |= {(porteur, x), (x, porteur)}
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
        # Tout ou rien : l'état en mémoire (profils, préférences) est restauré si une validation échoue. Suspendre ses
        # sollicitations vaut pour les NOUVELLES propositions (règles dures) ; un accord déjà donné dans un essai se
        # retire explicitement dans cet essai (dit, daté), jamais en silence.
        profils_avant, prefs_avant = self.r.profils, {k: dict(v) for k, v in self.preferences.items()}
        try:
            if visibilite:
                self.preferences.setdefault(pid, {}).update(visibilite)
            self._remplacer_profil(p.model_copy(update=maj))
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
        return self.vues.vue_note(pid, note)

    def partager(self, pid: str, note_id: str, index: int) -> dict:
        """Le membre choisit explicitement ce qui quitte sa note privée (et rien d'autre)."""
        note = next((n for n in self.notes.get(pid, []) if n["id"] == note_id), None)
        if note is None or not 0 <= index < len(note["propositions"]):
            raise Introuvable("note ou proposition inconnue")
        prop = note["propositions"][index]
        if prop["type"] == "ajouter_recherche":
            self.modifier_profil(pid, ajouter_recherche=prop["texte"].rstrip("."))
        note["partagee"].append(index)
        return self.vues.vue_note(pid, note)



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
        miennes = [o for o in scan["opportunites"] if o.beneficiaire == pid]    # seulement ce qui le concerne : où il est aidé
        bloques = [x for x in scan["bloques"] if x["auteur"] == pid]
        return {"compris": [{"type": c.type, "libelle": c.libelle, "extrait": c.extrait, "obligatoire": c.obligatoire}
                            for c in b.criteres] + ([{"type": "contrainte", "libelle": "pas un concurrent direct", "extrait": None,
                                                      "obligatoire": True}] if b.exclure_concurrents else []),
                "incertain": [a.terme for a in b.ambiguites] + b.avertissements,
                "ia": rep.appel.model_dump(include={"fournisseur", "modele", "statut", "repli", "latence_ms"}),
                "decouvertes": [self.vues.decouverte(o, Spectateur("membre", pid)) for o in miennes],
                "sans_solution": [self.vues.vue_blocage(x) for x in bloques]}


    # ------------------------------------------------------------------ OBSERVER → DÉTECTER → EXPLIQUER
    def _version(self) -> tuple:
        """L'analyse est une fonction de (journal du Club, besoins, profils, date, journal des essais — la mémoire) :
        sa version se lit sans hachage ni heuristique."""
        return (len(self.r.memoire.evenements()), len(self.r.besoins), self._revision_profils, self.jour, len(self.banc.m.evenements()))

    def scanner(self, force: bool = False) -> dict:
        version = self._version()
        if self._scan is not None and self._version_scan == version and not force:
            return self._scan
        souvenirs = memoire_club.reutilisables_par_le_club(memoire_club.souvenirs(self.banc))
        d = Detecteur(self.r, self.tax, souvenirs=souvenirs)
        res = d.detecter()
        e = d.e
        res["phases"] = [
            {"etape": "Observer le réseau", "detail": f"{len(self.r.profils)} membres, {sum(len(v) for v in e.offreurs.values())} capacités déclarées"},
            {"etape": "Relations et leur fraîcheur", "detail": f"{len(e.relies)} relations de moins d'un an"},
            {"etape": "Fenêtres d'événements", "detail": f"{len(e.evenements_proches)} événement(s) dans les 30 jours"},
            {"etape": "Besoins publiés", "detail": f"{res['besoins']} besoin(s), {len(res['bloques'])} capacité(s) introuvable(s)"},
            {"etape": "Intérêts déclarés et suites de rencontres", "detail": f"{sum(len(v) for v in e.recherches.values())} intérêts déclarés"},
            {"etape": "Mémoire du Club", "detail": f"{len(souvenirs)} contribution(s) confirmée(s) et partagée(s)"},
            {"etape": "Règles de consentement, fraîcheur, concurrence",
             "detail": f"{sum(res['ecartees'].values())} piste(s) écartée(s) (sans nommer personne)"},
            {"etape": "Découvertes", "detail": f"{len(res['opportunites'])}"}]
        self._scan, self._version_scan = res, version
        return res

    def _non_sollicitable(self, porteur: str, candidat: str) -> Optional[str]:
        """Pour le banc : pourquoi `candidat` ne peut pas être sollicité pour `porteur` (None : il peut l'être). L'état
        observé ne dépend pas des essais : il n'est relu que si le réseau a changé (pas à chaque geste du banc)."""
        version = self._version()[:-1]
        if self._etat is None or self._version_etat != version:
            self._etat, self._version_etat = observer(self.r, self.tax), version
        par_id = self.r.par_id()
        if porteur not in par_id or candidat not in par_id:
            return "membre inconnu"
        return self._etat.exclusion(par_id[porteur], par_id[candidat], None, introduction=False)

    def trouver_opportunite(self, oid: str) -> Opportunite:
        o = next((x for x in self.scanner()["opportunites"] if x.id == oid), None)
        if o is None:
            raise Introuvable("découverte inconnue (ou plus d'actualité)")
        return o

    def en_clair(self, oid: str, sp: Spectateur) -> dict:
        """L'IA reformule le « pourquoi » à partir de faits PSEUDONYMISÉS ; le texte est contrôlé puis rendu pour le
        spectateur. C'est une reformulation : la source reste l'explication structurée."""
        o = self.trouver_opportunite(oid)
        if sp.role == "membre" and sp.id != o.beneficiaire:
            raise Interdit("cette découverte ne vous concerne pas")
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

    def message_invitation(self, eid: str, pid: str) -> Optional[dict]:
        """Le message que lit une personne INVITÉE (geste sur invitation) : rédigé UNE fois par (essai, version, personne)
        — IA contrôlée si configurée, sinon gabarit déclaré — puis mémorisé : relire la page ne rappelle pas le modèle."""
        p = self.banc.protocole(eid)
        e = next((x for x in p.etapes if x.contributeur == pid and x.invitation), None)
        if e is None:
            return None
        cle = (eid, self.banc.version(eid), pid)
        if cle not in self.messages:
            porteur = self.banc.porteur(eid)
            prof, per = self.r.par_id().get(porteur), self.coffre.identite(porteur)
            faits = {"capacite_declaree": self.tax.libelle(e.concept) if e.concept else e.geste, "demande": p.question,
                     "secteur_demandeur": self.tax.libelle(prof.secteurs[0]) if prof and prof.secteurs else "non précisé",
                     "partage": "votre nom et votre organisation à cette personne seulement si vous acceptez"}
            rep = self.ia.rediger_sollicitation(faits, [per.nom if per else "", self.coffre.pseudonyme(porteur)])
            self.messages[cle] = {"texte": rep.sortie["message"],
                                  "ia": rep.appel.model_dump(include={"fournisseur", "modele", "statut", "repli"})}
        return self.messages[cle]

    # ------------------------------------------------------------------ PASSERELLE : la personne aidée demande un essai
    def proposer_essai(self, pid: str, oid: str) -> str:
        """Seule la personne aidée transforme une découverte en BROUILLON d'essai (visible d'elle seule) ; rien n'est
        envoyé à personne avant qu'elle le publie. Un essai déjà vivant pour cette découverte : Conflit (double clic)."""
        o = self.trouver_opportunite(oid)
        if o.beneficiaire != pid:
            raise Interdit("seule la personne aidée peut proposer un essai à partir de cette découverte")
        if o.type == "LACUNE" or not any(r.membre != pid for r in o.roles):
            raise Conflit("personne à inviter : cette découverte signale un manque du Club")
        if essai_existant([(x, self.banc.protocole(x).origine, self.banc.etat(x)) for x in self.banc.essais()], oid):
            raise Conflit("un essai existe déjà pour cette découverte")
        return self.banc.brouillon(pid, brouillon(o, self.r, self.tax, self.jour))

    # ------------------------------------------------------------------ temps
    def avancer(self, jours: int) -> list[str]:
        if not 1 <= jours <= 60:
            raise Invalide("avance de 1 à 60 jours")
        self.r.aujourd_hui = self.jour + timedelta(days=jours)
        self.r.memoire.ajouter(Evt(type="HORLOGE", le=self.jour, statut=Statut.SIMULE, donnees={"avance_jours": jours}))
        self._scan = None
        return self.banc.echeances()

    # ------------------------------------------------------------------ banc d'essai : ce qui passe par l'IA
    def preparer_essai(self, pid: str, texte: str) -> dict:
        """Formulation du porteur → brouillon à corriger. Le texte est SA proposition (pas une note privée) ; les noms,
        courriels et téléphones des membres connus en sont retirés avant tout envoi (défense complémentaire)."""
        if not 3 <= len(texte.strip()) <= 600:
            raise Invalide("formulation vide ou trop longue")
        noms = [per.nom for per in self.coffre._personnes.values()] + [o.nom for o in self.coffre.orgs.values()]
        propre = nettoyer(texte, noms)
        rep = self.ia.structurer_essai(propre)
        return rep.sortie | {"echeance": (self.jour + timedelta(days=10)).isoformat(),
                             "ia": {"fournisseur": rep.appel.fournisseur, "modele": rep.appel.modele, "statut": rep.appel.statut,
                                    "repli": rep.appel.repli, "mode": rep.sortie.get("mode")}}

    def _protocole(self, champs: dict) -> Protocole:
        etapes = [Etape(id=f"e{i + 1}", nature=e["nature"], geste=e["geste"], duree_min=e["duree_min"])
                  for i, e in enumerate(champs.get("etapes") or [])]
        p = Protocole(question=champs["question"], objet=champs.get("objet", ""), pourquoi=champs.get("pourquoi", ""),
                      critere=champs.get("critere", ""), echeance=date.fromisoformat(champs["echeance"]), etapes=etapes)
        if p.echeance < self.jour:
            raise Invalide("échéance passée")
        return p

    def jouer(self, pid: str, geste: str, role: Optional[str] = None) -> None:
        """Trace d'un geste JOUÉ par l'équipe pour un personnage (démonstration) : affiché comme tel, jamais confondu avec
        une action faite sur un téléphone. L'écran commun n'en montre que le RÔLE, jamais le nom."""
        self.joues.append({"le": self.jour.isoformat(), "membre": pid, "role": role, "geste": geste, "joue_par": "l'équipe (console)"})

    def role_dans(self, eid: str, pid: str) -> Optional[str]:
        """Le rôle que tient `pid` dans la version courante de l'essai (lu AU MOMENT du geste joué)."""
        return next((e.role for e in self.banc.protocole(eid).etapes if e.contributeur == pid and e.role), None)

    # ------------------------------------------------------------------ ACTION COLLECTIVE : demande → exigences → proposition
    def preparer_action(self, pid: str, texte: str) -> dict:
        """Les mots du membre → exigences PROPOSÉES et ce qui manque (IA contrôlée ou règles simples, déclaré). Rien n'est
        écrit : le membre confirme ou corrige. Les noms connus du Club sont retirés du texte avant tout envoi."""
        if not 3 <= len(texte.strip()) <= 600:
            raise Invalide("formulation vide ou trop longue")
        noms = [per.nom for per in self.coffre._personnes.values()] + [o.nom for o in self.coffre.orgs.values()]
        rep = self.ia.comprendre_action(nettoyer(texte, noms), self.jour)
        livrables = [x["livrable"] for x in rep.sortie.get("exigences", []) if x.get("livrable")]
        critere = ("L'action a lieu au créneau convenu" + (f" et « {livrables[0]} » est remis" if livrables else "")
                   + " ; je dirai ce que j'en ai observé.")          # jamais une fiche que personne n'a demandée
        return rep.sortie | {"texte": texte.strip(), "critere_suggere": critere,
                             "ia": {"fournisseur": rep.appel.fournisseur, "modele": rep.appel.modele, "statut": rep.appel.statut,
                                    "repli": rep.appel.repli, "prompt": rep.appel.prompt, "trace": rep.appel.trace, "mode": rep.sortie.get("mode")}}

    def creer_action(self, pid: str, champs: dict) -> str:
        """Le membre CONFIRME ses exigences et sa fenêtre : un brouillon, visible de lui seul."""
        f = champs["fenetre"]
        fen = Plage(jour=date.fromisoformat(f["jour"]), debut=f["debut"], fin=f["fin"])
        if fen.jour < self.jour:
            raise Invalide("jour passé")
        etapes = [Etape(id=f"e{i + 1}", nature=x["nature"], geste=x["geste"], duree_min=x["duree_min"], concept=x.get("concept"),
                        livrable=x.get("livrable"), role=x.get("role"))
                  for i, x in enumerate(champs["exigences"])]
        for e in etapes:
            if e.concept is not None and e.concept not in self.tax.concepts:
                raise Invalide(f"capacité inconnue : {e.concept}")
        p = Protocole(question=champs["question"], objet=champs.get("objet", ""), critere=champs.get("critere", ""), echeance=fen.jour,
                      fenetre=fen, duree_min_acceptable=champs.get("duree_min_acceptable"), etapes=etapes)
        return self.banc.brouillon(pid, p)

    def publier_action(self, pid: str, eid: str, version: int) -> int:
        """Publier la proposition que le serveur a TROUVÉE (recalculée ici, jamais reçue du navigateur)."""
        a = self.banc.assembler(pid, eid)
        if a["solution"] is None:
            raise Conflit("aucune proposition complète : " + (a["blocage"] or "exigences non couvertes"))
        sol = a["solution"]
        return self.banc.proposer(pid, eid, version, {k: v for k, v in sol["choix"].items() if v}, sol["creneau"])

    def publier_offre(self, pid: str, nature: str, quoi: str, capacite: int, du: date, au: date, duree_max_min: Optional[int],
                      conditions: str, concept: Optional[str], plages: Optional[list[dict]] = None) -> str:
        """Une offre ne peut porter qu'une capacité que le membre DÉCLARE dans son profil (jamais une capacité supposée)."""
        if concept is not None and concept not in {o.concept for o in self.profil(pid).offre}:
            raise Invalide("capacité non déclarée dans votre profil : ajoutez-la d'abord à « je peux aider »")
        return self.banc.publier_offre(pid, nature, quoi, capacite, du, au, duree_max_min=duree_max_min, conditions=conditions, concept=concept,
                                       plages=[Plage(**x) for x in plages or []])

    def modifier_offre(self, pid: str, oid: str, champs: dict) -> list[str]:
        """Le PROPRIÉTAIRE change ses conditions (dont ses horaires) ; les essais concernés sont réévalués pour tous."""
        if champs.get("plages") is not None:
            champs = champs | {"plages": [Plage(**x) for x in champs["plages"]]}
        return self.banc.modifier_offre(pid, oid, **champs)

    def creer_essai(self, pid: str, champs: dict) -> str:
        return self.banc.brouillon(pid, self._protocole(champs))

    def corriger_essai(self, pid: str, eid: str, version: int, champs: dict) -> int:
        """Correction du brouillon. Sans `etapes`, les gestes existants sont CONSERVÉS (invitations, capacités, livrables,
        rôles) ainsi que l'origine et le « quand » — une correction de texte ne défait pas ce qui a été préparé."""
        if champs.get("etapes") is None:
            cur = self.banc.protocole(eid)
            p = self._protocole(champs | {"etapes": []}).model_copy(update={
                "etapes": cur.etapes, "origine": cur.origine, "fenetre": cur.fenetre, "creneau": cur.creneau,
                "duree_min_acceptable": cur.duree_min_acceptable})
            return self.banc.modifier_brouillon(pid, eid, version, Protocole(**p.model_dump()))
        return self.banc.modifier_brouillon(pid, eid, version, self._protocole(champs))


__all__ = ["ClubPulse", "ErreurPulse", "CRITERE_SUGGERE", "CRITERE_ACTION", "descripteur"]
