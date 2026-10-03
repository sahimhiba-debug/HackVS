"""P3 n°10 — TABLEAU DE BORD DU SECRÉTARIAT : demandes bloquées, métiers manquants, invités actifs ; agrégats, « < 3 »."""
import json

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


def test_tableau_agrege_sans_nom():
    r = client.get("/api/pulse/console/tableau", headers=CONSOLE)
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["monde"] == "monde de démonstration" and t["demandes_sans_reponse"] >= 1
    assert {"metier", "demandes", "age_max_jours"} <= set(t["metiers_manquants"][0])
    assert t["nouveaux_liens"] == "< 3" and t["associes"] == 0 and t["annonces"]["annonces"] == 0
    noms = [p["nom"] for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json() if p.get("nom")]
    texte = json.dumps(t, ensure_ascii=False)
    assert not [n for n in noms if n in texte]


def test_exige_la_console():
    assert client.get("/api/pulse/console/tableau").status_code in (401, 403)
