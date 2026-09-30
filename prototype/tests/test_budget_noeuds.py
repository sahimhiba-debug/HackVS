"""BUDGET DE NŒUDS du compositeur (`Banc.BUDGET_NOEUDS`). (1) Le monde de démonstration reste LARGEMENT sous le budget,
mesuré (pic observé `noeuds_max`), sur tout ce que la démo joue : le registre (scénario A, retrait, recomposition) et
l'action collective guidée jusqu'à +30 jours. (2) L'état « budget atteint » se déclenche exprès et se VOIT. Données FICTIVES."""
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo

TAX = charger_taxonomie()
A = "delegation_acheteurs"


def test_le_monde_de_demo_reste_largement_sous_le_budget():
    d = Demo(TAX)
    c = d.club
    c.projection_capacites()
    c.repondre_ask(md.PAULINE, c.asks_pour(md.PAULINE)[0][1], True, {"places": 14})     # scénario A (vendredi 09.10)
    c.projection_capacites()
    c.retirer_consentement(md.PAULINE, A)                                              # retrait → recomposition
    c.projection_capacites()
    c.repondre_ask(md.MARKUS, c.asks_pour(md.MARKUS)[0][1], True, {"places": 20})
    assert next(i.statut for i in c.projection_capacites() if i.finalite == A) == "ACTIVE"
    registre = c.banc.noeuds_max
    d.rejouer(len(d.ETAPES))                                                           # l'action collective guidée, jusqu'à +30 j
    d.club.projection_capacites()
    for banc in (c.banc, d.club.banc):
        assert banc.recherches_tronquees == 0
        assert 0 < banc.noeuds_max <= banc.BUDGET_NOEUDS // 100, (registre, d.club.banc.noeuds_max)   # marge ≥ ×100
