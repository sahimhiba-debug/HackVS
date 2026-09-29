"""Passerelle de modèles : registre de capacités, routage par tâche, repli tracé.

Trois états d'une capacité, jamais confondus :
- DOCUMENTEE  : ce que le fournisseur annonce (source citée) — une promesse, pas une mesure ;
- CONFIGUREE  : les variables d'environnement nécessaires sont présentes (aucun appel fait) ;
- VERIFIEE    : une vérification contre l'API RÉELLE a produit un fichier de télémétrie (scripts/verifier_llm.py).
Le routage préfère VERIFIEE ; un fournisseur seulement CONFIGURE peut servir mais la trace le dit ; sans aucun
fournisseur, la tâche retombe sur un repli DÉTERMINISTE (jamais présenté comme une inférence).
Les clés ne sont jamais lues ici au-delà de leur PRÉSENCE ; elles ne quittent jamais l'environnement.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

Etat = Literal["VERIFIEE", "CONFIGUREE", "NON_CONFIGUREE"]


class Profil(BaseModel):
    nom: str
    variables: list[str]                       # noms des variables requises (jamais leurs valeurs)
    documente: dict[str, str]                  # capacité → source de l'annonce
    hebergement: str
    note: str = ""


class Route(BaseModel):
    tache: str
    choisi: str
    etat: Etat | Literal["DETERMINISTE"]
    candidats: list[dict]
    raison: str


PROFILS: dict[str, Profil] = {
    "claude": Profil(
        nom="claude", variables=["ANTHROPIC_API_KEY|ANTHROPIC_AUTH_TOKEN"],
        documente={"sortie_structuree": "docs.anthropic.com (tool use / JSON)", "multilingue": "docs.anthropic.com",
                   "diffusion_progressive": "docs.anthropic.com (streaming)"},
        hebergement="API Anthropic (hors de Suisse)"),
    "apertus": Profil(
        nom="apertus", variables=["APERTUS_API_KEY", "APERTUS_BASE_URL", "APERTUS_MODEL"],
        documente={"multilingue": "annonce EPFL / ETH / CSCS (1 000+ langues, dont le suisse allemand et le romanche)",
                   "modele_ouvert": "poids et données d'entraînement publiés (annonce EPFL / ETH / CSCS)",
                   "api_compatible_openai": "dépend de l'hébergeur (Swisscom, Public AI…)"},
        hebergement="dépend de l'hébergeur choisi (possible en Suisse)",
        note="sortie structurée (JSON Schema) NON documentée de façon uniforme selon l'hébergeur : à vérifier"),
}

# Ce que chaque tâche EXIGE. Une tâche critique pour la sûreté n'a jamais de LLM : elle n'est pas routable.
TACHES: dict[str, dict] = {
    "extraction_besoin": {"exige": ["sortie_structuree|api_compatible_openai"], "repli": "regles_locales",
                          "validation": "chaque critère extrait est revalidé contre la taxonomie et le texte source"},
    "compilation_intention": {"exige": ["sortie_structuree|api_compatible_openai"], "repli": "grammaire",
                              "validation": "la spécification produite est validée contre le domaine (L0)"},
    "optimisation": {"exige": None, "repli": "solveur", "validation": "validateurs indépendants L2-L6"},
    "politique": {"exige": None, "repli": "gardien", "validation": "règles déterministes"},
}

TELEMETRIE = Path(__file__).resolve().parent.parent / "eval"


def etat(nom: str, env: Optional[dict] = None, dossier: Path = TELEMETRIE) -> tuple[Etat, dict]:
    env = dict(os.environ) if env is None else env
    manque = [v for v in PROFILS[nom].variables if not any(env.get(x) for x in v.split("|"))]
    tele = dossier / f"telemetrie_{nom}.json"
    if tele.exists():
        try:
            synthese = json.loads(tele.read_text(encoding="utf-8")).get("synthese", {})
        except ValueError:
            synthese = {}
        if synthese and not manque:
            return "VERIFIEE", {"verification": synthese}
    if manque:
        return "NON_CONFIGUREE", {"manque": manque}
    return "CONFIGUREE", {"verification": "aucune (lancer scripts/verifier_llm.py --confirmer)"}


def _satisfait(p: Profil, exige: list[str]) -> bool:
    return all(any(alt in p.documente for alt in e.split("|")) for e in exige)


def router(tache: str, preference: Optional[str] = None, env: Optional[dict] = None, dossier: Path = TELEMETRIE) -> Route:
    t = TACHES[tache]
    if t["exige"] is None:
        return Route(tache=tache, choisi=t["repli"], etat="DETERMINISTE", candidats=[],
                     raison="tâche déterministe : aucun modèle de langage n'est autorisé ici")
    candidats = []
    for nom, p in PROFILS.items():
        e, info = etat(nom, env, dossier)
        candidats.append({"nom": nom, "etat": e, "capable": _satisfait(p, t["exige"]), **info})
    rang = {"VERIFIEE": 0, "CONFIGUREE": 1, "NON_CONFIGUREE": 2}
    utilisables = sorted((c for c in candidats if c["capable"] and c["etat"] != "NON_CONFIGUREE"),
                         key=lambda c: (rang[c["etat"]], c["nom"] != preference))
    if not utilisables:
        return Route(tache=tache, choisi=t["repli"], etat="DETERMINISTE", candidats=candidats,
                     raison="aucun fournisseur configuré : repli déterministe (ce n'est PAS une inférence)")
    c = utilisables[0]
    raison = f"{c['nom']} : {c['etat'].lower()}"
    if c["etat"] == "CONFIGUREE":
        raison += " mais jamais vérifié contre l'API réelle ; la sortie reste validée et un repli existe"
    return Route(tache=tache, choisi=c["nom"], etat=c["etat"], candidats=candidats, raison=raison)


def registre(env: Optional[dict] = None, dossier: Path = TELEMETRIE) -> dict:
    """Vue publique : capacités annoncées vs état constaté. Aucune valeur de clé, seulement des noms de variables."""
    return {"profils": {n: p.model_dump() | dict(zip(("etat", "details"), etat(n, env, dossier), strict=True))
                        for n, p in PROFILS.items()},
            "taches": TACHES,
            "routes": {t: router(t, env=env, dossier=dossier).model_dump(exclude={"candidats"}) for t in TACHES}}
