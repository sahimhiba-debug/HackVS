"""Analyse hybride du besoin : règles d'abord, couche sémantique locale seulement si les règles ne trouvent rien.

Ordre de confiance :
1. règles (vocabulaire du Club) : précises, explicables ;
2. sémantique (multilingual-e5-large, local) : utilisée si AUCUNE compétence n'est reconnue ;
   - par défaut : QUESTION à l'utilisateur avec 1 à 3 compétences (classement hybride dense + lexical,
     nombre adaptatif) ; il confirme ou garde sa formulation ;
   - décision automatique seulement si HACKVS_SEMANTIQUE_AUTO=1 ET seuils calibrés atteints (désactivée : données de
     calibration trop peu nombreuses pour garantir un faible taux de fausses acceptations) ;
   - sinon → la recherche hors catalogue et l'abstention s'appliquent comme avant.
"""
from __future__ import annotations

import os

from . import semantique
from .models import Ambiguite, Besoin, Critere, OptionAmbiguite
from .parser_rules import analyser as analyser_regles
from .taxonomy import Taxonomie



def analyser_hybride(texte: str, tax: Taxonomie, semantique_active: bool = True) -> tuple[Besoin, dict]:
    b = analyser_regles(texte, tax)
    info: dict = {"semantique": "non utilisée"}
    if not semantique_active or not semantique.disponible():
        info["semantique"] = "indisponible" if semantique_active else "désactivée"
        return b, info
    if any(c.type == "expertise" for c in b.criteres) or b.ambiguites:
        return b, info  # les règles ont compris : la sémantique n'intervient pas
    r = semantique.inferer_concept(texte, tax)
    info = {"semantique": "consultée", **r}
    if r is None:
        return b, info
    libre = [c for c in b.criteres if c.type == "texte_libre"]
    # Par défaut, l'IA locale ne décide JAMAIS seule : avec ~50 négatifs de calibration, on ne peut pas garantir
    # un taux de fausses acceptations bas (règle de trois : borne ≈ 3/n ≈ 5 %). Elle suggère, le membre confirme.
    auto = os.environ.get("HACKVS_SEMANTIQUE_AUTO", "0") == "1"
    if r["accepte"] and auto:
        crit = Critere(type="expertise", valeur=r["concept"], libelle=tax.libelle(r["concept"]), obligatoire=True,
                       note=f"Compris par similarité sémantique (IA locale, score {r['score']:.2f}, marge {r['marge']:.3f}) : vérifiez.")
        b.criteres = [crit] + [c for c in b.criteres if c.type != "texte_libre"]
        b.avertissements = [a for a in b.avertissements if not a.startswith("Je n'ai pas compris")]
        b.contexte.append("Termes d'origine : " + " ".join(c.valeur for c in libre) if libre else "")
        b.contexte = [x for x in b.contexte if x]
        b.analyseur = "regles+semantique"
    else:
        # L'IA SUGGÈRE (1 à 3 compétences, nombre adaptatif), le membre CONFIRME ou garde sa formulation.
        sug = semantique.suggerer(texte, tax)
        info["options"] = sug["options"]
        b.ambiguites.append(Ambiguite(
            terme="votre besoin", extrait=texte[:60] + ("…" if len(texte) > 60 else ""),
            options=[OptionAmbiguite(valeur=c, libelle=tax.libelle(c)) for c in sug["options"]]))
        b.analyseur = "regles+semantique (question)"
    return b, info
