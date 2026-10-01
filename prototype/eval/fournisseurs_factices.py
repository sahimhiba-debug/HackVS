"""Fournisseurs FACTICES pour le banc multi-fournisseurs (`--dry-run`) : ils respectent le contrat `Fournisseur`
(`completer` → texte brut, ou `ErreurFournisseur`) sans AUCUN appel réseau, pour vérifier toute la chaîne du banc —
mêmes cas, même prompt, même validation du produit, mêmes mesures — avant d'avoir les clés. Ils ne mesurent RIEN
d'un vrai modèle : leurs résultats ne vont jamais dans eval/resultats_banc/ (seulement var/banc_dry_run/)."""
from __future__ import annotations

import json
from typing import Callable, Optional

from intelligence.ia import ErreurFournisseur

NATURE = {"voix": "competence", "lieu": "lieu", "public": "competence", "autre": "competence"}


def _cas() -> list[dict]:
    from eval.banc_comprendre_action import charger
    return charger()[0]


def _cas_du_message(message: str) -> Optional[dict]:
    """Le cas dont le texte figure dans le message envoyé (le factice « lit » la demande comme un modèle)."""
    return next((c for c in _cas() if c["texte"] in message), None)


def sortie_attendue(c: dict) -> dict:
    """Une sortie CONFORME aux attentes du cas (premier ensemble de rôles acceptable)."""
    roles = sorted(c["roles"][0])
    h = c["heures"] if isinstance(c["heures"], list) else [None, None]
    exig = [{"role": r, "nature": NATURE[r], "concept": None, "geste": f"Apporter : {r}",
             "duree_min": c.get("duree") or 45, "livrable": "Un résultat remis" if c.get("livrable") and i == 0 else None}
            for i, r in enumerate(roles)]
    return {"objet": "fictif", "langue_public": None, "exigences": exig,
            "fenetre": {"jour": c["jour"] if c["jour"] != "*" else None, "debut": h[0], "fin": h[1]},
            "manquant": [] if exig else ["Que faudrait-il réunir ?"]}


class _Factice:
    nom = "factice"
    modele = "factice"
    contrainte: Optional[str] = "serveur"

    def completer(self, systeme_txt: str, message: str, schema: Optional[dict]) -> str:
        raise NotImplementedError


class FauxValide(_Factice):
    """Répond la sortie attendue de chaque cas (les cas d'abstention, impossibles sous le schéma, finissent rejetés)."""
    nom, modele = "factice-valide", "factice-valide-1"

    def completer(self, systeme_txt, message, schema):
        c = _cas_du_message(message)
        return json.dumps(sortie_attendue(c) if c else {}, ensure_ascii=False)


class FauxJSONInvalide(_Factice):
    nom, modele = "factice-json-invalide", "factice-json-invalide-1"

    def completer(self, systeme_txt, message, schema):
        return "Bien sûr ! Voici les exigences : une personne qui parle allemand, jeudi."


class FauxHorsSchema(_Factice):
    """JSON lisible, mais hors schéma : rôle inconnu, jour non ISO (comme observé chez de vrais modèles)."""
    nom, modele = "factice-hors-schema", "factice-hors-schema-1"

    def completer(self, systeme_txt, message, schema):
        return json.dumps({"objet": "x", "langue_public": "fr", "manquant": [], "fenetre": {"jour": "jeudi", "debut": None, "fin": None},
                           "exigences": [{"role": "chef", "nature": "competence", "concept": None, "geste": "Diriger", "duree_min": 45,
                                          "livrable": None}]})


class FauxIncoherent(_Factice):
    """Conforme au schéma, incohérent pour le métier : capacité hors catalogue, durée 180 min (observé chez Apertus)."""
    nom, modele = "factice-incoherent", "factice-incoherent-1"

    def completer(self, systeme_txt, message, schema):
        return json.dumps({"objet": "x", "langue_public": "fr", "manquant": [], "fenetre": {"jour": None, "debut": None, "fin": None},
                           "exigences": [{"role": "voix", "nature": "competence", "concept": "evenementiel", "geste": "Animer",
                                          "duree_min": 180, "livrable": None}]})


class FauxDelai(_Factice):
    nom, modele = "factice-delai", "factice-delai-1"
    contrainte = None

    def completer(self, systeme_txt, message, schema):
        raise ErreurFournisseur("ReadTimeout", reessayable=True)


class FauxReseau(_Factice):
    nom, modele = "factice-reseau", "factice-reseau-1"
    contrainte = None

    def completer(self, systeme_txt, message, schema):
        raise ErreurFournisseur("ConnectError", reessayable=True)


FACTICES: dict[str, Callable[[], _Factice]] = {
    "valide": FauxValide, "json-invalide": FauxJSONInvalide, "hors-schema": FauxHorsSchema,
    "incoherent": FauxIncoherent, "delai": FauxDelai, "reseau": FauxReseau}
