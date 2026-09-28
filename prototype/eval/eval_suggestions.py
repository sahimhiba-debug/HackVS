"""Banc d'essai des SUGGESTIONS de compétences (quand les règles ne reconnaissent rien).

Question mesurée : quand un membre écrit son besoin avec ses mots, les compétences que l'IA locale lui
PROPOSE (à confirmer) sont-elles les bonnes, et se tait-elle quand le besoin est hors catalogue ?

Métriques (vocabulaire standard de la recherche d'information, cf. évaluateurs Haystack) :
- hit@1, hit@3 : une compétence acceptable est 1re / parmi les 3 premières du classement ;
- MRR : moyenne de 1 / rang de la première compétence acceptable ;
- options affichées hors sujet : part des options MONTRÉES au membre qui ne sont pas acceptables (positifs) ;
- positifs sans aucune option : le membre ne reçoit rien alors qu'une compétence existait ;
- négatifs avec options : besoin hors catalogue pour lequel on affiche quand même des compétences.

Usage (depuis prototype/) : python -m eval.eval_suggestions --jeu dev --methode dense|hybride [--ecrire]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("HACKVS_SEMANTIQUE", "1")

from app import semantique  # noqa: E402
from app.taxonomy import charger_taxonomie  # noqa: E402

ICI = Path(__file__).resolve().parent / "suggestions"


def evaluer(jeu: str, methode: str) -> dict:
    tax = charger_taxonomie()
    cas = json.loads((ICI / f"{jeu}.json").read_text(encoding="utf-8"))["cas"]
    lignes, pos, neg = [], [], []
    for c in cas:
        r = semantique.suggerer(c["texte"], tax, methode=methode)
        classement = [x["concept"] for x in r["classement"]]
        options = r["options"]
        acc = set(c["acceptables"])
        if acc:
            rang = next((i + 1 for i, x in enumerate(classement) if x in acc), None)
            pos.append({"hit1": rang == 1, "hit3": rang is not None and rang <= 3, "rr": 1 / rang if rang else 0.0,
                        "affichees": len(options), "hors_sujet": sum(o not in acc for o in options),
                        "vide": not options})
        else:
            neg.append({"avec_options": bool(options)})
        lignes.append((c["texte"], sorted(acc), options, classement[:3]))
    n = len(pos)
    aff = sum(p["affichees"] for p in pos)
    return {
        "jeu": jeu, "methode": methode, "positifs": n, "negatifs": len(neg),
        "hit@1": round(sum(p["hit1"] for p in pos) / n, 3), "hit@3": round(sum(p["hit3"] for p in pos) / n, 3),
        "mrr": round(sum(p["rr"] for p in pos) / n, 3),
        "options_affichees_hors_sujet": f"{sum(p['hors_sujet'] for p in pos)}/{aff}",
        "positifs_sans_option": f"{sum(p['vide'] for p in pos)}/{n}",
        "negatifs_avec_options": f"{sum(x['avec_options'] for x in neg)}/{len(neg)}",
        "lignes": lignes,
    }


def rapport(r: dict) -> str:
    out = [f"# Suggestions de compétences — jeu `{r['jeu']}`, méthode `{r['methode']}`", "",
           "| Mesure | Valeur |", "|---|---|"]
    for k in ("positifs", "negatifs", "hit@1", "hit@3", "mrr", "options_affichees_hors_sujet", "positifs_sans_option",
              "negatifs_avec_options"):
        out.append(f"| {k} | {r[k]} |")
    out += ["", "| Besoin | Acceptables | Options affichées | Top 3 du classement |", "|---|---|---|---|"]
    for t, acc, opts, top in r["lignes"]:
        out.append(f"| {t} | {', '.join(acc) or '(hors catalogue)'} | {', '.join(opts) or '—'} | {', '.join(top)} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--jeu", default="dev", choices=["dev", "reserve", "italien"])
    ap.add_argument("--methode", default="hybride", choices=["dense", "hybride"])
    ap.add_argument("--ecrire", action="store_true")
    a = ap.parse_args()
    res = evaluer(a.jeu, a.methode)
    print(json.dumps({k: v for k, v in res.items() if k != "lignes"}, ensure_ascii=False))
    if a.ecrire:
        (ICI / f"resultats_{a.jeu}_{a.methode}.md").write_text(rapport(res), encoding="utf-8")
