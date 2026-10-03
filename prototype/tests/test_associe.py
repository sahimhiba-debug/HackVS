"""P3 n°8 — STATUT « MEMBRE ASSOCIÉ » : une personne d'une organisation partenaire (ici un EXEMPLE FICTIF, jamais un
partenaire réel présenté comme acquis) reçoit les demandes du Club comme un membre, et le Club les compte à part,
en agrégats (« < 3 » en entreprises). Journalisé (ASSOCIE), retirable. Données FICTIVES."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence import associe
from intelligence import monde_demo as md

CONSOLE = {"X-Pulse-Console": "1"}
client = TestClient(app)


@pytest.fixture(autouse=True)
def _foire(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    yield
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)


def _session(pid):
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    return {"X-Pulse-Session": per[pid]["session"]}


def test_le_partenaire_est_un_exemple_fictif():
    assert associe.PARTENAIRE["exemple"] is True and "exemple" in associe.PARTENAIRE["nom"].lower()


def test_declarer_un_associe_puis_le_voir_sur_son_telephone_et_en_agregat():
    r = client.post("/api/pulse/console/associes", headers=CONSOLE, json={"membre": md.PAULINE})
    assert r.status_code == 200, r.text
    moi = client.get("/api/pulse/moi/associe", headers=_session(md.PAULINE)).json()
    assert moi["statut"] == "membre associé" and moi["partenaire"]["exemple"] is True
    agr = client.get("/api/pulse/console/associes", headers=CONSOLE).json()
    assert agr["associes"] == "< 3" and agr["partenaire"]["exemple"] is True
    assert "Pauline" not in json.dumps(agr, ensure_ascii=False)
    assert client.get("/api/pulse/console/suivi", headers=CONSOLE).json()["associes"] == "< 3"


def test_retirer_le_statut():
    client.post("/api/pulse/console/associes", headers=CONSOLE, json={"membre": md.PAULINE})
    assert client.post("/api/pulse/console/associes/retirer", headers=CONSOLE, json={"membre": md.PAULINE}).status_code == 200
    assert client.get("/api/pulse/moi/associe", headers=_session(md.PAULINE)).json()["statut"] == "membre"


def test_membre_inconnu_refuse_et_console_exigee():
    assert client.post("/api/pulse/console/associes", headers=CONSOLE, json={"membre": "zz99"}).status_code == 404
    assert client.post("/api/pulse/console/associes", json={"membre": md.PAULINE}).status_code in (401, 403)
