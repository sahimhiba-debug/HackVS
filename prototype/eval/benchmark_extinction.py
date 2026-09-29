"""Benchmark EXP-F : quelles relations raviver pour préserver le réseau projeté ? (données GÉNÉRÉES, SYNTHETIC)

Mêmes relations menacées, même budget, même plafond (1 ravivement par membre) pour toutes les méthodes.
Mesures à l'horizon (90 jours, projection pessimiste) : membres avec au moins une relation actuelle, plus grand groupe,
nombre de groupes (≥ 3 membres), ravivements utilisés.

    python -m eval.benchmark_extinction [--reseaux 20] [--sortie eval/resultats_benchmark_extinction.md]
"""
from __future__ import annotations

import argparse
import random
import statistics
from datetime import timedelta
from pathlib import Path

import networkx as nx

from adaptateurs.club import extinction as ex
from adaptateurs.club import reseau
from eval.perf_echelle import generer


echeances = ex.echeances


def _plafonne(ordre: list[str], k: int, plafond: int) -> list[str]:
    res, n = [], {}
    for x in ordre:
        if len(res) == k:
            break
        a, b = x.split("|")
        if n.get(a, 0) < plafond and n.get(b, 0) < plafond:
            res.append(x)
            n[a], n[b] = n.get(a, 0) + 1, n.get(b, 0) + 1
    return res


def mesure(g_act, membres, ech, t, horizon, ravivees) -> dict:
    g, _ = ex.projeter(g_act, membres, ech, t, horizon, frozenset(ravivees))
    ind = ex.indicateurs_actuels(g, membres)
    return {"avec_relation": ind["avec_relation_actuelle"], "plus_grand_groupe": ind["plus_grand_groupe"],
            "groupes": sum(1 for c in nx.connected_components(g) if len(c) >= 3), "ravivements": len(ravivees)}


def un_reseau(graine: int, n: int, k: int, horizon: int, plafond: int) -> dict:
    profils, m, t = generer(n, graine)
    membres = sorted(p.id for p in profils)
    g = reseau.graphe_actuel(m, t)
    ech = {x: d for x, d in echeances(m, t).items() if g.has_edge(*x.split("|"))}
    fin = t + timedelta(days=horizon)
    menacees = sorted(x for x, d in ech.items() if d <= fin)
    deg = lambda x: sum(g.degree(y) for y in x.split("|"))  # noqa: E731
    res = {"AUJOURD_HUI": mesure(g, membres, ech, t, 0, []),
           "SANS_ACTION": mesure(g, membres, ech, t, horizon, []),
           "STRUCTURE (nous)": mesure(g, membres, ech, t, horizon, ex.prevenir(g, membres, ech, t, horizon, k, plafond)),
           "STRUCTURE_COHESION (nous)": mesure(g, membres, ech, t, horizon, ex.prevenir(g, membres, ech, t, horizon, k, plafond, "COHESION")),
           "PLUS_PROCHES_D_ABORD": mesure(g, membres, ech, t, horizon, _plafonne(sorted(menacees, key=lambda x: (ech[x], x)), k, plafond)),
           "PLUS_RELIES_D_ABORD": mesure(g, membres, ech, t, horizon, _plafonne(sorted(menacees, key=lambda x: (-deg(x), x)), k, plafond))}
    tirages = []
    for s in range(30):
        o = list(menacees)
        random.Random(s).shuffle(o)
        tirages.append(mesure(g, membres, ech, t, horizon, _plafonne(o, k, plafond)))
    res["HASARD (30)"] = {c: statistics.mean(x[c] for x in tirages) for c in tirages[0]}
    res["_menacees"] = len(menacees)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reseaux", type=int, default=20)
    ap.add_argument("--membres", type=int, default=150)
    ap.add_argument("--budget", type=int, default=5)
    ap.add_argument("--horizon", type=int, default=30)   # 90 = TOUTES les relations actuelles s'éteignent (1re mesure)
    ap.add_argument("--plafond", type=int, default=2)
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    runs = [un_reseau(500 + s, a.membres, a.budget, a.horizon, a.plafond) for s in range(a.reseaux)]
    meth = [x for x in runs[0] if not x.startswith("_")]
    cles = ["avec_relation", "plus_grand_groupe", "groupes", "ravivements"]
    lignes = ["# Échéancier d'extinction — prévention (SYNTHETIC)", "",
              f"{a.reseaux} réseaux GÉNÉRÉS de {a.membres} membres ; horizon {a.horizon} jours ; budget {a.budget} ravivements ; "
              f"plafond {a.plafond} par membre ; relations menacées par réseau : {statistics.mean(r['_menacees'] for r in runs):.1f}.", "",
              "| Méthode | " + " | ".join(cles) + " |", "|---|" + "---|" * len(cles)]
    for x in meth:
        lignes.append(f"| {x} | " + " | ".join(f"{statistics.mean(r[x][c] for r in runs):.2f}" for c in cles) + " |")
    bases = ["PLUS_PROCHES_D_ABORD", "PLUS_RELIES_D_ABORD", "HASARD (30)"]
    for nous, c in (("STRUCTURE (nous)", "avec_relation"), ("STRUCTURE_COHESION (nous)", "plus_grand_groupe"),
                    ("STRUCTURE (nous)", "plus_grand_groupe"), ("STRUCTURE_COHESION (nous)", "avec_relation")):
        g = sum(r[nous][c] > max(r[b][c] for b in bases) for r in runs)
        e = sum(r[nous][c] == max(r[b][c] for b in bases) for r in runs)
        lignes.append(f"- {nous} sur « {c} » : gagne {g}, égalité {e}, perd {len(runs) - g - e} (contre la meilleure baseline).")
    lignes += ["", "Projection pessimiste (aucune interaction spontanée) ; règle des 90 jours = hypothèse de produit."]
    texte = "\n".join(lignes) + "\n"
    print(texte)
    if a.sortie:
        Path(a.sortie).write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
