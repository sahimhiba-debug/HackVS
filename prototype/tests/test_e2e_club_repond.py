"""Bout en bout dans un VRAI navigateur : « Le Club répond » (bureau puis mobile), le mode jury, le téléchargement.

Même règle que la scène : ignoré seulement si aucun Chromium n'est disponible ; obligatoire en CI.
"""
import os

import pytest

from tests.test_e2e_scene import INTERDITS, _chromium, url  # noqa: F401  (fixture partagée : un serveur démo isolé)

CAPTURES = os.environ.get("HACKVS_CAPTURES")          # dossier optionnel : captures d'écran pour la revue visuelle


def _parcours(pg, base, largeur):
    pg.goto(base + "/demo/club-repond")
    pg.click("#reinit")
    pg.wait_for_function("document.querySelector('#horloge').textContent.includes('étape 0/')")
    total = int(pg.inner_text("#horloge").split("/")[-1])
    for i in range(1, total + 1):
        pg.click("#suiv")
        pg.wait_for_function(f"document.querySelector('#horloge').textContent.includes('étape {i}/')")
        texte = pg.inner_text("#carte")
        assert not any(x in texte for x in INTERDITS), (i, texte)
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), f"débordement horizontal étape {i}"
        if CAPTURES:
            pg.screenshot(path=f"{CAPTURES}/club-{largeur}-{i}.png", full_page=True)
        if i == 2:
            assert "Anna Zufferey" in texte and "Markus Heinzmann" in texte and "membres non dérangés" in texte
        if i == 3:
            assert "Une personne du Club" in texte and "Tisanes" not in texte
        if i == 5:
            assert "DÉBLOQUÉE" in texte
        if i == 6:
            assert "Réponse immédiate" in texte and "à vérifier" in texte
    return total


def test_club_repond_bureau_mobile_jury_et_fiche(url):  # noqa: F811
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        b = _chromium(p)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.set_default_timeout(90_000)
        erreurs: list[str] = []
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
        _parcours(pg, url, 1440)
        for n in (7, 6):                                   # une action à la fois (un double clic est ignoré)
            pg.click("#prec")
            pg.wait_for_function(f"document.querySelector('#horloge').textContent.includes('étape {n}/')")
        # la fiche confirmée se télécharge, avec sa provenance et la mention « fictif »
        with pg.expect_download() as dl:
            pg.click("#carte a[download]")
        contenu = open(dl.value.path(), encoding="utf-8").read()
        assert "Provenance" in contenu and "FICTIVES" in contenu and "Sophie" not in contenu
        # mode jury : trois comportements distincts, tous calculés, rien n'est écrit
        avant = pg.inner_text("#horloge")
        for bouton, attendu in (("ambiguë", "Une seule question"), ("hors du Club", "ne peut pas aider"),
                                ("contrainte", "Plus petite modification")):
            pg.click(f".essais button:has-text('{bouton}')")
            pg.wait_for_function(f"document.querySelector('#verdict').innerText.includes({attendu!r})")
            assert not any(x in pg.inner_text("#verdict") for x in INTERDITS)
        pg.fill("#texte", "Je cherche une traductrice pour nos étiquettes.")
        pg.click("#essayer")
        pg.wait_for_function("document.querySelector('#verdict').innerText.includes('Anna Zufferey')")
        assert pg.inner_text("#horloge") == avant
        mob = b.new_page(viewport={"width": 390, "height": 844})
        mob.set_default_timeout(90_000)
        mob.on("pageerror", lambda e: erreurs.append(str(e)))
        _parcours(mob, url, 390)
        b.close()
    assert erreurs == []
