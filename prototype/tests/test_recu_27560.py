"""P3 n°2 — REÇUS ALIGNÉS sur ISO/IEC TS 27560:2023 (jamais « certifiés ») : table de correspondance des champs, export
JSON-LD avec le vocabulaire DPV, test de conformité (chaque champ obligatoire présent et non vide, statut juste, aucune
identité). Interrupteur HACKVS_RECU_27560 (allumé par défaut). Données FICTIVES."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence import monde_demo as md
from intelligence import recu_27560 as r27

CONSOLE = {"X-Pulse-Console": "1"}
A = "delegation_acheteurs"
client = TestClient(app)


def _session(pid):
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    return {"X-Pulse-Session": per[pid]["session"]}


@pytest.fixture
def pauline(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    assert client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE).status_code == 200
    s = _session(md.PAULINE)
    ask = next(x for x in client.get("/api/pulse/moi/asks", headers=s).json() if x["id"].startswith(A))
    assert client.post(f"/api/pulse/moi/asks/{ask['id']}/reponse", headers=s, json={"oui": True, "attributs": {"places": 14}}).status_code == 200
    yield s
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)


def _export(s):
    r = client.get("/api/pulse/moi/recus/27560", headers=s)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/ld+json")
    return r.json()


def test_table_de_correspondance_couvre_les_champs_obligatoires():
    assert {c["champ_27560"] for c in r27.CHAMPS if c["obligatoire"]} >= {
        "identifiant de l'enregistrement", "personne concernée", "responsable du traitement", "finalité",
        "données personnelles", "base légale", "statut du consentement", "date de l'accord", "méthode d'expression"}
    assert all(c["terme_dpv"].startswith("dpv:") for c in r27.CHAMPS)


def test_export_jsonld_conforme_pour_chaque_recu(pauline):
    doc = _export(pauline)
    assert doc["@context"]["dpv"] == "https://w3id.org/dpv#"
    assert doc["alignement"] == "aligné sur ISO/IEC TS 27560:2023 — pas une certification"
    assert doc["@graph"]
    for rec in doc["@graph"]:
        assert r27.conforme(rec) == [], r27.conforme(rec)
        assert rec["@type"] == "dpv:ConsentRecord" and rec["dpv:hasConsentStatus"] == "dpv:ConsentGiven"


def test_retrait_donne_consent_withdrawn_et_une_date(pauline):
    assert client.post(f"/api/pulse/moi/capacites/{A}/retrait", headers=pauline).status_code == 200
    rec = next(x for x in _export(pauline)["@graph"] if x["dpv:hasConsentStatus"] == "dpv:ConsentWithdrawn")
    assert rec["dpv:hasWithdrawalTime"] and r27.conforme(rec) == []


def test_aucune_identite_dans_l_export(pauline):
    texte = json.dumps(_export(pauline), ensure_ascii=False)
    per = client.get("/api/pulse/console/personas", headers=CONSOLE).json()
    p = next(x for x in per if x["id"] == md.PAULINE)
    assert p.get("nom") and p["nom"] not in texte
    assert md.PAULINE not in texte                                  # l'identifiant technique non plus : un pseudonyme


def test_conforme_detecte_un_champ_manquant():
    assert "dpv:hasPurpose" in " ".join(r27.conforme({"@type": "dpv:ConsentRecord"}))


def test_exige_une_session_et_interrupteur(monkeypatch, pauline):
    assert client.get("/api/pulse/moi/recus/27560").status_code == 401
    monkeypatch.setenv("HACKVS_RECU_27560", "0")
    assert client.get("/api/pulse/moi/recus/27560", headers=pauline).status_code == 404
