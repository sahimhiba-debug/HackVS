"""EXP-L — Invitation ciblée (données GÉNÉRÉES, SYNTHETIC).

Même budget d'invitations, même capacité d'accueil, même juge : pour chaque méthode, le nombre MAXIMAL d'invités qui
peuvent effectivement être servis (flot maximal sur les invités qu'elle a choisis).

    python -m eval.benchmark_invitations [--reseaux 20] [--sortie eval/resultats_benchmark_invitations.md]
"""
from __future__ import annotations

import argparse
import random
import statistics
from pathlib import Path

from adaptateurs.club import cycle as cy
from adaptateurs.club import invitations as inv
from adaptateurs.club import reseau
from app.soiree import calculer_aides
from app.taxonomy import charger_taxonomie
from eval.perf_echelle import generer

TAX = charger_taxonomie()


def un_reseau(graine: int, n: int, budget: int, capacite: int, nb_presents: int = 0) -> dict:
    profils, m, t = generer(n, graine)
    g = reseau.graphe_actuel(m, t)
    ouverts = [p for p in profils if p.type == "membre_club" and p.accepte_introductions and p.disponible]
    ids = {p.id for p in ouverts}
    presents = sorted(x for x in ids if x in g and g.degree(x) > 0)
    if nb_presents:                          # petite soirée : les hôtes deviennent rares (contention)
        presents = sorted(random.Random(graine).sample(presents, min(nb_presents, len(presents))))
    invitables = sorted(x for x in ids if not (x in g and g.degree(x) > 0))
    aides = {frozenset(k) for k in calculer_aides(ouverts, cy.besoins_publies(m, t), TAX)}
    etats = reseau.etats_detailles(m, t)
    derniere = {}
    for k, v in etats.items():
        for x in k.split("|"):
            if v["derniere_interaction"] and v["derniere_interaction"] > derniere.get(x, ""):
                derniere[x] = v["derniere_interaction"]
    nb_aides = {x: sum(frozenset((x, y)) in aides for y in presents) for x in invitables}
    res = {"NOUS (flot exact)": inv.choisir(invitables, presents, aides, budget, capacite)["servis"],
           "PLUS_D_AIDES": inv.servis(sorted(invitables, key=lambda x: (-nb_aides[x], x))[:budget], presents, aides, capacite),
           "INACTIF_RECENT": inv.servis(sorted(invitables, key=lambda x: (derniere.get(x, ""), x), reverse=True)[:budget],
                                        presents, aides, capacite)}
    tir = []
    for s in range(30):
        o = list(invitables)
        random.Random(s).shuffle(o)
        tir.append(inv.servis(o[:budget], presents, aides, capacite))
    res["HASARD (30)"] = statistics.mean(tir)
    res["_invitables_avec_aide"] = sum(1 for x in invitables if nb_aides[x])
    res["_invitables"] = len(invitables)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reseaux", type=int, default=20)
    ap.add_argument("--membres", type=int, default=150)
    ap.add_argument("--budget", type=int, default=10)
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    lignes = ["# Invitation ciblée — SYNTHETIC", "",
              f"{a.reseaux} réseaux GÉNÉRÉS de {a.membres} membres ; budget {a.budget} invitations ; juge commun : flot maximal.", ""]
    for cap, nbp, b in ((1, 0, a.budget), (2, 0, a.budget), (1, 15, 15)):
        runs = [un_reseau(700 + s, a.membres, b, cap, nbp) for s in range(a.reseaux)]
        meth = [x for x in runs[0] if not x.startswith("_")]
        titre = f"petite soirée : {nbp} présents, budget {b}" if nbp else "tous les membres actifs présents"
        lignes += [f"## Capacité d'accueil : {cap} invité(s) par présent — {titre}", "",
                   f"Invitables : {statistics.mean(r['_invitables'] for r in runs):.1f} (dont avec une aide prouvée : "
                   f"{statistics.mean(r['_invitables_avec_aide'] for r in runs):.1f}).", "",
                   "| Méthode | Invités servis (moyenne) |", "|---|---|"]
        lignes += [f"| {x} | {statistics.mean(r[x] for r in runs):.2f} |" for x in meth]
        bases = [x for x in meth if not x.startswith("NOUS")]
        g = sum(r["NOUS (flot exact)"] > max(r[b] for b in bases) for r in runs)
        e = sum(r["NOUS (flot exact)"] == max(r[b] for b in bases) for r in runs)
        lignes += ["", f"NOUS contre la meilleure baseline de chaque réseau : gagne {g}, égalité {e}, perd {len(runs) - g - e}.", ""]
    lignes.append("Hypothèse : les membres actifs sont présents ; « servi » = rencontre avec une aide prouvée possible.")
    texte = "\n".join(lignes) + "\n"
    print(texte)
    if a.sortie:
        Path(a.sortie).write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
