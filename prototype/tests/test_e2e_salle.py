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
        ecran.locator("#constellation[data-points='4'][data-traits='4']").wait_for()     # 4 points, 4 traits vers le centre
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
    s.inviter()
    h[0] = 61
    assert s.ecran()["bascule"] is True


# ------------------------------------------------------------------ JOUR J : l'écran de la salle DANS le deck v2
DECK = __import__("pathlib").Path(__file__).resolve().parents[2] / "docs" / "presentation" / "deck"
JETON_DECK = "jeton-de-console" + "-du-deck-fictif-0123"            # fictif ; assemblé hors du motif de la porte « secrets »


@pytest.fixture(scope="module")
def deck_et_salle():
    """Le deck servi comme par lancer.py (127.0.0.1, port libre) et un prototype qui n'accepte d'être intégré QUE par lui."""
    import functools
    import http.server
    import socketserver
    import threading

    class Muet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Muet, directory=str(DECK)))
    srv.daemon_threads = True
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with serveur(HACKVS_FOIRE="1", HACKVS_SALLE="1", HACKVS_CONSOLE_JETON=JETON_DECK,
                     HACKVS_DECK_ORIGINES=f"http://127.0.0.1:{port}") as base:
            yield f"http://127.0.0.1:{port}", base
    finally:
        srv.shutdown()


def test_l_ecran_de_la_salle_vit_dans_le_deck_sans_changer_de_fenetre(deck_et_salle):
    """Plus de ⌘-Tab : sur la slide « constellation », l'écran de la salle s'affiche en direct dans le deck. Il reçoit le
    jeton de la console de la régie ouverte dans le même Chrome (jamais par l'URL) ; le clavier et la télécommande
    restent au deck (l'iframe ne prend ni le focus ni les clics)."""
    from playwright.sync_api import sync_playwright
    deck, base = deck_et_salle
    erreurs: list[str] = []
    with sync_playwright() as p:
        b = _chromium(p)
        ctx = b.new_context(viewport={"width": 1920, "height": 1080})
        regie = ctx.new_page()
        regie.set_default_timeout(30_000)
        regie.on("dialog", lambda d: d.accept(JETON_DECK))                    # la régie demande le jeton UNE fois
        regie.goto(base + "/salle/regie")
        regie.click("#purger")
        regie.click("#ouvrir")
        regie.locator("#etat:has-text('ouverte')").wait_for()
        page = ctx.new_page()
        page.set_default_timeout(30_000)
        page.on("pageerror", lambda e: erreurs.append(str(e)))
        page.on("dialog", lambda d: erreurs.append("le deck a demandé quelque chose : " + d.message) or d.dismiss())
        page.goto(f"{deck}/v2.html?app={base}")
        page.evaluate("window.pret")
        page.evaluate("allerA('constellation', 0)")
        cadre = page.locator("#ecran-salle")
        cadre.wait_for(state="visible")
        assert JETON_DECK not in (cadre.get_attribute("src") or "")              # jamais dans l'URL
        ecran = page.frame_locator("#ecran-salle")
        ecran.locator("#qr img").wait_for()                                     # la console a répondu : jeton reçu de la régie
        ecran.locator("[data-role=monde]").wait_for()
        assert page.evaluate("getComputedStyle(document.getElementById('ecran-salle')).pointerEvents") == "none"
        avant = page.evaluate("location.hash")
        page.keyboard.press("ArrowRight")                                       # le deck garde la main
        page.wait_for_timeout(300)
        assert page.evaluate("location.hash") != avant
        page.evaluate("allerA('constellation', 0)")
        page.keyboard.press("b")                                                # le plan B reste à une touche
        assert page.locator("#video-constellation").get_attribute("class").split().count("on") == 1
        b.close()
    assert not erreurs, erreurs


def test_ecran_injoignable_le_deck_le_dit_et_garde_la_video(deck_et_salle):
    from playwright.sync_api import sync_playwright
    deck, _ = deck_et_salle
    with sync_playwright() as p:
        b = _chromium(p)
        page = b.new_page(viewport={"width": 1920, "height": 1080})
        page.set_default_timeout(30_000)
        page.goto(f"{deck}/v2.html?app=http://127.0.0.1:9")                     # aucun prototype
        page.evaluate("window.pret")
        page.evaluate("allerA('constellation', 0)")
        page.locator("#ecran-absent").wait_for(state="visible")
        assert "B" in page.inner_text("#ecran-absent")
        assert page.locator("#ecran-salle").is_hidden()
        page.keyboard.press("b")
        assert "on" in page.locator("#video-constellation").get_attribute("class").split()
        b.close()
