"""ANNÉE 1 · audit des lots 6-8, I5 (resté « non fait », repris) : la langue choisie dans « Mon espace » s'applique au
téléphone. SANS requête supplémentaire : elle voyage dans la réponse de `/moi/foire`, que le téléphone lit déjà au
démarrage, et seulement quand l'espace membre est allumé (éteint : réponse identique à la démo). Données FICTIVES."""
import json
import urllib.request

import pytest

pytest.importorskip("playwright.sync_api")


def _api(base, chemin, corps=None, session=None):
    h = {"Content-Type": "application/json", "X-Pulse-Console": "1"} | ({"X-Pulse-Session": session} if session else {})
    req = urllib.request.Request(base + chemin, data=json.dumps(corps).encode() if corps is not None else None, headers=h)
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def _session(base, pid="s01"):
    code = {q["id"]: q["code"] for q in _api(base, "/api/pulse/console/personas")}[pid]
    return _api(base, "/api/pulse/acces", {"code": code})["session"]


@pytest.mark.parametrize("langue,attendu", [("de", "de"), ("en", "en")])
def test_la_langue_de_mon_espace_s_applique_au_telephone(tmp_path, langue, attendu):
    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    env = {"HACKVS_ESPACE_MEMBRE": "1", "HACKVS_MULTICLUB": "1", "HACKVS_ESSAIS_DB": str(tmp_path / "j.db")}
    with serveur(**env) as base, sync_playwright() as p:
        s = _session(base)
        _api(base, "/api/pulse/moi/preferences", {"langue": langue, "region": "", "canaux": ["app"]}, session=s)
        b = _chromium(p)
        pg = b.new_page()
        pg.goto(f"{base}/app#actions")
        pg.evaluate("(s) => sessionStorage.setItem('pulse-session', s)", s)
        pg.reload()
        pg.locator(f"html[lang='{attendu}']").wait_for(state="attached", timeout=8000)
        b.close()


def test_eteint_la_reponse_de_moi_foire_reste_celle_de_la_demo(tmp_path):
    from tests.test_e2e_scene import serveur
    with serveur(HACKVS_FOIRE="1", HACKVS_ESSAIS_DB=str(tmp_path / "j.db")) as base:
        assert _api(base, "/api/pulse/moi/foire", session=_session(base)) == {"actif": True}
