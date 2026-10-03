"""FOIRE 2026 · E — « LE CLUB CHERCHE » : demandes sans réponse par métier (nombre, âge), « Inviter un contact » →
passe découverte LIÉ (lien, QR, texte FR/DE) ; métiers présents/absents depuis une liste d'entreprises : DÉCOMPTES
seulement — jamais un nom d'entreprise lu ni affiché. Sans la liste : dit. Données FICTIVES."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence import club_cherche, metiers
from intelligence import monde_demo as md

CONSOLE = {"X-Pulse-Console": "1"}
client = TestClient(app)


@pytest.fixture(autouse=True)
def _foire(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    monkeypatch.setenv("HACKVS_ENTREPRISES_CSV", str(tmp_path / "absente.csv"))
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    yield
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)


def _cherche():
    r = client.get("/api/pulse/console/club-cherche", headers=CONSOLE)
    assert r.status_code == 200, r.text
    return r.json()


def test_demandes_sans_reponse_par_metier_avec_nombre_et_age():
    x = _cherche()
    assert x["monde"] == "monde de démonstration"
    transport = next(g for g in x["metiers"] if g["metier"] == "transport")
    assert transport["nombre"] == len(transport["demandes"]) >= 1
    assert all(isinstance(d["age_jours"], int) and d["age_jours"] >= 0 for d in transport["demandes"])
    assert x["marche"]["source"] == "absente"


def test_une_demande_repondue_quitte_la_liste():
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    s = {"X-Pulse-Session": per[md.PAULINE]["session"]}
    ask = client.get("/api/pulse/moi/asks", headers=s).json()[0]
    client.post(f"/api/pulse/moi/asks/{ask['id']}/reponse", headers=s, json={"oui": True, "attributs": {"places": 14}})
    ids = [d["id"] for g in _cherche()["metiers"] for d in g["demandes"]]
    assert ask["id"] not in ids


def test_inviter_un_contact_emet_un_passe_lie_avec_textes_fr_de():
    d = _cherche()["metiers"][0]["demandes"][0]
    p = client.post("/api/pulse/console/decouverte", headers=CONSOLE, json={"origine": "demande", "demande": d["id"]}).json()
    assert p["origine"] == "demande" and p["qr"] and p["url"] in p["invitation"]["fr"] and p["url"] in p["invitation"]["de"]
    assert "sans être membre" in p["invitation"]["fr"] and "ohne Mitgliedschaft" in p["invitation"]["de"]
    inv = {"X-Pulse-Invite": client.post("/api/pulse/decouverte/activer", json={"jeton": p["jeton"]}).json()["invite"]}
    assert client.get("/api/pulse/decouverte/moi", headers=inv).json()["demandes"][0]["id"] == d["id"]


def test_liste_d_entreprises_decomptes_seulement_jamais_de_nom(monkeypatch, tmp_path):
    f = tmp_path / "entreprises.csv"
    f.write_text("nom;metier;ville\nTransports Alpins Fictifs SA;transport;Sion\nCars du Rhône Fictifs;Transport de personnes;Martigny\n"
                 "Hôtel Fictif;tourisme;Zermatt\nInconnue Fictive;astrologie;Brig\n", encoding="utf-8")
    monkeypatch.setenv("HACKVS_ENTREPRISES_CSV", str(f))
    x = _cherche()
    brut = json.dumps(x, ensure_ascii=False)
    for nom in ("Transports Alpins", "Cars du Rhône", "Hôtel Fictif", "Inconnue", "Sion", "Martigny"):
        assert nom not in brut
    assert x["marche"]["lignes"] == 4 and x["marche"]["non_classees"] == 1 and x["marche"]["metiers_presents"] == 2
    assert x["marche"]["metiers_absents"] == len(metiers.metiers()) - 2
    assert next(g for g in x["metiers"] if g["metier"] == "transport")["entreprises_de_ce_metier"] == 2


def test_liste_sans_colonne_metier_le_dit(tmp_path):
    f = tmp_path / "e.csv"
    f.write_text("nom,ville\nX Fictive,Sion\n", encoding="utf-8")
    assert club_cherche.entreprises_par_metier(f)["note"] == "aucune colonne métier reconnue"


def test_interrupteur_eteint_404(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    assert client.get("/api/pulse/console/club-cherche", headers=CONSOLE).status_code == 404
