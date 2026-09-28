"""Analyse du besoin par Claude (optionnelle), en flux, encadrée par des garde-fous déterministes.

Le modèle ne fait qu'une chose : traduire une phrase libre en critères choisis dans un
vocabulaire fermé. Pendant la génération, les critères déjà complets sont émis comme
PROVISOIRES (affichés en pointillés, jamais utilisés pour chercher). À la fin, le code valide :
- concept / zone / langue hors vocabulaire → ignoré et signalé ;
- extrait cité absent du texte saisi → extrait retiré et signalé ;
- termes hors catalogue non présents dans le texte → ignorés ;
- erreur réseau, refus, sortie invalide → repli sur l'analyse par règles, AFFICHÉ.
Le modèle ne voit jamais les profils et ne décide jamais de l'éligibilité.
"""
from __future__ import annotations

import json
import os
import time
from typing import Iterator, Optional

from pydantic import BaseModel

from .models import Besoin, Critere, Exclusion
from .parser_rules import analyser as analyser_regles
from .taxonomy import Taxonomie, norm

MODELE_PAR_DEFAUT = "claude-opus-5"


class _Item(BaseModel):
    valeur: str
    obligatoire: bool
    extrait: str


class _Excl(BaseModel):
    valeur: str
    extrait: str


class SortieLLM(BaseModel):
    competences: list[_Item]
    langues: list[_Item]
    zones: list[_Item]
    implantations: list[_Item]
    exclusions: list[_Excl]
    exclure_concurrents: bool
    contexte: list[str]
    termes_hors_catalogue: list[str]


def _schema_item(avec_obligatoire: bool = True) -> dict:
    props = {"valeur": {"type": "string"}, "extrait": {"type": "string"}}
    if avec_obligatoire:
        props["obligatoire"] = {"type": "boolean"}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


SCHEMA = {
    "type": "object",
    "properties": {
        "competences": {"type": "array", "items": _schema_item()},
        "langues": {"type": "array", "items": _schema_item()},
        "zones": {"type": "array", "items": _schema_item()},
        "implantations": {"type": "array", "items": _schema_item()},
        "exclusions": {"type": "array", "items": _schema_item(False)},
        "exclure_concurrents": {"type": "boolean"},
        "contexte": {"type": "array", "items": {"type": "string"}},
        "termes_hors_catalogue": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["competences", "langues", "zones", "implantations", "exclusions",
                 "exclure_concurrents", "contexte", "termes_hors_catalogue"],
    "additionalProperties": False,
}


def systeme(tax: Taxonomie) -> str:
    lignes = [f"- {c.id} : {c.libelle}" + (f" (sous-catégorie de {c.parent})" if c.parent else "") for c in tax.concepts.values()]
    langues = ", ".join(f"{k} ({v['libelle']})" for k, v in tax.langues.items())
    return (
        "Tu aides des membres d'un club d'affaires valaisan à formuler un besoin professionnel.\n"
        "Transforme le texte en critères de recherche, dans l'ordre où ils apparaissent. Règles :\n"
        "1. N'utilise QUE les identifiants listés ci-dessous pour compétences, langues, zones et implantations.\n"
        "2. Ne retiens que ce que la personne CHERCHE, pas ce qu'elle vend, produit ou où elle se trouve elle-même.\n"
        "3. La première compétence est le besoin principal (obligatoire). Un critère introduit par « idéalement », "
        "« si possible », « de préférence » est non obligatoire. Ne transforme jamais une préférence en obligation.\n"
        "4. « zones » = où le prestataire doit INTERVENIR (livrer, travailler). « implantations » = où il doit être "
        "INSTALLÉ (« basé à », « implanté en »). « Nous sommes basés à X » décrit le demandeur : ce n'est pas un critère.\n"
        "5. Une compétence explicitement refusée (« pas de… », « sauf… », « je ne cherche pas… ») va dans « exclusions ».\n"
        "6. « extrait » recopie mot pour mot le passage du texte qui justifie le critère.\n"
        "7. Si le besoin ne correspond à aucune compétence listée, laisse « competences » vide et mets les mots-clés "
        "du besoin (recopiés du texte) dans « termes_hors_catalogue ». Ne force jamais une correspondance approximative.\n"
        "8. « contexte » : fréquences, délais, volumes ou budgets mentionnés.\n"
        "9. exclure_concurrents = true seulement si la personne demande d'éviter des concurrents.\n\n"
        "Compétences :\n" + "\n".join(lignes) + f"\n\nLangues : {langues}\nZones et implantations : {', '.join(tax.zones)}\n"
    )


def llm_configure() -> bool:
    return os.environ.get("HACKVS_LLM", "").lower() == "claude" and bool(
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def valider(texte: str, sortie: SortieLLM, tax: Taxonomie) -> Besoin:
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
    for type_, items in (("zone", sortie.zones), ("implantation", sortie.implantations)):
        for it in items:
            if it.valeur not in tax.zones:
                avert.append(f"Zone « {it.valeur} » inconnue : ignorée.")
                continue
            criteres.append(Critere(type=type_, valeur=it.valeur, libelle=it.valeur,
                                    obligatoire=it.obligatoire, extrait=extrait_verifie(it.extrait)))
    exclusions = [Exclusion(valeur=e.valeur, libelle=tax.libelle(e.valeur), extrait=extrait_verifie(e.extrait))
                  for e in sortie.exclusions if e.valeur in tax.concepts]

    exp = [c for c in criteres if c.type == "expertise"]
    if exp:  # invariant : la compétence principale est obligatoire, les autres gardent l'avis du modèle
        exp[0].obligatoire = True
    else:
        termes = [t for t in sortie.termes_hors_catalogue if t and norm(t) in n_texte]
        if termes:
            criteres.insert(0, Critere(type="texte_libre", valeur=" ".join(termes), libelle="Compétence hors catalogue",
                                       obligatoire=True,
                                       note="Aucune catégorie du Club reconnue : recherche par mots dans les offres déclarées."))
        else:
            avert.append("Je n'ai pas compris quelle compétence vous cherchez. Précisez-la ou choisissez-la dans la liste.")
    return Besoin(texte=texte, criteres=criteres, exclusions=exclusions, exclure_concurrents=sortie.exclure_concurrents,
                  contexte=sortie.contexte, analyseur="claude", avertissements=avert)


def _objets_complets(texte: str, cle: str) -> list[dict]:
    """Extrait les objets JSON déjà complets du tableau `cle` d'un JSON en cours d'écriture."""
    i = texte.find(f'"{cle}"')
    if i < 0:
        return []
    i = texte.find("[", i)
    if i < 0:
        return []
    objets, profondeur, debut, dans_chaine, echappe = [], 0, None, False, False
    for j in range(i + 1, len(texte)):
        ch = texte[j]
        if dans_chaine:
            echappe = ch == "\\" and not echappe
            if ch == '"' and not echappe:
                dans_chaine = False
            continue
        if ch == '"':
            dans_chaine = True
        elif ch == "{":
            if profondeur == 0:
                debut = j
            profondeur += 1
        elif ch == "}":
            profondeur -= 1
            if profondeur == 0 and debut is not None:
                try:
                    objets.append(json.loads(texte[debut:j + 1]))
                except json.JSONDecodeError:
                    pass
        elif ch == "]" and profondeur == 0:
            break
    return objets


def analyser_flux(texte: str, tax: Taxonomie, client=None) -> Iterator[dict]:
    """Événements : {"type": "provisoire", "critere": …} puis {"type": "final", "besoin": …, "telemetrie": …}."""
    t0 = time.perf_counter()
    modele = os.environ.get("HACKVS_CLAUDE_MODEL", MODELE_PAR_DEFAUT)
    try:
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        tampon, emis = "", set()
        premier_ms = None
        with client.messages.stream(
            model=modele, max_tokens=4000, system=systeme(tax),
            messages=[{"role": "user", "content": texte}],
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        ) as flux:
            for morceau in flux.text_stream:
                tampon += morceau
                for cle, type_ in (("competences", "expertise"), ("zones", "zone"), ("implantations", "implantation"), ("langues", "langue")):
                    for o in _objets_complets(tampon, cle):
                        k = (type_, o.get("valeur"))
                        if k not in emis:
                            emis.add(k)
                            premier_ms = premier_ms or round((time.perf_counter() - t0) * 1000)
                            yield {"type": "provisoire", "critere": {"type": type_, **o}}
            final = flux.get_final_message()
        if getattr(final, "stop_reason", None) == "refusal":
            raise ValueError("refus du modèle")
        sortie = SortieLLM.model_validate_json("".join(b.text for b in final.content if getattr(b, "type", "") == "text"))
        besoin = valider(texte, sortie, tax)
        usage = getattr(final, "usage", None)
        yield {"type": "final", "besoin": besoin.model_dump(), "telemetrie": {
            "analyseur": "claude", "modele": modele, "latence_ms": round((time.perf_counter() - t0) * 1000),
            "premier_critere_ms": premier_ms, "tokens_entree": getattr(usage, "input_tokens", None),
            "tokens_sortie": getattr(usage, "output_tokens", None)}}
    except Exception as e:  # repli visible, jamais silencieux
        besoin = analyser_regles(texte, tax)
        besoin.avertissements.insert(0, f"Claude indisponible ({type(e).__name__}) : analyse par règles locales.")
        yield {"type": "final", "besoin": besoin.model_dump(), "telemetrie": {
            "analyseur": "regles (repli)", "erreur": type(e).__name__, "latence_ms": round((time.perf_counter() - t0) * 1000)}}


def analyser(texte: str, tax: Taxonomie, client=None) -> tuple[Besoin, dict]:
    """Version non progressive (API, évaluation) : consomme le flux et renvoie le résultat final."""
    for ev in analyser_flux(texte, tax, client):
        if ev["type"] == "final":
            return Besoin(**ev["besoin"]), ev["telemetrie"]
    raise RuntimeError("flux sans résultat final")
