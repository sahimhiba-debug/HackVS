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
    env = {"HACKVS_COMPTES": "1", "HACKVS_ESSAIS_DB": journal, "HACKVS_SECRET": secret, "HACKVS_FOIRE": "1"}
    with serveur(**env) as base, sync_playwright() as p:
        admin = subprocess.run([sys.executable, "scripts/comptes.py", "amorcer", "Administration (fictive)"], capture_output=True,
                               text=True, cwd=PROTO, env={**os.environ, **env}).stdout.strip().splitlines()[-1]

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
        nav.close()
    capturer_espace()
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
        jour = pg.evaluate("fetch('/api/pulse/moi/date', {headers: {'X-Pulse-Session': new URLSearchParams(location.search)"
                           ".get('session')}}).then(r => r.json())")
        pg.fill("#pause-date", (date.fromisoformat(jour["date"]) + timedelta(days=14)).isoformat())
        pg.click("#pause-ok")
        pg.locator("#pause-etat:has-text('En pause')").wait_for()
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(DOSSIER / "lot3-espace-membre.png"), full_page=True)
        nav.close()


if __name__ == "__main__":
    main()
