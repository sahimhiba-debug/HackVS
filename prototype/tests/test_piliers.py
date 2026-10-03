"""P3 n°15 — escalade vers des membres « piliers » volontaires : opt-in journalisé, retirable ; un pilier voit les
demandes bloquées (sans nom, sans qui a dit non) ; le secrétariat ne voit que le nombre (« < 3 »)."""
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence import piliers
from intelligence.demo import Demo
from intelligence.erreurs import Interdit

CONSOLE = {"X-Pulse-Console": "1"}
client = TestClient(app)


@pytest.fixture
def c(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_SECRET", "un-secret-de-test-assez-long-pour-32-octets!")
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(charger_taxonomie()).club


def test_seul_un_pilier_voit_les_escalades_et_sans_nom(c):
    with pytest.raises(Interdit):
        piliers.escalades(c, md.MARKUS)
    piliers.declarer(c, md.MARKUS, True)
    assert piliers.escalades(c, md.MARKUS) == []                 # rien n'est bloqué depuis 3 jours au départ
    c.avancer(3)                                                 # horloge du monde (simulée) : vendredi 09.10
    esc = piliers.escalades(c, md.MARKUS)
    assert esc and all(e["age_jours"] >= 3 for e in esc)
    noms = [p.nom for p in c.coffre._personnes.values()]
    assert not [n for n in noms if n in json.dumps(esc, ensure_ascii=False)]
    assert piliers.agregats(c)["piliers"] == "< 3"
    piliers.declarer(c, md.MARKUS, False)
    assert piliers.agregats(c)["piliers"] == 0


def test_routes(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    s = {"X-Pulse-Session": per[md.MARKUS]["session"]}
    assert client.get("/api/pulse/moi/escalades", headers=s).json() == {"pilier": False, "escalades": []}
    assert client.post("/api/pulse/moi/pilier", headers=s, json={"actif": True}).json() == {"pilier": True}
    assert client.get("/api/pulse/moi/escalades", headers=s).json()["pilier"] is True
    agr = client.get("/api/pulse/console/piliers", headers=CONSOLE).json()
    assert agr["piliers"] == "< 3" and per[md.MARKUS]["nom"] not in json.dumps(agr, ensure_ascii=False)
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
