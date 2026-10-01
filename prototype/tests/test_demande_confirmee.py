"""F01 — `POST /moi/demandes` : le modèle INTERPRÈTE, le membre CONFIRME. Aucune interprétation du modèle n'entre dans
l'état sans confirmation explicite. Avant : la route écrivait le BESOIN interprété puis lançait la détection.
Données FICTIVES."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pulse_api import creer_routeur
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo

TAX = charger_taxonomie()
TEXTE = "Je cherche quelqu'un pour traduire nos fiches produit en allemand."


def test_interpreter_n_ecrit_rien_confirmer_publie_exactement_ce_qui_a_ete_montre():
    c = Demo(TAX).club
    avant, besoins = len(c.journal.evenements()), len(c.r.besoins)
    prop = c.demander(md.SOPHIE, TEXTE)
    nouveaux = [e.type for e in c.journal.evenements()[avant:]]
    assert set(nouveaux) <= {"APPEL_IA"} and len(c.r.besoins) == besoins                 # rien d'autre que la trace IA
    assert prop["a_confirmer"] and prop["compris"] and "decouvertes" not in prop
    res = c.confirmer_demande(md.SOPHIE, prop["proposition"])
    besoin = c.journal.evenements("BESOIN")[-1].donnees["besoin"]
    assert besoin["confirme"] is True and besoin["texte"] == TEXTE
    assert [x["libelle"] for x in res["compris"]] == [x["libelle"] for x in prop["compris"]]   # ce qui a été montré
    assert "decouvertes" in res and len(c.r.besoins) == besoins + 1


def test_une_proposition_se_confirme_une_fois_et_seulement_par_son_auteur():
    c = Demo(TAX).club
    prop = c.demander(md.SOPHIE, TEXTE)
    import pytest

    from intelligence.erreurs import Introuvable
    with pytest.raises(Introuvable):
        c.confirmer_demande(md.LEA, prop["proposition"])                 # pas la sienne
    c.confirmer_demande(md.SOPHIE, prop["proposition"])
    with pytest.raises(Introuvable):
        c.confirmer_demande(md.SOPHIE, prop["proposition"])              # déjà publiée


def test_par_http_la_route_n_ecrit_rien_et_la_confirmation_publie():
    app = FastAPI()
    app.include_router(creer_routeur(TAX))
    client = TestClient(app)
    console = {"X-Pulse-Console": "1"}
    client.post("/api/pulse/demo/reinitialiser", headers=console)
    session = next(p["session"] for p in client.get("/api/pulse/console/personas", headers=console).json() if p["id"] == md.LEA)
    h = {"X-Pulse-Session": session}
    prop = client.post("/api/pulse/moi/demandes", headers=h, json={"texte": TEXTE})
    assert prop.status_code == 200 and prop.json()["a_confirmer"]
    r = client.post(f"/api/pulse/moi/demandes/{prop.json()['proposition']}/confirmer", headers=h)
    assert r.status_code == 200 and "decouvertes" in r.json()
    assert client.post(f"/api/pulse/moi/demandes/{prop.json()['proposition']}/confirmer", headers=h).status_code == 404
