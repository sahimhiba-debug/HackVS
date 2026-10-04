"""DECK v3 (docs/presentation/deck/v3.html) — le deck « spectaculaire », en motion design, pour une salle dans la
pénombre. Il vit À CÔTÉ de v2 (plan B, intact, que le lanceur continue d'ouvrir). Mêmes slides, mêmes clics, même
texte que v2 : le script, le prompteur et les chronos restent justes. Tout est local (aucune ressource externe).
Le fil visuel : les membres sont des points lumineux (canvas)."""
import json
import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[2]
DECK = RACINE / "docs" / "presentation" / "deck"
V3 = DECK / "v3.html"


def _html(nom="v3.html") -> str:
    return (DECK / nom).read_text(encoding="utf-8")


def _ids(html: str) -> list[str]:
    return re.findall(r'<section class="[^"]*slide[^"]*"[^>]*data-id="([^"]+)"', html)


def _pas(html: str) -> list[tuple[str, str]]:
    sections = re.findall(r'<section class="[^"]*slide[^"]*"[^>]*>', html)
    return [(re.search(r'data-id="([^"]+)"', s).group(1), (re.search(r'data-pas="(\d+)"', s) or [None, "0"])[1]) for s in sections]


# ------------------------------------------------------------------ v2 intact, v3 à côté, le lanceur ouvre v2
def test_v3_existe_a_cote_de_v2_et_le_lanceur_ouvre_toujours_v2():
    assert V3.exists()
    assert "v2.html" in (RACINE / "1 - Lancer Club Pulse.command").read_text(encoding="utf-8")
    assert "v3.html" not in (RACINE / "1 - Lancer Club Pulse.command").read_text(encoding="utf-8")


def test_memes_slides_memes_clics_que_v2():
    assert _ids(_html()) == _ids(_html("v2.html"))
    assert _pas(_html()) == _pas(_html("v2.html"))


def test_texte_verrouille_identique():
    v3 = re.sub(r"<[^>]+>", " ", _html())
    for phrase in ("La Foire crée la rencontre.", "Club Pulse crée", "Cette année, la Foire fait son cinéma.", "Nous aussi.",
                   "Un pilote de 45 jours avec 50 membres volontaires parmi vos 173 représentants.",
                   "Regardez votre téléphone :", "vous avez un reçu.", "Hier, vous nous avez dit…",
                   "On y a travaillé jusqu'au soir.", "Et après"):
        assert phrase in re.sub(r"\s+", " ", v3), phrase
    assert "Public AI" not in v3 and "certifié" not in v3


# ------------------------------------------------------------------ hors ligne, mouvement, accessibilité
def test_aucune_ressource_externe():
    h = _html()
    externes = [u for u in re.findall(r'(?:src|href)\s*=\s*["\'](https?://[^"\']+)', h)]
    assert externes == [], externes
    assert "@import" not in h and "fonts.googleapis" not in h and "cdn" not in h.lower()


def test_un_seul_langage_de_mouvement():
    h = _html()
    assert "cubic-bezier(0.22, 1, 0.36, 1)" in h
    durees = set(int(x) for x in re.findall(r"(\d+)ms", h))
    assert durees <= {240, 480, 720}, durees


def test_nuit_par_defaut_jour_sur_J_et_mouvement_coupe_sur_M():
    h = _html()
    assert 'return "nuit"' in h and '"j" || k === "J"' in h
    assert '"m" || k === "M"' in h and "prefers-reduced-motion" in h


def test_le_film_le_plan_b_la_constellation_le_qr_et_les_chronos_sont_la():
    h = _html()
    for x in ('id="film"', 'class="planb"', 'id="ecran-salle"', 'id="video-constellation"', 'data-chemin="/qr/salle.svg"',
              'data-id="ea3"', "const CP = [", "club-pulse-jeton-manquant", 'src="assets/film.mp4"'):
        assert x in h, x


# ------------------------------------------------------------------ dans un vrai navigateur
@pytest.fixture(scope="module")
def deck():
    import functools
    import http.server
    import socketserver
    import threading

    class Muet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Muet, directory=str(DECK)))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _page(p, deck, url="v3.html", reduit=False):
    from tests.test_e2e_scene import _chromium
    b = _chromium(p)
    ctx = b.new_context(viewport={"width": 1920, "height": 1080}, reduced_motion="reduce" if reduit else "no-preference")
    pg = ctx.new_page()
    erreurs: list[str] = []
    pg.on("pageerror", lambda e: erreurs.append(str(e)))
    externes: list[str] = []
    pg.on("request", lambda r: externes.append(r.url) if not r.url.startswith((deck, "data:", "http://127.0.0.1:8000")) else None)
    pg.goto(f"{deck}/{url}")
    pg.evaluate("window.pret")
    return b, pg, erreurs, externes


def test_chaque_slide_et_chaque_pas_s_affichent_sans_erreur_ni_requete_externe(deck):
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b, pg, erreurs, externes = _page(p, deck)
        assert pg.evaluate("document.body.classList.contains('jour')") is False          # nuit par défaut
        n = 0
        for sid in pg.evaluate("SLIDES"):
            for k in range(pg.evaluate(f"pasDe({json.dumps(sid)})") + 1):
                pg.evaluate(f"allerA({json.dumps(sid)}, {k})")
                pg.wait_for_timeout(60)
                n += 1
        pg.wait_for_timeout(500)
        assert n > 30
        assert pg.evaluate("window.points && window.points.vivant()") is True        # le champ de points tourne
        b.close()
    assert not erreurs, erreurs
    assert not externes, externes


def test_un_clic_au_milieu_d_une_animation_la_termine_aussitot(deck):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b, pg, erreurs, _ = _page(p, deck)
        pg.evaluate("allerA('1', 0)")
        pg.keyboard.press("ArrowRight")                     # la carte se dissout en points…
        pg.wait_for_timeout(80)
        assert pg.evaluate("window.points.enCours()") is True
        pg.keyboard.press("ArrowRight")                     # …un clic : l'animation est terminée, on avance
        pg.wait_for_timeout(30)
        assert pg.evaluate("window.points.enCours()") is False
        assert pg.evaluate("location.hash") == "#matin.1"
        b.close()
    assert not erreurs, erreurs


def test_M_coupe_le_mouvement_et_le_mouvement_reduit_est_respecte(deck):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b, pg, erreurs, _ = _page(p, deck)
        pg.keyboard.press("m")
        assert pg.evaluate("document.body.classList.contains('sans-mouvement')") is True
        assert pg.evaluate("window.points.mouvement()") is False
        pg.keyboard.press("m")
        assert pg.evaluate("window.points.mouvement()") is True
        b.close()
        b, pg, erreurs2, _ = _page(p, deck, reduit=True)
        assert pg.evaluate("window.points.mouvement()") is False
        b.close()
    assert not erreurs and not erreurs2


def test_60_images_par_seconde_visees_et_version_allegee_sous_30(deck):
    """Mesuré avec un processeur ralenti 4 fois (CDP) : soit ≥ 30 i/s, soit la version allégée a pris le relais."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b, pg, erreurs, _ = _page(p, deck)
        cdp = pg.context.new_cdp_session(pg)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        pg.evaluate("allerA('stat', 0)")                    # le champ le plus dense : la Foire, les liens
        pg.wait_for_timeout(4000)
        m = pg.evaluate("window.points.mesure()")
        assert m["ips"] >= 30 or m["allege"] is True, m
        b.close()
    assert not erreurs, erreurs


def test_contraste_AA_en_mode_nuit(deck):
    from playwright.sync_api import sync_playwright
    axe = (RACINE / "prototype" / "tests" / "vendor" / "axe-core-4.13.0" / "axe.min.js")
    if not axe.exists():
        pytest.skip("axe-core absent de cette branche")
    with sync_playwright() as p:
        b, pg, erreurs, _ = _page(p, deck)
        ko = {}
        for sid in ("matin", "stat", "2", "salle", "chiffres-club", "assembler", "science", "preuves", "ou", "jalons",
                    "suisse", "demande", "19", "21"):
            pg.evaluate(f"allerA({json.dumps(sid)}, 'max')")
            pg.wait_for_timeout(900)
            pg.evaluate(axe.read_text(encoding="utf-8"))
            r = pg.evaluate("""async () => (await axe.run(document.querySelector('.slide.active'),
                {runOnly: {type: 'rule', values: ['color-contrast']}})).violations.map(v => v.nodes.map(n => n.target.join(' ')).join(' ; '))""")
            if r:
                ko[sid] = r
        b.close()
    assert not ko, ko
