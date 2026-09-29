"""Échelle d'impact : définitions sur les faits, cumulativité, séparation simulé / réel. Données FICTIVES."""
import random
from datetime import date, timedelta

from adaptateurs.club import impact
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

J0 = date(2026, 1, 5)


def _e(m, typ, j, a="a", b="b", st=Statut.DECLARE, **d):
    m.ajouter(Evt(type=typ, le=J0 + timedelta(days=j), acteurs=[a, b], statut=st, donnees=d))


def test_chaque_niveau_sur_un_historique_ecrit_a_la_main():
    m = Memoire()
    _e(m, "RENCONTRE", 0, st=Statut.SIMULE)                         # contact simulé seulement
    _e(m, "RENCONTRE", 0, "c", "d", Statut.SIMULE)
    _e(m, "RENCONTRE_CONFIRMEE", 1, "c", "d")                       # connexion réelle
    _e(m, "INTRO_ACCEPTEE", 0, "e", "f")
    _e(m, "RESULTAT", 20, "e", "f", resultat="affaire_en_cours")    # activation, pas persistance (20 jours)
    _e(m, "INTRO_ACCEPTEE", 0, "g", "h")
    _e(m, "RESULTAT", 30, "g", "h", resultat="utile")
    _e(m, "SUIVI", 100, "g", "h")                                   # persistance : étalé ≥ 90 j et actuel
    e = impact.entonnoir(m, J0 + timedelta(days=120))
    n = e["niveaux"]
    assert n["CONTACT"] == {"reel": 3, "simule_seulement": 1}
    assert n["CONNEXION"] == {"reel": 3, "simule_seulement": 0}
    assert n["ACTIVATION"]["reel"] == 2 and n["PERSISTANCE"]["reel"] == 1


def test_une_relation_activee_puis_endormie_n_est_pas_persistante():
    m = Memoire()
    _e(m, "INTRO_ACCEPTEE", 0)
    _e(m, "RESULTAT", 100, resultat="utile")
    assert impact.entonnoir(m, J0 + timedelta(days=150))["niveaux"]["PERSISTANCE"]["reel"] == 1
    assert impact.entonnoir(m, J0 + timedelta(days=200))["niveaux"]["PERSISTANCE"]["reel"] == 0   # > 90 j sans interaction


def test_pas_pertinent_n_est_pas_une_activation_et_l_effet_reseau_est_compte():
    m = Memoire()
    _e(m, "INTRO_ACCEPTEE", 0)
    _e(m, "RESULTAT", 5, resultat="pas_pertinent")
    _e(m, "SUIVI", 0, "v", "x")
    m.ajouter(Evt(type="OPPORTUNITE_OUVERTE", le=J0 + timedelta(days=10), acteurs=["x", "z"], statut=Statut.INFERE,
                  donnees={"via": "v"}))
    e = impact.entonnoir(m, J0 + timedelta(days=20))
    assert e["niveaux"]["ACTIVATION"]["reel"] == 0
    assert e["effet_reseau"]["reel"] == 1                           # la relation v–x a servi d'appui


def test_propriete_entonnoir_non_croissant_sur_historiques_aleatoires():
    types = ["RENCONTRE", "RENCONTRE_CONFIRMEE", "INTRO_ACCEPTEE", "SUIVI", "RESULTAT", "INTRO_DECLINEE"]
    for graine in range(60):
        rnd = random.Random(graine)
        m = Memoire()
        for k in range(rnd.randint(1, 30)):
            a, b = rnd.sample("abcdef", 2)
            t = rnd.choice(types)
            d = {"resultat": rnd.choice(["utile", "affaire_en_cours", "pas_pertinent"])} if t == "RESULTAT" else {"k": k}
            m.ajouter(Evt(type=t, le=J0 + timedelta(days=rnd.randint(0, 200)), acteurs=[a, b],
                          statut=rnd.choice([Statut.SIMULE, Statut.DECLARE]), donnees=d))
        n = impact.entonnoir(m, J0 + timedelta(days=rnd.randint(0, 300)))["niveaux"]
        tot = [n[x]["reel"] + n[x]["simule_seulement"] for x in impact.NIVEAUX]
        assert tot == sorted(tot, reverse=True), (graine, tot)
        reels = [n[x]["reel"] for x in impact.NIVEAUX]
        assert reels == sorted(reels, reverse=True), (graine, reels)
