"""Attaques de confidentialité sur le réseau : brouillons, besoins clos, nouveaux membres, liens de tiers."""
import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SOPHIE = {"X-Membre": "p00"}
SECRET = "Nous envisageons discrètement de céder l'entreprise et cherchons un transporteur frigorifique pour Zurich"


def _besoin(texte, publier, qui=SOPHIE):
    b = client.post("/api/analyser", json={"texte": texte}).json()["besoin"]
    return client.post("/api/besoins", json={"besoin": b, "publier": publier, "anonyme": False}, headers=qui).json()


def test_brouillon_jamais_utilise_comme_raison_de_rencontre():
    client.post("/api/demo/reinitialiser")
    _besoin(SECRET, publier=False)
    plan = client.get("/api/soiree/plan").json()
    assert "céder" not in json.dumps(plan, ensure_ascii=False)
    d = client.post("/api/decisions", json={"demande": "des rencontres utiles"}).json()
    assert "céder" not in json.dumps(d, ensure_ascii=False)


def test_besoin_clos_ne_sert_plus_de_raison():
    client.post("/api/demo/reinitialiser")
    b = _besoin(SECRET, publier=True)
    client.post(f"/api/besoins/{b['id']}/cloturer", json={"note": "fini"}, headers=SOPHIE)
    assert "céder" not in json.dumps(client.get("/api/soiree/plan").json(), ensure_ascii=False)
