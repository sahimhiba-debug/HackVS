"""MODE SALLE dans un VRAI navigateur : la télécommande ouvre la salle ; l'écran géant montre le QR et le compteur ;
quatre téléphones scannent, choisissent une capacité et consentent (deux gestes) ; la demande part ; trois « Oui »
ferment l'anneau sur l'écran ; un participant retire son consentement → la réserve reprend la pièce (recomposition) ;
la télécommande affiche le bilan ; la purge efface tout. Données FICTIVES (aucun nom n'est jamais saisi)."""
import pytest

from tests.test_e2e_pulse import _api, _sans_debordement
from tests.test_e2e_scene import _chromium, serveur


@pytest.fixture(scope="module")
def url_salle():
    with serveur(HACKVS_FOIRE="1", HACKVS_SALLE="1", HACKVS_SALLE_MIN="2") as base:
        yield base


def test_le_club_c_est_vous(url_salle):
    from playwright.sync_api import sync_playwright
    erreurs: list[str] = []
    with sync_playwright() as p:
        b = _chromium(p)
        regie = b.new_context(viewport={"width": 420, "height": 860}).new_page()
        regie.set_default_timeout(30_000)
        regie.on("pageerror", lambda e: erreurs.append(str(e)))
        ecran = b.new_context(viewport={"width": 1600, "height": 900}).new_page()
        ecran.set_default_timeout(30_000)
        ecran.on("pageerror", lambda e: erreurs.append(str(e)))
        regie.goto(url_salle + "/salle/regie")
        _api(url_salle, "/api/pulse/console/salle/purger", {})
        regie.click("#ouvrir")
        ecran.goto(url_salle + "/salle/ecran")
        ecran.locator("#qr img").wait_for()
        lien = _api(url_salle, "/api/pulse/console/salle")["url"]
        telephones = []
        for capacite in ("voiture", "voiture", "salle", "allemand"):
            t = b.new_context(viewport={"width": 390, "height": 844}).new_page()
            t.set_default_timeout(30_000)
            t.on("pageerror", lambda e: erreurs.append(str(e)))
            t.goto(lien)
            t.click(f"[data-capacite={capacite}]")
            t.check("#consens")
            t.click("#valider")
            t.locator("[data-role=recu]").wait_for()
            assert "s=" not in t.url and "effacées après la présentation" in t.inner_text("body")
            telephones.append(t)
        ecran.locator("[data-role=participants]:has-text('4')").wait_for()
        regie.click("#lancer")
        for t in (telephones[0], telephones[2], telephones[3], telephones[1]):
            t.locator("[data-choix=oui]").click()
            t.locator("[data-role=message]").wait_for()
        ecran.locator("[data-role=anneau][data-fermee=true]").wait_for()
        telephones[0].locator("#retirer").click()
        telephones[0].locator("[data-role=message]:has-text('Personne ne sera prévenu')").wait_for()
        ecran.locator(".fil >> text=recomposition").wait_for()
        ecran.locator("[data-role=anneau][data-fermee=true]").wait_for()
        assert "transport :" not in ecran.inner_text(".fil")                 # 2 porteurs de « voiture » : rôle non dit
        regie.click("#bilan")
        ecran.locator("[data-role=bilan]:has-text('cette salle a rendu possible')").wait_for()
        assert _sans_debordement(telephones[0])
        regie.once("dialog", lambda d: d.accept())
        regie.click("#purger")
        ecran.locator("[data-role=participants]:has-text('0')").wait_for()
        telephones[1].wait_for_timeout(2500)
        telephones[1].locator("[data-role=invalide]").wait_for()              # le passe ne vaut plus rien
        b.close()
    assert not [e for e in erreurs if "401" not in e], erreurs


def test_bascule_vers_la_demo_scriptee_si_la_salle_est_vide(url_salle):
    from intelligence.salle import Salle
    h = [0.0]
    s = Salle(b"x" * 32, minimum=2, horloge=lambda: h[0])
    s.ouvrir()
    h[0] = 61
    assert s.ecran()["bascule"] is True
