"""Le serveur des tests de bout en bout (`tests/test_e2e_scene.serveur`) : déclaré prêt dès qu'il répond, et un serveur
qui NE DÉMARRE PAS est une erreur immédiate et claire — jamais 20 s d'attente aveugle suivies d'échecs trompeurs.
(F03 : la sonde interrogeait `/api/stage`, hors du périmètre servi depuis la Phase 1 : 404, pris pour « pas prêt ».)"""
import re
import time

import pytest

from tests.test_e2e_scene import serveur


def test_un_serveur_sain_est_pret_en_quelques_secondes():
    t = time.perf_counter()
    with serveur():
        pret = time.perf_counter() - t
    assert pret < 10, f"prêt après {pret:.1f} s"


def test_un_serveur_qui_ne_demarre_pas_est_une_erreur_claire():
    t = time.perf_counter()
    with pytest.raises(RuntimeError, match="serveur de démonstration non démarré"):
        with serveur(HACKVS_SECRET="x" * 10):                          # Reglages refuse un secret < 32 caractères
            pass
    assert time.perf_counter() - t < 15


def test_le_serveur_e2e_tourne_dans_la_configuration_du_produit():
    """Les E2E testent le produit tel qu'il est servi : SANS l'ancien prototype (drapeau éteint), même si la suite en
    processus l'allume (conftest). Sinon un chemin bloqué par le périmètre en réalité passerait en E2E."""
    import urllib.error
    import urllib.request
    with serveur() as base:
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base + "/api/etat", timeout=5)          # route de l'ancien prototype
        assert e.value.code == 404
        assert urllib.request.urlopen(base + "/etabli", timeout=5).status == 200


# --------------------------------------------------------------- jeton de console (déploiement accessible du réseau)
# Avec HACKVS_CONSOLE_JETON (Cloud Run, tout serveur joignable d'ailleurs), chaque appel de console exige ce jeton exact.
# Vérifié dans un vrai conteneur le 01.10 : la régie envoyait toujours « 1 » (403), et l'Établi et la projection, ouverts
# par les liens de la console (nouvel onglet, rel=noopener : sessionStorage NON copié), restaient en 403 sans rien
# demander. Exigences : le jeton suit dans un nouvel onglet SANS passer par l'URL ni par un stockage durable, et la
# protection reste entière (sans jeton, ou avec un faux, rien ne s'ouvre).
JETON_E2E = "jeton-console-e2e-" + "k" * 24
ECRANS = {"/console": "date simulée", "/etabli": "date du Club", "/projection": "date simulée|jour des offres"}   # écrits après un appel réussi


@pytest.fixture(scope="module")
def url_jeton():
    with serveur(HACKVS_CONSOLE_JETON=JETON_E2E) as base:
        yield base


def _contexte(b, reponse_au_dialogue):
    """Un navigateur d'animatrice : chaque demande de jeton (window.prompt) est comptée, par page, et reçoit
    `reponse_au_dialogue` (None = « Annuler »). Toutes les URL demandées et les refus de console sont relevés."""
    ctx = b.new_context()
    journal = {"dialogues": [], "urls": [], "refus": []}

    def repondre(d):
        journal["dialogues"].append(d.page.url if d.page else "?")
        d.accept(reponse_au_dialogue) if reponse_au_dialogue is not None else d.dismiss()
    ctx.on("dialog", repondre)
    ctx.on("request", lambda r: journal["urls"].append(r.url))
    ctx.on("response", lambda r: journal["refus"].append(r.url) if r.status == 403 and "/api/pulse/console/" in r.url else None)
    return ctx, journal


def _ouvert(pg, chemin):
    pg.wait_for_function("t => new RegExp(t).test((document.querySelector('#date') || {}).textContent || '')", arg=ECRANS[chemin], timeout=15_000)


def _jeton_jamais_expose(ctx, journal):
    assert not [u for u in journal["urls"] if JETON_E2E in u], "le jeton est passé dans une URL"
    for pg in ctx.pages:
        assert JETON_E2E not in (pg.evaluate("JSON.stringify(localStorage)") or ""), f"jeton en stockage durable : {pg.url}"


def test_l_etabli_et_la_projection_ouverts_depuis_la_console_recoivent_le_jeton(url_jeton):
    pw = pytest.importorskip("playwright.sync_api")
    from tests.test_e2e_scene import _chromium
    with pw.sync_playwright() as p:
        b = _chromium(p)
        ctx, journal = _contexte(b, JETON_E2E)
        c = ctx.new_page()
        c.goto(url_jeton + "/console")
        _ouvert(c, "/console")
        assert len(journal["dialogues"]) == 1                                  # demandé une fois, à la console
        for lien, chemin in [("Ouvrir l'établi des capacités", "/etabli"), ("Ouvrir la projection", "/projection")]:
            with ctx.expect_page() as nouvelle:
                c.get_by_role("link", name=lien).click()
            n = nouvelle.value
            assert n.evaluate("window.opener") is None                         # toujours noopener : rien n'a été relâché
            _ouvert(n, chemin)
            assert n.url == url_jeton + chemin                                 # rien dans l'URL
        assert len(journal["dialogues"]) == 1, journal["dialogues"]            # les nouveaux onglets n'ont rien redemandé
        _jeton_jamais_expose(ctx, journal)
        b.close()


def test_la_regie_utilise_le_jeton_de_console(url_jeton):
    pw = pytest.importorskip("playwright.sync_api")
    from tests.test_e2e_scene import _chromium
    with pw.sync_playwright() as p:
        b = _chromium(p)
        # 1. ouverte seule (aucun autre onglet) : le jeton est demandé, puis la régie se monte
        ctx, journal = _contexte(b, JETON_E2E)
        r = ctx.new_page()
        r.goto(url_jeton + "/demo/regie")
        r.wait_for_function("() => window.pret === true", timeout=15_000)
        assert len(journal["dialogues"]) == 1
        pw.expect(r.frame_locator("#projection").locator("#date")).to_have_text(re.compile(ECRANS["/projection"]), timeout=15_000)
        _jeton_jamais_expose(ctx, journal)
        ctx.close()
        # 2. console déjà déverrouillée dans un autre onglet : la régie, ouverte à la main, ne redemande rien
        ctx, journal = _contexte(b, JETON_E2E)
        c = ctx.new_page()
        c.goto(url_jeton + "/console")
        _ouvert(c, "/console")
        r = ctx.new_page()
        r.goto(url_jeton + "/demo/regie")
        r.wait_for_function("() => window.pret === true", timeout=15_000)
        assert len(journal["dialogues"]) == 1, journal["dialogues"]
        _jeton_jamais_expose(ctx, journal)
        b.close()


@pytest.mark.parametrize("reponse", [None, "un-faux-jeton-de-console-" + "z" * 20], ids=["annule", "faux"])
def test_sans_le_bon_jeton_rien_ne_s_ouvre(url_jeton, reponse):
    """Contre-épreuve : la passation entre onglets n'affaiblit pas la garde. Annuler, ou donner un faux jeton : chaque
    écran reste fermé (403 à chaque appel), et un refus n'est pas redemandé en boucle à chaque rafraîchissement."""
    pw = pytest.importorskip("playwright.sync_api")
    from tests.test_e2e_scene import _chromium
    with pw.sync_playwright() as p:
        b = _chromium(p)
        for chemin in ["/console", "/etabli", "/projection", "/demo/regie"]:
            ctx, journal = _contexte(b, reponse)
            pg = ctx.new_page()
            pg.goto(url_jeton + chemin)
            pg.wait_for_timeout(3500)                                          # plusieurs cycles de rafraîchissement
            if chemin in ECRANS:
                assert not re.search(ECRANS[chemin], pg.text_content("#date") or ""), chemin
            else:
                assert pg.evaluate("window.pret") is not True
            assert journal["refus"], chemin
            assert len(journal["dialogues"]) <= (1 if reponse is None else 2), (chemin, journal["dialogues"])
            ctx.close()
        b.close()
