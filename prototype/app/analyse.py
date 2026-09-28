"""Analyse hybride du besoin : règles d'abord, couche sémantique locale seulement si les règles ne trouvent rien.

Ordre de confiance :
1. règles (vocabulaire du Club) : précises, explicables ;
2. sémantique calibrée (multilingual-e5-large, local) : utilisée si AUCUNE compétence n'est reconnue ;
   - proposition sûre (seuils calibrés) → critère « compris par similarité », signalé comme tel ;
   - proposition incertaine mais plausible → QUESTION à l'utilisateur (« vouliez-vous dire… ? »), jamais une décision ;
   - sinon → la recherche hors catalogue et l'abstention s'appliquent comme avant.
"""
from __future__ import annotations

from . import semantique
from .models import Ambiguite, Besoin, Critere, OptionAmbiguite
from .parser_rules import analyser as analyser_regles
from .taxonomy import Taxonomie

MARGE_QUESTION = 0.03  # sous τ mais à moins de 0,03 : on pose la question au lieu de décider


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
    if r["accepte"]:
        crit = Critere(type="expertise", valeur=r["concept"], libelle=tax.libelle(r["concept"]), obligatoire=True,
                       note=f"Compris par similarité sémantique (IA locale, score {r['score']:.2f}, marge {r['marge']:.3f}) : vérifiez.")
        b.criteres = [crit] + [c for c in b.criteres if c.type != "texte_libre"]
        b.avertissements = [a for a in b.avertissements if not a.startswith("Je n'ai pas compris")]
        b.contexte.append("Termes d'origine : " + " ".join(c.valeur for c in libre) if libre else "")
        b.contexte = [x for x in b.contexte if x]
        b.analyseur = "regles+semantique"
    elif r["score"] >= r["tau"] - MARGE_QUESTION:
        b.ambiguites.append(Ambiguite(
            terme="votre besoin", extrait=texte[:60] + ("…" if len(texte) > 60 else ""),
            options=[OptionAmbiguite(valeur=r["concept"], libelle=tax.libelle(r["concept"])),
                     OptionAmbiguite(valeur=r["second"], libelle=tax.libelle(r["second"]))]))
        b.analyseur = "regles+semantique (question)"
    return b, info
