"""E2E HERMÉTIQUES : le Chromium des tests de bout en bout ne résout AUCUN domaine externe (seuls 127.0.0.1 et localhost),
et toute requête tentée vers l'extérieur fait ÉCHOUER le test qui l'a émise, même si la page s'est affichée. Une démo qui
dépend d'Internet sans le savoir échoue ici, pas dans la salle."""
import pytest

from tests.capture_e2e import externes_tentees, verifier_hermetique
from tests.test_e2e_scene import _chromium, url  # noqa: F401  (serveur démo isolé partagé)


def test_un_domaine_externe_est_bloque_et_la_tentative_est_signalee():
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = _chromium(p)
        pg = b.new_context().new_page()
        charge = []
        pg.on("requestfinished", lambda r: charge.append(r.url))
        pg.set_content('<img src="https://fonts.googleapis.com/hermetique.png"><link rel="stylesheet" href="http://example.org/x.css">')
        pg.wait_for_timeout(500)
        tentees = externes_tentees()
        assert not [u for u in charge if "googleapis" in u or "example.org" in u]      # rien n'est arrivé de l'extérieur
        assert {"https://fonts.googleapis.com/hermetique.png", "http://example.org/x.css"} <= set(tentees)
        with pytest.raises(AssertionError, match="E2E non hermétique"):
            verifier_hermetique()
        assert externes_tentees() == []                                               # la vérification vide la liste
        b.close()


def test_le_local_n_est_pas_signale(url):  # noqa: F811
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = _chromium(p)
        pg = b.new_page()
        pg.goto(url + "/etabli")
        pg.wait_for_selector("#date")
        assert externes_tentees() == []
        b.close()
