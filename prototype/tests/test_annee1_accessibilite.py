"""ANNÉE 1 · LOT 11 — Accessibilité WCAG 2.2 AA vérifiée AUTOMATIQUEMENT : axe-core (copie dans tests/vendor, licence
MPL-2.0) tourne dans un vrai Chromium sur chaque page servie, dans ses états remplis (téléphone connecté, console,
secrétariat élevé, borne avec jeton), tous interrupteurs ALLUMÉS, puis sur la démo telle quelle (interrupteurs éteints).

Ce que cela prouve, et pas plus : aucune violation des règles AUTOMATISABLES d'axe pour les étiquettes wcag2a, wcag2aa,
wcag21a, wcag21aa, wcag22aa. Une bonne partie des critères WCAG (ordre de lecture sensé, sens des alternatives, usage au
lecteur d'écran…) ne se vérifie pas par machine : elle reste à éprouver par des personnes (docs/annee-1/qualite)."""
import hashlib
import hmac
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

AXE = Path(__file__).parent / "vendor" / "axe-core-4.13.0" / "axe.min.js"
AXE_SHA256 = "c24f097bd2f451d4f933e8bc7d8d539f8672a2ebcb5cc9f9f3eec8ca9470a0c1"
ETIQUETTES = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
CONSOLE = {"Content-Type": "application/json", "X-Pulse-Console": "1"}
TOUT_ALLUME = dict(HACKVS_FOIRE="1", HACKVS_COMPTES="1", HACKVS_ESPACE_MEMBRE="1", HACKVS_SECRETARIAT="1",
                   HACKVS_NOTIFICATIONS="1", HACKVS_MULTICLUB="1", HACKVS_FOIRE_ALLUMAGE="1", HACKVS_EID="1",
                   HACKVS_SUIVI_IA="1", HACKVS_HORS_LIGNE="1", HACKVS_SECRET="a" * 40,
                   HACKVS_CRITERES_PILOTE=str(Path(__file__).resolve().parents[2] / "docs/annee-1/pilote/criteres.json"))
ECRANS = ("/console", "/etabli", "/projection", "/suivi", "/salle", "/salle/ecran", "/salle/regie", "/demo/regie",
          "/decouverte", "/reponse", "/confidentialite", "/feuille-de-route", "/preflight")


def _axe() -> str:
    source = AXE.read_bytes()
    assert hashlib.sha256(source).hexdigest() == AXE_SHA256, "copie d'axe-core altérée"
    return source.decode("utf-8")


def _violations(pg) -> list[str]:
    """axe dans la page (evaluate : hors de la CSP de la page, qui reste celle servie aux membres)."""
    pg.wait_for_load_state("networkidle")              # les lectures de données de l'écran sont terminées (audit M3)
    pg.wait_for_timeout(300)
    pg.evaluate(_axe())
    r = pg.evaluate("""async (tags) => (await axe.run(document, {runOnly: {type: 'tag', values: tags}})).violations
        .map(v => `${v.id} (${v.impact}) : ` + v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(' ; '))""", ETIQUETTES)
    return list(r)


def _api(base, chemin, corps=None):
    req = urllib.request.Request(base + chemin, data=json.dumps(corps).encode() if corps is not None else None, headers=CONSOLE)
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def _telephone_connecte(b, base):
    _api(base, "/api/pulse/demo/reinitialiser", {})
    _api(base, "/api/pulse/demo/aller/4", {})
    code = {p["id"]: p["code"] for p in _api(base, "/api/pulse/console/personas")}["n01"]
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.goto(f"{base}/app?code={code}#acces")
    pg.click("text=Continuer")
    pg.wait_for_selector("h1:has-text('Mes actions')")
    return pg


def _balayer_telephone(b, base, ko):
    pg = _telephone_connecte(b, base)
    for onglet in ("actions", "action", "nouveau", "souvenirs", "demandes"):
        pg.click(f"nav.onglets a[data-o={onglet}]")
        ko[f"/app#{onglet}"] = _violations(pg)
    for ancre in ("donnees", "pouls"):
        pg.evaluate(f"location.hash = '#{ancre}'")
        ko[f"/app#{ancre}"] = _violations(pg)
    return pg


def test_axe_detecte_bien_une_violation_contre_preuve(tmp_path):
    """Le harnais n'est pas vacant : un champ sans étiquette injecté dans une vraie page est signalé."""
    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    with serveur(HACKVS_ESSAIS_DB=str(tmp_path / "j.db")) as base, sync_playwright() as p:
        b = _chromium(p)
        pg = b.new_page()
        pg.goto(base + "/confidentialite")
        assert _violations(pg) == []
        pg.evaluate("document.body.appendChild(Object.assign(document.createElement('select'), {id: 'piege'}))")
        assert any(v.startswith("select-name") and "#piege" in v for v in _violations(pg))
        b.close()


def test_wcag22_aa_toutes_les_pages_tout_allume(tmp_path):
    from playwright.sync_api import sync_playwright

    from intelligence import foire_allumage as fa
    from intelligence.reglages import Reglages
    from tests.aide_comptes import elever_http
    from tests.test_e2e_scene import _chromium, serveur
    env = TOUT_ALLUME | {"HACKVS_ESSAIS_DB": str(tmp_path / "j.db")}
    ko: dict[str, list[str]] = {}
    with serveur(**env) as base, sync_playwright() as p:
        admin = subprocess.run([sys.executable, "scripts/comptes.py", "amorcer", "Administration fictive"], capture_output=True,
                               text=True, cwd=Path(__file__).resolve().parents[1],
                               env={**os.environ, **env}).stdout.strip().splitlines()[-1]
        elever_http(base, admin)
        b = _chromium(p)
        # d'abord l'administration : la démo réinitialisée plus bas repart d'un monde neuf (comptes compris)
        adm = b.new_page(viewport={"width": 1100, "height": 900})
        adm.goto(base + "/compte")
        adm.evaluate("(s) => sessionStorage.setItem('compte-session', s)", admin)
        adm.goto(base + "/compte")
        ko["/compte (administration)"] = _violations(adm)
        adm.goto(base + "/secretariat")
        adm.locator("#pilote tr").first.wait_for()
        ko["/secretariat (administration élevée)"] = _violations(adm)
        tel = _balayer_telephone(b, base, ko)
        session = tel.evaluate("sessionStorage.getItem('pulse-session')")
        for chemin in ("/espace", "/attestation"):
            tel.goto(f"{base}{chemin}?session={session}")
            ko[f"{chemin} (membre)"] = _violations(tel)
        tel.goto(f"{base}/app?lang=en#actions")
        ko["/app (EN)"] = _violations(tel)
        tel.goto(f"{base}/app?lang=de#actions")
        ko["/app (DE)"] = _violations(tel)
        nu = b.new_page(viewport={"width": 390, "height": 844})
        for chemin in ("/app", "/compte", "/desinscription", "/borne", "/attestation", "/espace", "/secretariat"):
            nu.goto(base + chemin)
            ko[f"{chemin} (sans session)"] = _violations(nu)
        cle = hmac.new(Reglages.depuis_env({"HACKVS_SECRET": env["HACKVS_SECRET"]}).secret, b"bornes|annee-1",
                       hashlib.sha256).digest()
        borne = b.new_page()
        borne.goto(f"{base}/borne#b={fa.jeton_borne(cle, 'stand-test')}")
        ko["/borne (jeton)"] = _violations(borne)
        borne.click("#prendre")
        borne.locator("#ref").wait_for()
        ko["/borne (passe remise)"] = _violations(borne)
        grand = b.new_page(viewport={"width": 1440, "height": 900})
        for chemin in ECRANS:
            grand.goto(base + chemin)
            ko[chemin] = _violations(grand)
        b.close()
    assert len(ko) >= 30
    assert not {k: v for k, v in ko.items() if v}, {k: v for k, v in ko.items() if v}


def test_wcag22_aa_la_demo_telle_quelle(tmp_path):
    """Interrupteurs éteints : les pages de la DÉMO (téléphone, écrans) passent les mêmes règles."""
    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    ko: dict[str, list[str]] = {}
    with serveur(HACKVS_FOIRE="1", HACKVS_ESSAIS_DB=str(tmp_path / "j.db")) as base, sync_playwright() as p:
        b = _chromium(p)
        _balayer_telephone(b, base, ko)
        grand = b.new_page(viewport={"width": 1440, "height": 900})
        for chemin in ECRANS:
            grand.goto(base + chemin)
            ko[chemin] = _violations(grand)
        b.close()
    assert not {k: v for k, v in ko.items() if v}, {k: v for k, v in ko.items() if v}
