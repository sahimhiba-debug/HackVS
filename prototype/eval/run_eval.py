"""Évaluation exploratoire : moteur « Le Fil du Club » vs référence mots-clés.

Usage : python -m eval.run_eval            (depuis prototype/)
        python -m eval.run_eval --claude   (analyse par Claude si configurée : coûte des appels API)

Mesures (top 3 affiché à l'utilisateur) :
- succès@3 : au moins un profil attendu dans les 3 premiers (cas non-abstention) ;
- violations : profil interdit (contrainte violée ou faux ami) dans les 3 premiers ;
- abstention correcte : s'abstient quand il faut, et seulement quand il faut ;
- preuves vérifiées : part des justifications retrouvées mot pour mot dans le profil ;
- invariants : aucun visiteur, aucun profil refusant les introductions, jamais.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from app import parser_llm, parser_rules
from app.baseline import rechercher_mots_cles
from app.matching import preuve_valide, rechercher
from app.models import Profil
from app.taxonomy import DATA_DIR, charger_taxonomie

ICI = Path(__file__).resolve().parent


def charger():
    brut = json.loads((DATA_DIR / "profils_demo.json").read_text(encoding="utf-8"))
    profils = [Profil(**p) for p in brut["profils"]]
    par_id = {p.id: p for p in profils}
    return profils, par_id, par_id[brut["utilisateur_demo"]]


JEUX = {"base": "cas.json", "adversarial": "cas_adversariaux.json", "reserve": "cas_reserve.json", "reserve2": "cas_reserve2.json"}


def _critere_ok(attendu: dict, criteres) -> bool:
    return any(c.type == attendu["type"] and c.valeur == attendu["valeur"]
               and ("obligatoire" not in attendu or c.obligatoire == attendu["obligatoire"]) for c in criteres)


def evaluer(claude: bool = False, jeu: str = "base") -> dict:
    tax = charger_taxonomie()
    profils, par_id, moi = charger()
    cas = json.loads((ICI / JEUX[jeu]).read_text(encoding="utf-8"))["cas"]
    crit_ok = crit_total = 0
    interdits_globaux = {p.id for p in profils if p.type == "visiteur" or not p.accepte_introductions}
    lignes, agg = [], {"moteur": [], "reference": []}
    latences_analyse, preuves_total, preuves_ok = [], 0, 0
    telemetries: list[dict] = []

    for c in cas:
        t0 = time.perf_counter()
        if claude:
            besoin, tele = parser_llm.analyser(c["texte"], tax)
            regles = parser_rules.analyser(c["texte"], tax)
            cle = lambda b: sorted((x.type, x.valeur, x.obligatoire) for x in b.criteres)
            telemetries.append({**tele, "id": c["id"], "accord_regles": cle(besoin) == cle(regles)})
        else:
            besoin = parser_rules.analyser(c["texte"], tax)
        latences_analyse.append((time.perf_counter() - t0) * 1000)
        resultats = {
            "moteur": rechercher(besoin, moi, profils, tax),
            "reference": rechercher_mots_cles(besoin, moi, profils, tax),
        }
        for a in c.get("criteres_attendus", []):
            crit_total += 1
            crit_ok += _critere_ok(a, besoin.criteres)
        for a in c.get("criteres_interdits", []):
            crit_total += 1
            crit_ok += not _critere_ok(a, besoin.criteres)
        ligne = {"id": c["id"], "categorie": c["categorie"],
                 "criteres": [f"{x.type}:{x.valeur}{'' if x.obligatoire else '?'}" for x in besoin.criteres]}
        for nom, r in resultats.items():
            top = [s.profil.id for s in r.suggestions[:3]]
            succes = None if c["abstention"] else bool(set(top) & set(c["attendus"]))
            violation = bool(set(top) & (set(c["interdits"]) | interdits_globaux))
            abst_ok = r.abstention == c["abstention"]
            if nom == "moteur":
                for s in r.suggestions + r.pistes_elargies:
                    for pr in s.preuves + ([s.reciprocite] if s.reciprocite else []):
                        preuves_total += 1
                        preuves_ok += preuve_valide(par_id[s.profil.id], pr)
            ligne[nom] = {"top3": top, "succes": succes, "violation": violation, "abstention_ok": abst_ok,
                          "duree_ms": r.duree_ms}
            agg[nom].append(ligne[nom])
        lignes.append(ligne)

    def synthese(rs):
        avec = [r for r in rs if r["succes"] is not None]
        return {
            "succes@3": f"{sum(r['succes'] for r in avec)}/{len(avec)}",
            "violations": f"{sum(r['violation'] for r in rs)}/{len(rs)}",
            "abstention_correcte": f"{sum(r['abstention_ok'] for r in rs)}/{len(rs)}",
        }

    return {
        "analyseur": "claude" if claude else "regles",
        "jeu": jeu,
        "nb_cas": len(cas),
        "nb_profils": len(profils),
        "criteres_corrects": f"{crit_ok}/{crit_total}",
        "moteur": synthese(agg["moteur"]),
        "reference": synthese(agg["reference"]),
        "preuves_verifiees": f"{preuves_ok}/{preuves_total}",
        "latence_analyse_ms_mediane": round(statistics.median(latences_analyse), 2),
        "latence_recherche_ms_mediane": round(statistics.median(r["duree_ms"] for r in agg["moteur"]), 2),
        "detail": lignes,
        "telemetrie_claude": telemetries,
    }


def en_markdown(res: dict) -> str:
    o = [f"# Résultats d'évaluation (exploratoire, données fictives)\n",
         f"Jeu : **{res['jeu']}** · analyseur : **{res['analyseur']}** · {res['nb_cas']} cas · généré par `python -m eval.run_eval --jeu {res['jeu']}`\n",
         (f"Critères extraits conformes (type, valeur, obligatoire/souhaité ; critères interdits absents) : {res['criteres_corrects']}\n"
          if not res['criteres_corrects'].endswith("/0") else ""),
         "| Mesure | Le Fil du Club | Mots-clés + mêmes filtres |", "|---|---|---|"]
    for k in ("succes@3", "violations", "abstention_correcte"):
        o.append(f"| {k} | {res['moteur'][k]} | {res['reference'][k]} |")
    o.append(f"\nPreuves citées retrouvées mot pour mot dans le profil : {res['preuves_verifiees']} "
             "(vrai par construction pour l'extraction par règles ; le garde-fou compte surtout si un LLM rédige un jour les explications).")
    o.append(f"\nLatence médiane : analyse {res['latence_analyse_ms_mediane']} ms, recherche {res['latence_recherche_ms_mediane']} ms (machine locale, {res['nb_profils']} profils).\n")
    o.append("| Cas | Catégorie | Critères extraits | Moteur top 3 | ok | Référence top 3 | ok |")
    o.append("|---|---|---|---|---|---|---|")
    for l in res["detail"]:
        def ok(r):
            s = "✓" if (r["succes"] or r["succes"] is None) and not r["violation"] and r["abstention_ok"] else "✗"
            return s + (" (viol.)" if r["violation"] else "")
        o.append(f"| {l['id']} | {l['categorie']} | {', '.join(l['criteres']) or '—'} | "
                 f"{', '.join(l['moteur']['top3']) or 'abstention'} | {ok(l['moteur'])} | "
                 f"{', '.join(l['reference']['top3']) or 'abstention'} | {ok(l['reference'])} |")
    o.append(f"\n**Limites** : cas écrits par l'auteur de la taxonomie (circularité), {res['nb_profils']} profils fictifs, "
             "aucun utilisateur réel. Ces chiffres montrent que le mécanisme fonctionne comme conçu, pas qu'il est utile aux membres.")
    return "\n".join(o) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--claude", action="store_true")
    ap.add_argument("--jeu", choices=list(JEUX) + ["tous"], default="tous")
    ap.add_argument("--archive", help="étiquette : copie aussi le résultat dans eval/archives/<étiquette>_<jeu>.md")
    a = ap.parse_args()
    for jeu in (list(JEUX) if a.jeu == "tous" else [a.jeu]):
        res = evaluer(claude=a.claude, jeu=jeu)
        suffixe = "_claude" if a.claude else ""
        (ICI / f"resultats_{jeu}{suffixe}.md").write_text(en_markdown(res), encoding="utf-8")
        if a.archive:
            (ICI / "archives").mkdir(exist_ok=True)
            (ICI / "archives" / f"{a.archive}_{jeu}{suffixe}.md").write_text(en_markdown(res), encoding="utf-8")
        print(json.dumps({k: v for k, v in res.items() if k != "detail"}, ensure_ascii=False, indent=2))
