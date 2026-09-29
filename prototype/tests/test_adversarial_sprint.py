"""Le générateur de réseaux PATHOLOGIQUES retourné contre les algorithmes du sprint : invariants, pas des scores."""
import random
from datetime import date, timedelta

import networkx as nx
import pytest

from adaptateurs.club import extinction as ex
from adaptateurs.club import pareto as pa
from adaptateurs.club import sante
from adaptateurs.club.interventions import Candidate
from eval import reseaux_pathologiques as rp

T = date(2026, 10, 1)


def _candidates(r, graine, n=80):
    rnd = random.Random(graine)
    m, g = r["membres"], r["g_act"]
    vus, res = set(), []
    while len(res) < n:
        a, b = sorted(rnd.sample(m, 2))
        if (a, b) not in vus and not g.has_edge(a, b):
            vus.add((a, b))
            res.append(Candidate("INTRODUCTION", a, b, rnd.choice([0.5, 1.0]), rnd.random() < 0.3))
    return res


@pytest.mark.parametrize("nom", rp.PATHOLOGIES + ["SAIN"])
def test_pareto_sur_reseaux_pathologiques(nom):
    r = rp.sain(3) if nom == "SAIN" else rp.pathologique(nom, 3)
    cands = _candidates(r, 7)
    f1 = pa.frontiere(r["g_act"], r["membres"], cands, k=6)
    assert f1 == pa.frontiere(r["g_act"], r["membres"], cands, k=6)                  # déterministe
    permis = {(c.a, c.b) for c in cands}
    objs = [p["objectifs"] for p in f1["front"]]
    assert objs and all(not pa.domine(u, v) for u in objs for v in objs)
    for p in f1["front"]:
        assert all(tuple(x) in permis for x in p["paires"])                            # rien d'inventé
        vus = [y for x in p["paires"] for y in x]
        assert len(vus) == len(set(vus))                                               # plafond 1, même pour un hub


@pytest.mark.parametrize("nom", rp.PATHOLOGIES)
def test_prevention_sur_reseaux_pathologiques(nom):
    r = rp.pathologique(nom, 4)
    rnd = random.Random(4)
    ech = {"|".join(sorted(e)): T + timedelta(days=rnd.randint(1, 60)) for e in r["g_act"].edges()}
    for v in ("INCLUSION", "COHESION"):
        choix = ex.prevenir(r["g_act"], r["membres"], ech, T, 30, k=5, plafond=2, variante=v)
        assert all(ech[x] <= T + timedelta(days=30) for x in choix)                     # seulement des relations menacées
        compte = {}
        for x in choix:
            for y in x.split("|"):
                compte[y] = compte.get(y, 0) + 1
        assert all(c <= 2 for c in compte.values())


def test_cas_minimaux_sans_plantage():
    vide = nx.Graph()
    assert sante.phenomenes(vide, vide, [])["phenomenes"] == []
    assert pa.frontiere(vide, ["a"], [], k=3)["decision"] == "NE_RIEN_FAIRE"
    assert ex.prevenir(vide, ["a"], {}, T, 30, k=3) == []
    g = nx.Graph([("a", "b")])
    assert pa.plus_grand_groupe_robuste(g, ["a", "b"]) == 1
    assert pa.frontiere(g, ["a", "b", "c"], [Candidate("INTRODUCTION", "b", "c", 1, True)], k=3)["front"]
