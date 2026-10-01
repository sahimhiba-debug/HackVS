"""Captures RÉELLES des écrans montrés au jury pendant la démo (actes 4–6, docs/presentation/04_DEMO_RUNBOOK.md § 6).

    cd prototype && python scripts/capturer_presentation.py [dossier]   # défaut : ../docs/presentation/captures

Rejoue la scène « Registre » de DEMO_SCRIPT sur un serveur de démonstration neuf et isolé (monde FICTIF, horloge
simulée), IA ÉTEINTE (arbitrage D-PRES-1 : aucune variable APERTUS_* transmise), dans Chromium :
Établi « il manque une pièce » → téléphone de Pauline, Demandes → « Proposer à partir de mon texte » (forme
déterministe) → Oui → Établi « le Club peut le faire » → reçu → retrait → « ce composant n'est plus disponible » →
passe juré (Markus) sur un second téléphone. Ne modifie rien du produit ; n'écrit que des images."""
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for k in [k for k in os.environ if k.startswith(("APERTUS_", "OPENAI_"))] + ["ANTHROPIC_API_KEY", "LLM_PROVIDER"]:
    os.environ.pop(k, None)                                  # IA éteinte : aucun fournisseur configuré

from playwright.sync_api import sync_playwright  # noqa: E402

from tests.test_e2e_scene import serveur  # noqa: E402

DOSSIER = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "docs" / "presentation" / "captures"
CONSOLE = {"X-Pulse-Console": "1", "Content-Type": "application/json"}
CARTE = "article[data-finalite='delegation_acheteurs']"


def api(base, chemin, corps=None):
    r = urllib.request.Request(base + chemin, data=None if corps is None else json.dumps(corps).encode(), headers=CONSOLE)
    return json.load(urllib.request.urlopen(r))


def main() -> None:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    with serveur() as base, sync_playwright() as p:
        api(base, "/api/pulse/demo/reinitialiser", {})
        codes = {x["id"]: x["code"] for x in api(base, "/api/pulse/console/personas")}
        nav = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        etabli = nav.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2).new_page()
        etabli.goto(base + "/etabli")
        carte = etabli.locator(CARTE)
        carte.locator("[data-role=statut]:has-text('il manque une pièce')").wait_for()
        etabli.wait_for_timeout(600)
        etabli.screenshot(path=str(DOSSIER / "etabli-1-manque.png"))

        tel = nav.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2).new_page()
        tel.goto(base + f"/app?code={codes['s01']}#acces")
        tel.click("text=Continuer")
        tel.wait_for_selector("h1:has-text('Mes actions')")
        tel.click("nav.onglets >> text=Demandes")
        tel.wait_for_selector("[data-ask]")
        tel.wait_for_timeout(400)
        tel.screenshot(path=str(DOSSIER / "tel-1-demande.png"))

        tel.fill("#ask-mots", "Mon minibus a 14 places, libre vendredi après-midi.")
        tel.click("#ask-proposer")
        tel.locator("#ask-ia:has-text('forme déterministe')").wait_for()
        tel.fill("#att-places", "14")
        tel.locator("[data-ask]").scroll_into_view_if_needed()
        tel.wait_for_timeout(300)
        tel.screenshot(path=str(DOSSIER / "tel-1b-proposition.png"))

        tel.click("#ask-oui")
        tel.wait_for_selector("[data-recu='delegation_acheteurs']")
        carte.locator("[data-role=statut]:has-text('le Club peut le faire')").wait_for()
        etabli.wait_for_timeout(600)
        etabli.screenshot(path=str(DOSSIER / "etabli-2-peut.png"))
        tel.locator("[data-recu='delegation_acheteurs']").scroll_into_view_if_needed()
        tel.wait_for_timeout(300)
        tel.screenshot(path=str(DOSSIER / "tel-2-recu.png"))
        tel.locator("[data-recu='delegation_acheteurs']").screenshot(path=str(DOSSIER / "tel-2-recu-carte.png"))

        tel.click("#retirer-delegation_acheteurs")
        carte.locator("[data-role=statut]:has-text('un consentement ne vaut plus')").wait_for()
        etabli.wait_for_timeout(600)
        etabli.screenshot(path=str(DOSSIER / "etabli-3-retrait.png"))
        carte.screenshot(path=str(DOSSIER / "etabli-3-retrait-carte.png"))
        tel.wait_for_timeout(300)
        tel.screenshot(path=str(DOSSIER / "tel-2b-retrait.png"))

        etabli.click("#qr-jure")
        etabli.wait_for_selector("section[aria-label='QR juré'] img")
        etabli.locator("section[aria-label='QR juré']").scroll_into_view_if_needed()
        etabli.wait_for_timeout(400)
        etabli.screenshot(path=str(DOSSIER / "etabli-4-qr-jure.png"))
        etabli.locator("section[aria-label='QR juré']").screenshot(path=str(DOSSIER / "etabli-4-qr-jure-zoom.png"))
        passe = api(base, "/api/pulse/console/jure", {"persona": "s14", "minutes": 15})["url"].split("://", 1)[1].split("/", 1)[1]
        jure = nav.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2).new_page()
        jure.goto(f"{base}/{passe}")
        jure.wait_for_selector("#bandeau-jure:not([hidden])")
        jure.wait_for_selector("[data-ask]")
        jure.wait_for_timeout(400)
        jure.screenshot(path=str(DOSSIER / "tel-3-jure.png"))
        nav.close()
    for f in sorted(DOSSIER.glob("*.png")):
        print(f.name, f.stat().st_size)


if __name__ == "__main__":
    main()
