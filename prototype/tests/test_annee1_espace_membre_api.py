"""ANNÉE 1 · LOT 3 — L'espace membre par HTTP : éteint par défaut (404), puis pause, préférences, mes demandes, export,
effacement définitif avec confirmation explicite. Chaque route exige la session du membre. Données FICTIVES."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence import monde_demo as md

CONSOLE = {"X-Pulse-Console": "1"}
client = TestClient(app)
ROUTES = [("get", "/api/pulse/moi/espace", None), ("post", "/api/pulse/moi/pause", {"jusqu_au": "2026-10-20"}),
          ("post", "/api/pulse/moi/pause/fin", {}), ("post", "/api/pulse/moi/preferences",
                                                    {"langue": "fr", "region": "", "canaux": ["app"]}),
          ("get", "/api/pulse/moi/export", None), ("post", "/api/pulse/moi/effacer-definitivement", {"confirme": True})]


@pytest.fixture(autouse=True)
def _monde(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    monkeypatch.setenv("HACKVS_ESPACE_MEMBRE", "1")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    yield
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)


def _s(pid):
    p = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    return {"X-Pulse-Session": p[pid]["session"]}


def _appel(methode, chemin, corps, headers):
    return getattr(client, methode)(chemin, headers=headers, **({"json": corps} if corps is not None else {}))


def test_eteint_par_defaut_aucune_route(monkeypatch):
    monkeypatch.delenv("HACKVS_ESPACE_MEMBRE")
    s = _s(md.PAULINE)
    for m, chemin, corps in ROUTES:
        assert _appel(m, chemin, corps, s).status_code == 404, chemin
    assert client.get("/espace").status_code == 404


def test_chaque_route_exige_la_session_du_membre():
    for m, chemin, corps in ROUTES:
        assert _appel(m, chemin, corps, {}).status_code in (401, 403), chemin


def test_pause_preferences_et_espace():
    s = _s(md.PAULINE)
    jour = client.get("/api/pulse/moi/date", headers=s).json()
    from datetime import date
    fin = (date.fromisoformat(jour["date"] if isinstance(jour, dict) else jour) + timedelta(days=7)).isoformat()
    assert client.post("/api/pulse/moi/pause", headers=s, json={"jusqu_au": fin}).json()["en_pause"] is True
    assert client.post("/api/pulse/moi/preferences", headers=s, json={"langue": "de", "region": "Valais",
                                                                      "canaux": ["app", "sms"]}).status_code == 200
    assert client.post("/api/pulse/moi/preferences", headers=s, json={"langue": "xx", "region": "", "canaux": ["app"]}).status_code == 422
    e = client.get("/api/pulse/moi/espace", headers=s).json()
    assert e["pause"]["en_pause"] and e["preferences"]["langue"] == "de" and "solde" in e and "demandes" in e
    assert client.post("/api/pulse/moi/pause/fin", headers=s).json()["en_pause"] is False


def test_export_telechargeable():
    r = client.get("/api/pulse/moi/export", headers=_s(md.PAULINE))
    assert r.status_code == 200 and "attachment" in r.headers.get("content-disposition", "")
    assert r.json()["membre"] == md.PAULINE


def test_effacement_definitif_exige_la_confirmation_puis_ferme_la_session():
    s = _s(md.PAULINE)
    assert client.post("/api/pulse/moi/effacer-definitivement", headers=s, json={}).status_code == 422
    r = client.post("/api/pulse/moi/effacer-definitivement", headers=s, json={"confirme": True})
    assert r.status_code == 200 and r.json()["faits_purges"] >= 1
    assert client.get("/api/pulse/moi/espace", headers=s).status_code in (401, 403, 404)


def test_la_page_espace_dans_un_vrai_navigateur(tmp_path):
    """Serveur réel, interrupteur allumé : pause, préférences, solde, puis suppression définitive ; aucune erreur JS (la
    CSP stricte autorise bien le script de la page)."""
    import json
    import urllib.request

    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    with serveur(HACKVS_ESPACE_MEMBRE="1", HACKVS_ESSAIS_DB=str(tmp_path / "j.db"), HACKVS_FOIRE="1") as base:
        req = urllib.request.Request(base + "/api/pulse/console/personas", headers=CONSOLE)
        session = next(p["session"] for p in json.load(urllib.request.urlopen(req)) if p["id"] == md.PAULINE)
        erreurs: list[str] = []
        with sync_playwright() as p:
            b = _chromium(p)
            pg = b.new_page(viewport={"width": 390, "height": 844})
            pg.on("pageerror", lambda e: erreurs.append(str(e)))
            pg.goto(f"{base}/espace?session={session}")
            pg.locator("#b-pause").wait_for()
            jour = pg.evaluate("fetch('/api/pulse/moi/date', {headers: {'X-Pulse-Session': "
                               "new URLSearchParams(location.search).get('session')}}).then(r => r.json())")
            from datetime import date
            pg.fill("#pause-date", (date.fromisoformat(jour["date"]) + timedelta(days=14)).isoformat())
            pg.click("#pause-ok")
            pg.locator("#pause-etat:has-text('En pause')").wait_for()
            pg.select_option("#langue", "de")
            pg.click("#pref-ok")
            pg.locator("#etat:has-text('Préférences enregistrées')").wait_for()
            pg.check("#effacer-sur")
            pg.click("#effacer")
            pg.locator("#etat:has-text('supprimé')").wait_for()
            b.close()
        assert not erreurs, erreurs
