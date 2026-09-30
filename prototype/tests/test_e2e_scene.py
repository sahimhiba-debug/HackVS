"""Bout en bout dans un VRAI navigateur : la scène complète, le clic sur une relation, la tour de contrôle, le mobile.

Ignoré seulement si aucun Chromium n'est disponible (la CI l'installe : job « reproductibilite »).
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

PROTO = Path(__file__).resolve().parents[1]
INTERDITS = ("null", "undefined", "NaN", "[object")


def _chromium(p):
    """Chromium du poste (ou celui de Playwright). Enregistré pour la CAPTURE SUR ÉCHEC (tests/capture_e2e.py) : si le
    test échoue, chaque page encore ouverte est sauvegardée (capture d'écran + HTML) avant la fermeture du navigateur."""
    from tests.capture_e2e import enregistrer
    return enregistrer(_lancer(p))


def _lancer(p):
    from tests.capture_e2e import REGLES_RESOLUTION
    chemin = "/opt/pw-browsers/chromium"
    options = {"args": [REGLES_RESOLUTION]} | ({"executable_path": chemin} if os.path.exists(chemin) else {})
    try:
        return p.chromium.launch(**options)
    except Exception as e:  # navigateur absent : on le dit, on n'invente pas un succès
        if os.environ.get("HACKVS_E2E_OBLIGATOIRE"):
            raise                                   # en CI, un navigateur absent est un échec, pas un saut
        pytest.skip(f"Chromium indisponible : {type(e).__name__}")


@pytest.fixture(scope="module")
def url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {**os.environ, "HACKVS_SEMANTIQUE": "0", "HACKVS_DB": ":memory:", "HACKVS_DECISIONS_DB": ":memory:",
           "HACKVS_CYCLE_DB": ":memory:", "HACKVS_MODE": "demo"}
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=PROTO, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(80):
        try:
            urllib.request.urlopen(base + "/api/stage", timeout=1)
            break
        except OSError:
            time.sleep(0.25)
    if os.environ.get("HACKVS_MODE_SALLE"):                 # scripts/mode_salle.py : on le PROUVE, on ne le suppose pas
        with socket.socket() as s:
            s.settimeout(2)
            assert s.connect_ex(("1.1.1.1", 443)) != 0, "mode salle : l'extérieur est joignable"
        requete = urllib.request.Request(base + "/api/pulse/etat", headers={"X-Pulse-Console": "1"})
        ia = json.load(urllib.request.urlopen(requete, timeout=5))["ia"]
        assert ia["configure"] is False and ia["fournisseur"] == "deterministe", ia
    yield base
    srv.terminate()


def test_scene_complete_bureau_puis_mobile(url):
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        b = _chromium(p)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.set_default_timeout(90_000)   # machine chargée (suite complète) : on teste le parcours, pas la vitesse (mesurer_scene.py)
        erreurs: list[str] = []
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
        pg.goto(url + "/demo/stage")
        pg.click("#reinit")
        pg.wait_for_function("document.querySelector('#horloge').textContent.includes('étape 0/')")
        total = int(pg.inner_text("#horloge").split("/")[-1])
        titres = []
        for i in range(1, total + 1):
            pg.click("#suiv")
            pg.wait_for_function(f"document.querySelector('#horloge').textContent.includes('étape {i}/')")
            texte = pg.inner_text("#carte")
            assert not [m for m in INTERDITS if m in texte.split() or m in texte], (i, texte[:300])
            titres.append(pg.inner_text("#carte h1"))
            if i == 8:                                             # clic RÉEL sur une relation : contrefactuel
                pg.locator("line.lien-zone").first.dispatch_event("click")
                pg.wait_for_function("document.querySelector('#carte').innerText.toLowerCase().includes('votre simulation')")
        assert "Je préfère m'abstenir" in " ".join(titres)
        pg.click("#btn-tour")                                     # tour de contrôle : chaque chiffre s'ouvre sur sa définition
        pg.wait_for_selector("dialog#tour[open] details.indic")
        assert pg.locator("details.indic").count() == 8
        pg.keyboard.press("Escape")
        with pg.expect_response(lambda r: "/api/stage/aller/" in r.url):   # rejeu : attendre la réponse, pas l'affichage
            pg.click("#rejouer")
        with pg.expect_response(lambda r: "/api/stage/reinitialiser" in r.url):
            pg.click("#reinit")
        pg.wait_for_function("document.querySelector('#horloge').textContent.includes('étape 0/')")
        pg.set_viewport_size({"width": 390, "height": 844})       # mobile : aucun défilement horizontal
        pg.click("#suiv")
        pg.wait_for_function("document.querySelector('#horloge').textContent.includes('étape 1/')")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        b.close()
    assert erreurs == []
