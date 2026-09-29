"""Mémoire des interventions : comptes après intervention, contexte, simulé à part, pas de taux sur petits nombres."""
from datetime import date, timedelta

from adaptateurs.club import bilan
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

J0 = date(2026, 3, 2)


def _e(m, typ, j, a, b, st=Statut.DECLARE, **d):
    m.ajouter(Evt(type=typ, le=J0 + timedelta(days=j), acteurs=[a, b], statut=st, donnees=d))


def _groupe(b, typ, ctx):
    return next(g for g in b["groupes"] if g["type"] == typ and g["contexte"] == ctx)


def test_bilan_par_type_et_contexte():
    m = Memoire()
    deux_sens = [{"qui_est_aide": "a", "qui_aide": "b"}, {"qui_est_aide": "b", "qui_aide": "a"}]
    _e(m, "RENCONTRE", 0, "a", "b", Statut.SIMULE, run_id="r1", raisons=deux_sens)
    _e(m, "RENCONTRE", 0, "c", "d", Statut.SIMULE, run_id="r1", raisons=[{"qui_est_aide": "c", "qui_aide": "d"}])
    _e(m, "RENCONTRE_CONFIRMEE", 2, "a", "b")
    _e(m, "RESULTAT", 30, "a", "b", resultat="utile")                     # la table « deux sens » a produit un résultat
    _e(m, "RELANCE_ACCEPTEE", 40, "c", "d", raison="NOUVEAU_BESOIN", relance_id="x")
    _e(m, "SUIVI", 40, "c", "d", relance_id="x")
    _e(m, "RELANCE_REFUSEE", 40, "e", "f", raison="NOUVEAU_BESOIN", relance_id="y")
    b = bilan.bilan(m, J0 + timedelta(days=60))
    t2 = _groupe(b, "TABLE_SOIREE", "aide dans les deux sens")
    assert t2["interventions"] == 1 and t2["apres"]["ACTIVATION"]["reel"] == 1
    t1 = _groupe(b, "TABLE_SOIREE", "aide dans un seul sens")
    assert t1["apres"]["CONTACT"] == {"reel": 1, "simule_seulement": 0} and t1["apres"]["ACTIVATION"]["reel"] == 0
    r = _groupe(b, "RELANCE", "NOUVEAU_BESOIN")
    assert r["interventions"] == 2 and r["refusees"] == 1 and r["apres"]["CONNEXION"]["reel"] == 1
    assert not any(g["taux_affichables"] for g in b["groupes"])           # jamais de taux sur 1 ou 2 cas


def test_une_table_simulee_sans_suite_ne_produit_que_du_simule():
    m = Memoire()
    _e(m, "RENCONTRE", 0, "a", "b", Statut.SIMULE, run_id="r1", raisons=[])
    g = _groupe(bilan.bilan(m, J0 + timedelta(days=10)), "TABLE_SOIREE", "sans aide documentée")
    assert g["apres"]["CONTACT"] == {"reel": 0, "simule_seulement": 1}
    assert all(g["apres"][n]["reel"] == 0 for n in ("CONNEXION", "ACTIVATION", "PERSISTANCE"))


def test_un_resultat_anterieur_a_l_intervention_ne_lui_est_pas_attribue():
    m = Memoire()
    _e(m, "INTRO_ACCEPTEE", 0, "a", "b")
    _e(m, "RESULTAT", 5, "a", "b", resultat="utile")
    _e(m, "RENCONTRE", 50, "a", "b", Statut.SIMULE, run_id="r2", raisons=[])
    g = _groupe(bilan.bilan(m, J0 + timedelta(days=60)), "TABLE_SOIREE", "sans aide documentée")
    assert g["apres"]["ACTIVATION"] == {"reel": 0, "simule_seulement": 0}


def test_taux_affiche_seulement_a_partir_de_dix_interventions():
    m = Memoire()
    for i in range(10):
        _e(m, "RENCONTRE", 0, f"a{i}", f"b{i}", Statut.SIMULE, run_id="r1", raisons=[])
        if i < 3:
            _e(m, "RESULTAT", 20, f"a{i}", f"b{i}", resultat="utile")
    g = _groupe(bilan.bilan(m, J0 + timedelta(days=30)), "TABLE_SOIREE", "sans aide documentée")
    assert g["taux_affichables"] and g["taux_activation_reelle"] == 0.3
