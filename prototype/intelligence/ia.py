"""Couche IA : Apertus pour COMPRENDRE et DIRE ; le code pour DÉCIDER.

    Fournisseur (Apertus | aucun) ─→ sortie brute ─→ VALIDATION déterministe ─→ acceptée | rejetée → repli déterministe

- `Apertus` : API compatible OpenAI (/chat/completions), point d'accès, modèle, délai et nouvel essai configurables
  (APERTUS_BASE_URL, APERTUS_API_KEY, APERTUS_MODEL, APERTUS_DELAI_S). Aucune clé dans le code. Sortie JSON contrainte
  quand le serveur l'accepte, sinon consigne seule — et TOUJOURS revalidée.
- Sans configuration, `Intelligence` utilise le repli DÉTERMINISTE, et chaque appel le dit (`fournisseur`,
  `repli`) : aucun appel n'est simulé, aucun libellé « Apertus » n'apparaît si Apertus n'a pas répondu.
- `Maquette` : réponses écrites à la main, pour les TESTS uniquement (jamais sélectionnée par l'application).
- Minimisation : le modèle ne reçoit jamais la base, jamais un nom ni un contact — seulement le texte saisi par le
  membre, ou des faits PSEUDONYMISÉS (MEMBRE-xxx). Il ne décide ni d'une permission, ni d'un état, ni d'une révélation.
- Traçabilité : chaque appel → `AppelIA` (trace, tâche, fournisseur, modèle, version du prompt, latence, statut,
  contrôle) ; le contenu n'est pas journalisé.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import random
import re
from datetime import date, timedelta
import time
from pathlib import Path
from typing import Callable, Literal, Optional, Protocol

from pydantic import BaseModel, ValidationError, model_validator

from adaptateurs.club.synthese import verifier
from app.models import Besoin
from app.parser_llm import SCHEMA as SCHEMA_BESOIN
from app.parser_llm import SortieLLM, _json_de, systeme, valider

from app.parser_rules import analyser as analyser_regles
from app.taxonomy import Taxonomie, norm

_journal = logging.getLogger("intelligence.ia")
PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
Statut = Literal["OK", "INCERTAIN", "REJETE", "INDISPONIBLE"]
# CE QUI A PRODUIT la sortie montrée — jamais « simulé » : le modèle (sortie acceptée), un enregistrement rejoué sans
# rappeler le modèle, ou la forme déterministe (aucun modèle, panne, sortie rejetée)
Issue = Literal["MODEL_CALLED", "CACHE_REPLAY", "FALLBACK_FORM"]


def prompt(nom: str) -> tuple[str, str]:
    """(texte, version) : la version la plus récente de `prompts/<nom>_vN.md`."""
    fichiers = sorted(PROMPTS.glob(f"{nom}_v*.md"), key=lambda p: int(p.stem.rsplit("_v", 1)[1]))
    if not fichiers:
        raise FileNotFoundError(nom)
    f = fichiers[-1]
    return f.read_text(encoding="utf-8"), f.stem


class AppelIA(BaseModel):
    trace: str
    tache: str
    fournisseur: str               # « apertus », « deterministe » ou « maquette » (tests)
    modele: Optional[str] = None
    prompt: Optional[str] = None
    latence_ms: float
    statut: Statut
    repli: bool = False            # la sortie montrée vient du repli déterministe
    erreur: Optional[str] = None
    politique: Optional[str] = None  # raison d'un traitement LOCAL imposé (ex. note privée)
    controle: Optional[dict] = None
    issue: Optional[Issue] = None    # déduite si absente : repli ou aucun modèle → FALLBACK_FORM, sinon MODEL_CALLED
    # tâches REJOUABLES seulement (sorties sans donnée personnelle, validées) : de quoi rejouer sans rappeler le modèle
    cle: Optional[str] = None        # HMAC (secret du processus) de la version du prompt et du message protégé
    sortie: Optional[dict] = None    # la sortie ACCEPTÉE (jamais une sortie brute ni rejetée)
    rejoue: Optional[str] = None     # CACHE_REPLAY : la trace de l'appel rejoué
    tentatives: int = 0              # appels au modèle pour cette sortie (1 nouvel essai au plus après un rejet)
    rejets: list[str] = []           # raisons des sorties rejetées (jamais leur contenu)

    @model_validator(mode="after")
    def _issue(self) -> "AppelIA":
        if self.issue is None:
            self.issue = "FALLBACK_FORM" if self.repli or self.fournisseur == "deterministe" else "MODEL_CALLED"
        return self


class Reponse(BaseModel):
    sortie: dict
    appel: AppelIA


class ErreurFournisseur(RuntimeError):
    """CONTRAT de tout fournisseur : toute panne (réseau, délai, 429, 5xx, réponse mal formée) est levée sous ce type.
    `Intelligence` ne rattrape QUE celui-ci : un bogue de notre code n'est jamais déguisé en « fournisseur indisponible »."""

    def __init__(self, cause: str, reessayable: bool = False):
        super().__init__(cause)
        self.cause, self.reessayable = cause, reessayable


class Fournisseur(Protocol):
    nom: str
    modele: str

    def completer(self, systeme_txt: str, message: str, schema: Optional[dict]) -> str:
        """Texte brut du modèle, ou `ErreurFournisseur`. Jamais d'autre exception."""
        ...


class NonConfigure(RuntimeError):
    pass


class Apertus:
    """Apertus via une API compatible OpenAI. Délai borné, 3 tentatives au plus avec recul exponentiel et gigue sur
    les erreurs RÉESSAYABLES (réseau, délai, 429, 5xx) — une requête ne peut ni pendre, ni boucler."""
    nom = "apertus"
    TENTATIVES = 3

    def __init__(self, http=None, dormir: Callable[[float], None] = time.sleep, alea: Optional[random.Random] = None):
        manque = [k for k in ("APERTUS_BASE_URL", "APERTUS_API_KEY", "APERTUS_MODEL") if not os.environ.get(k)]
        if manque:
            raise NonConfigure("variables absentes : " + ", ".join(manque))
        self.base = os.environ["APERTUS_BASE_URL"].rstrip("/")
        self.modele = os.environ["APERTUS_MODEL"]
        self._cle = os.environ["APERTUS_API_KEY"]
        self.delai = float(os.environ.get("APERTUS_DELAI_S", "30"))
        self.http = http
        self._dormir, self._alea = dormir, alea or random.Random()

    def __repr__(self) -> str:                               # jamais la clé dans une trace ou un journal
        return f"Apertus(base={self.base!r}, modele={self.modele!r})"

    @staticmethod
    def configure() -> bool:
        return all(os.environ.get(k) for k in ("APERTUS_BASE_URL", "APERTUS_API_KEY", "APERTUS_MODEL"))

    def completer(self, systeme_txt: str, message: str, schema: Optional[dict]) -> str:
        import httpx
        client = self.http or httpx.Client(timeout=httpx.Timeout(self.delai, connect=10.0))
        corps: dict = {"model": self.modele, "temperature": 0, "max_tokens": 900,
                       "messages": [{"role": "system", "content": systeme_txt + (
                           "\nRéponds UNIQUEMENT par un objet JSON conforme à ce schéma :\n" + json.dumps(schema, ensure_ascii=False)
                           if schema else "")}, {"role": "user", "content": message}]}
        if schema:
            corps["response_format"] = {"type": "json_schema", "json_schema": {"name": "sortie", "schema": schema, "strict": True}}
        entetes = {"Authorization": f"Bearer {self._cle}", "Content-Type": "application/json"}
        derniere = ErreurFournisseur("aucune tentative")
        for tentative in range(self.TENTATIVES):
            if tentative:
                self._dormir(min(4.0, 0.5 * 2 ** (tentative - 1)) * (0.5 + self._alea.random()))   # recul + gigue
            try:
                rep = client.post(f"{self.base}/chat/completions", headers=entetes, json=corps)
                if rep.status_code in (400, 422) and "response_format" in corps:
                    corps.pop("response_format")              # serveur sans sortie contrainte : la consigne reste
                    rep = client.post(f"{self.base}/chat/completions", headers=entetes, json=corps)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                derniere = ErreurFournisseur(type(e).__name__, reessayable=True)
                continue
            if rep.status_code == 429 or rep.status_code >= 500:
                derniere = ErreurFournisseur(f"HTTP {rep.status_code}", reessayable=True)
                continue
            if rep.status_code >= 400:
                raise ErreurFournisseur(f"HTTP {rep.status_code}")               # 401, 403, 404… : inutile de réessayer
            try:
                return str(rep.json()["choices"][0]["message"]["content"] or "")
            except (ValueError, KeyError, IndexError, TypeError) as e:
                raise ErreurFournisseur(f"réponse mal formée ({type(e).__name__})") from None
        raise derniere


class Maquette:
    """TESTS UNIQUEMENT : renvoie des réponses écrites à la main, par tâche."""
    nom = "maquette"
    modele = "maquette"

    def __init__(self, reponses: dict[str, str]):
        self.reponses = reponses

    def completer(self, systeme_txt: str, message: str, schema: Optional[dict]) -> str:
        cle = next((k for k in self.reponses if k in systeme_txt), None)
        if cle is None:
            raise ErreurFournisseur("aucune réponse de maquette")   # même contrat que le vrai fournisseur
        return self.reponses[cle]


# ------------------------------------------------------------------ schémas et sorties
class Extrait(BaseModel):
    concept: str
    extrait: str


class Capture(BaseModel):
    personne_mentionnee: Optional[str] = None
    organisation_mentionnee: Optional[str] = None
    sujets: list[str] = []
    besoin_de_l_autre: Optional[Extrait] = None
    capacite_de_l_autre: Optional[Extrait] = None
    besoin_du_membre: Optional[Extrait] = None
    suite_proposee: Optional[str] = None
    incertitudes: list[str] = []
    statut: Literal["OK", "INSUFFISANT"] = "OK"


def _schema_extrait() -> dict:
    return {"anyOf": [{"type": "null"}, {"type": "object", "properties": {"concept": {"type": "string"}, "extrait": {"type": "string"}},
                                          "required": ["concept", "extrait"], "additionalProperties": False}]}


SCHEMA_CAPTURE = {"type": "object", "additionalProperties": False,
                  "required": ["personne_mentionnee", "organisation_mentionnee", "sujets", "besoin_de_l_autre",
                               "capacite_de_l_autre", "besoin_du_membre", "suite_proposee", "incertitudes"],
                  "properties": {"personne_mentionnee": {"type": ["string", "null"]}, "organisation_mentionnee": {"type": ["string", "null"]},
                                 "sujets": {"type": "array", "items": {"type": "string"}},
                                 "besoin_de_l_autre": _schema_extrait(), "capacite_de_l_autre": _schema_extrait(),
                                 "besoin_du_membre": _schema_extrait(), "suite_proposee": {"type": ["string", "null"]},
                                 "incertitudes": {"type": "array", "items": {"type": "string"}}}}
SCHEMA_ESSAI = {"type": "object", "additionalProperties": False, "required": ["question", "objet", "critere", "etapes"],
                "properties": {"question": {"type": "string"}, "objet": {"type": "string"}, "critere": {"type": "string"},
                               "etapes": {"type": "array", "maxItems": 3, "items": {
                                   "type": "object", "additionalProperties": False, "required": ["nature", "geste", "duree_min"],
                                   "properties": {"nature": {"type": "string", "enum": ["temps", "lieu", "objet", "competence"]},
                                                  "geste": {"type": "string"}, "duree_min": {"type": "integer"}}}}}}
SCHEMA_ACTION = {"type": "object", "additionalProperties": False, "required": ["objet", "langue_public", "exigences", "fenetre", "manquant"],
                 "properties": {
                     "objet": {"type": "string"}, "langue_public": {"type": ["string", "null"]},
                     "exigences": {"type": "array", "minItems": 1, "maxItems": 4, "items": {
                         "type": "object", "additionalProperties": False,
                         "required": ["role", "nature", "concept", "geste", "duree_min", "livrable"],
                         "properties": {"role": {"type": "string", "enum": ["voix", "lieu", "public", "autre"]},
                                        "nature": {"type": "string", "enum": ["temps", "lieu", "objet", "competence"]},
                                        "concept": {"type": ["string", "null"]}, "geste": {"type": "string"},
                                        "duree_min": {"type": "integer"}, "livrable": {"type": ["string", "null"]}}}},
                     "fenetre": {"type": "object", "additionalProperties": False, "required": ["jour", "debut", "fin"],
                                 "properties": {"jour": {"type": ["string", "null"]}, "debut": {"type": ["string", "null"]},
                                                "fin": {"type": ["string", "null"]}}},
                     "manquant": {"type": "array", "maxItems": 4, "items": {"type": "string"}}}}
SCHEMA_TEXTE = {"explication": {"type": "object", "additionalProperties": False, "required": ["explication"],
                                "properties": {"explication": {"type": "string"}}},
                "message": {"type": "object", "additionalProperties": False, "required": ["message"],
                            "properties": {"message": {"type": "string"}}}}

# Une sortie de modèle qui contient un courriel, un téléphone ou une adresse web est rejetée : le modèle ne reçoit
# aucune de ces données, donc toute occurrence est soit inventée, soit une fuite — les deux sont refusées.
_DONNEES_PERSONNELLES = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+|(?:\+|00)\d[\d .-]{7,}\d|https?://|www\.", re.I)
_PREMIERE = re.compile(r"\b(je|j'|nous|moi|mon|ma|mes|notre|nos|ich|wir|mein|meine|i|we|my|our)\b")
_BESOIN = re.compile(r"(cherch|veu|besoin|souhait|recherch|aimerai|voudrai|trouver|\bdois\b|\bdevons\b|\bfaut\b|sucht|suchen|brauch|looking for|need|want)")
_RENCONTRE = re.compile(r"(rencontr|croise|vu |getroffen|met )")
_CAPACITE = re.compile(r"(propos|represent|repr[ée]sent|fai[ts]|vend|offr|sp[ée]cialis|fabriqu|install|distribu|anbiet|verkauf|offer|provide|sell)")
_MAJ = re.compile(r"\b([A-ZÀ-Ý][a-zà-ÿ]+(?:[- ][A-ZÀ-Ý][a-zà-ÿ]+)?)\b")
_NON_NOMS = {"Je", "Il", "Elle", "Ils", "Elles", "Nous", "Moi", "Ma", "Mon", "Mes", "La", "Le", "Les", "Un", "Une", "On",
             "Foire", "Salon", "Club", "Valais", "Allemagne", "France", "Suisse", "Ich", "Wir", "Er", "Sie", "I", "We", "Ce",
             "Cette", "Et", "Mais", "Donc", "Pour", "Avec", "Chez", "Au", "Aux", "Des", "Du", "De", "Rencontré", "Rencontre",
             "Croisé", "Vu", "Bonne", "Bon", "Super", "Munich", "Sion", "Martigny", "Bio"}


class Intelligence:
    """Point d'entrée unique des tâches de langage. `fournisseur=None` : repli déterministe (déclaré)."""

    def __init__(self, tax: Taxonomie, fournisseur: Optional[Fournisseur] = None,
                 journal: Optional[Callable[[AppelIA], None]] = None, notes_privees_autorisees: bool = False,
                 horloge: Callable[[], float] = time.monotonic):
        self.tax = tax
        self.f = fournisseur
        self.journal = journal
        self.appels: list[AppelIA] = []
        self.notes_privees_autorisees = notes_privees_autorisees
        self._horloge = horloge
        # identités réelles (coffre) à retirer de TOUT message avant envoi : défense centrale, quelle que soit la tâche
        # ou l'appelant (défaut trouvé à l'audit : `comprendre_demande` recevait un nom réel non nettoyé)
        self.identites: Callable[[], list[str]] = lambda: []
        # INTERRUPTEUR visible (console) : IA éteinte → la forme déterministe partout, dite comme telle
        self.actif = True
        # REJEU : clé secrète des empreintes, et recherche d'un appel ACCEPTÉ déjà enregistré (branchées par Club Pulse)
        self.secret_empreinte: bytes = os.urandom(32)
        self.rejeu: Callable[[str], Optional[dict]] = lambda cle: None
        self._echecs_consecutifs = 0
        self._ferme_jusqu_a = 0.0

    SEUIL_DISJONCTEUR = 3                   # 3 pannes de suite : on cesse d'appeler le fournisseur…
    PAUSE_DISJONCTEUR_S = 60.0              # …pendant 60 s (la démonstration reste fluide), puis on réessaie

    @classmethod
    def depuis_environnement(cls, tax: Taxonomie, journal=None, notes_privees_autorisees: bool = False) -> "Intelligence":
        """LE seul endroit qui choisit le fournisseur. Le reste du code ne teste jamais « est-ce Apertus ? »."""
        return cls(tax, Apertus() if Apertus.configure() else None, journal, notes_privees_autorisees)

    def etat(self) -> dict:
        derniers = [a for a in self.appels if a.fournisseur == "apertus"]
        return {"fournisseur": self.f.nom if self.f else "deterministe", "modele": self.f.modele if self.f else None,
                "configure": self.f is not None, "actif": self.actif,
                "issues": {k: sum(1 for a in self.appels if a.issue == k) for k in ("MODEL_CALLED", "CACHE_REPLAY", "FALLBACK_FORM")},
                "appels_apertus_reussis": sum(1 for a in derniers if a.statut == "OK" and not a.repli),
                "appels_apertus_echoues": sum(1 for a in derniers if a.repli)}

    # ------------------------------------------------------------------ mécanique commune
    def _tracer(self, a: AppelIA) -> None:
        self.appels.append(a)
        # métadonnées seulement : ni l'entrée, ni le prompt rempli, ni la sortie du modèle
        _journal.log(logging.WARNING if a.repli and a.fournisseur != "deterministe" else logging.INFO, "appel IA",
                     extra={"trace": a.trace, "tache": a.tache, "fournisseur": a.fournisseur, "modele": a.modele, "prompt": a.prompt,
                            "statut": a.statut, "repli": a.repli, "politique": a.politique, "erreur_ia": a.erreur, "duree_ms": a.latence_ms})
        if self.journal:
            self.journal(a)

    def proteger(self, message: str) -> str:
        """Ce qui quitte le serveur vers un modèle : sans nom, organisation, courriel ni téléphone du coffre."""
        from .identite import nettoyer
        return nettoyer(message, [x for x in self.identites() if x])

    def _executer(self, tache: str, nom_prompt: Optional[str], message: str, schema: Optional[dict],
                  valider_sortie: Callable[[str], tuple[dict, Optional[dict]]], repli: Callable[[], dict],
                  local_seulement: Optional[str] = None, rejouable: bool = False) -> Reponse:
        """entrée → fournisseur → sortie BRUTE (non fiable) → validation (schéma, vocabulaire, extraits, faits, données
        personnelles) → acceptée, ou rejetée au profit du repli déterministe. Chaque issue est tracée."""
        # identifiant d'appel SANS lien avec le contenu : une empreinte du message (ancienne version) permettait, à qui
        # lit les journaux, de confirmer une supposition sur une note privée courte
        trace = f"ia-{len(self.appels) + 1:06d}"
        t0 = time.perf_counter()
        ms = lambda: round((time.perf_counter() - t0) * 1000, 1)  # noqa: E731
        if not self.actif and not local_seulement:
            local_seulement = "IA éteinte par l'animation (interrupteur)"
        if rejouable and not local_seulement:
            return self._rejouable(tache, nom_prompt, message, schema, valider_sortie, repli, trace, t0)
        if self.f is None or local_seulement:
            sortie = repli()
            a = AppelIA(trace=trace, tache=tache, fournisseur="deterministe", latence_ms=ms(), politique=local_seulement,
                        statut="OK" if sortie.get("statut", "OK") == "OK" else "INCERTAIN")
            self._tracer(a)
            return Reponse(sortie=sortie, appel=a)
        texte_prompt, version = prompt(nom_prompt) if nom_prompt else (systeme(self.tax), "comprendre_demande_v1")
        if self._horloge() < self._ferme_jusqu_a:                 # disjoncteur ouvert : on n'insiste pas
            sortie = repli()
            a = AppelIA(trace=trace, tache=tache, fournisseur=self.f.nom, modele=self.f.modele, prompt=version, latence_ms=ms(),
                        statut="INDISPONIBLE", repli=True, erreur="disjoncteur ouvert après pannes répétées")
            self._tracer(a)
            return Reponse(sortie=sortie, appel=a)
        try:
            brut = self.f.completer(texte_prompt, self.proteger(message), schema)
            self._echecs_consecutifs = 0
        except ErreurFournisseur as e:                            # panne du FOURNISSEUR seulement : repli VISIBLE
            self._echecs_consecutifs += 1
            if self._echecs_consecutifs >= self.SEUIL_DISJONCTEUR:
                self._ferme_jusqu_a = self._horloge() + self.PAUSE_DISJONCTEUR_S
            sortie = repli()
            a = AppelIA(trace=trace, tache=tache, fournisseur=self.f.nom, modele=self.f.modele, prompt=version,
                        latence_ms=ms(), statut="INDISPONIBLE", repli=True, erreur=e.cause[:120])
            self._tracer(a)
            return Reponse(sortie=sortie, appel=a)
        try:
            if _DONNEES_PERSONNELLES.search(brut):
                raise ValueError("la sortie contient une donnée personnelle (courriel, téléphone ou adresse web)")
            sortie, controle = valider_sortie(brut)
            statut: Statut = "OK" if sortie.get("statut", "OK") == "OK" else "INCERTAIN"
            a = AppelIA(trace=trace, tache=tache, fournisseur=self.f.nom, modele=self.f.modele, prompt=version,
                        latence_ms=round((time.perf_counter() - t0) * 1000, 1), statut=statut, controle=controle)
        except (ValueError, ValidationError, KeyError, TypeError) as e:   # sortie invalide ou infidèle : rejetée
            sortie = repli()
            a = AppelIA(trace=trace, tache=tache, fournisseur=self.f.nom, modele=self.f.modele, prompt=version,
                        latence_ms=round((time.perf_counter() - t0) * 1000, 1), statut="REJETE", repli=True,
                        erreur=str(e).splitlines()[0][:200])
        self._tracer(a)
        return Reponse(sortie=sortie, appel=a)

    def empreinte(self, version: str, message_protege: str) -> str:
        return hmac.new(self.secret_empreinte, f"{version}\n{message_protege}".encode(), hashlib.sha256).hexdigest()[:32]

    def _rejouable(self, tache: str, nom_prompt: Optional[str], message: str, schema: Optional[dict],
                   valider_sortie: Callable[[str], tuple[dict, Optional[dict]]], repli: Callable[[], dict],
                   trace: str, t0: float) -> Reponse:
        """Tâches du registre : (1) un appel ACCEPTÉ déjà enregistré pour la même entrée est REJOUÉ, sans rappeler le
        modèle (même hors ligne) ; (2) sinon le modèle, et UN nouvel essai si sa sortie est rejetée (la raison du rejet
        lui est dite, jamais la sortie d'un autre) ; (3) sinon la forme déterministe. La sortie acceptée est gardée."""
        texte_prompt, version = prompt(nom_prompt or tache)
        protege = self.proteger(message)
        cle = self.empreinte(version, protege)
        ms = lambda: round((time.perf_counter() - t0) * 1000, 1)  # noqa: E731
        ancien = self.rejeu(cle)
        if ancien is not None:
            a = AppelIA(trace=trace, tache=tache, fournisseur=ancien["fournisseur"], modele=ancien.get("modele"), prompt=version,
                        latence_ms=ms(), statut="OK", issue="CACHE_REPLAY", cle=cle, sortie=ancien["sortie"], rejoue=ancien["trace"])
            self._tracer(a)
            return Reponse(sortie=dict(ancien["sortie"]), appel=a)
        rejets: list[str] = []
        erreur: Optional[str] = None
        disjoncte = self._horloge() < self._ferme_jusqu_a
        if self.f is not None and not disjoncte:
            consigne = protege
            for _ in range(2):
                try:
                    brut = self.f.completer(texte_prompt, consigne, schema)
                    self._echecs_consecutifs = 0
                except ErreurFournisseur as e:
                    self._echecs_consecutifs += 1
                    if self._echecs_consecutifs >= self.SEUIL_DISJONCTEUR:
                        self._ferme_jusqu_a = self._horloge() + self.PAUSE_DISJONCTEUR_S
                    erreur = e.cause[:120]
                    break
                try:
                    if _DONNEES_PERSONNELLES.search(brut):
                        raise ValueError("la sortie contient une donnée personnelle (courriel, téléphone ou adresse web)")
                    sortie, controle = valider_sortie(brut)
                    a = AppelIA(trace=trace, tache=tache, fournisseur=self.f.nom, modele=self.f.modele, prompt=version, latence_ms=ms(),
                                statut="OK", controle=controle, cle=cle, sortie=sortie, tentatives=len(rejets) + 1, rejets=rejets)
                    self._tracer(a)
                    return Reponse(sortie=sortie, appel=a)
                except (ValueError, ValidationError, KeyError, TypeError, AttributeError) as e:
                    rejets.append(str(e).splitlines()[0][:160])
                    consigne = protege + "\n\nTa sortie précédente a été REJETÉE : " + rejets[-1] + ". Corrige-la en respectant le schéma."
        elif disjoncte:
            erreur = "disjoncteur ouvert après pannes répétées"
        sortie = repli()
        a = AppelIA(trace=trace, tache=tache, fournisseur=self.f.nom if self.f else "deterministe", modele=self.f.modele if self.f else None,
                    prompt=version, latence_ms=ms(), statut="REJETE" if rejets else ("INDISPONIBLE" if erreur else "OK"), repli=True,
                    issue="FALLBACK_FORM", erreur=erreur, cle=cle, tentatives=len(rejets) + (1 if erreur and self.f and not disjoncte else 0),
                    rejets=rejets)
        self._tracer(a)
        return Reponse(sortie=sortie, appel=a)

    # ------------------------------------------------------------------ tâches
    def comprendre_demande(self, texte: str) -> Reponse:
        def valide(brut: str) -> tuple[dict, Optional[dict]]:
            b = valider(texte, SortieLLM.model_validate_json(_json_de(brut)), self.tax)
            b.analyseur = "apertus"
            return {"besoin": b.model_dump()}, {"avertissements": b.avertissements}
        return self._executer("comprendre_demande", None, texte, SCHEMA_BESOIN, valide,
                              lambda: {"besoin": analyser_regles(texte, self.tax).model_dump()})

    OBJETS_CONNUS = ("étiquette", "emballage", "flacon", "bouteille", "présentoir", "stand", "affiche", "flyer", "brochure",
                     "carte de visite", "site web", "menu", "logo", "boîte", "sachet", "vitrine")

    def structurer_essai(self, texte: str) -> Reponse:
        """Formulation d'un membre → BROUILLON d'essai (question, objet, critère, gestes) qu'il corrige. Ce n'est jamais
        une décision : aucun nom, aucune disponibilité, aucun accord ne peut en sortir (le schéma ne les contient pas).
        Secours : FORMULAIRE pré-rempli par des règles simples (texte recopié, objet reconnu dans une liste courte) —
        il ne prétend pas comprendre le texte libre ; le reste est à compléter par le membre."""
        def valide(brut: str) -> tuple[dict, Optional[dict]]:
            d = json.loads(_json_de(brut))
            etapes = d.get("etapes") or []
            if not isinstance(etapes, list) or len(etapes) > 3:
                raise ValueError("gestes absents ou trop nombreux")
            propres = []
            for e in etapes:
                if e.get("nature") not in ("temps", "lieu", "objet", "competence"):
                    raise ValueError("nature de geste inconnue")
                duree = int(e.get("duree_min", 0))
                if not 1 <= duree <= 60 or not 3 <= len(str(e.get("geste", ""))) <= 200:
                    raise ValueError("geste ou durée hors bornes")
                propres.append({"nature": e["nature"], "geste": str(e["geste"]).strip(), "duree_min": duree})
            champs = {k: str(d.get(k) or "").strip() for k in ("question", "objet", "critere")}
            if not 3 <= len(champs["question"]) <= 300 or len(champs["objet"]) > 120 or len(champs["critere"]) > 300:
                raise ValueError("champ vide ou trop long")
            if "MEMBRE-" in brut:
                raise ValueError("la sortie cite un identifiant de membre")
            return champs | {"etapes": propres, "mode": "apertus"}, None

        def repli() -> dict:
            t = " ".join(texte.split())
            n = t.lower()
            objet = next((o for o in self.OBJETS_CONNUS if o in n), "")
            return {"question": t[:300], "objet": objet, "critere": "", "etapes": [], "mode": "formulaire"}
        return self._executer("structurer_essai", "structurer_essai", texte, SCHEMA_ESSAI, valide, repli)

    LANGUES = {"de": ("allemand", ("allemand", "germanophone", "deutsch", "german", "alémanique")),
               "it": ("italien", ("italien", "italophone", "italiano", "italian")),
               "en": ("anglais", ("anglais", "anglophone", "english"))}
    PUBLIC_PAR_LANGUE = {"de": "export_allemagne"}
    JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
    # ordre significatif : « après-midi » contient « midi » (défaut trouvé en l'exécutant)
    MOMENTS = {"apres-midi": ("14:00", "18:00"), "apres midi": ("14:00", "18:00"), "matin": ("08:00", "12:00"),
               "soir": ("17:00", "20:00"), "midi": ("11:30", "14:00")}

    def comprendre_action(self, texte: str, aujourd_hui: date) -> Reponse:
        """Formulation libre d'un membre → EXIGENCES d'une action collective (qui apporterait quoi, quand) et ce qui
        MANQUE pour la préparer. Une proposition à confirmer par le membre, jamais une décision : aucune offre, aucune
        disponibilité, aucun nom ne peut en sortir (le schéma ne les contient pas ; le serveur cherche les offres).
        Secours : RÈGLES SIMPLES visibles (mots reconnus : langue, lieu, public, jour, moment, durée)."""
        message = (f"Date du jour : {aujourd_hui.isoformat()} ({self.JOURS[aujourd_hui.weekday()]})\nCapacités du catalogue :\n"
                   + "\n".join(f"- {c.id} : {c.libelle}" for c in self.tax.concepts.values()) + f"\n\nTexte du membre :\n{texte}")

        def valide(brut: str) -> tuple[dict, Optional[dict]]:
            if "MEMBRE-" in brut:
                raise ValueError("la sortie cite un identifiant de membre")
            d = json.loads(_json_de(brut))
            exig = d.get("exigences") or []
            if not 1 <= len(exig) <= 4:
                raise ValueError("exigences absentes ou trop nombreuses")
            propres = []
            for x in exig:
                if x.get("nature") not in ("temps", "lieu", "objet", "competence") or x.get("role") not in ("voix", "lieu", "public", "autre"):
                    raise ValueError("nature ou rôle inconnu")
                if x.get("concept") is not None and x["concept"] not in self.tax.concepts:
                    raise ValueError(f"capacité hors catalogue : {x['concept']}")
                if not 5 <= int(x.get("duree_min", 0)) <= 120 or not 3 <= len(str(x.get("geste", ""))) <= 200:
                    raise ValueError("geste ou durée hors bornes")
                propres.append({"role": x["role"], "nature": x["nature"], "concept": x.get("concept"), "geste": str(x["geste"]).strip(),
                                "duree_min": int(x["duree_min"]), "livrable": (str(x["livrable"]).strip()[:120] or None) if x.get("livrable") else None})
            f = d.get("fenetre") or {}
            fenetre = self._fenetre_valide(f.get("jour"), f.get("debut"), f.get("fin"), aujourd_hui)
            manquant = [str(m).strip()[:160] for m in (d.get("manquant") or [])][:4]
            return {"objet": str(d.get("objet") or "").strip()[:120], "langue_public": d.get("langue_public") if d.get("langue_public") in
                    self.LANGUES else None, "exigences": propres, "fenetre": fenetre, "manquant": manquant, "reconnu": [],
                    "mode": "apertus"}, None
        return self._executer("comprendre_action", "comprendre_action", message, SCHEMA_ACTION, valide,
                              lambda: self._action_regles(texte, aujourd_hui))

    @staticmethod
    def _fenetre_valide(jour: Optional[str], debut: Optional[str], fin: Optional[str], aujourd_hui: date) -> dict:
        """Une fenêtre sortie d'un modèle est une donnée non fiable : jour ISO dans les 60 jours, heures HH:MM, ordre."""
        heure_ok = lambda h: h is None or bool(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(h)))  # noqa: E731
        if not heure_ok(debut) or not heure_ok(fin) or (debut and fin and str(fin) <= str(debut)):
            raise ValueError("heures invalides")
        if jour is not None:
            j = date.fromisoformat(str(jour))
            if not aujourd_hui <= j <= aujourd_hui + timedelta(days=60):
                raise ValueError("jour hors de l'horizon de 60 jours")
        return {"jour": jour, "debut": debut, "fin": fin}

    def _action_regles(self, texte: str, aujourd_hui: date) -> dict:
        n = norm(texte)
        reconnu: list[str] = []
        langue = next((code for code, (_, mots) in self.LANGUES.items() if any(m in n for m in mots)), None)
        if langue:
            reconnu.append(f"public : {self.LANGUES[langue][0]}")
        m = re.search(r"(\d{2,3})\s*min", n) or re.search(r"(une|1)\s*(h\b|heure)", n)
        duree = (int(m.group(1)) if m.group(1).isdigit() else 60) if m else 45
        manquant = [] if m else [f"Durée proposée : {duree} min — à confirmer"]
        exig = []
        if langue:
            nom = self.LANGUES[langue][0]
            # un LIVRABLE seulement s'il est demandé : la fiche n'est pas ajoutée d'office (défaut trouvé par la revue « jury »)
            ecrit = re.search(r"fiche|document|flyer|brochure|depliant|texte|traduire|traduction", n)
            exig.append({"role": "voix", "nature": "competence", "concept": "traduction", "geste": f"Présenter le produit en {nom}",
                         "duree_min": min(duree, 120), "livrable": f"Fiche produit en {nom}" if ecrit else None})
            if ecrit:
                reconnu.append(f"un écrit : fiche en {nom}")
        # un lieu : NOMMÉ seulement — « présenter pendant la Foire » ne dit pas qu'il manque un lieu (on ne le suppose plus)
        if re.search(r"stand|presentoir|lieu|salle|table|degustation|demonstration|vitrine|gouter|deguster", n):
            reconnu.append("un lieu")
            exig.append({"role": "lieu", "nature": "lieu", "concept": None, "geste": "Prêter un lieu adapté (présentoir, table, stand)",
                         "duree_min": min(duree, 120), "livrable": None})
        if re.search(r"acheteur|client|distributeur|revendeur|visiteur|public|kaufer|buyer|importateur|grossiste", n):
            reconnu.append("un public")
            exig.append({"role": "public", "nature": "competence", "concept": self.PUBLIC_PAR_LANGUE.get(langue or ""),
                         "geste": "Amener des acheteurs" + (f" {self.LANGUES[langue][0]}s" if langue else ""), "duree_min": min(duree, 120),
                         "livrable": None})
        jour = None
        jm = re.search(r"\b(" + "|".join(self.JOURS) + r")\b", n)
        if jm:
            k = self.JOURS.index(jm.group(1))
            jour = aujourd_hui + timedelta(days=(k - aujourd_hui.weekday()) % 7 or 7)
            reconnu.append(f"jour : {jm.group(1)} {jour.strftime('%d.%m')}")
        elif "demain" in n:
            jour = aujourd_hui + timedelta(days=1)
            reconnu.append("jour : demain")
        moment = next((v for k, v in self.MOMENTS.items() if k in n), None)
        hm = re.search(r"(?:entre|de)\s*(\d{1,2})\s*h\s*(\d{2})?\s*(?:et|a|-)\s*(\d{1,2})\s*h\s*(\d{2})?", n)
        if hm and int(hm.group(1)) < int(hm.group(3)) <= 23:           # « entre 15h et 17h » : des heures dites, reprises telles quelles
            moment = (f"{int(hm.group(1)):02d}:{hm.group(2) or '00'}", f"{int(hm.group(3)):02d}:{hm.group(4) or '00'}")
        if moment:
            reconnu.append(f"moment : {moment[0]}–{moment[1]}")
        if not exig:
            manquant.append("Qu'est-ce que d'autres membres devraient apporter (une langue, un lieu, un public…) ?")
        if jour is None:
            manquant.append("Quel jour ?")
        if moment is None:
            manquant.append("Entre quelles heures ?")
        om = re.search(r"presenter (?:nos|notre|mes|mon|ma|le|la|les) ([a-z]+)", n)
        return {"objet": om.group(1) if om else "", "langue_public": langue, "exigences": exig,
                "fenetre": {"jour": jour.isoformat() if jour else None, "debut": moment[0] if moment else None, "fin": moment[1] if moment else None},
                "manquant": manquant, "reconnu": reconnu, "mode": "regles"}

    def capturer_rencontre(self, note: str) -> Reponse:
        concepts = "\n".join(f"- {c.id} : {c.libelle}" for c in self.tax.concepts.values())
        message = f"Compétences autorisées :\n{concepts}\n\nNote du membre :\n{note}"

        def valide(brut: str) -> tuple[dict, Optional[dict]]:
            c = Capture.model_validate_json(_json_de(brut))
            return self._valider_capture(note, c), None
        return self._executer("capturer_rencontre", "capturer_rencontre", message, SCHEMA_CAPTURE, valide,
                              lambda: self._capture_regles(note),
                              local_seulement=None if self.notes_privees_autorisees else
                              "note privée : traitée localement (APERTUS_NOTES_PRIVEES non activé)")

    def expliquer(self, faits: dict, pseudonymes: set[str]) -> Reponse:
        repli = {"explication": self.gabarit_explication(faits), "statut": "OK"}

        def valide(brut: str) -> tuple[dict, Optional[dict]]:
            t = json.loads(_json_de(brut))["explication"].strip()
            if not t or len(t) > 700:
                raise ValueError("explication vide ou trop longue")
            v = verifier(t, faits, pseudonymes)
            if not v["fidele"]:
                raise ValueError(f"explication infidèle aux faits : {v['nombres_inventes'] or v['identifiants_inventes'] or v['nombres_en_lettres']}")
            return {"explication": t, "statut": "OK"}, v
        return self._executer("expliquer_opportunite", "expliquer_opportunite", json.dumps(faits, ensure_ascii=False),
                              SCHEMA_TEXTE["explication"], valide, lambda: repli)

    @staticmethod
    def gabarit_sollicitation(faits: dict) -> str:
        """Le message d'invitation SANS modèle (repli déclaré) : aussi ce qu'une LECTURE montre si rien n'a été rédigé."""
        return (f"Vous avez déclaré pouvoir aider sur : « {faits['capacite_declaree']} ». "
                f"Une personne du Club ({faits['secteur_demandeur']}) aurait besoin de : {faits['demande']}. "
                f"Si vous acceptez : {faits['partage']}. Vous pouvez refuser sans vous justifier ; "
                "ni le Club ni personne d'autre que la personne qui vous invite ne le saura.")

    @staticmethod
    def gabarit_explication(faits: dict) -> str:
        return " ".join(faits.get("raisonnement", [])[:4])

    def rediger_sollicitation(self, faits: dict, interdits: list[str]) -> Reponse:
        repli = {"message": self.gabarit_sollicitation(faits), "statut": "OK"}

        def valide(brut: str) -> tuple[dict, Optional[dict]]:
            t = json.loads(_json_de(brut))["message"].strip()
            fuites = [x for x in interdits if x and x.lower() in t.lower()]
            if "MEMBRE-" in t or fuites:
                raise ValueError("le message révèle une identité non autorisée")
            if not t or len(t) > 600:
                raise ValueError("message vide ou trop long")
            return {"message": t, "statut": "OK"}, {"fuites": fuites}
        return self._executer("rediger_sollicitation", "rediger_sollicitation", json.dumps(faits, ensure_ascii=False),
                              SCHEMA_TEXTE["message"], valide, lambda: repli)

    # ------------------------------------------------------------------ validation et repli de la capture
    def _valider_capture(self, note: str, c: Capture) -> dict:
        n = norm(note)
        incert = list(c.incertitudes)

        def ok_ext(e: Optional[Extrait], quoi: str) -> Optional[dict]:
            if e is None:
                return None
            if e.concept not in self.tax.concepts:
                incert.append(f"{quoi} : compétence « {e.concept} » hors vocabulaire, ignorée")
                return None
            if not e.extrait or norm(e.extrait) not in n:
                incert.append(f"{quoi} : extrait introuvable dans la note, ignoré")
                return None
            return e.model_dump()
        sortie = {
            "personne_mentionnee": c.personne_mentionnee if c.personne_mentionnee and norm(c.personne_mentionnee) in n else None,
            "organisation_mentionnee": c.organisation_mentionnee if c.organisation_mentionnee and norm(c.organisation_mentionnee) in n else None,
            "sujets": [s for s in c.sujets if s in self.tax.concepts],
            "besoin_de_l_autre": ok_ext(c.besoin_de_l_autre, "besoin de l'autre"),
            "capacite_de_l_autre": ok_ext(c.capacite_de_l_autre, "capacité de l'autre"),
            "besoin_du_membre": ok_ext(c.besoin_du_membre, "votre besoin"),
            "suite_proposee": c.suite_proposee, "incertitudes": incert}
        sortie["statut"] = "OK" if any(sortie[k] for k in ("besoin_de_l_autre", "capacite_de_l_autre", "besoin_du_membre")) else "INSUFFISANT"
        return sortie

    def _capture_regles(self, note: str) -> dict:
        """Repli déterministe : phrases, concepts de la taxonomie, marqueurs de personne et de besoin/offre."""
        res: dict = {"personne_mentionnee": None, "organisation_mentionnee": None, "sujets": [], "besoin_de_l_autre": None,
                     "capacite_de_l_autre": None, "besoin_du_membre": None, "suite_proposee": None, "incertitudes": []}
        for phrase in [p.strip() for p in re.split(r"(?<=[.!?])\s+", note) if p.strip()]:
            n = norm(phrase)
            concepts = sorted(self.tax.concepts_dans(n))
            for a in self.tax.ambigus.values():
                if re.search(rf"\b{re.escape(norm(a['libelle']))}\b", n) and not concepts:
                    res["incertitudes"].append(f"« {a['libelle']} » : plusieurs sens possibles ({', '.join(self.tax.libelle(o) for o in a['options'])})")
            for c in concepts:
                if c not in res["sujets"]:
                    res["sujets"].append(c)
            if not concepts:
                continue
            ext = {"concept": concepts[0], "extrait": phrase}
            moi = bool(_PREMIERE.search(n)) and not _RENCONTRE.search(n)   # « j'ai rencontré une boîte de X » : X est à l'autre
            if _RENCONTRE.search(n) and not _BESOIN.search(n):
                cle = "capacite_de_l_autre"
            elif _BESOIN.search(n):
                cle = "besoin_du_membre" if moi else "besoin_de_l_autre"
            elif _CAPACITE.search(n) or not moi:
                cle = "capacite_de_l_autre" if not moi else "besoin_du_membre"
            else:
                continue
            res[cle] = res[cle] or ext
            if not res["personne_mentionnee"]:
                noms = [m for m in _MAJ.findall(phrase[1:]) if m.split()[0] not in _NON_NOMS]
                res["personne_mentionnee"] = noms[0] if noms else None
        if not res["personne_mentionnee"]:
            noms = [m for m in _MAJ.findall(note[1:]) if m.split()[0] not in _NON_NOMS]
            res["personne_mentionnee"] = noms[0] if noms else None
        if res["besoin_de_l_autre"] or res["capacite_de_l_autre"]:
            res["suite_proposee"] = "Proposer un échange de suivi"
        res["statut"] = "OK" if any(res[k] for k in ("besoin_de_l_autre", "capacite_de_l_autre", "besoin_du_membre")) else "INSUFFISANT"
        if res["statut"] == "INSUFFISANT":
            res["incertitudes"].append("La note ne dit pas assez clairement qui cherche ou propose quoi : précisez, ou gardez-la telle quelle.")
        return res


def besoin_de(r: Reponse) -> Besoin:
    return Besoin(**r.sortie["besoin"])
