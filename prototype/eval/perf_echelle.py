"""Montée en charge : 50 → 5000 membres (données GÉNÉRÉES, SYNTHETIC).

Mesure le temps des opérations du parcours réel sur une mémoire et des profils générés : lecture de la mémoire,
graphe, graphe actuel, état d'une relation, recherche d'un besoin, cartes (dimensions) des candidats, boîte réseau,
relances, opportunités. Aucune valeur n'est inventée : le tableau est produit par ce script.

    python -m eval.perf_echelle [--tailles 50,150,500,1000,5000] [--sortie eval/resultats_perf_echelle.md]
"""
from __future__ import annotations

import argparse
import json
import random
import resource
import time
from datetime import date, timedelta
from pathlib import Path

from adaptateurs.club import cycle as cy
from adaptateurs.club import reseau
from app.matching import rechercher
from app.models import Profil
from app.parser_rules import analyser
from app.taxonomy import DATA_DIR, charger_taxonomie
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire, graphe

TAX = charger_taxonomie()
BASE = json.loads((DATA_DIR / "profils_demo.json").read_text(encoding="utf-8"))["profils"]
J0 = date(2026, 10, 3)
BESOIN = "Nous cherchons un agent commercial pour placer nos jus dans les épiceries fines de Berne cet automne"


def generer(n: int, graine: int = 7) -> tuple[list[Profil], Memoire, date]:
    """n membres (profils de démo recopiés avec de nouveaux identifiants), ~4 rencontres par membre sur 300 jours,
    un suivi pour 1 rencontre sur 4, une introduction pour 1 membre sur 5, 1 besoin publié pour 1 membre sur 10."""
    rnd = random.Random(graine)
    profils = []
    for i in range(n):
        d = dict(BASE[i % len(BASE)])
        d.update(id=f"g{i:05d}", nom=f"Membre {i}", accepte_introductions=rnd.random() > 0.1)
        profils.append(Profil(**d))
    m = Memoire()
    ids = [p.id for p in profils]
    for _ in range(2 * n):                         # 2n arêtes ≈ 4 rencontres par membre
        a, b = rnd.sample(ids, 2)
        j = rnd.randint(0, 300)
        m.ajouter(Evt(type="RENCONTRE", le=J0 + timedelta(days=j), acteurs=sorted([a, b]), statut=Statut.SIMULE,
                      donnees={"evenement": f"soirée {j // 30}"}))
        if rnd.random() < 0.25:
            m.ajouter(Evt(type="SUIVI", le=J0 + timedelta(days=j + 12), acteurs=sorted([a, b]), statut=Statut.SIMULE))
    for i in range(0, n, 5):
        a, b = rnd.sample(ids, 2)
        m.ajouter(Evt(type="INTRO_DEMANDEE", le=J0 + timedelta(days=rnd.randint(0, 300)), acteurs=[a, b],
                      statut=Statut.SIMULE, donnees={"relation_id": f"r{i}"}))
    for i in range(0, n, 10):
        cy.publier_besoin(m, ids[i], BESOIN, J0 + timedelta(days=rnd.randint(0, 300)), TAX, Statut.SIMULE)
    return profils, m, J0 + timedelta(days=310)


def _t(f):
    t0 = time.perf_counter()
    r = f()
    return round((time.perf_counter() - t0) * 1000, 1), r


def mesurer(n: int, relances: bool = True) -> dict:
    profils, m, t = generer(n)
    par_id = {p.id: p for p in profils}
    moi = profils[0]
    res = {"membres": n, "evenements": len(m.evenements())}
    res["lecture_memoire_ms"], _ = _t(lambda: m.evenements())
    res["graphe_ms"], g = _t(lambda: graphe(m, t))
    res["graphe_actuel_ms"], ga = _t(lambda: reseau.graphe_actuel(m, t))
    res["liens"], res["liens_actuels"] = g.number_of_edges(), ga.number_of_edges()
    a, b = next(iter(g.edges()))
    res["etat_relation_ms"], _ = _t(lambda: reseau.etat_relation(m, a, b, t))
    besoin = analyser(BESOIN, TAX)
    res["recherche_ms"], r = _t(lambda: rechercher(besoin, moi, profils, TAX))
    gc = reseau.graphe_de_confiance(m, t)
    sugg = [s.model_dump() for s in r.suggestions]
    res["cartes_ms"], _ = _t(lambda: [reseau.dimensions(m, moi, s, par_id, t, None, gc, TAX, []) for s in sugg])
    res["boite_ms"], _ = _t(lambda: reseau.boite(m, moi, profils, [], {}, t))
    res["opportunites_ms"], _ = _t(lambda: cy.opportunites(m, profils, TAX, t))
    if relances:
        res["relances_ms"], _ = _t(lambda: cy.relances(m, profils, TAX, t))
    res["rss_max_processus_mo"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)  # cumulatif
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tailles", default="50,150,500,1000,5000")
    ap.add_argument("--sans-relances-au-dela", type=int, default=1000)
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    lignes = []
    for n in [int(x) for x in a.tailles.split(",")]:
        r = mesurer(n, relances=n <= a.sans_relances_au_dela)
        print(json.dumps(r), flush=True)
        lignes.append(r)
    if a.sortie:
        cols = list(dict.fromkeys(k for r in lignes for k in r))
        md = ["# Montée en charge — données GÉNÉRÉES (SYNTHETIC), une machine, un seul processus", "",
              "Produit par `python -m eval.perf_echelle`. Temps en millisecondes (une exécution, pas une moyenne).", "",
              "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        md += ["| " + " | ".join(str(r.get(c, "non mesuré")) for c in cols) + " |" for r in lignes]
        Path(a.sortie).write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
