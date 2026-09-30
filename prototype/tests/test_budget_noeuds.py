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


BORNEE = "recherche bornée atteinte : une composition a pu échapper au calcul (absence non garantie)"


def _borne(budget: int):
    c = Demo(TAX).club
    c.banc.BUDGET_NOEUDS = budget                                   # déclenché EXPRÈS : le budget est plus petit que le besoin
    return c


def test_budget_atteint_la_capacite_reste_affichee_et_le_dit():
    """Budget épuisé avant toute composition : la capacité n'a pas de statut calculable. Elle ne DISPARAÎT pas de
    l'écran (ce serait un « impossible » silencieux) : elle est montrée, marquée incertaine, et l'animation le voit."""
    c = _borne(1)
    v = c.vues_capacites.console()
    carte = next((x for x in v["capacites"] if x["finalite"] == A), None)
    assert carte is not None, "capacité à la recherche tronquée absente de l'écran"
    assert carte["recherche_bornee"] is True and carte["statut"] is None
    assert carte["statut_libelle"] == "état incertain : recherche bornée atteinte"
    assert BORNEE in carte["hypotheses"]
    assert "Accueillir une délégation d'acheteurs germanophones (recherche bornée : à vérifier)" in v["attention"]["decision"]


def test_budget_atteint_apres_une_composition_partielle_est_dit_aussi():
    c = _borne(3)                                                   # assez pour une capacité, pas pour toutes les recherches
    v = c.vues_capacites.console()
    bornees = [x for x in v["capacites"] if x["recherche_bornee"]]
    assert bornees and all(BORNEE in x["hypotheses"] for x in bornees)
    assert c.banc.recherches_tronquees > 0


def test_sous_le_budget_rien_n_est_dit():
    v = Demo(TAX).club.vues_capacites.console()
    assert not any(x["recherche_bornee"] for x in v["capacites"])
    assert not any("recherche bornée" in d for d in v["attention"]["decision"])


def test_le_budget_se_regle_par_l_environnement():
    from intelligence.reglages import Reglages
    assert Reglages.depuis_env({}).budget_noeuds == 20_000
    assert Reglages.depuis_env({"HACKVS_BUDGET_NOEUDS": "7"}).budget_noeuds == 7
