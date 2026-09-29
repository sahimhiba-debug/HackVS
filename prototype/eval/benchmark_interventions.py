"""Benchmark de l'intervention minimale (idée I-01) — données GÉNÉRÉES (SYNTHETIC), jamais présentées comme réelles.

Question : à budget égal (k actions) et sur les MÊMES candidats (aides prouvées, consentement et refus respectés),
le choix glouton par gain structurel relie-t-il plus de membres sans relation actuelle et réunit-il plus de groupes
que des méthodes simples ? Et que perd-il ?

Méthodes comparées (toutes limitées au même plafond de sollicitations par membre) :
- STRUCTURE (la nôtre) : gain marginal lexicographique (isolés reliés, groupes réunis, réciprocité, preuve) ;
- PREUVE_D_ABORD : les candidates à la plus forte aide prouvée (ce que ferait un moteur de recommandation) ;
- POPULAIRES : les candidates entre membres déjà les plus reliés (effet « riche devient plus riche ») ;
- HASARD : tirage uniforme parmi les candidates (moyenne sur 30 graines).
Hypothèse déclarée : chaque action choisie est acceptée (comme la simulation du produit).

    python -m eval.benchmark_interventions [--reseaux 20] [--sortie eval/resultats_benchmark_interventions.md]
"""
from __future__ import annotations

import argparse
import random
import statistics
from datetime import timedelta

import networkx as nx

from adaptateurs.club import interventions as iv
from adaptateurs.club import reseau
from eval.perf_echelle import generer
from plateforme.affirmations import Statut
from plateforme.memoire import Evt
from app.taxonomy import charger_taxonomie
from adaptateurs.club import cycle as cy

TAX = charger_taxonomie()


def _plafonne(ordre: list, k: int, plafond: int) -> list:
    sol, n = [], {}
    for c in ordre:
        if len(sol) == k:
            break
        if n.get(c.a, 0) < plafond and n.get(c.b, 0) < plafond:
            sol.append(c)
            for x in (c.a, c.b):
                n[x] = n.get(x, 0) + 1
    return sol


def evaluer(g: nx.Graph, membres: list[str], choix: list) -> dict:
    apres = g.copy()
    apres.add_edges_from((c.a, c.b) for c in choix)
    i = iv.indicateurs_actuels(apres, membres)
    avant = iv.indicateurs_actuels(g, membres)
    return {"isoles_relies": avant["sans_relation_actuelle"] - i["sans_relation_actuelle"],
            "plus_grand_groupe": max(len(c) for c in nx.connected_components(apres.subgraph(membres))),
            "valeur_aides": sum(c.valeur for c in choix), "reciproques": sum(c.reciproque for c in choix),
            "actions": len(choix)}


def un_reseau(graine: int, n: int, k: int, plafond: int) -> dict:
    profils, m, t = generer(n, graine)
    rnd = random.Random(graine)
    ids = [p.id for p in profils]
    for _ in range(n // 10):   # quelques refus, pour que la contrainte soit exercée
        a, b = rnd.sample(ids, 2)
        m.ajouter(Evt(type="INTRO_DECLINEE", le=t - timedelta(days=5), acteurs=[a, b], statut=Statut.SIMULE, donnees={"r": graine}))
    g = reseau.graphe_actuel(m, t)
    membres = sorted(p.id for p in profils if p.type == "membre_club")
    g.add_nodes_from(membres)
    cands = iv.candidates(profils, cy.besoins_publies(m, t), TAX, g, reseau.etats_par_paire(m, t))
    ids_c = {(c.a, c.b): c for c in cands}
    choix = lambda v: [ids_c[tuple(x["paire"])] for x in iv.choisir(g, cands, k, plafond, variante=v)]  # noqa: E731
    res = {"INCLUSION": evaluer(g, membres, choix("INCLUSION")), "COHESION": evaluer(g, membres, choix("COHESION")),
           "ABLATION_V1": evaluer(g, membres, choix("V1")),
           "PREUVE_D_ABORD": evaluer(g, membres, _plafonne(sorted(cands, key=lambda c: (-c.valeur, -c.reciproque, c.a, c.b)), k, plafond)),
           "POPULAIRES": evaluer(g, membres, _plafonne(sorted(cands, key=lambda c: (-(g.degree(c.a) + g.degree(c.b)), c.a, c.b)), k, plafond))}
    tirages = []
    for s in range(30):
        o = list(cands)
        random.Random(s).shuffle(o)
        tirages.append(evaluer(g, membres, _plafonne(o, k, plafond)))
    res["HASARD"] = {key: statistics.mean(x[key] for x in tirages) for key in tirages[0]}
    res["_candidates"] = len(cands)
    res["_isoles_avant"] = iv.indicateurs_actuels(g, membres)["sans_relation_actuelle"]
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reseaux", type=int, default=20)
    ap.add_argument("--membres", type=int, default=150)
    ap.add_argument("--budget", type=int, default=10)
    ap.add_argument("--plafond", type=int, default=1)
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    runs = [un_reseau(100 + s, a.membres, a.budget, a.plafond) for s in range(a.reseaux)]
    methodes = ["INCLUSION", "COHESION", "ABLATION_V1", "PREUVE_D_ABORD", "POPULAIRES", "HASARD"]
    cles = ["isoles_relies", "plus_grand_groupe", "valeur_aides", "reciproques", "actions"]
    lignes = ["# Benchmark — intervention minimale (SYNTHETIC)", "",
              f"{a.reseaux} réseaux GÉNÉRÉS de {a.membres} membres ; budget {a.budget} actions ; plafond {a.plafond} "
              "sollicitation(s) par membre ; mêmes candidates pour toutes les méthodes. Moyennes par réseau.",
              f"Candidates par réseau : {statistics.mean(r['_candidates'] for r in runs):.1f} ; membres sans relation "
              f"actuelle avant : {statistics.mean(r['_isoles_avant'] for r in runs):.1f}.", "",
              "| Méthode | " + " | ".join(cles) + " |", "|---|" + "---|" * len(cles)]
    for meth in methodes:
        lignes.append(f"| {meth} | " + " | ".join(f"{statistics.mean(r[meth][c] for r in runs):.2f}" for c in cles) + " |")
    bases = ["PREUVE_D_ABORD", "POPULAIRES", "HASARD"]
    for meth, cle_ in (("INCLUSION", "isoles_relies"), ("COHESION", "plus_grand_groupe"),
                       ("INCLUSION", "plus_grand_groupe"), ("COHESION", "isoles_relies")):
        n = sum(r[meth][cle_] >= max(r[x][cle_] for x in bases) for r in runs)
        lignes.append(f"- {meth} ≥ la meilleure baseline sur « {cle_} » : {n}/{len(runs)} réseaux.")
    lignes += ["", "ABLATION_V1 (isolés d'abord, sans regarder à quoi on les relie) : elle relie plus d'isolés mais "
               "crée des îlots de deux ; c'est l'effet de second ordre qui a motivé la version retenue.",
               "Hypothèse : toutes les actions acceptées. Vérité : générée par nous (biais de conception possible)."]
    texte = "\n".join(lignes) + "\n"
    print(texte)
    if a.sortie:
        with open(a.sortie, "w", encoding="utf-8") as f:
            f.write(texte)


if __name__ == "__main__":
    main()
