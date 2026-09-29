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

from plateforme import modeles
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


def fournisseur() -> str | None:
    """« claude » (API Anthropic) ou « apertus » (LLM suisse, API compatible OpenAI : Swisscom, Public AI…)."""
    return os.environ.get("HACKVS_LLM", "").lower() or None


def llm_configure() -> bool:
    f = fournisseur()
    if f == "claude":
        return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    if f == "apertus":
        return all(os.environ.get(k) for k in ("APERTUS_API_KEY", "APERTUS_BASE_URL", "APERTUS_MODEL"))
    return False


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


def _morceaux_claude(texte: str, tax: Taxonomie, client, tele: dict, suite: tuple = ()) -> Iterator[str]:
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    tele["modele"] = os.environ.get("HACKVS_CLAUDE_MODEL", MODELE_PAR_DEFAUT)
    with client.messages.stream(
        model=tele["modele"], max_tokens=4000, system=systeme(tax),
        messages=[{"role": "user", "content": texte}, *suite],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    ) as flux:
        yield from flux.text_stream
        final = flux.get_final_message()
    if getattr(final, "stop_reason", None) == "refusal":
        raise ValueError("refus du modèle")
    usage = getattr(final, "usage", None)
    tele["tokens_entree"], tele["tokens_sortie"] = getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None)
    tele["texte_final"] = "".join(b.text for b in final.content if getattr(b, "type", "") == "text")


def _morceaux_apertus(texte: str, tax: Taxonomie, http, tele: dict, suite: tuple = ()) -> Iterator[str]:
    """API compatible OpenAI (/chat/completions, stream). Sortie JSON contrainte si le serveur la prend en charge,
    sinon consigne seule ; dans les deux cas, le code valide ensuite chaque élément."""
    import httpx
    base = os.environ["APERTUS_BASE_URL"].rstrip("/")
    tele["modele"] = os.environ["APERTUS_MODEL"]
    entetes = {"Authorization": f"Bearer {os.environ['APERTUS_API_KEY']}", "Content-Type": "application/json"}
    consigne = (systeme(tax) + "\nRéponds UNIQUEMENT par un objet JSON valide conforme à ce schéma, sans texte autour :\n"
                + json.dumps(SCHEMA, ensure_ascii=False))
    corps = {"model": tele["modele"], "stream": True, "temperature": 0, "max_tokens": 1500,
             "stream_options": {"include_usage": True},
             "messages": [{"role": "system", "content": consigne}, {"role": "user", "content": texte}, *suite],
             "response_format": {"type": "json_schema", "json_schema": {"name": "criteres", "schema": SCHEMA, "strict": True}}}
    client = http or httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0))
    for tentative in (1, 2):
        with client.stream("POST", f"{base}/chat/completions", headers=entetes, json=corps) as rep:
            if rep.status_code in (400, 422) and tentative == 1:
                rep.read()
                corps.pop("response_format")  # serveur sans sortie contrainte : on garde la consigne
                tele["sortie_contrainte"] = False
                continue
            rep.raise_for_status()
            tele.setdefault("sortie_contrainte", "response_format" in corps)
            accu = ""
            for ligne in rep.iter_lines():
                if not ligne.startswith("data:"):
                    continue
                donnee = ligne[5:].strip()
                if donnee == "[DONE]":
                    break
                evt = json.loads(donnee)
                if evt.get("usage"):
                    tele["tokens_entree"] = evt["usage"].get("prompt_tokens")
                    tele["tokens_sortie"] = evt["usage"].get("completion_tokens")
                for ch in evt.get("choices") or []:
                    morceau = (ch.get("delta") or {}).get("content") or ""
                    if morceau:
                        accu += morceau
                        yield morceau
            tele["texte_final"] = accu
            return


def completer_apertus(systeme_txt: str, message: str, schema: Optional[dict] = None, http=None,
                      max_tokens: int = 1200) -> str:
    """Appel simple (sans flux) à l'API compatible OpenAI d'Apertus, pour les bancs d'évaluation.
    Sortie JSON contrainte si `schema` est donné et que le serveur la prend en charge ; sinon consigne seule."""
    import httpx
    base = os.environ["APERTUS_BASE_URL"].rstrip("/")
    entetes = {"Authorization": f"Bearer {os.environ['APERTUS_API_KEY']}", "Content-Type": "application/json"}
    if schema is not None:
        systeme_txt += ("\nRéponds UNIQUEMENT par un objet JSON valide conforme à ce schéma, sans texte autour :\n"
                        + json.dumps(schema, ensure_ascii=False))
    corps = {"model": os.environ["APERTUS_MODEL"], "temperature": 0, "max_tokens": max_tokens,
             "messages": [{"role": "system", "content": systeme_txt}, {"role": "user", "content": message}]}
    if schema is not None:
        corps["response_format"] = {"type": "json_schema", "json_schema": {"name": "sortie", "schema": schema, "strict": True}}
    client = http or httpx.Client(timeout=httpx.Timeout(120.0, connect=10.0))
    rep = client.post(f"{base}/chat/completions", headers=entetes, json=corps)
    if rep.status_code in (400, 422) and "response_format" in corps:
        corps.pop("response_format")          # serveur sans sortie contrainte : on garde la consigne
        rep = client.post(f"{base}/chat/completions", headers=entetes, json=corps)
    rep.raise_for_status()
    texte = rep.json()["choices"][0]["message"]["content"] or ""
    return _json_de(texte) if schema is not None else texte


def _json_de(texte: str) -> str:
    """Retire d'éventuelles balises ```json autour de la réponse."""
    t = texte.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        t = t.rsplit("```", 1)[0]
    debut, fin = t.find("{"), t.rfind("}")
    return t[debut:fin + 1] if debut >= 0 and fin > debut else t


def analyser_flux(texte: str, tax: Taxonomie, client=None, http=None) -> Iterator[dict]:
    """Événements : {"type": "provisoire", "critere": …} puis {"type": "final", "besoin": …, "telemetrie": …}."""
    t0 = time.perf_counter()
    f = fournisseur() or "claude"
    route = modeles.router("extraction_besoin", preference=f)
    tele: dict = {"analyseur": f, "passerelle": {"etat": route.etat if route.choisi == f else "NON_CONFIGUREE", "raison": route.raison}}
    try:
        tampon, emis, premier_ms = "", set(), None
        suite: tuple = ()
        sortie: Optional[SortieLLM] = None
        tele["reessais"] = 0
        for tentative in (1, 2):
            morceaux = (_morceaux_apertus(texte, tax, http, tele, suite) if f == "apertus"
                        else _morceaux_claude(texte, tax, client, tele, suite))
            tampon = ""
            for morceau in morceaux:
                tampon += morceau
                for cle, type_ in (("competences", "expertise"), ("zones", "zone"), ("implantations", "implantation"), ("langues", "langue")):
                    for o in _objets_complets(tampon, cle):
                        k = (type_, o.get("valeur"))
                        if k not in emis:
                            emis.add(k)
                            premier_ms = premier_ms or round((time.perf_counter() - t0) * 1000)
                            yield {"type": "provisoire", "critere": {"type": type_, **o}}
            brut = tele.pop("texte_final", tampon)
            try:
                sortie = SortieLLM.model_validate_json(_json_de(brut))
                break
            except ValueError as err:  # JSON invalide ou non conforme au schéma
                if tentative == 2:
                    raise
                # Patron « ModelRetry » (Pydantic AI) : on renvoie UNE fois l'erreur de validation au modèle.
                tele["reessais"] = 1
                resume = str(err).splitlines()[0][:300]
                suite = ({"role": "assistant", "content": brut[:4000] or "(vide)"},
                         {"role": "user", "content": f"Ta réponse n'est pas un JSON valide conforme au schéma ({resume}). "
                                                     "Renvoie uniquement l'objet JSON corrigé, sans texte autour."})
        assert sortie is not None                    # la boucle sort par break après validation, sinon lève
        besoin = valider(texte, sortie, tax)
        besoin.analyseur = f
        yield {"type": "final", "besoin": besoin.model_dump(), "telemetrie": {
            **tele, "latence_ms": round((time.perf_counter() - t0) * 1000), "premier_critere_ms": premier_ms}}
    except Exception as e:  # repli visible, jamais silencieux
        besoin = analyser_regles(texte, tax)
        nom = {"claude": "Claude", "apertus": "Apertus"}.get(f, f)
        besoin.avertissements.insert(0, f"{nom} indisponible ({type(e).__name__}) : analyse par règles locales.")
        tele.pop("texte_final", None)
        yield {"type": "final", "besoin": besoin.model_dump(), "telemetrie": {
            **tele, "analyseur": "regles (repli)", "erreur": type(e).__name__, "latence_ms": round((time.perf_counter() - t0) * 1000)}}


def analyser(texte: str, tax: Taxonomie, client=None, http=None) -> tuple[Besoin, dict]:
    """Version non progressive (API, évaluation) : consomme le flux et renvoie le résultat final."""
    for ev in analyser_flux(texte, tax, client, http):
        if ev["type"] == "final":
            return Besoin(**ev["besoin"]), ev["telemetrie"]
    raise RuntimeError("flux sans résultat final")
