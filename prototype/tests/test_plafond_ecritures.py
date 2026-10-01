"""D2 (décision de Hiba, contre-expertise du 01.10) — au plus 30 écritures par minute et par membre (offres, essais, notes),
même plafond pour un passe juré. Au-delà : 429, message dans le vocabulaire du produit, au même format que les autres
refus. Pourquoi : sans plafond, un membre — ou un juré — pouvait publier des centaines d'offres ou de brouillons et
alourdir chaque recalcul de l'Établi (durcissement H2 : ≈ 1,1 s par recalcul sous 200 parasites, après correctif).
Le plafond est PAR MEMBRE : un autre membre n'est pas freiné ; les lectures ne le sont jamais. Données FICTIVES."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pulse_api import creer_routeur
from app.taxonomy import charger_taxonomie

TAX = charger_taxonomie()
CONSOLE = {"X-Pulse-Console": "1"}


def _monde(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    app = FastAPI()
    app.include_router(creer_routeur(TAX))
    c = TestClient(app)
    codes = {p["id"]: p["code"] for p in c.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    s = {k: {"X-Pulse-Session": c.post("/api/pulse/acces", json={"code": codes[k]}).json()["session"]} for k in ("s14", "s01")}
    return c, s


def _offre(c, h, i):
    return c.post("/api/pulse/moi/offres", headers=h, json={"nature": "objet", "quoi": f"Offre fictive {i}", "au": "2026-10-10"})


def test_trente_ecritures_par_minute_puis_429_dans_le_vocabulaire_du_produit(tmp_path, monkeypatch):
    c, s = _monde(tmp_path, monkeypatch)
    statuts = [_offre(c, s["s14"], i).status_code for i in range(30)]
    assert statuts == [200] * 30
    r = _offre(c, s["s14"], 30)
    assert r.status_code == 429
    assert r.json()["detail"].startswith("trop de publications en une minute"), r.json()   # format uniforme : {"detail": …}


def test_essais_et_notes_comptent_dans_le_meme_plafond(tmp_path, monkeypatch):
    c, s = _monde(tmp_path, monkeypatch)
    h = s["s14"]
    for i in range(10):
        assert _offre(c, h, i).status_code == 200
    for i in range(10):
        assert c.post("/api/pulse/moi/essais", headers=h, json={"question": f"Question fictive {i} ?", "echeance": "2026-10-09"}).status_code == 200
    for i in range(10):
        assert c.post("/api/pulse/moi/notes", headers=h, json={"texte": f"Note fictive numéro {i}"}).status_code == 200
    assert c.post("/api/pulse/moi/essais", headers=h, json={"question": "Une de trop ?", "echeance": "2026-10-09"}).status_code == 429
    assert c.post("/api/pulse/moi/notes", headers=h, json={"texte": "Une note de trop"}).status_code == 429


def test_le_plafond_est_par_membre_et_ne_freine_jamais_la_lecture(tmp_path, monkeypatch):
    c, s = _monde(tmp_path, monkeypatch)
    for i in range(31):
        _offre(c, s["s14"], i)
    assert _offre(c, s["s14"], 99).status_code == 429
    assert _offre(c, s["s01"], 0).status_code == 200                       # un autre membre n'est pas freiné
    assert c.get("/api/pulse/moi/donnees", headers=s["s14"]).status_code == 200   # lire reste possible


def test_le_passe_jure_a_le_meme_plafond(tmp_path, monkeypatch):
    c, _ = _monde(tmp_path, monkeypatch)
    passe = c.post("/api/pulse/console/jure", json={"persona": "s04", "minutes": 15}, headers=CONSOLE).json()["url"].split("jure=", 1)[1]
    j = {"X-Pulse-Session": c.post("/api/pulse/jure", json={"jeton": passe}).json()["session"]}
    statuts = [_offre(c, j, i).status_code for i in range(31)]
    assert statuts == [200] * 30 + [429], statuts
