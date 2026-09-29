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
import json
import os
import re
import time
from pathlib import Path
from typing import Callable, Literal, Optional, Protocol

from pydantic import BaseModel, ValidationError

from adaptateurs.club.synthese import verifier
from app.models import Besoin
from app.parser_llm import SCHEMA as SCHEMA_BESOIN
from app.parser_llm import SortieLLM, _json_de, systeme, valider
from app.parser_rules import analyser as analyser_regles
from app.taxonomy import Taxonomie, norm

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
Statut = Literal["OK", "INCERTAIN", "REJETE", "INDISPONIBLE"]


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
    controle: Optional[dict] = None


class Reponse(BaseModel):
    sortie: dict
    appel: AppelIA


class Fournisseur(Protocol):
    nom: str
    modele: str

    def completer(self, systeme_txt: str, message: str, schema: Optional[dict]) -> str: ...


class NonConfigure(RuntimeError):
    pass


class Apertus:
    nom = "apertus"

    def __init__(self, http=None):
        manque = [k for k in ("APERTUS_BASE_URL", "APERTUS_API_KEY", "APERTUS_MODEL") if not os.environ.get(k)]
        if manque:
            raise NonConfigure("variables absentes : " + ", ".join(manque))
        self.base = os.environ["APERTUS_BASE_URL"].rstrip("/")
        self.modele = os.environ["APERTUS_MODEL"]
        self._cle = os.environ["APERTUS_API_KEY"]
        self.delai = float(os.environ.get("APERTUS_DELAI_S", "30"))
        self.http = http

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
        derniere: Optional[Exception] = None
        for _ in range(2):                                   # un nouvel essai sur erreur réseau ou 5xx
            try:
                rep = client.post(f"{self.base}/chat/completions", headers=entetes, json=corps)
                if rep.status_code in (400, 422) and "response_format" in corps:
                    corps.pop("response_format")              # serveur sans sortie contrainte : la consigne reste
                    rep = client.post(f"{self.base}/chat/completions", headers=entetes, json=corps)
                if rep.status_code >= 500:
                    derniere = RuntimeError(f"HTTP {rep.status_code}")
                    continue
                rep.raise_for_status()
                return rep.json()["choices"][0]["message"]["content"] or ""
            except (httpx.TransportError, httpx.TimeoutException) as e:
                derniere = e
        raise derniere or RuntimeError("échec")


class Maquette:
    """TESTS UNIQUEMENT : renvoie des réponses écrites à la main, par tâche."""
    nom = "maquette"
    modele = "maquette"

    def __init__(self, reponses: dict[str, str]):
        self.reponses = reponses

    def completer(self, systeme_txt: str, message: str, schema: Optional[dict]) -> str:
        cle = next((k for k in self.reponses if k in systeme_txt), None)
        if cle is None:
            raise RuntimeError("aucune réponse de maquette")
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
SCHEMA_TEXTE = {"explication": {"type": "object", "additionalProperties": False, "required": ["explication"],
                                "properties": {"explication": {"type": "string"}}},
                "message": {"type": "object", "additionalProperties": False, "required": ["message"],
                            "properties": {"message": {"type": "string"}}}}

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
                 journal: Optional[Callable[[AppelIA], None]] = None):
        self.tax = tax
        self.f = fournisseur
        self.journal = journal
        self.appels: list[AppelIA] = []

    @classmethod
    def depuis_environnement(cls, tax: Taxonomie, journal=None) -> "Intelligence":
        return cls(tax, Apertus() if Apertus.configure() else None, journal)

    def etat(self) -> dict:
        derniers = [a for a in self.appels if a.fournisseur == "apertus"]
        return {"fournisseur": self.f.nom if self.f else "deterministe", "modele": self.f.modele if self.f else None,
                "configure": self.f is not None, "appels_apertus_reussis": sum(1 for a in derniers if a.statut == "OK" and not a.repli),
                "appels_apertus_echoues": sum(1 for a in derniers if a.repli)}

    # ------------------------------------------------------------------ mécanique commune
    def _tracer(self, a: AppelIA) -> None:
        self.appels.append(a)
        if self.journal:
            self.journal(a)

    def _executer(self, tache: str, nom_prompt: Optional[str], message: str, schema: Optional[dict],
                  valider_sortie: Callable[[str], tuple[dict, Optional[dict]]], repli: Callable[[], dict]) -> Reponse:
        trace = hashlib.sha256(f"{tache}|{message}|{len(self.appels)}".encode()).hexdigest()[:12]
        t0 = time.perf_counter()
        if self.f is None:
            sortie = repli()
            a = AppelIA(trace=trace, tache=tache, fournisseur="deterministe", latence_ms=round((time.perf_counter() - t0) * 1000, 1),
                        statut="OK" if sortie.get("statut", "OK") == "OK" else "INCERTAIN")
            self._tracer(a)
            return Reponse(sortie=sortie, appel=a)
        texte_prompt, version = prompt(nom_prompt) if nom_prompt else (systeme(self.tax), "comprendre_demande_v1")
        try:
            brut = self.f.completer(texte_prompt, message, schema)
        except Exception as e:                                # indisponible : repli VISIBLE
            sortie = repli()
            a = AppelIA(trace=trace, tache=tache, fournisseur=self.f.nom, modele=self.f.modele, prompt=version,
                        latence_ms=round((time.perf_counter() - t0) * 1000, 1), statut="INDISPONIBLE", repli=True,
                        erreur=type(e).__name__)
            self._tracer(a)
            return Reponse(sortie=sortie, appel=a)
        try:
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

    # ------------------------------------------------------------------ tâches
    def comprendre_demande(self, texte: str) -> Reponse:
        def valide(brut: str) -> tuple[dict, Optional[dict]]:
            b = valider(texte, SortieLLM.model_validate_json(_json_de(brut)), self.tax)
            b.analyseur = "apertus"
            return {"besoin": b.model_dump()}, {"avertissements": b.avertissements}
        return self._executer("comprendre_demande", None, texte, SCHEMA_BESOIN, valide,
                              lambda: {"besoin": analyser_regles(texte, self.tax).model_dump()})

    def capturer_rencontre(self, note: str) -> Reponse:
        concepts = "\n".join(f"- {c.id} : {c.libelle}" for c in self.tax.concepts.values())
        message = f"Compétences autorisées :\n{concepts}\n\nNote du membre :\n{note}"

        def valide(brut: str) -> tuple[dict, Optional[dict]]:
            c = Capture.model_validate_json(_json_de(brut))
            return self._valider_capture(note, c), None
        return self._executer("capturer_rencontre", "capturer_rencontre", message, SCHEMA_CAPTURE, valide,
                              lambda: self._capture_regles(note))

    def expliquer(self, faits: dict, pseudonymes: set[str]) -> Reponse:
        repli = {"explication": " ".join(faits.get("raisonnement", [])[:4]), "statut": "OK"}

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

    def rediger_sollicitation(self, faits: dict, interdits: list[str]) -> Reponse:
        repli = {"message": (f"Vous avez déclaré pouvoir aider sur : « {faits['capacite_declaree']} ». "
                             f"Une personne du Club ({faits['secteur_demandeur']}) aurait besoin de : {faits['demande']}. "
                             f"Si vous acceptez : {faits['partage']}. Vous pouvez refuser sans vous justifier ; "
                             "votre refus ne sera montré à personne."), "statut": "OK"}

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
