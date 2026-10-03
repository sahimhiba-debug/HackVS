"""P3 n°12 — PONT THE ARK : une variante du passe découverte pour les start-ups (180 jours au lieu de 90), marquée
« proposé, à valider avec la fondation ». Le reste du passe est identique (usage unique, révocable, aucun nom affiché)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

CONSOLE = {"X-Pulse-Console": "1"}
client = TestClient(app)


@pytest.fixture(autouse=True)
def _foire(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    yield
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)


def test_passe_startup_deux_fois_plus_long_et_marque_a_valider():
    stand = client.post("/api/pulse/console/decouverte", headers=CONSOLE, json={"origine": "stand"}).json()
    s = client.post("/api/pulse/console/decouverte", headers=CONSOLE, json={"origine": "startup"}).json()
    assert stand["jours"] == 90 and s["jours"] == 180
    assert "The Ark" in s["variante"] and "à valider" in s["variante"]
    r = client.post("/api/pulse/decouverte/activer", json={"jeton": s["jeton"]})
    assert r.status_code == 200 and r.json()["role"] == "invité"
    assert next(x for x in client.get("/api/pulse/console/decouverte", headers=CONSOLE).json() if x["nonce"] == s["nonce"])["origine"] == "startup"


def test_origine_inconnue_refusee():
    assert client.post("/api/pulse/console/decouverte", headers=CONSOLE, json={"origine": "ark"}).status_code == 422


def test_l_invite_retire_son_consentement_et_son_passe_ne_vaut_plus_rien():
    """Audit D2 : le reçu dit « révocable » — l'invité rend son passe ; le nom n'a jamais été dans le journal."""
    s = client.post("/api/pulse/console/decouverte", headers=CONSOLE, json={"origine": "stand"}).json()
    inv = {"X-Pulse-Invite": client.post("/api/pulse/decouverte/activer", json={"jeton": s["jeton"]}).json()["invite"]}
    ref = client.get("/api/pulse/decouverte/referentiel", headers=inv).json()
    corps = {"entreprise": "Atelier Témoin Sàrl", "metier": "transport", "zone": ref["zones"][0]}
    assert client.post("/api/pulse/decouverte/declaration", headers=inv, json=corps).status_code == 200
    assert client.post("/api/pulse/decouverte/retirer", headers=inv).json()["retire"] is True
    assert client.get("/api/pulse/decouverte/moi", headers=inv).status_code == 401
