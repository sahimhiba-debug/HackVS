"""Benchmark de la frontière de Pareto des interventions (données GÉNÉRÉES, SYNTHETIC).

Questions :
1. Les objectifs sont-ils réellement en conflit (sinon un front « riche » serait artificiel) ? → corrélations de rang
   entre objectifs sur les plans explorés, et fréquence d'un plan qui atteint l'idéal sur tous les axes.
2. Les plans simples (hasard, populaires, preuve d'abord) et nos plans à objectif unique sont-ils DOMINÉS par le front ?

    python -m eval.benchmark_pareto [--reseaux 20] [--sortie eval/resultats_benchmark_pareto.md]
"""
from __future__ import annotations

import argparse
import random
import statistics
from pathlib import Path

from adaptateurs.club import cycle as cy
from adaptateurs.club import interventions as iv
from adaptateurs.club import pareto as pa
from adaptateurs.club import reseau
from app.taxonomy import charger_taxonomie
from eval.benchmark_interventions import _plafonne
from eval.perf_echelle import generer

TAX = charger_taxonomie()


def diversite(profils, cands) -> dict[tuple, bool]:
    par = {p.id: p for p in profils}
    return {(c.a, c.b): not any(TAX.meme_famille(x, y) for x in par[c.a].secteurs for y in par[c.b].secteurs) for c in cands}


def _rangs(v: list[float]) -> list[float]:
    ordre = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(ordre):
        j = i
        while j + 1 < len(ordre) and v[ordre[j + 1]] == v[ordre[i]]:
            j += 1
        for k in range(i, j + 1):
            r[ordre[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(x: list[float], y: list[float]) -> float:
    rx, ry = _rangs(x), _rangs(y)
    if len(set(rx)) < 2 or len(set(ry)) < 2:
        return float("nan")
    return statistics.correlation(rx, ry)


def un_reseau(graine: int, n: int, k: int) -> dict:
    profils, m, t = generer(n, graine)
    g = reseau.graphe_actuel(m, t)
    membres = sorted(p.id for p in profils if p.type == "membre_club")
    g.add_nodes_from(membres)
    cands = iv.candidates(profils, cy.besoins_publies(m, t), TAX, g, reseau.etats_par_paire(m, t))
    div_secteur = diversite(profils, cands)
    # diversité sectorielle et non-redondance : mesurées puis abandonnées comme axes (quasi constantes entre plans)
    non_redondantes = sum(not (set(g[c.a]) & set(g[c.b])) for c in cands) / max(1, len(cands))
    ids = {(c.a, c.b): c for c in cands}
    plans_simples = {
        "INCLUSION (cycle 6)": [ids[tuple(a["paire"])] for a in iv.choisir(g, cands, k, 1, "INCLUSION")],
        "COHESION (cycle 6)": [ids[tuple(a["paire"])] for a in iv.choisir(g, cands, k, 1, "COHESION")],
        "PREUVE_D_ABORD": _plafonne(sorted(cands, key=lambda c: (-c.valeur, -c.reciproque, c.a, c.b)), k, 1),
        "POPULAIRES": _plafonne(sorted(cands, key=lambda c: (-(g.degree(c.a) + g.degree(c.b)), c.a, c.b)), k, 1),
    }
    for s in range(10):
        o = list(cands)
        random.Random(s).shuffle(o)
        plans_simples[f"HASARD_{s}"] = _plafonne(o, k, 1)
    heuristiques = [v for n, v in plans_simples.items() if not n.startswith("HASARD")]
    for s in range(100, 130):            # vivier élargi : 30 plans aléatoires d'EXPLORATION (graines ≠ tirages de contrôle 0–9)
        o = list(cands)
        random.Random(s).shuffle(o)
        heuristiques.append(_plafonne(o, k, 1))
    f = pa.frontiere(g, membres, cands, k, plans_supplementaires=heuristiques)
    domines = {nom: any(pa.domine(p["objectifs"], pa.evaluer(g, membres, plan)) for p in f["front"])
               for nom, plan in plans_simples.items()}
    tous = [p["objectifs"] for p in f["front"]]
    return {"part_intersecteur": sum(div_secteur.values()) / max(1, len(div_secteur)), "part_non_redondante": non_redondantes,
            "front": len(f["front"]), "explores": f["plans_explores"], "ideal": f["un_plan_atteint_l_ideal"],
            "nommes": len(f["plans_nommes"]), "domines": domines, "front_obj": tous}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reseaux", type=int, default=20)
    ap.add_argument("--membres", type=int, default=150)
    ap.add_argument("--budget", type=int, default=10)
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    runs = [un_reseau(300 + s, a.membres, a.budget) for s in range(a.reseaux)]
    corr = {}
    for i, x in enumerate(pa.AXES):
        for y in pa.AXES[i + 1:]:
            vals = [spearman([p[x] for p in r["front_obj"]], [p[y] for p in r["front_obj"]]) for r in runs if len(r["front_obj"]) >= 3]
            vals = [v for v in vals if v == v]
            corr[f"{x} × {y}"] = (statistics.mean(vals) if vals else float("nan"), len(vals))
    noms = list(runs[0]["domines"])
    base = [nom for nom in noms if not nom.startswith("HASARD")]
    lignes = ["# Frontière de Pareto des interventions — SYNTHETIC", "",
              f"{a.reseaux} réseaux GÉNÉRÉS de {a.membres} membres ; budget {a.budget} actions ; plafond 1 ; "
              "15 pondérations + 4 plans heuristiques + 30 plans aléatoires d'exploration ; "
              "contrôle : 10 tirages aléatoires DISTINCTS, hors du vivier.", "",
              f"- Taille du front (plans non dominés) : médiane {statistics.median(r['front'] for r in runs)}, "
              f"min {min(r['front'] for r in runs)}, max {max(r['front'] for r in runs)} ; plans distincts explorés : "
              f"médiane {statistics.median(r['explores'] for r in runs)}.",
              f"- Un plan atteint l'idéal sur les 3 axes à la fois : {sum(r['ideal'] for r in runs)}/{len(runs)} réseaux.",
              f"- Part des actions candidates qui relient deux secteurs différents : "
              f"{statistics.mean(r['part_intersecteur'] for r in runs):.0%} (d'où l'abandon de la diversité sectorielle comme axe) ; "
              f"sans aucun contact commun : {statistics.mean(r['part_non_redondante'] for r in runs):.0%} (non-redondance abandonnée).",
              f"- Plans nommés distincts (extrêmes + équilibre, doublons fusionnés) : médiane {statistics.median(r['nommes'] for r in runs)}.",
              "", "## Corrélation de rang entre objectifs, sur les plans du front (moyenne ; négatif = conflit)", "",
              "| Paire d'objectifs | Spearman moyen | Réseaux (front ≥ 3) |", "|---|---|---|"]
    lignes += [f"| {k} | {v[0]:.2f} | {v[1]} |" for k, v in corr.items()]
    lignes += ["", "## Plans simples dominés par au moins un plan du front", "", "| Plan | Dominé |", "|---|---|"]
    lignes += [f"| {nom} | {sum(r['domines'][nom] for r in runs)}/{len(runs)} |" for nom in base]
    hasard = sum(r["domines"][n] for r in runs for n in noms if n.startswith("HASARD"))
    lignes.append(f"| HASARD de contrôle (10 tirages × {len(runs)} réseaux, hors vivier) | {hasard}/{10 * len(runs)} |")
    lignes += ["", "Hypothèse : toutes les actions acceptées. Un plan non dominé n'est pas « meilleur » : il est un compromis "
               "que l'humain choisit."]
    texte = "\n".join(lignes) + "\n"
    print(texte)
    if a.sortie:
        Path(a.sortie).write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
