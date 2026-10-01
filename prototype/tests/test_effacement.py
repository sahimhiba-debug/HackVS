"""F34 — « Tout effacer », pour de vrai : un fait EFFACEMENT journalisé ; le coffre oublie l'identité (nom, organisation,
contacts) ; les projections oublient le membre (déclarations, offres, consentements, préférences, notes, compte) ; un
redémarrage REJOUE l'effacement (avant : `Coffre.supprimer` existait, jamais appelé, et le coffre se reconstruisait de
l'import à chaque démarrage). Ce qui reste, dit tel quel : le journal en ajout seul garde l'identifiant technique et
les textes déclarés (déjà sans identité), qu'aucune vue ne montre plus. Données FICTIVES."""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pulse_api import creer_routeur
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.erreurs import NonAuthentifie

TAX = charger_taxonomie()
A = "delegation_acheteurs"


def _pauline_a_repondu(c):
    ask = next(a for _, a in c.asks_pour(md.PAULINE) if a.startswith(A))
    assert c.repondre_ask(md.PAULINE, ask, True, {"places": 14}).statut == "ACTIVE"


def test_tout_effacer_oublie_le_membre_et_survit_au_redemarrage(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    monkeypatch.setenv("HACKVS_SECRET", "un-secret-de-test-assez-long-pour-32-octets!")
    c = Demo(TAX).club
    _pauline_a_repondu(c)
    nom, courriel = c.coffre.identite(md.PAULINE).nom, c.coffre.identite(md.PAULINE).courriel
    session = c.session(md.PAULINE)

    bilan = c.effacer(md.PAULINE)

    assert [e.acteurs for e in c.journal.evenements("EFFACEMENT")] == [[md.PAULINE]]
    assert c.coffre.identite(md.PAULINE) is None and md.PAULINE not in c.coffre.actives
    with pytest.raises(NonAuthentifie):
        c.verifier_session(session)
    p = c.profil(md.PAULINE)
    assert not p.offre and not p.recherche and not p.presentation and p.disponible is False
    assert not [o for o in c.banc.offres() if o.auteur == md.PAULINE and c.banc.etat_offre(o.id) == "active"]
    assert not [x for x in c.claims() if x.membre == md.PAULINE and x.valable(c.jour)]
    assert all(r["etat"] != "valable" for r in c.capacites.recus(md.PAULINE))
    assert next(i for i in c.capacites.projeter() if i.finalite == A).statut != "ACTIVE"      # sa pièce ne compte plus
    vues = json.dumps([c.vues_capacites.console(), c.vues_essai.console(), c.vues.panneau()], ensure_ascii=False, default=str)
    assert nom not in vues and courriel not in vues
    assert bilan["reste"] and "journal" in bilan["reste"]                                       # ce qui reste est dit

    relu = Demo(TAX, reprendre=True).club                                                       # redémarrage
    assert relu.coffre.identite(md.PAULINE) is None and relu.empreinte_etat() == c.empreinte_etat()


def test_par_http_tout_effacer_exige_une_confirmation_puis_ferme_la_session():
    app = FastAPI()
    app.include_router(creer_routeur(TAX))
    client = TestClient(app)
    console = {"X-Pulse-Console": "1"}
    client.post("/api/pulse/demo/reinitialiser", headers=console)
    h = {"X-Pulse-Session": next(p["session"] for p in client.get("/api/pulse/console/personas", headers=console).json()
                                 if p["id"] == md.PAULINE)}
    assert client.post("/api/pulse/moi/effacer", headers=h, json={}).status_code == 422          # pas sans confirmation
    assert client.post("/api/pulse/moi/effacer", headers=h, json={"confirme": False}).status_code == 422
    r = client.post("/api/pulse/moi/effacer", headers=h, json={"confirme": True})
    assert r.status_code == 200 and r.json()["efface"]
    assert client.get("/api/pulse/moi/profil", headers=h).status_code == 401
