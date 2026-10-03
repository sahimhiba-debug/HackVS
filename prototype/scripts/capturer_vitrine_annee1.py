"""Vitrine ANNÉE 1 : captures RÉELLES des écrans construits sur la branche annee-1 (pas dans la démo).

    cd prototype && python scripts/capturer_vitrine_annee1.py [dossier]   # défaut : ../docs/annee-1/vitrine

Serveur neuf et isolé (monde FICTIF), interrupteurs annee-1 allumés. Chaque capture porte la mention « construit —
branche annee-1, pas dans la démo » à l'écran."""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for k in [k for k in os.environ if k.startswith(("APERTUS_", "OPENAI_"))] + ["ANTHROPIC_API_KEY", "LLM_PROVIDER"]:
    os.environ.pop(k, None)

from playwright.sync_api import sync_playwright  # noqa: E402

from intelligence.comptes import code_totp  # noqa: E402
from tests.test_e2e_scene import serveur  # noqa: E402

PROTO = Path(__file__).resolve().parents[1]
DOSSIER = Path(sys.argv[1]) if len(sys.argv) > 1 else PROTO.parent / "docs" / "annee-1" / "vitrine"
TELEPHONE = {"width": 390, "height": 844}


def main() -> None:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp()
    journal, secret = str(Path(tmp) / "j.db"), "v" * 40
    env = {"HACKVS_COMPTES": "1", "HACKVS_SECRETARIAT": "1", "HACKVS_ESSAIS_DB": journal, "HACKVS_SECRET": secret,
           "HACKVS_FOIRE": "1"}
    with serveur(**env) as base, sync_playwright() as p:
        admin = subprocess.run([sys.executable, "scripts/comptes.py", "amorcer", "Administration (fictive)"], capture_output=True,
                               text=True, cwd=PROTO, env={**os.environ, **env}).stdout.strip().splitlines()[-1]
        from tests.aide_comptes import elever_http
        elever_http(base, admin)                         # l'administration active son second facteur avant d'inviter

        def api(chemin: str, corps: dict, session: str) -> dict:
            req = urllib.request.Request(base + chemin, data=json.dumps(corps).encode(),
                                         headers={"Content-Type": "application/json", "X-Pulse-Compte": session})
            return json.load(urllib.request.urlopen(req))
        jeton = api("/api/pulse/comptes/admin/invitations", {"role": "secretariat", "etiquette": "Secrétariat 1 (fictif)",
                                                             "duree_s": 600}, admin)["jeton"]
        nav = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = nav.new_context(viewport=TELEPHONE).new_page()
        pg.goto(f"{base}/compte#invitation={jeton}")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(DOSSIER / "lot2-1-invitation.png"))
        pg.fill("#appareil", "Mac du secrétariat")
        pg.click("#accepter")
        pg.locator("#liste li").first.wait_for()
        pg.click("#preparer")
        pg.locator("#cle").wait_for(state="visible")
        pg.fill("#code", code_totp(pg.inner_text("#cle"), time.time()))
        pg.click("#confirmer")
        pg.locator("#etat:has-text('activée')").wait_for()
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(DOSSIER / "lot2-2-compte-totp.png"), full_page=True)
        # LOT 4 : la même session, élevée par un code, ouvre la console du secrétariat
        pg.fill("#code", code_totp(pg.inner_text("#cle"), time.time() + 30))
        pg.click("#elever")
        pg.locator("#qui:has-text('console ouverte')").wait_for()
        large = nav.new_context(viewport={"width": 1100, "height": 900}).new_page()
        large.goto(f"{base}/compte")                     # même origine : la session est dans sessionStorage de l'onglet
        large.evaluate("s => sessionStorage.setItem('compte-session', s)", pg.evaluate("sessionStorage.getItem('compte-session')"))
        large.goto(f"{base}/secretariat")
        large.locator("#pilote tr").first.wait_for()
        large.select_option("#camp-metier", index=0)
        large.click("#camp-ok")
        large.locator("#campagnes tr").first.wait_for()
        large.wait_for_timeout(300)
        large.screenshot(path=str(DOSSIER / "lot4-console-secretariat.png"), full_page=True)
        nav.close()
    capturer_espace()
    capturer_desinscription()
    capturer_multiclub()
    capturer_borne()
    capturer_attestation()
    print("vitrine annee-1 capturée dans", DOSSIER)


def capturer_espace() -> None:
    """LOT 3 : l'espace membre d'un membre FICTIF du monde de démonstration (pause posée, préférences, solde)."""
    from datetime import date, timedelta
    tmp = tempfile.mkdtemp()
    with serveur(HACKVS_ESPACE_MEMBRE="1", HACKVS_ESSAIS_DB=str(Path(tmp) / "j.db"), HACKVS_FOIRE="1") as base, \
            sync_playwright() as p:
        req = urllib.request.Request(base + "/api/pulse/console/personas", headers={"X-Pulse-Console": "1"})
        from intelligence.monde_demo import PAULINE
        session = next(x["session"] for x in json.load(urllib.request.urlopen(req)) if x["id"] == PAULINE)
        nav = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = nav.new_context(viewport=TELEPHONE).new_page()
        pg.goto(f"{base}/espace?session={session}")
        pg.locator("#b-pause").wait_for()
        jour = pg.evaluate("fetch('/api/pulse/moi/date', {headers: {'X-Pulse-Session': sessionStorage"
                           ".getItem('pulse-session')}}).then(r => r.json())")
        pg.fill("#pause-date", (date.fromisoformat(jour["date"]) + timedelta(days=14)).isoformat())
        pg.click("#pause-ok")
        pg.locator("#pause-etat:has-text('En pause')").wait_for()
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(DOSSIER / "lot3-espace-membre.png"), full_page=True)
        nav.close()


def capturer_desinscription() -> None:
    """LOT 5 : la page de désinscription, telle que l'ouvre le lien d'un e-mail (avant le clic)."""
    with serveur(HACKVS_NOTIFICATIONS="1", HACKVS_ESSAIS_DB=str(Path(tempfile.mkdtemp()) / "j.db")) as base, sync_playwright() as p:
        nav = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = nav.new_context(viewport=TELEPHONE).new_page()
        pg.goto(f"{base}/desinscription#j=exemple.email.lien.fictif")
        pg.locator("#ok").wait_for()
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(DOSSIER / "lot5-desinscription.png"))
        nav.close()


def capturer_multiclub() -> None:
    """LOT 8 : un club partenaire EXEMPLE FICTIF ; « Mes clubs » dans l'espace ; l'interface en anglais."""
    tmp = str(Path(tempfile.mkdtemp()) / "j.db")
    env = {"HACKVS_MULTICLUB": "1", "HACKVS_ESPACE_MEMBRE": "1", "HACKVS_ESSAIS_DB": tmp, "HACKVS_FOIRE": "1"}
    with serveur(**env) as base, sync_playwright() as p:
        req = urllib.request.Request(base + "/api/pulse/console/personas", headers={"X-Pulse-Console": "1"})
        from intelligence.monde_demo import PAULINE
        session = next(x["session"] for x in json.load(urllib.request.urlopen(req)) if x["id"] == PAULINE)
        subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, '.'); from app.taxonomy import charger_taxonomie; "
                        "from intelligence.demo import Demo; from intelligence import clubs; c = Demo(charger_taxonomie(), "
                        "reprendre=True).club; clubs.declarer(c, 'hs-exemple', 'Club partenaire Haute-Savoie — exemple fictif', "
                        "region='Haute-Savoie', pays='FR', fictif=True)"], cwd=PROTO, env={**os.environ, **env}, check=True)
        nav = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = nav.new_context(viewport=TELEPHONE).new_page()
        pg.goto(f"{base}/espace?session={session}")
        pg.locator("#clubs li").first.wait_for()
        pg.locator("#b-clubs").scroll_into_view_if_needed()
        pg.wait_for_timeout(300)
        pg.locator("#b-clubs").screenshot(path=str(DOSSIER / "lot8-mes-clubs.png"))
        en = nav.new_context(viewport=TELEPHONE).new_page()
        en.goto(f"{base}/app?lang=en#acces")
        en.locator("[data-role=traduction]").wait_for()
        en.wait_for_timeout(300)
        en.screenshot(path=str(DOSSIER / "lot8-interface-en.png"))
        nav.close()


def capturer_borne() -> None:
    """LOT 9 : la borne du stand, après qu'un visiteur a pris son passe (QR réel, monde fictif)."""
    import hashlib
    import hmac
    secret = "c" * 40
    env = {"HACKVS_FOIRE_ALLUMAGE": "1", "HACKVS_ESSAIS_DB": str(Path(tempfile.mkdtemp()) / "j.db"), "HACKVS_SECRET": secret,
           "HACKVS_FOIRE": "1"}
    from intelligence import foire_allumage as fa
    from intelligence.reglages import Reglages
    jeton = fa.jeton_borne(hmac.new(Reglages.depuis_env({"HACKVS_SECRET": secret}).secret, b"bornes|annee-1",
                                    hashlib.sha256).digest(), "stand-vitrine")
    with serveur(**env) as base, sync_playwright() as p:
        nav = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = nav.new_context(viewport={"width": 820, "height": 1000}).new_page()
        pg.goto(f"{base}/borne#b={jeton}")
        pg.click("#prendre")
        pg.locator("#ref").wait_for()
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(DOSSIER / "lot9-borne.png"), full_page=True)
        nav.close()


def capturer_attestation() -> None:
    """LOT 10 : une attestation réelle (SD-JWT VC, émetteur local) vérifiée par le vérificateur local."""
    env = {"HACKVS_EID": "1", "HACKVS_ESSAIS_DB": str(Path(tempfile.mkdtemp()) / "j.db"), "HACKVS_FOIRE": "1"}
    with serveur(**env) as base, sync_playwright() as p:
        console = {"X-Pulse-Console": "1", "Content-Type": "application/json"}
        urllib.request.urlopen(urllib.request.Request(base + "/api/pulse/demo/aller/9", data=b"{}", headers=console))
        sd = None
        for x in json.load(urllib.request.urlopen(urllib.request.Request(base + "/api/pulse/console/personas", headers=console))):
            if x.get("session"):
                a = json.load(urllib.request.urlopen(urllib.request.Request(base + "/api/pulse/moi/attestations",
                                                                            headers={"X-Pulse-Session": x["session"]})))["attestations"]
                if a:
                    sd = a[0]["sd_jwt"]
                    break
        nav = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = nav.new_context(viewport={"width": 760, "height": 900}).new_page()
        pg.goto(f"{base}/attestation")
        pg.fill("#sd", sd)
        pg.click("#verifier")
        pg.locator("#verdict.ok").wait_for()
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(DOSSIER / "lot10-attestation.png"), full_page=True)
        nav.close()


if __name__ == "__main__":
    main()
