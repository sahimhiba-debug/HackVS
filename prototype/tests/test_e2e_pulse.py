"""Club Pulse dans un VRAI navigateur : la console (démonstration guidée, téléphone intégré) puis l'application du membre
sur des écrans de téléphone. Ignoré seulement si aucun Chromium n'est disponible ; obligatoire en CI."""
import json
import os
import urllib.request

import pytest

from tests.test_e2e_scene import INTERDITS, _chromium, url  # noqa: F401  (serveur démo isolé partagé)

CAPTURES = os.environ.get("HACKVS_CAPTURES")


def _sans_debordement(pg):
    return pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")


def test_console_demo_guidee_complete(url):  # noqa: F811
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        b = _chromium(p)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.set_default_timeout(90_000)
        erreurs: list[str] = []
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
        pg.goto(url + "/console")
        pg.click("#reinit")
        pg.wait_for_function("document.querySelector('#etape').textContent.includes('Étape 0/10')")
        for i in range(1, 11):
            pg.click("#suivant")
            try:
                pg.wait_for_function(f"document.querySelector('#etape').textContent.includes('Étape {i}/10')")
            except Exception as e:                                          # message utile en cas d'échec
                raise AssertionError((i, pg.inner_text("#etape"), pg.inner_text("#toasts"), erreurs,
                                      pg.evaluate("document.querySelector('#suivant').disabled"))) from e
            texte = pg.inner_text("main") + pg.inner_text("#legende")
            assert not any(x in texte for x in INTERDITS), (i, texte[:400])
            if i == 3:
                pg.wait_for_selector("#phases li")                           # phases RÉELLES du scan affichées
            if i == 5:                                                       # le téléphone montre Anna : demande anonyme
                tel = pg.frame_locator("#tel")
                tel.locator("text=Un membre du Club a une demande").first.wait_for()
                assert "Sophie" not in tel.locator("main").inner_text()
            if CAPTURES:
                pg.screenshot(path=f"{CAPTURES}/console-{i}.png")
        assert "demandes débloquées" in pg.inner_text("#situation")
        pg.locator("#activations button").first.click()
        pg.wait_for_selector("#detail .chrono li")
        assert "Anna" not in pg.inner_text("#detail")                        # même le Club ne voit pas qui a décliné
        assert _sans_debordement(pg)
        b.close()
    assert erreurs == []


@pytest.mark.parametrize("taille", [(390, 844), (412, 915)])                 # iPhone / Android
def test_application_membre_de_l_invitation_au_pouls(url, taille):  # noqa: F811
    pw = pytest.importorskip("playwright.sync_api")
    console = {"Content-Type": "application/json", "X-Pulse-Console": "1"}
    urllib.request.urlopen(urllib.request.Request(url + "/api/pulse/demo/reinitialiser", data=b"{}", headers=console))
    personas = urllib.request.urlopen(urllib.request.Request(url + "/api/pulse/console/personas", headers=console)).read()
    code = next(x["code"] for x in json.loads(personas) if x["id"] == "n01")
    with pw.sync_playwright() as p:
        b = _chromium(p)
        pg = b.new_page(viewport={"width": taille[0], "height": taille[1]})
        pg.set_default_timeout(90_000)
        erreurs: list[str] = []
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
        pg.goto(url + f"/app?code={code}#acces")
        pg.click("text=Continuer")
        pg.wait_for_selector("text=Identité (importée de votre adhésion)")
        pg.fill("#t-aide", "tisanes de plantes alpines bio")
        pg.locator("button:has-text('Proposer')").first.click()
        pg.locator("button:has-text('Production de boissons')").first.click()
        pg.fill("#t-cherche", "faire valider la conformité de nos étiquettes pour le marché allemand")
        pg.locator("button:has-text('Proposer')").nth(1).click()
        pg.wait_for_selector("button:has-text('Emballage et étiquetage')")  # le moteur propose « emballage »…
        pg.locator("button:has-text('garder tel quel')").last.click()       # …le membre corrige
        pg.check("#visible")
        pg.click("text=Terminer")
        pg.wait_for_selector("text=Ce que votre réseau peut faire maintenant")
        pg.click("nav.onglets >> text=Mémoire")
        pg.fill("#note", "Rencontré Markus à la Foire du Valais : il représente des marques bio en Allemagne et cherche des "
                         "producteurs de boissons. Je dois aussi faire traduire mes étiquettes.")
        pg.click("text=Garder cette note")
        pg.wait_for_selector("text=visible par vous seul·e")
        pg.locator("button:has-text('Traduction')").first.click()
        pg.wait_for_selector("text=partagé")
        pg.click("nav.onglets >> text=Pouls")
        pg.wait_for_selector(".item.opportunite")
        pg.locator(".item.opportunite").first.click()
        pg.wait_for_selector("text=Opportunité détectée")
        texte = pg.inner_text("main")
        assert "Anna" not in texte and "une personne du Club" in texte       # identité cachée avant accord
        assert not any(x in texte for x in INTERDITS) and _sans_debordement(pg)
        if CAPTURES:
            pg.screenshot(path=f"{CAPTURES}/app-{taille[0]}-opportunite.png", full_page=True)
        pg.click("nav.onglets >> text=Profil")
        pg.wait_for_selector("text=Je peux aider avec")
        assert _sans_debordement(pg)
        b.close()
    assert erreurs == []
