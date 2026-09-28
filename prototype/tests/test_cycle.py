"""Cycle des relations : soirée → rencontres → +10 jours → pourquoi reprendre contact ? → suivi → opportunité →
soirée suivante. Données FICTIVES ; horloge simulée ; aucun LLM, aucun réseau."""
import json
from datetime import date

import pytest

from adaptateurs.club import cycle as cy
from adaptateurs.club.adaptateur import AdaptateurClub
from app.models import Profil
from app.taxonomy import DATA_DIR, charger_taxonomie
from plateforme import action as ac
from plateforme import memoire as me
from plateforme import pipeline as pl
from plateforme.affirmations import Statut
from plateforme.execution import Journal

TAX = charger_taxonomie()
P = [Profil(**p) for p in json.loads((DATA_DIR / "profils_demo.json").read_text(encoding="utf-8"))["profils"]]
J0 = date(2026, 10, 3)
BESOIN = "Nous cherchons un agent commercial pour placer nos jus dans les épiceries fines de Berne cet automne"


def _monde():
    m, j = me.Memoire(), Journal()

    def fournisseur():
        t = m.maintenant(J0)
        return P, cy.besoins_publies(m, t), cy.relations(m, t), "demo", cy.opportunites(m, P, TAX, t)
    return m, j, AdaptateurClub(fournisseur, TAX)


def _soiree(m, j, ad, demande="tout le monde au moins une rencontre utile, et les opportunités ouvertes, 3 tours", nom="Soirée"):
    r = pl.executer(ad, demande, j, sensibilite=False)
    ac.decider(j, r.run_id, ac.DecisionHumaine(verdict="APPROUVER", par="org"))
    cy.enregistrer_soiree(m, j, r.run_id, nom, m.maintenant(J0))
    return r


@pytest.fixture(scope="module")
def cycle_complet():
    m, j, ad = _monde()
    r1 = _soiree(m, j, ad, nom="Soirée 1")
    avant = cy.relances(m, P, TAX, m.avancer(9, J0))
    sans_rien = cy.relances(m, P, TAX, m.avancer(1, J0))
    return m, j, ad, r1, avant, sans_rien


def test_soiree_uniquement_depuis_un_plan_approuve():
    m, j, ad = _monde()
    r = pl.executer(ad, "des rencontres utiles", j, sensibilite=False)
    with pytest.raises(cy.ErreurCycle):
        cy.enregistrer_soiree(m, j, r.run_id, "S", J0)
    ac.decider(j, r.run_id, ac.DecisionHumaine(verdict="APPROUVER", par="org"))
    cy.enregistrer_soiree(m, j, r.run_id, "S", J0)
    with pytest.raises(cy.ErreurCycle):
        cy.enregistrer_soiree(m, j, r.run_id, "S", J0)
    liens = me.graphe(m).edges(data=True)
    assert len(liens) == len(r.retenue["rencontres"]) and all(d["statut"] == Statut.SIMULE for *_, d in liens)


def test_pas_de_relance_avant_dix_jours_ni_sans_raison_nouvelle(cycle_complet):
    _, _, _, r1, avant, sans_rien = cycle_complet
    assert not avant["propositions"] and avant["abstentions"]["trop_tot"] == len(r1.retenue["rencontres"])
    assert not sans_rien["propositions"] and sans_rien["abstentions"]["rien_de_nouveau"] == len(r1.retenue["rencontres"])


def test_confirmation_par_un_des_deux_seulement(cycle_complet):
    m, *_ = cycle_complet
    a, b = sorted(me.graphe(m).edges())[0]
    autre = next(p.id for p in P if p.id not in (a, b))
    with pytest.raises(cy.ErreurCycle):
        cy.confirmer_rencontre(m, a, b, autre, m.maintenant(J0))


def test_boucle_complete_jusqu_a_la_soiree_suivante():
    m, j, ad = _monde()
    r1 = _soiree(m, j, ad, nom="Soirée 1")
    assert any({a, b} == {"p00", "p32"} for _, a, b in r1.retenue["rencontres"])     # Sophie rencontre Reto
    cy.publier_besoin(m, "p00", BESOIN, m.avancer(6, J0), TAX, Statut.SIMULE)
    rel = cy.relances(m, P, TAX, m.avancer(4, J0))
    assert len(rel["propositions"]) == 1
    p = rel["propositions"][0]
    r = p["raisons"][0]
    assert p["paire"] == ["p00", "p32"] and r["type"] == "NOUVEAU_BESOIN"
    offre_reto = next(x for x in P if x.id == "p32").offre[0].texte
    assert any(x["extrait"] == offre_reto for x in r["preuves"])                        # preuve citée mot pour mot
    assert r["preuves"][0]["statut"] == "SIMULE"                                        # le besoin du scénario est dit simulé
    with pytest.raises(cy.ErreurCycle):
        cy.repondre(m, P, TAX, m.maintenant(J0), r["id"], True, "p06")                   # un tiers ne répond pas
    assert cy.repondre(m, P, TAX, m.maintenant(J0), r["id"], True, "p00")["suivi"]
    assert not cy.relances(m, P, TAX, m.maintenant(J0))["propositions"]                  # jamais reproposée
    opps = cy.opportunites(m, P, TAX, m.maintenant(J0))
    assert [(o["a"], o["c"], o["via"]) for o in opps] == [("p00", "p06", "p32")]         # Grégoire, via Reto
    m.avancer(20, J0)
    r2 = _soiree(m, j, ad, nom="Soirée 2")
    inst = j.instantane(r2.instantane_empreinte)
    assert inst["opportunites"]["p00|p06"]["via"] == "p32"
    aff = next(a for a in inst["affirmations"] if a["predicat"] == "opportunite_ouverte")
    assert aff["statut"] == "INFERE"
    paires1 = {frozenset((a, b)) for _, a, b in r1.retenue["rencontres"]}
    paires2 = {frozenset((a, b)) for _, a, b in r2.retenue["rencontres"]}
    assert frozenset(("p00", "p06")) in paires2 and not paires1 & paires2               # réalisée ; aucune répétition
    assert not [v for v in r2.verdicts if v["etat"] == "FAIL"]
    c = me.croissance(m)
    assert [x["apres"] for x in c] == ["Soirée 1", "Soirée 2"] and c[1]["liens"] > c[0]["liens"]
    assert c[1]["portee_moyenne_2_sauts"] > c[0]["portee_moyenne_2_sauts"]


def test_relance_refusee_n_insiste_pas():
    m, j, ad = _monde()
    _soiree(m, j, ad)
    cy.publier_besoin(m, "p00", BESOIN, m.avancer(6, J0), TAX, Statut.SIMULE)
    r = cy.relances(m, P, TAX, m.avancer(4, J0))["propositions"][0]["raisons"][0]
    assert cy.repondre(m, P, TAX, m.maintenant(J0), r["id"], False, "p00") == {"suivi": False}
    assert not cy.relances(m, P, TAX, m.avancer(30, J0))["propositions"]
    assert not cy.opportunites(m, P, TAX, m.maintenant(J0))                             # pas de suivi → pas d'opportunité


def test_memoire_idempotente_et_rejouable():
    m1, m2 = me.Memoire(), me.Memoire()
    e = me.Evt(type="RENCONTRE", le=J0, acteurs=["a", "b"], statut=Statut.SIMULE)
    m1.ajouter(e), m1.ajouter(e)
    assert len(m1.evenements()) == 1
    for x in m1.evenements():
        m2.ajouter(x)
    assert m1.empreinte() == m2.empreinte()
    assert me.force(J0, J0) == 1.0 and me.force(J0, date(2026, 11, 2)) == 0.5


def test_api_cycle(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.cycle_api import creer_routeur
    app = FastAPI()
    app.include_router(creer_routeur(lambda: P, TAX, ":memory:"))
    c = TestClient(app)
    plan = c.post("/api/cycle/soiree", json={}).json()
    rid = plan["run"]["run_id"]
    assert c.post(f"/api/cycle/soiree/{rid}/approuver", json={}).json()["rencontres"] > 0
    assert c.post(f"/api/cycle/soiree/{rid}/approuver", json={}).status_code == 409
    c.post("/api/cycle/avancer", json={"jours": 6})
    assert c.post("/api/cycle/besoin", json={"auteur": "p00", "texte": BESOIN}).json()["statut"] == "SIMULE"
    c.post("/api/cycle/avancer", json={"jours": 4})
    rel = c.get("/api/cycle/relances").json()
    r = rel["propositions"][0]["raisons"][0]
    assert c.post(f"/api/cycle/relances/{r['id']}", json={"accepte": True, "par": "p00"}).json()["suivi"]
    etat = c.get("/api/cycle/etat").json()
    assert etat["horloge"] == "SIMULEE" and etat["opportunites"][0]["via"] == "p32"
    assert c.post("/api/cycle/besoin", json={"auteur": "inconnu", "texte": BESOIN}).status_code == 404
    assert c.post("/api/cycle/reinitialiser").json()["ok"] and c.get("/api/cycle/etat").json()["evenements"] == 0
