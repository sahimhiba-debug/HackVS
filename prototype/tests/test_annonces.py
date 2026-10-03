"""P3 n°9 — ANNONCES SOUS CHIFFRE, relayées par le secrétariat jusqu'à l'accord mutuel.

Un membre publie une annonce sous une référence (« chiffre ») : aucun auteur affiché. Un autre membre dit son intérêt
(par le relais, sans voir l'auteur ; l'auteur ne voit qu'« intérêt n° 1 »). L'auteur accepte UN intérêt : accord
mutuel → les deux, et eux seuls, voient le nom et l'entreprise de l'autre. Le secrétariat ne voit que des décomptes.
Interrupteur : HACKVS_FOIRE. Données FICTIVES."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
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


def _p():
    return {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}


def _s(pid):
    return {"X-Pulse-Session": _p()[pid]["session"]}


def _publier():
    r = client.post("/api/pulse/moi/annonces", headers=_s(md.PAULINE), json={"texte": "Cherche un local de stockage à Martigny, 20 m², 3 mois."})
    assert r.status_code == 200, r.text
    return r.json()["chiffre"]


def test_l_annonce_ne_montre_pas_son_auteur():
    ch = _publier()
    liste = client.get("/api/pulse/annonces", headers=_s(md.MARKUS)).json()
    a = next(x for x in liste if x["chiffre"] == ch)
    texte = json.dumps(liste, ensure_ascii=False)
    nom = _p()[md.PAULINE]["nom"]
    assert nom not in texte and md.PAULINE not in texte and "auteur" not in a


def test_interet_puis_accord_mutuel_revele_les_deux_et_eux_seuls():
    ch = _publier()
    assert client.post(f"/api/pulse/moi/annonces/{ch}/interet", headers=_s(md.MARKUS)).status_code == 200
    mes = client.get("/api/pulse/moi/annonces", headers=_s(md.PAULINE)).json()
    mine = next(x for x in mes if x["chiffre"] == ch)
    assert [i["n"] for i in mine["interets"]] == [1] and _p()[md.MARKUS]["nom"] not in json.dumps(mes, ensure_ascii=False)
    assert client.post(f"/api/pulse/moi/annonces/{ch}/accepter/1", headers=_s(md.PAULINE)).status_code == 200
    cote_auteur = next(x for x in client.get("/api/pulse/moi/annonces", headers=_s(md.PAULINE)).json() if x["chiffre"] == ch)
    assert cote_auteur["interets"][0]["contact"]["nom"] == _p()[md.MARKUS]["nom"]
    cote_interesse = next(x for x in client.get("/api/pulse/annonces", headers=_s(md.MARKUS)).json() if x["chiffre"] == ch)
    assert cote_interesse["contact"]["nom"] == _p()[md.PAULINE]["nom"]
    tiers = next(x for x in client.get("/api/pulse/annonces", headers=_s(md.LEA)).json() if x["chiffre"] == ch)
    assert "contact" not in tiers


def test_le_secretariat_ne_voit_que_des_decomptes():
    ch = _publier()
    client.post(f"/api/pulse/moi/annonces/{ch}/interet", headers=_s(md.MARKUS))
    agr = client.get("/api/pulse/console/annonces", headers=CONSOLE).json()
    assert agr["annonces"] == 1 and agr["interets"] == "< 3"
    assert _p()[md.PAULINE]["nom"] not in json.dumps(agr, ensure_ascii=False)


def test_on_ne_s_interesse_pas_a_sa_propre_annonce_ni_n_accepte_un_interet_inexistant():
    ch = _publier()
    assert client.post(f"/api/pulse/moi/annonces/{ch}/interet", headers=_s(md.PAULINE)).status_code == 409
    assert client.post(f"/api/pulse/moi/annonces/{ch}/accepter/1", headers=_s(md.PAULINE)).status_code == 404
    assert client.post(f"/api/pulse/moi/annonces/{ch}/accepter/1", headers=_s(md.MARKUS)).status_code in (403, 404)
