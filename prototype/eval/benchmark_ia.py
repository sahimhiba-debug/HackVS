"""G1 — Comprendre un besoin : MOTEUR seul contre IA SEULE contre HYBRIDE (et hybride EN REPLI).

Voir competition/GENAI_RESEARCH.md (pré-inscription : hypothèses et critères écrits avant exécution).
- MOTEUR       : analyse par règles + moteur de recherche.
- IA_SEULE     : le LLM reçoit le besoin ET les profils publics FICTIFS et choisit jusqu'à 3 membres (ou s'abstient).
                 Bras d'ÉVALUATION seulement : dans le produit, le LLM ne voit jamais les profils (règle testée).
- HYBRIDE      : le LLM traduit le besoin en critères du vocabulaire fermé (validés par le code) ; le moteur décide.
- HYBRIDE_REPLI: règles d'abord ; LLM seulement si les règles ne reconnaissent aucune compétence ou signalent une ambiguïté.
Notation identique à eval/run_eval.py (succès@3, violations, abstention) + identifiants inventés + coût (appels, latence).
Sans modèle configuré, les bras IA sont marqués NON EXÉCUTÉ : aucun chiffre n'est inventé.

    HACKVS_LLM=claude python -m eval.benchmark_ia [--jeux base,adversarial,...] [--sortie eval/resultats_benchmark_ia.md]
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Callable, Optional

from app import parser_llm, parser_rules
from app.matching import rechercher
from app.taxonomy import charger_taxonomie
from eval.run_eval import ICI, JEUX, charger

TAX = charger_taxonomie()

SCHEMA_IA_SEULE = {"type": "object", "properties": {
    "ids": {"type": "array", "items": {"type": "string"}},
    "abstention": {"type": "boolean"},
    "justification": {"type": "string"}},
    "required": ["ids", "abstention", "justification"], "additionalProperties": False}


def _profil_public(p) -> dict:
    return {"id": p.id, "type": p.type, "entreprise": p.entreprise, "commune": p.commune, "secteurs": p.secteurs,
            "offre": [o.texte for o in p.offre], "langues": p.langues, "zones_service": p.zones_service,
            "presentation": p.presentation, "accepte_introductions": p.accepte_introductions}


def ia_seule_client(profils, moi, client=None, apertus_http=None) -> Callable[[str], dict]:
    """Le LLM choisit lui-même, sans vocabulaire fermé ni filtre du moteur. `client` : SDK Anthropic (ou double de test) ;
    avec HACKVS_LLM=apertus, l'API compatible OpenAI d'Apertus (`apertus_http` : double de test httpx)."""
    annuaire = json.dumps([_profil_public(p) for p in profils if p.id != moi.id], ensure_ascii=False)
    systeme = ("Tu recommandes, parmi les membres d'un club d'affaires, au plus 3 personnes capables de répondre au "
               "besoin. Respecte les contraintes exprimées (langue, zone, exclusions). Ne propose jamais un visiteur ni "
               "un membre qui n'accepte pas les introductions. Si personne ne convient, abstiens-toi. "
               "Réponds avec les identifiants exacts de l'annuaire.\n\nAnnuaire (JSON) :\n" + annuaire)
    if client is None and parser_llm.fournisseur() == "apertus":
        return lambda texte: json.loads(parser_llm.completer_apertus(systeme, texte, SCHEMA_IA_SEULE, apertus_http, 800))
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    modele = os.environ.get("HACKVS_CLAUDE_MODEL", parser_llm.MODELE_PAR_DEFAUT)

    def choisir(texte: str) -> dict:
        r = client.messages.create(model=modele, max_tokens=800, system=systeme,
                                   messages=[{"role": "user", "content": texte}],
                                   output_config={"format": {"type": "json_schema", "schema": SCHEMA_IA_SEULE}})
        if getattr(r, "stop_reason", None) == "refusal":
            raise ValueError("refus du modèle")
        brut = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return json.loads(brut)
    return choisir


def evaluer_bras(bras: str, cas: list[dict], profils, par_id, moi, llm: Optional[Callable] = None,
                 client=None, http=None) -> dict:
    interdits_globaux = {p.id for p in profils if p.type == "visiteur" or not p.accepte_introductions}
    lignes, appels, latences = [], 0, []
    for c in cas:
        t0 = time.perf_counter()
        inventes = 0
        if bras == "MOTEUR" or bras == "HYBRIDE_REPLI":
            besoin = parser_rules.analyser(c["texte"], TAX)
            if bras == "HYBRIDE_REPLI" and (not any(x.type == "expertise" for x in besoin.criteres) or besoin.ambiguites):
                besoin, _ = parser_llm.analyser(c["texte"], TAX, client, http)
                appels += 1
            r = rechercher(besoin, moi, profils, TAX)
            top, abstention = [s.profil.id for s in r.suggestions[:3]], r.abstention
        elif bras == "HYBRIDE":
            besoin, _ = parser_llm.analyser(c["texte"], TAX, client, http)
            appels += 1
            r = rechercher(besoin, moi, profils, TAX)
            top, abstention = [s.profil.id for s in r.suggestions[:3]], r.abstention
        else:                                         # IA_SEULE
            sortie = llm(c["texte"])
            appels += 1
            ids = [x for x in sortie.get("ids", [])][:3]
            inventes = sum(1 for x in ids if x not in par_id)
            top, abstention = [x for x in ids if x in par_id], bool(sortie.get("abstention")) or not ids
        latences.append((time.perf_counter() - t0) * 1000)
        succes = None if c["abstention"] else bool(set(top) & set(c["attendus"]))
        lignes.append({"id": c["id"], "categorie": c["categorie"], "top3": top, "succes": succes,
                       "violation": bool(set(top) & (set(c["interdits"]) | interdits_globaux)),
                       "abstention_ok": abstention == c["abstention"], "inventes": inventes})
    avec = [x for x in lignes if x["succes"] is not None]
    return {"bras": bras, "succes@3": sum(x["succes"] for x in avec), "sur": len(avec),
            "violations": sum(x["violation"] for x in lignes), "abstention_ok": sum(x["abstention_ok"] for x in lignes),
            "inventes": sum(x["inventes"] for x in lignes), "cas": len(lignes), "appels_llm": appels,
            "latence_mediane_ms": round(sorted(latences)[len(latences) // 2], 1) if latences else None, "detail": lignes}


def _nom_modele() -> str:
    if parser_llm.fournisseur() == "apertus":
        return f"Apertus ({os.environ.get('APERTUS_MODEL')})"
    return f"Claude ({os.environ.get('HACKVS_CLAUDE_MODEL', parser_llm.MODELE_PAR_DEFAUT)})"


def modele_disponible() -> bool:
    return parser_llm.llm_configure()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jeux", default=",".join(JEUX))
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    profils, par_id, moi = charger()
    cas = [dict(c, jeu=j) for j in a.jeux.split(",") for c in json.loads((ICI / JEUX[j]).read_text(encoding="utf-8"))["cas"]]
    dispo = modele_disponible()
    resultats = [evaluer_bras("MOTEUR", cas, profils, par_id, moi)]
    if dispo:
        resultats.append(evaluer_bras("HYBRIDE", cas, profils, par_id, moi))
        resultats.append(evaluer_bras("HYBRIDE_REPLI", cas, profils, par_id, moi))
        resultats.append(evaluer_bras("IA_SEULE", cas, profils, par_id, moi, llm=ia_seule_client(profils, moi)))
    lignes = ["# G1 — Comprendre un besoin : moteur seul, IA seule, hybride", "",
              f"Modèle : {_nom_modele() if dispo else 'aucun'}. {len(cas)} cas ({a.jeux}) écrits avant exécution ; notation identique à eval/run_eval.py.", "",
              "| Bras | succès@3 | Violations | Abstention correcte | Identifiants inventés | Appels au modèle | Latence médiane |",
              "|---|---|---|---|---|---|---|"]
    for r in resultats:
        lignes.append(f"| {r['bras']} | {r['succes@3']}/{r['sur']} | {r['violations']}/{r['cas']} | {r['abstention_ok']}/{r['cas']} | "
                      f"{r['inventes']} | {r['appels_llm']} | {r['latence_mediane_ms']} ms |")
    if not dispo:
        lignes += [f"| {b} | NON EXÉCUTÉ | — | — | — | — | — |" for b in ("HYBRIDE", "HYBRIDE_REPLI", "IA_SEULE")]
        lignes += ["", "Aucun modèle génératif configuré dans l'environnement : les bras IA n'ont pas été exécutés et "
                   "aucun chiffre n'est donné pour eux (voir competition/GENAI_RESEARCH.md)."]
    else:
        m = next(r for r in resultats if r["bras"] == "MOTEUR")
        echecs = {x["id"] for x in m["detail"] if x["succes"] is False or x["violation"] or not x["abstention_ok"]}
        for r in resultats[1:]:
            rec = sum(1 for x in r["detail"] if x["id"] in echecs and x["succes"] is not False and not x["violation"] and x["abstention_ok"])
            nouv = sum(1 for x, y in zip(r["detail"], m["detail"], strict=True) if x["violation"] and not y["violation"])
            lignes.append(f"- {r['bras']} : récupère {rec}/{len(echecs)} échecs du moteur ; nouvelles violations : {nouv}.")
    texte = "\n".join(lignes) + "\n"
    print(texte)
    if a.sortie:
        Path(a.sortie).write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
