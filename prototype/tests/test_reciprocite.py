"""P3 n°16 — balance de réciprocité PRIVÉE : le membre seul la voit (aucune route console) ; décomptes, aucun nom."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence import monde_demo as md

CONSOLE = {"X-Pulse-Console": "1"}
client = TestClient(app)
A = "delegation_acheteurs"


@pytest.fixture(autouse=True)
def _foire(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    yield
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)


def _s(pid):
    return {"X-Pulse-Session": {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}[pid]["session"]}


def test_un_oui_compte_comme_donne_pour_lui_seul():
    s = _s(md.PAULINE)
    avant = client.get("/api/pulse/moi/reciprocite", headers=s).json()
    ask = next(x for x in client.get("/api/pulse/moi/asks", headers=s).json() if x["id"].startswith(A))
    client.post(f"/api/pulse/moi/asks/{ask['id']}/reponse", headers=s, json={"oui": True, "attributs": {"places": 14}})
    apres = client.get("/api/pulse/moi/reciprocite", headers=s).json()
    assert apres["donne"] == avant["donne"] + 1 and "vous seul" in apres["prive"]
    assert client.get("/api/pulse/moi/reciprocite", headers=_s(md.MARKUS)).json()["donne"] == 0


def test_aucune_route_console_ne_l_expose():
    from app.main import app as a
    chemins = [getattr(r, "path", "") for r in a.routes]
    assert not [p for p in chemins if "reciprocite" in p and "/console" in p]
    assert client.get("/api/pulse/moi/reciprocite").status_code == 401
