"""Analyse du besoin par Claude (optionnelle), encadrée par des garde-fous déterministes.

Le modèle ne fait qu'une chose : traduire une phrase libre en critères choisis dans
un vocabulaire fermé. Le code valide ensuite chaque élément :
- concept / zone / langue hors vocabulaire → ignoré et signalé ;
- extrait cité absent du texte saisi → extrait retiré et signalé ;
- erreur réseau, refus ou sortie invalide → repli sur l'analyse par règles, affiché.
Le modèle ne voit jamais les profils et ne décide jamais de l'éligibilité.
"""
from __future__ import annotations

import os
import time
from typing import Optional

from pydantic import BaseModel

from .models import Besoin, Critere
from .parser_rules import analyser as analyser_regles
from .taxonomy import Taxonomie, norm

MODELE_PAR_DEFAUT = "claude-opus-5"


class _Item(BaseModel):
    valeur: str
    obligatoire: bool
    extrait: str


class SortieLLM(BaseModel):
    competences: list[_Item]
    langues: list[_Item]
    zones: list[_Item]
    exclure_concurrents: bool
    contexte: list[str]
    termes_non_couverts: list[str]


def _systeme(tax: Taxonomie) -> str:
    lignes = [f"- {c.id} : {c.libelle}" + (f" (sous-catégorie de {c.parent})" if c.parent else "") for c in tax.concepts.values()]
    langues = ", ".join(f"{k} ({v['libelle']})" for k, v in tax.langues.items())
    zones = ", ".join(tax.zones)
    return (
        "Tu aides des membres d'un club d'affaires valaisan à formuler un besoin professionnel.\n"
        "Transforme le texte de l'utilisateur en critères de recherche. Règles :\n"
        "1. N'utilise QUE les identifiants de compétences, langues et zones listés ci-dessous.\n"
        "2. Ne retiens que ce que la personne CHERCHE, pas ce qu'elle vend ou produit elle-même.\n"
        "3. La compétence principale est obligatoire. Un critère introduit par « idéalement », "
        "« si possible », « de préférence » est non obligatoire.\n"
        "4. Pour chaque critère, « extrait » recopie mot pour mot le passage du texte qui le justifie.\n"
        "5. Si un besoin exprimé ne correspond à aucune compétence de la liste, mets-le dans "
        "« termes_non_couverts » au lieu de forcer une correspondance approximative.\n"
        "6. « contexte » : fréquences, délais, volumes ou budgets mentionnés (non vérifiables dans les profils).\n"
        "7. exclure_concurrents = true seulement si la personne demande explicitement d'éviter des concurrents.\n\n"
        f"Compétences :\n" + "\n".join(lignes) + f"\n\nLangues : {langues}\nZones : {zones}\n"
    )


def llm_configure() -> bool:
    return os.environ.get("HACKVS_LLM", "").lower() == "claude" and bool(
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    )


def _valider(texte: str, sortie: SortieLLM, tax: Taxonomie) -> Besoin:
    n_texte = norm(texte)
    avert: list[str] = []
    criteres: list[Critere] = []

    def extrait_verifie(ex: str) -> Optional[str]:
        if ex and norm(ex) in n_texte:
            return ex
        if ex:
            avert.append(f"Extrait « {ex} » introuvable dans votre texte : retiré.")
        return None

    for it in sortie.competences:
        if it.valeur not in tax.concepts:
            avert.append(f"Compétence « {it.valeur} » proposée par le modèle mais absente du vocabulaire : ignorée.")
            continue
        criteres.append(Critere(type="expertise", valeur=it.valeur, libelle=tax.libelle(it.valeur),
                                obligatoire=it.obligatoire, extrait=extrait_verifie(it.extrait)))
    for it in sortie.langues:
        if it.valeur not in tax.langues:
            avert.append(f"Langue « {it.valeur} » inconnue : ignorée.")
            continue
        criteres.append(Critere(type="langue", valeur=it.valeur, libelle=tax.langues[it.valeur]["libelle"],
                                obligatoire=it.obligatoire, extrait=extrait_verifie(it.extrait)))
    for it in sortie.zones:
        if it.valeur not in tax.zones:
            avert.append(f"Zone « {it.valeur} » inconnue : ignorée.")
            continue
        criteres.append(Critere(type="zone", valeur=it.valeur, libelle=it.valeur,
                                obligatoire=it.obligatoire, extrait=extrait_verifie(it.extrait)))

    # Invariant : exactement une compétence principale obligatoire en tête.
    exp = [c for c in criteres if c.type == "expertise"]
    if exp and not any(c.obligatoire for c in exp):
        exp[0].obligatoire = True
    for t in sortie.termes_non_couverts:
        avert.append(f"« {t} » : aucune catégorie correspondante dans le Club (démo).")
    if not exp:
        avert.append("Aucune compétence reconnue. Choisissez-en une dans la liste ou reformulez.")
    return Besoin(texte=texte, criteres=criteres, exclure_concurrents=sortie.exclure_concurrents,
                  contexte=sortie.contexte, analyseur="claude", avertissements=avert)


def analyser(texte: str, tax: Taxonomie, client=None) -> tuple[Besoin, dict]:
    """Retourne (besoin, télémétrie). `client` injectable pour les tests."""
    t0 = time.perf_counter()
    modele = os.environ.get("HACKVS_CLAUDE_MODEL", MODELE_PAR_DEFAUT)
    try:
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        rep = client.messages.parse(
            model=modele, max_tokens=4000, system=_systeme(tax),
            messages=[{"role": "user", "content": texte}], output_format=SortieLLM,
        )
        if getattr(rep, "stop_reason", None) == "refusal" or rep.parsed_output is None:
            raise ValueError(f"réponse inutilisable (stop_reason={getattr(rep, 'stop_reason', None)})")
        besoin = _valider(texte, rep.parsed_output, tax)
        usage = getattr(rep, "usage", None)
        tele = {"analyseur": "claude", "modele": modele, "latence_ms": round((time.perf_counter() - t0) * 1000),
                "tokens_entree": getattr(usage, "input_tokens", None), "tokens_sortie": getattr(usage, "output_tokens", None)}
        return besoin, tele
    except Exception as e:  # repli visible, jamais silencieux
        besoin = analyser_regles(texte, tax)
        besoin.avertissements.insert(0, f"Claude indisponible ({type(e).__name__}) : analyse par règles locales.")
        return besoin, {"analyseur": "regles (repli)", "erreur": type(e).__name__,
                        "latence_ms": round((time.perf_counter() - t0) * 1000)}
