"""ANNÉE 1 · LOT 11 — Application installable (PWA) et FILE D'ATTENTE HORS LIGNE pour les réponses (Oui / Non / Pas
cette fois). Interrupteur `HACKVS_HORS_LIGNE=1` (éteint par défaut : hors ligne, le téléphone dit seulement qu'il
attend le réseau, comme dans la démo). Allumé : une réponse donnée sans réseau est GARDÉE sur le téléphone, dite
« en attente », puis envoyée au retour du réseau ; le serveur reste seul juge (une demande qui n'est plus d'actualité
est refusée, et le membre le sait). Vrai Chromium, réseau coupé par le navigateur. Données FICTIVES."""
import json
import tempfile
import urllib.request

import pytest

pytest.importorskip("playwright.sync_api")

FILE = "pulse-file-hors-ligne"


def _api(base, chemin, corps=None, session=None):
    h = {"Content-Type": "application/json", "X-Pulse-Console": "1"} | ({"X-Pulse-Session": session} if session else {})
    req = urllib.request.Request(base + chemin, data=json.dumps(corps).encode() if corps is not None else None, headers=h)
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def _pauline_aux_demandes(b, base, erreurs):
    from tests.test_e2e_pulse import _telephone
    _api(base, "/api/pulse/demo/reinitialiser", {})
    code = {p["id"]: p["code"] for p in _api(base, "/api/pulse/console/personas")}["s01"]
    ctx, pg = _telephone(b, base, code, (390, 844), erreurs)
    pg.click("nav.onglets >> text=Demandes")
    pg.wait_for_selector("[data-ask]")
    pg.fill("#att-places", "14")
    return ctx, pg


def _consentements(base, pg):
    return _api(base, "/api/pulse/moi/donnees", session=pg.evaluate("sessionStorage.getItem('pulse-session')"))["consentements"]


def test_allume_une_reponse_hors_ligne_part_au_retour_du_reseau(tmp_path):
    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    erreurs: list[str] = []
    with serveur(HACKVS_HORS_LIGNE="1", HACKVS_ESSAIS_DB=str(tmp_path / "j.db")) as base, sync_playwright() as p:
        b = _chromium(p)
        ctx, pg = _pauline_aux_demandes(b, base, erreurs)
        erreurs.clear()                                         # seules comptent les erreurs APRÈS la coupure
        ctx.set_offline(True)
        pg.click("#ask-oui")
        pg.locator("[data-ask] [data-role=en-attente]:has-text('en attente du réseau')").wait_for()
        assert len(json.loads(pg.evaluate(f"localStorage.getItem('{FILE}')"))) == 1
        assert _consentements(base, pg) == []                  # rien n'est parti
        ctx.set_offline(False)                                  # le réseau revient : la file se vide d'elle-même
        pg.wait_for_selector("[data-recu='delegation_acheteurs']")
        assert pg.evaluate(f"localStorage.getItem('{FILE}')") in (None, "[]")
        assert [c["finalite"] for c in _consentements(base, pg)] == ["delegation_acheteurs"]
        b.close()
    assert not [e for e in erreurs if "ERR_INTERNET_DISCONNECTED" not in e], erreurs


def test_allume_une_reponse_qui_n_est_plus_d_actualite_est_dite_et_retiree_de_la_file(tmp_path):
    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    with serveur(HACKVS_HORS_LIGNE="1", HACKVS_ESSAIS_DB=str(tmp_path / "j.db")) as base, sync_playwright() as p:
        b = _chromium(p)
        ctx, pg = _pauline_aux_demandes(b, base, [])
        ctx.set_offline(True)
        pg.click("#ask-oui")
        pg.locator("[data-role=en-attente]").wait_for()
        session = pg.evaluate("sessionStorage.getItem('pulse-session')")
        ask = pg.get_attribute("[data-ask]", "data-ask")
        _api(base, f"/api/pulse/moi/asks/{ask}/reponse", {"oui": False, "choix": "non", "attributs": {}}, session=session)
        ctx.set_offline(False)                                  # entre-temps, la demande a reçu une autre réponse
        pg.locator(".toast:has-text(\"n'a pas pu partir\")").wait_for()
        assert pg.evaluate(f"localStorage.getItem('{FILE}')") in (None, "[]")
        assert _consentements(base, pg) == []
        b.close()


def test_eteint_rien_n_est_garde_hors_ligne_comme_dans_la_demo(tmp_path):
    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    with serveur(HACKVS_ESSAIS_DB=str(tmp_path / "j.db")) as base, sync_playwright() as p:
        b = _chromium(p)
        ctx, pg = _pauline_aux_demandes(b, base, [])
        assert "hors_ligne" not in _api(base, "/api/pulse/moi/date", session=pg.evaluate("sessionStorage.getItem('pulse-session')"))
        ctx.set_offline(True)
        pg.click("#ask-oui")
        pg.locator(".toast:has-text('Hors ligne')").wait_for()
        assert pg.evaluate(f"localStorage.getItem('{FILE}')") is None
        assert pg.locator("[data-role=en-attente]").count() == 0
        ctx.set_offline(False)
        pg.wait_for_timeout(1500)
        assert _consentements(base, pg) == []                  # éteint : rien ne part tout seul
        b.close()


def test_l_application_est_installable_selon_chromium(tmp_path):
    """Contexte PERSISTANT (un contexte de test est « incognito », jamais installable) : Chromium ne relève aucune
    erreur d'installabilité (manifeste, icône, service worker, portée)."""
    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import serveur
    import os
    with serveur(HACKVS_ESSAIS_DB=str(tmp_path / "j.db")) as base, sync_playwright() as p:
        chemin = "/opt/pw-browsers/chromium"
        ctx = p.chromium.launch_persistent_context(tempfile.mkdtemp(dir=tmp_path),
                                                   **({"executable_path": chemin} if os.path.exists(chemin) else {}))
        pg = ctx.new_page()
        pg.goto(base + "/app")
        pg.wait_for_function("navigator.serviceWorker.controller !== null || navigator.serviceWorker.getRegistrations().then(r => r.length > 0)")
        pg.wait_for_timeout(1000)
        assert ctx.new_cdp_session(pg).send("Page.getInstallabilityErrors")["installabilityErrors"] == []
        ctx.close()
