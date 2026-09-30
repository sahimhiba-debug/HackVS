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

import hashlib
import json
import threading
from datetime import date, timedelta
from typing import Optional

from app.models import Besoin, Offre, Profil
from app.parser_rules import extraire_profil
from app.taxonomy import Taxonomie
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

from . import memoire_club
from .capacites import Claim, Instance, Registre, charger_patrons, choisir_asks, index_claims, pulse_diff
from . import monde_demo as md
from .acces import Sessions
from .detection import Detecteur
from .erreurs import Conflit, ErreurMetier, Interdit, Introuvable, Invalide, NonAuthentifie
from .essai import Banc, Etape, Plage, Protocole
from .ia import AppelIA, Intelligence, besoin_de
from .roles_ia import RolesIA
from .identite import AdhesionsSynthetiques, Coffre, nettoyer
from .modele import BesoinActif, Opportunite
from .observateur import Etat, observer
from .passerelle import CRITERE_SUGGERE, brouillon, essai_existant
from .politique import MODIFIABLES, Contexte, Rendu, Spectateur, descripteur
from .reglages import Reglages
from .vues_capacites import VuesCapacites
from .vues_essai import VuesEssai
from .vues_intelligence import VuesIntelligence

ErreurPulse = ErreurMetier             # nom historique : tout refus du service (sous-classes typées)
# ce qu'on considérera comme RÉALISÉ : une suggestion que le porteur adopte ou remplace (jamais écrite à sa place)
CRITERE_ACTION = ("La présentation a lieu au créneau convenu et la fiche promise est remise ; "
                  "je dirai ce que les acheteurs en ont retenu.")
# Ce qu'un membre DÉCLARE dans son profil et qui est journalisé (événement PROFIL) : rien d'autre ne change un profil.
DECLARATIFS = ("offre", "recherche", "secteurs", "disponible", "accepte_introductions", "maj")
ETAT_MEMBRES = ("PROFIL", "BESOIN", "PREFERENCES", "HORLOGE")


class ClubPulse:
    def __init__(self, tax: Taxonomie, ia: Optional[Intelligence] = None, reglages: Optional[Reglages] = None,
                 neuf: bool = False):
        """`neuf=True` : un journal VIDE (nouvelle démonstration) ; sinon l'état est REPRIS du journal existant.

        UN journal (`self.journal`, fichier si HACKVS_ESSAIS_DB) porte TOUT l'état métier : essais et offres, profils
        déclarés (PROFIL), besoins publiés (BESOIN), préférences de visibilité (PREFERENCES), horloge (HORLOGE),
        appels IA et textes rédigés. L'état en mémoire n'en est qu'un repli : `empreinte_etat()` est la même pour le même
        journal. Hors journal, PAR CONCEPTION : le coffre d'identités et l'activation des comptes, les sessions, les
        notes privées (visibles de leur seule autrice, jamais utilisées par une règle)."""
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
        self._semis = self._empreinte_semis()
        self._profils_depart = {p.id: p for p in brut.profils}      # le monde de départ (données préparées) : base des claims
        self.ia = ia or Intelligence.depuis_environnement(tax, journal=self._tracer_ia,
                                                          notes_privees_autorisees=self.reglages.notes_privees_vers_ia)
        self.ia.journal = self._tracer_ia
        self.ia.identites = self._identites                   # rien du coffre ne part vers un modèle (défense centrale)
        self.ia.secret_empreinte = self.reglages.secret        # empreintes de rejeu : non confirmables sans le secret
        self.ia.rejeu = self._rejeu_ia                        # un appel accepté déjà journalisé est rejoué, pas rappelé
        self.roles_ia = RolesIA(self.ia, tax)                 # EXTRACT, NORMALIZE, NARRATE (registre des capacités)
        self.vues = VuesIntelligence(self)
        # ACTIVATION ENGINE : son propre journal — fichier si HACKVS_ESSAIS_DB (survit au redémarrage), sinon en mémoire.
        # Qui peut être sollicité pour qui : les règles DURES du réseau (langue commune, consentement, disponibilité,
        # profil récent, introduction déjà déclinée), lues dans l'état observé courant — une seule source de vérité.
        self.banc = Banc(Memoire(self.reglages.essais_db), lambda: self.jour, self.organisation_de, self._non_sollicitable,
                         self._membre_peut)
        self.banc.BUDGET_NOEUDS = self.reglages.budget_noeuds
        self.journal = self.banc.m
        # REGISTRE DES CAPACITÉS : patrons écrits par des humains × claims × consentements de finalité, composés par le banc
        self.capacites = Registre(self.banc, charger_patrons(concepts=set(tax.concepts)), lambda: self.jour)
        self.vues_essai = VuesEssai(self)
        self.vues_capacites = VuesCapacites(self)
        self.notes: dict[str, list[dict]] = {}
        self.preferences: dict[str, dict] = {}
        self._scan: Optional[dict] = None
        self._etat: Optional[Etat] = None
        self._version_etat: tuple = ()
        self._version_scan: tuple = ()
        self._revision_profils = 0            # incrémentée à chaque modification de profil (invalide l'analyse)
        for pid in self.coffre._personnes:                   # tous ont activé leur compte, sauf la nouvelle venue
            if pid != md.SOPHIE:
                self.coffre.actives.add(pid)
        if neuf:
            self.journal.vider()
        self._restaurer()

    # ------------------------------------------------------------------ journal : l'état est un repli
    def _empreinte_semis(self) -> str:
        """Ce qui identifie le monde de DÉPART (données préparées, sans identité) : un journal ne se rejoue que sur lui."""
        return hashlib.sha256(json.dumps([self.r.nom, self.r.aujourd_hui.isoformat(), sorted(p.id for p in self.r.profils),
                                          sorted(b.id for b in self.r.besoins)]).encode()).hexdigest()[:16]

    def _restaurer(self) -> None:
        semis = self.journal.evenements("SEMIS")
        if not semis:
            self.journal.ajouter(Evt(type="SEMIS", le=self.jour, statut=Statut.SYNTHETIQUE,
                                     donnees={"monde": self.r.nom, "empreinte": self._semis}))
            return
        if semis[-1].donnees["empreinte"] != self._semis:
            raise ValueError("ce journal appartient à un autre monde de démonstration : il ne peut pas être rejoué ici "
                             "(videz-le, ou choisissez un autre HACKVS_ESSAIS_DB)")
        for e in self.journal.evenements(*ETAT_MEMBRES):
            self._appliquer(e)

    def _appliquer(self, e: Evt) -> None:
        """LE seul chemin qui modifie profils, besoins, préférences et horloge : en direct comme au rejeu."""
        d = e.donnees
        if e.type == "PROFIL":
            p = self.profil(d["membre"])
            self.r.profils = [Profil(**(p.model_dump() | d["champs"])) if q.id == p.id else q for q in self.r.profils]
        elif e.type == "BESOIN":
            b = d["besoin"]
            self.r.besoins.append(BesoinActif(id=b["id"], auteur=b["auteur"], texte=b["texte"], le=date.fromisoformat(b["le"]),
                                              besoin=Besoin(**b["besoin"]), anonyme=b["anonyme"]))
        elif e.type == "PREFERENCES":
            self.preferences[d["membre"]] = dict(d["preferences"])
        elif e.type == "HORLOGE":
            self.r.aujourd_hui = date.fromisoformat(d["jour"])
        self._revision_profils += 1
        self._scan = None

    def _enregistrer(self, type_: str, acteurs: list[str], statut: Optional[Statut] = None, **donnees) -> None:
        """Écrire un fait de l'état des membres puis l'appliquer (même fonction qu'au rejeu). Origine : celle du bloc
        (`joue()` pour la console), DÉCLARÉ par défaut."""
        self.banc._ecrire(type_, acteurs, statut, **donnees)
        self._appliquer(self.journal.evenements(type_)[-1])

    def empreinte_etat(self) -> str:
        """Empreinte de l'état métier COMPLET, recalculé : horloge, profils (sans la clé d'organisation, dérivée du secret
        du processus), besoins, préférences, offres et essais. Même journal → même empreinte."""
        etat = {"jour": self.jour.isoformat(),
                "profils": [p.model_dump(mode="json", exclude={"entreprise"}) for p in sorted(self.r.profils, key=lambda x: x.id)],
                "besoins": [{"id": b.id, "auteur": b.auteur, "texte": b.texte, "le": b.le.isoformat(), "anonyme": b.anonyme,
                             "besoin": b.besoin.model_dump(mode="json")} for b in self.r.besoins],
                "preferences": {k: dict(sorted(v.items())) for k, v in sorted(self.preferences.items())},
                "banc": self.banc.etat_canonique(),
                "capacites": [i.model_dump(mode="json") for i in self.capacites.projeter()]}
        return hashlib.sha256(json.dumps(etat, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

    # ------------------------------------------------------------------ bases
    @property
    def jour(self) -> date:
        return self.r.aujourd_hui

    def organisation_de(self, pid: str) -> str:
        o = self.coffre.organisation_de(pid)
        return o.id if o else f"org-{pid}"

    def _tracer_ia(self, a: AppelIA) -> None:
        # la latence reste dans `ia.appels` (mesure) ; le journal garde un contenu déterministe, donc rejouable à l'octet.
        # Un appel est un fait OBSERVÉ par le système (jamais « simulé ») ; son `issue` dit ce qui a produit la sortie.
        self.banc._ecrire("APPEL_IA", [], Statut.OBSERVE, appel=a.model_dump(exclude={"latence_ms"}))

    def _rejeu_ia(self, cle: str) -> Optional[dict]:
        return next((e.donnees["appel"] for e in reversed(self.journal.evenements("APPEL_IA"))
                     if e.donnees["appel"].get("cle") == cle and e.donnees["appel"].get("issue") == "MODEL_CALLED"), None)

    def _net(self, texte: str) -> str:
        """FRONTIÈRE DU MOTEUR : un texte libre d'un membre que le moteur LIT (profil, besoin, offre, réponse à une
        demande) n'entre dans l'état et le journal que sans identité du coffre — noms, organisations, courriels,
        téléphones —, la sienne comprise. Les textes échangés de personne à personne (question d'un essai, livrable,
        observation) restent tels quels ; vers un modèle, ils passent par `Intelligence.proteger`."""
        return nettoyer(texte, [x for x in self._identites() if x])

    def _identites(self) -> list[str]:
        per = list(self.coffre._personnes.values())
        return [p.nom for p in per] + [p.courriel for p in per] + [p.telephone for p in per if p.telephone] \
            + [o.nom for o in self.coffre.orgs.values()]

    def profil(self, pid: str) -> Profil:
        p = self.r.par_id().get(pid)
        if p is None:
            raise Introuvable("membre inconnu")
        return p

    def _champs_declares(self, p: Profil) -> dict:
        """Ce qui change entre le profil courant et `p` — seulement des champs DÉCLARATIFS (sinon : erreur de programmation)."""
        avant, apres = self.profil(p.id).model_dump(mode="json"), p.model_dump(mode="json")
        change = {k for k in apres if apres[k] != avant[k]}
        if change - set(DECLARATIFS):
            raise ValueError(f"champs non déclaratifs modifiés : {sorted(change - set(DECLARATIFS))}")
        return {k: apres[k] for k in sorted(change)}

    def _remplacer_profil(self, p: Profil) -> None:
        champs = self._champs_declares(p)
        if champs:
            with self.journal.transaction():
                self._enregistrer("PROFIL", [p.id], membre=p.id, champs=champs)
                self.banc.revoir_membre(p.id)

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

    # ------------------------------------------------------------------ registre des capacités
    def projection_capacites(self) -> list[Instance]:
        """La projection des capacités, MISE EN CACHE par ce dont elle dépend (journal, profils, horloge, patrons) : les
        écrans la relisent souvent ; le calcul n'est refait que si l'état a changé. Toujours recalculable."""
        cle = (len(self.journal.evenements()), self._revision_profils, self.jour,
               tuple((p.id, p.version) for p in self.capacites.patrons.values()))
        if getattr(self, "_cache_capacites", (None,))[0] != cle:
            self._cache_capacites = (cle, self.capacites.projeter())
        return [i.model_copy(deep=True) for i in self._cache_capacites[1]]

    def au(self, seq: int) -> "ClubPulse":
        """Une RÉPLIQUE en lecture de l'état tel qu'il était à la position `seq` du journal : les faits jusqu'à `seq`
        sont REJOUÉS dans un journal en mémoire, par la même fonction qu'un redémarrage. Aucun fournisseur de langage
        (le rejeu n'appelle jamais un modèle), rien n'est écrit dans le journal réel."""
        import dataclasses
        replique = ClubPulse(self.tax, ia=Intelligence(self.tax, None), reglages=dataclasses.replace(self.reglages, essais_db=":memory:"),
                             neuf=True)
        replique.journal.vider()
        with replique.journal.transaction():
            for e in self.journal.evenements():
                if e.seq <= seq:
                    replique.journal.ajouter(e)
        replique._restaurer()
        return replique

    def pulse(self, depuis: int, jusqu_a: Optional[int] = None) -> dict:
        """Le PULSE entre deux positions du journal, chacune calculée par rejeu (jamais stockée)."""
        dernier = self.journal.evenements()[-1].seq
        jusqu_a = dernier if jusqu_a is None else jusqu_a
        if not 0 <= depuis <= jusqu_a <= dernier:
            raise Invalide("positions hors du journal")
        avant, apres = self.au(depuis), (self if jusqu_a == dernier else self.au(jusqu_a))
        return pulse_diff(avant.capacites.projeter(), apres.capacites.projeter()) | {
            "depuis": {"position": depuis, "date": avant.jour.isoformat()}, "jusqu_a": {"position": jusqu_a, "date": apres.jour.isoformat()},
            "calcul": "par rejeu du journal, sans modèle de langage", "fictif": True}

    def claims(self) -> list[Claim]:
        """Index BI-TEMPOREL des faits déclarés (offres, compétences, intérêts) : projection du journal."""
        return index_claims(self.journal, self._profils_depart)

    def sollicitable(self, pid: str) -> bool:
        p = self.profil(pid)
        return pid in self.coffre.actives and p.disponible and p.accepte_introductions

    def asks_pour(self, pid: str) -> list[tuple[Instance, str]]:
        """Les demandes (Ask) qu'un membre peut recevoir : il est sollicitable, il n'est pas déjà une pièce de cette
        capacité, il ne s'y est pas retiré, et — si la pièce est une compétence du catalogue — il la DÉCLARE. Une
        catégorie, jamais un choix du système parmi des personnes ; plafond d'attention ; plus fort levier d'abord."""
        if not self.sollicitable(pid):
            return []
        # PLAFOND D'ATTENTION (Reglages) : au plus `asks_montrees` à la fois, aucune pendant `plafond_jours` après une
        # réponse (oui comme non). Lu à chaque lecture ; rien n'est écrit en lisant.
        recentes = [e for e in self.journal.evenements("ASK_REPONSE") if e.acteurs[0] == pid
                    and (self.jour - e.le).days < self.reglages.plafond_jours]
        if recentes:
            return []
        declarees = {o.concept for o in self.profil(pid).offre if o.concept}
        res = []
        for inst in self.projection_capacites():
            if inst.ask is None:
                continue
            deja = {self.banc.offre(v).auteur for v in inst.liaisons.values() if v}
            if pid in deja or (
                    inst.ask.concept is not None and inst.ask.concept not in declarees):
                continue
            res.append(inst)
        return [(i, i.ask.id) for i in choisir_asks(res, self.reglages.asks_montrees)]  # type: ignore[union-attr]

    def repondre_ask(self, pid: str, ask_id: str, oui: bool, attributs: Optional[dict[str, int]] = None, quoi: Optional[str] = None) -> Instance:
        """Relit les demandes de CE membre au moment de répondre (sous le verrou du monde) : deux réponses concurrentes à
        la même demande donnent une seule liaison — la seconde ne trouve plus la demande."""
        if ask_id not in {a for _, a in self.asks_pour(pid)}:
            raise Introuvable("demande inconnue ou plus d'actualité")
        return self.capacites.repondre(pid, ask_id, oui, attributs, self._net(quoi) if quoi else None,
                                       {o.concept for o in self.profil(pid).offre if o.concept})

    def consentir_capacite(self, pid: str, finalite: str) -> Instance:
        return self.capacites.consentir(pid, finalite)

    def retirer_consentement(self, pid: str, finalite: str) -> Instance:
        return self.capacites.retirer(pid, finalite)

    # ------------------------------------------------------------------ le modèle, en PROPOSITION seulement
    def proposer_reponse(self, pid: str, ask_id: str, texte: str) -> tuple[dict, AppelIA, Optional[AppelIA]]:
        """EXTRACT (et NORMALIZE si la pièce est une compétence) sur le texte d'un membre, pour SA demande : une
        proposition qu'il confirme ou corrige dans le formulaire. Rien n'est déclaré ni consenti ici."""
        ask = next((i.ask for i in self.projection_capacites() if i.ask and i.ask.id == ask_id), None)
        if ask is None or ask_id not in {a for _, a in self.asks_pour(pid)}:
            raise Introuvable("demande inconnue ou plus d'actualité")
        texte = self._net(texte)
        ext = self.roles_ia.extraire(texte, ask.minimums)
        nor = self.roles_ia.normaliser(texte) if ask.concept else None
        return {"attributs": ext.sortie["attributs"], "incertitudes": ext.sortie["incertitudes"],
                "concept": nor.sortie["concept"] if nor else None, "concept_attendu": ask.concept}, ext.appel, nor.appel if nor else None

    def raconter_capacite(self, finalite: str) -> tuple[dict, AppelIA]:
        carte = next((x for x in self.vues_capacites.console()["capacites"] if x["finalite"] == finalite), None)
        if carte is None:
            raise Introuvable("capacité inconnue ou sans état à raconter")
        faits = RolesIA.faits(carte)
        rep = self.roles_ia.raconter(faits)
        return {"faits": faits, "phrases": rep.sortie["phrases"]}, rep.appel

    def basculer_ia(self, actif: bool) -> dict:
        self.ia.actif = actif
        return self.ia.etat()

    def relancer_recherche(self, finalite: str) -> Instance:
        return self.capacites.relancer(finalite, self.reglages.budget_relance)

    def acquitter_recherche(self, finalite: str) -> Instance:
        return self.capacites.acquitter(finalite)

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
                    res.append(Offre(concept=c, texte=self._net(str(x["texte"]).strip())[:200]))
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
            ajouter_recherche = self._net(ajouter_recherche)
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
        # Tout ou rien : les deux faits (préférences, profil) sont écrits dans UNE transaction, après validation. Suspendre
        # ses sollicitations vaut pour les NOUVELLES propositions (règles dures) ; un accord déjà donné dans un essai se
        # retire explicitement dans cet essai (dit, daté), jamais en silence.
        nouveau = Profil(**p.model_copy(update=maj).model_dump())              # validé AVANT toute écriture
        champs = self._champs_declares(nouveau)
        with self.journal.transaction():
            if visibilite:
                self._enregistrer("PREFERENCES", [pid], membre=pid, preferences=self.preferences.get(pid, {}) | visibilite)
            if champs:
                self._enregistrer("PROFIL", [pid], membre=pid, champs=champs)
                self.banc.revoir_membre(pid)                  # ses accords en cours : réévalués, comme un changement d'offre
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
        texte = self._net(texte)
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
        self._enregistrer("BESOIN", [pid], besoin={"id": f"bj{len(self.r.besoins):05d}", "auteur": pid, "texte": texte.strip(),
                                                   "le": self.jour.isoformat(), "besoin": b.model_dump(mode="json"), "anonyme": False})
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

    def _membre_peut(self, pid: str, concept: Optional[str]) -> bool:
        """Ce que dit le PROFIL aujourd'hui : disponible, sollicitable, et — pour une capacité du catalogue — la déclare
        encore. Relu par le banc à chaque couverture (accords des essais, consentements des capacités)."""
        p = self.r.par_id().get(pid)
        return p is not None and p.disponible and p.accepte_introductions and (
            concept is None or concept in {o.concept for o in p.offre})

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

    def _faits_decouverte(self, oid: str, sp: Spectateur) -> tuple[Opportunite, dict]:
        o = self.trouver_opportunite(oid)
        if sp.role == "membre" and sp.id != o.beneficiaire:
            raise Interdit("cette découverte ne vous concerne pas")
        return o, {"titre": o.titre, "raisonnement": o.raisonnement, "manque": o.manque, "action": o.action,
                   "risques": o.risques, "personnes_a_solliciter": o.personnes_a_solliciter}

    def narrer_decouverte(self, oid: str, sp: Spectateur) -> dict:
        """COMMANDE : l'IA reformule le « pourquoi » à partir de faits PSEUDONYMISÉS ; le texte contrôlé est journalisé.
        Les lectures le relisent (`en_clair`) — une lecture ne déclenche jamais d'appel au modèle."""
        _, faits = self._faits_decouverte(oid, sp)
        rep = self.ia.expliquer(faits, self.pseudonymes())
        self.banc._ecrire("REDACTION", [], Statut.INFERE, objet=oid, pour=sp.role + (sp.id or ""), texte=rep.sortie["explication"],
                          meta=rep.appel.model_dump(include={"fournisseur", "modele", "prompt", "statut", "repli", "trace"}))
        return self.en_clair(oid, sp)

    def en_clair(self, oid: str, sp: Spectateur) -> dict:
        """LECTURE : la reformulation journalisée si elle existe, sinon l'explication du moteur (sans modèle)."""
        _, faits = self._faits_decouverte(oid, sp)
        pour = sp.role + (sp.id or "")
        e = next((x for x in reversed(self.journal.evenements("REDACTION"))
                  if x.donnees.get("objet") == oid and x.donnees.get("pour") == pour), None)
        texte, appel = (e.donnees["texte"], e.donnees["meta"]) if e else \
            (Intelligence.gabarit_explication(faits), {"fournisseur": "deterministe", "modele": None, "prompt": None, "statut": "OK",
                                                        "repli": False, "trace": None})
        return {"texte": self.rendu().texte(sp, texte), "ia": appel,
                "source": ("Apertus (texte contrôlé : fidèle aux faits)" if appel["fournisseur"] == "apertus" and not appel["repli"]
                           else "règles du moteur (aucun modèle génératif utilisé)")}

    def _faits_invitation(self, eid: str, pid: str) -> Optional[tuple[dict, list[str]]]:
        p = self.banc.protocole(eid)
        e = next((x for x in p.etapes if x.contributeur == pid and x.invitation), None)
        if e is None:
            return None
        porteur = self.banc.porteur(eid)
        prof, per = self.r.par_id().get(porteur), self.coffre.identite(porteur)
        faits = {"capacite_declaree": self.tax.libelle(e.concept) if e.concept else e.geste, "demande": p.question,
                 "secteur_demandeur": self.tax.libelle(prof.secteurs[0]) if prof and prof.secteurs else "non précisé",
                 "partage": "votre nom et votre organisation à cette personne seulement si vous acceptez"}
        return faits, [per.nom if per else "", self.coffre.pseudonyme(porteur)]

    def rediger_invitations(self, eid: str) -> int:
        """COMMANDE (après une écriture) : rédige UNE fois, par (essai, version, invité), le message d'invitation — IA
        contrôlée si configurée, sinon gabarit déclaré — et le JOURNALISE. Renvoie le nombre de messages rédigés."""
        v, n = self.banc.version(eid), 0
        if self.banc.etat(eid) == "BROUILLON":                   # rien n'est envoyé avant publication
            return 0
        for e in self.banc.protocole(eid).etapes:
            if not (e.invitation and e.contributeur) or self.banc.redaction(eid, v, e.contributeur):
                continue
            faits, interdits = self._faits_invitation(eid, e.contributeur) or ({}, [])
            rep = self.ia.rediger_sollicitation(faits, interdits)
            self.banc.enregistrer_redaction(eid, v, e.contributeur, rep.sortie["message"],
                                            rep.appel.model_dump(include={"fournisseur", "modele", "statut", "repli"}))
            n += 1
        return n

    def message_invitation(self, eid: str, pid: str) -> Optional[dict]:
        """LECTURE : le message qu'une personne INVITÉE lit — celui rédigé et journalisé, sinon le gabarit (sans modèle).
        Une lecture, un rafraîchissement ou un rejeu ne rappellent JAMAIS le modèle."""
        fi = self._faits_invitation(eid, pid)
        if fi is None:
            return None
        r = self.banc.redaction(eid, self.banc.version(eid), pid)
        if r is not None:
            return {"texte": r.donnees["texte"], "ia": r.donnees["meta"]}
        return {"texte": Intelligence.gabarit_sollicitation(fi[0]), "ia": {"fournisseur": "deterministe", "modele": None,
                                                                            "statut": "OK", "repli": False}}

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
        jour = self.jour + timedelta(days=jours)
        self.banc._ecrire("HORLOGE", [], Statut.SIMULE, avance_jours=jours, jour=jour.isoformat())
        self._appliquer(self.journal.evenements("HORLOGE")[-1])
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
        with self.banc.origine(Statut.JOUE):                   # JOURNALISÉ : la marque survit au redémarrage
            self.banc._ecrire("GESTE_JOUE", [pid], role=role, geste=geste)

    def joue(self):
        """Contexte : les faits écrits dedans sont JOUÉS par l'équipe (console de démonstration)."""
        return self.banc.origine(Statut.JOUE)

    @property
    def joues(self) -> list[dict]:
        """Gestes JOUÉS par l'équipe depuis la console (démonstration), relus du journal."""
        return [{"le": e.le.isoformat(), "membre": e.acteurs[0], "role": e.donnees["role"], "geste": e.donnees["geste"],
                 "joue_par": "l'équipe (console)"} for e in self.banc.m.evenements("GESTE_JOUE")]

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
        return self.banc.publier_offre(pid, nature, self._net(quoi), capacite, du, au, duree_max_min=duree_max_min,
                                       conditions=self._net(conditions), concept=concept,
                                       plages=[Plage(**x) for x in plages or []])

    def modifier_offre(self, pid: str, oid: str, champs: dict) -> list[str]:
        """Le PROPRIÉTAIRE change ses conditions (dont ses horaires) ; les essais concernés sont réévalués pour tous."""
        if champs.get("plages") is not None:
            champs = champs | {"plages": [Plage(**x) for x in champs["plages"]]}
        for k in ("quoi", "conditions"):
            if champs.get(k):
                champs = champs | {k: self._net(champs[k])}
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
