"""Boucle fermée prévu / réalisé : faits réels seulement, réseau reconstruit à la date de décision, rejouable."""
from datetime import date, timedelta

import pytest

from adaptateurs.club import boucle
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

J0 = date(2026, 10, 1)
MEMBRES = ["a", "b", "c", "d", "e", "f"]


def _monde():
    m = Memoire()
    for x, y in (("a", "b"), ("b", "c")):
        m.ajouter(Evt(type="RENCONTRE", le=J0 - timedelta(days=10), acteurs=[x, y], statut=Statut.DECLARE))
    plan = {"noms": ["INCLUSION"], "paires": [["c", "d"], ["e", "f"], ["a", "e"], ["b", "f"]],
            "objectifs": {"inclusion": 3, "cohesion": 6, "reciprocite": 0}}
    dec = boucle.enregistrer(m, J0, plan, "org", MEMBRES)
    return m, dec


def _e(m, typ, j, x, y, st=Statut.DECLARE, **d):
    m.ajouter(Evt(type=typ, le=J0 + timedelta(days=j), acteurs=[x, y], statut=st, donnees=d))


def test_prevu_contre_realise_sur_faits_reels_seulement():
    m, dec = _monde()
    _e(m, "INTRO_ACCEPTEE", 5, "c", "d")                       # réalisée (fait réel)
    _e(m, "RENCONTRE", 6, "e", "f", Statut.SIMULE)             # simulée seulement : pas un résultat
    _e(m, "INTRO_DEMANDEE", 7, "a", "e", r=1)
    _e(m, "INTRO_DECLINEE", 8, "a", "e", r=1)                  # refusée
    ec = boucle.ecart(m, dec, J0 + timedelta(days=30), MEMBRES)  # b–f : rien
    assert ec["comptes"] == {"REALISEE": 1, "REFUSEE": 1, "SIMULEE_SEULEMENT": 1, "REMPLACEE": 0, "SANS_SUITE_OBSERVEE": 1}
    assert ec["prevu"]["inclusion"] == 3 and ec["realise"]["inclusion"] == 1     # seul d a été relié pour de vrai
    assert ec["realise"]["cohesion"] == 4                                          # a-b-c-d


def test_un_fait_anterieur_a_la_decision_n_est_pas_un_resultat():
    m = Memoire()
    _e(m, "INTRO_ACCEPTEE", -5, "c", "d")
    dec = boucle.enregistrer(m, J0, {"paires": [["c", "d"]], "objectifs": {}}, "org", MEMBRES)
    assert boucle.ecart(m, dec, J0 + timedelta(days=10), MEMBRES)["comptes"]["REALISEE"] == 0


def test_enregistrement_refuse_un_plan_vide_ou_invalide():
    m = Memoire()
    for plan in ({"paires": []}, {"paires": [["a", "a"]]}, {"paires": [["a", "inconnu"]]}):
        with pytest.raises(boucle.ErreurDecision):
            boucle.enregistrer(m, J0, plan, "org", MEMBRES)
    assert not m.evenements("DECISION_ORGANISATION")


def test_historique_pas_de_taux_sous_dix_et_rejeu_identique():
    m, dec = _monde()
    _e(m, "INTRO_ACCEPTEE", 5, "c", "d")
    h1 = boucle.historique(m, J0 + timedelta(days=30), MEMBRES)
    h2 = boucle.historique(m, J0 + timedelta(days=30), MEMBRES)
    assert h1 == h2 and h1["actions"] == 4 and h1["taux_realisation"] is None
    assert h1["comptes"]["REALISEE"] == 1


def test_un_refus_suivi_d_une_connexion_reelle_est_une_action_realisee():
    m, dec = _monde()
    _e(m, "INTRO_DEMANDEE", 2, "c", "d", r=1)
    _e(m, "INTRO_DECLINEE", 3, "c", "d", r=1)
    _e(m, "INTRO_DEMANDEE", 10, "c", "d", r=2)
    _e(m, "INTRO_ACCEPTEE", 11, "c", "d", r=2)
    issues = {tuple(x["paire"]): x["issue"] for x in boucle.ecart(m, dec, J0 + timedelta(days=30), MEMBRES)["actions"]}
    assert issues[("c", "d")] == "REALISEE"


def test_api_decision_n_accepte_que_des_actions_proposables_puis_prevu_realise():
    from fastapi.testclient import TestClient

    from app import main
    c = TestClient(main.app)
    c.post("/api/demo/reinitialiser")
    d = c.get("/api/reseau/diagnostic?k=3").json()
    front = d["agir"]["front"]
    assert front, "la démo doit proposer au moins un plan"
    plan = front[0]
    ferme = next(p.id for p in main.profils_effectifs() if p.type == "membre_club" and not p.accepte_introductions)
    autre = next(x for x in plan["paires"][0] if x != ferme)
    assert c.post("/api/reseau/decision", json={"paires": [[ferme, autre]]}).status_code == 409   # consentement
    assert c.post("/api/reseau/decision", json={"paires": []}).status_code == 422                  # plan vide
    ok = c.post("/api/reseau/decision", json={"paires": plan["paires"], "objectifs": plan["objectifs"]})
    assert ok.status_code == 200
    h = c.get("/api/reseau/decisions").json()
    assert h["decisions"] == 1 and h["comptes"]["REALISEE"] == 0 and h["taux_realisation"] is None


def test_un_resultat_n_est_attribue_qu_a_la_decision_la_plus_recente_pour_cette_paire():
    """Défaut trouvé par EXP-N : une paire décidée deux fois (mois 1 sans suite, mois 2 acceptée) était créditée aux DEUX
    décisions — le bilan comptait plus de réalisations que d'acceptations."""
    m = Memoire()
    d1 = boucle.enregistrer(m, J0, {"paires": [["c", "d"]], "objectifs": {}}, "org", MEMBRES)
    d2 = boucle.enregistrer(m, J0 + timedelta(days=30), {"paires": [["c", "d"]], "objectifs": {"inclusion": 1}}, "org", MEMBRES)
    _e(m, "INTRO_ACCEPTEE", 33, "c", "d")
    fin = J0 + timedelta(days=60)
    assert boucle.ecart(m, d1, fin, MEMBRES)["actions"][0]["issue"] == "REMPLACEE"
    assert boucle.ecart(m, d2, fin, MEMBRES)["actions"][0]["issue"] == "REALISEE"
    assert boucle.historique(m, fin, MEMBRES)["comptes"]["REALISEE"] == 1


def test_integrite_de_la_boucle_sur_plusieurs_mois_le_bilan_retrouve_exactement_les_acceptations():
    from eval.simulation_boucle import jouer
    r = jouer(1100, 2, 0.5)
    assert r["decisions"] == 2 and r["realisees_selon_bilan"] == r["acceptees"]
