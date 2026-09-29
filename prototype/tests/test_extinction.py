"""EXP-F : échéancier d'extinction et prévention. Graphes construits à la main (vérité connue)."""
from datetime import date, timedelta

import networkx as nx

from adaptateurs.club import extinction as ex

T = date(2026, 10, 1)


def _monde():
    """Deux triangles reliés par un pont a3–b1 qui s'éteint dans 10 jours ; x relié seulement par x–a1 (dans 20 jours) ;
    une arête de triangle a1–a2 s'éteint aussi (redondante : a1 et a2 restent reliés via a3)."""
    g = nx.Graph([("a1", "a2"), ("a2", "a3"), ("a1", "a3"), ("b1", "b2"), ("b2", "b3"), ("b1", "b3"), ("a3", "b1"), ("x", "a1")])
    loin = T + timedelta(days=80)
    ech = {"|".join(sorted(e)): loin for e in g.edges()}
    ech["a3|b1"], ech["a1|x"], ech["a1|a2"] = T + timedelta(days=10), T + timedelta(days=20), T + timedelta(days=5)
    return g, sorted(g.nodes), ech


def test_projection_chronologique_et_sans_prediction():
    g, m, ech = _monde()
    final, chrono = ex.projeter(g, m, ech, T, 30)
    assert not final.has_edge("a3", "b1") and not final.has_edge("a1", "x") and final.has_edge("a2", "a3")
    types = {c["le"]: {e["type"] for e in c["evenements"]} for c in chrono}
    assert "PONT_DISPARU" in types[(T + timedelta(days=10)).isoformat()]
    assert "MEMBRE_ISOLE" in types[(T + timedelta(days=20)).isoformat()]
    assert ex.projeter(g, m, ech, T, 3)[1] == []                  # rien ne s'éteint avant 3 jours : aucun événement


def test_chaque_variante_ravive_ce_qui_compte_pour_elle_et_rien_de_superflu():
    g, m, ech = _monde()
    assert ex.prevenir(g, m, ech, T, 30, k=1, variante="INCLUSION") == ["a1|x"]      # x perdrait toute relation
    assert ex.prevenir(g, m, ech, T, 30, k=1, variante="COHESION") == ["a3|b1"]      # le réseau se couperait
    tout = ex.prevenir(g, m, ech, T, 30, k=5, plafond=3)
    assert "a1|a2" not in tout and len(tout) == 2                 # l'arête redondante n'est jamais ravivée : intervention minimale


def test_echeancier_distingue_raison_prouvee_et_invitation():
    g, m, ech = _monde()
    e = ex.echeancier(g, m, ech, T, horizon=30, k=2, plafond=3, aides={"a1|x"})
    actions = {"|".join(r["paire"]): r for r in e["ravivements"]}
    assert actions["a1|x"]["raison_prouvee"] is True and "relance" in actions["a1|x"]["action"]
    assert actions["a3|b1"]["raison_prouvee"] is False and "pas de relance" in actions["a3|b1"]["action"]
    assert e["sans_action"]["premiere_perte"] == (T + timedelta(days=10)).isoformat()
    assert e["avec_ravivements"]["a_l_horizon"]["sans_relation_actuelle"] < e["sans_action"]["a_l_horizon"]["sans_relation_actuelle"]
