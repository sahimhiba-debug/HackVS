"""FOIRE 2026 dans un VRAI navigateur, interrupteur ALLUMÉ (serveur propre à ce fichier) : le scénario du juré.
La console (/suivi) affiche le QR du stand → le juré ouvre le lien sur « son » téléphone → déclare « Exposant invité
d'Annecy » (traiteur, Haute-Savoie) et reçoit son reçu → propose son aide sur une demande → « Rejoindre le Club » →
« prévu ensuite ». Le Suivi compte l'invité (« < 3 ») sans jamais afficher le nom déclaré. Données FICTIVES."""
import pytest

from tests.test_e2e_pulse import _sans_debordement
from tests.test_e2e_scene import _chromium, serveur


@pytest.fixture(scope="module")
def url_foire():
    with serveur(HACKVS_FOIRE="1") as base:
        yield base


def test_le_jure_devient_exposant_invite_d_annecy(url_foire):
    from playwright.sync_api import sync_playwright
    erreurs: list[str] = []
    with sync_playwright() as p:
        b = _chromium(p)
        console = b.new_context(viewport={"width": 1366, "height": 860}).new_page()
        console.set_default_timeout(30_000)
        console.on("pageerror", lambda e: erreurs.append(str(e)))
        console.goto(url_foire + "/suivi")
        console.locator("[data-role=monde]:has-text('monde de démonstration')").wait_for()
        console.locator("[data-tuile='Demandes envoyées']").wait_for()
        console.click("#qr-stand")
        console.locator("[data-role=qr-decouverte] img").wait_for()
        lien = console.locator("[data-role=qr-decouverte] a").get_attribute("href")
        assert lien and "/decouverte#passe=" in lien

        tel = b.new_context(viewport={"width": 390, "height": 844}).new_page()
        tel.set_default_timeout(30_000)
        tel.on("pageerror", lambda e: erreurs.append(str(e)))
        tel.goto(lien)
        tel.locator("#entreprise").wait_for()
        assert "passe=" not in tel.url                                  # le passe ne reste pas dans l'adresse
        assert "monde de démonstration" in tel.inner_text("header")
        tel.fill("#entreprise", "Exposant invité d'Annecy")
        tel.select_option("#metier", "traiteur")
        tel.select_option("#zone", "France — Haute-Savoie")
        tel.click("#declarer")
        tel.locator("[data-role=recu]:has-text('90 jours')").wait_for()
        tel.locator("[data-demande] >> text=Je peux aider").first.click()
        tel.locator("[data-role=message]:has-text('Proposition transmise')").wait_for()
        tel.click("#rejoindre")
        tel.locator("[data-role=prevu]:has-text('simulé en démonstration')").wait_for()
        tel.click("#langue")
        tel.locator("h1:has-text('Den Club kennenlernen')").wait_for()
        assert _sans_debordement(tel)

        tel2 = b.new_context().new_page()                               # le même lien, rescanné : rien
        tel2.goto(lien)
        tel2.locator("[data-role=invalide]").wait_for()

        console.locator("[data-passe] >> text=intention d'adhésion").wait_for()
        console.locator("[data-tuile='Invités ayant contribué'] .n:has-text('< 3')").wait_for()
        assert "Annecy" not in console.inner_text("body") and "Exposant" not in console.inner_text("body")
        console.click("#vues >> text=Le Club cherche")                   # E : les demandes sans réponse, par métier
        console.locator("[data-metier] [data-inviter]").first.click()
        console.locator("[data-role=invitation] textarea[data-langue=DE]").wait_for()
        assert "/decouverte#passe=" in console.input_value("[data-role=invitation] textarea[data-langue=FR]")
        assert "ohne Mitgliedschaft" in console.input_value("[data-role=invitation] textarea[data-langue=DE]")
        b.close()
    assert not erreurs, erreurs
