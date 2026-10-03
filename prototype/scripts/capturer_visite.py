"""Captures RÉELLES de chaque écran, pour la visite guidée (docs/presentation/VISITE_GUIDEE.md).

    cd prototype && python scripts/capturer_visite.py [dossier]   # défaut : ../docs/presentation/visite

Serveur de démonstration neuf et isolé (monde FICTIF, IA éteinte, Foire 2026 et mode salle allumés), Chromium.
Écrit une image par écran et `boutons.json` : les libellés exacts des boutons et liens visibles de chaque écran, pour
que la visite ne décrive que ce qui existe. Ne modifie rien du produit."""
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

DOSSIER = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "docs" / "presentation" / "visite"
CONSOLE = {"X-Pulse-Console": "1", "Content-Type": "application/json"}
BUREAU, TELEPHONE = {"width": 1280, "height": 800}, {"width": 390, "height": 844}
LIBELLES = """[...document.querySelectorAll('button, a.btn, nav a, [role=tab]')]
  .filter(e => e.offsetParent !== null).map(e => e.textContent.replace(/\\s+/g, ' ').trim()).filter(Boolean)"""


def api(base: str, chemin: str, corps: dict | None = None) -> dict:
    r = urllib.request.Request(base + chemin, data=None if corps is None else json.dumps(corps).encode(), headers=CONSOLE)
    return json.load(urllib.request.urlopen(r))


def main() -> None:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    boutons: dict[str, list[str]] = {}
    with serveur(HACKVS_FOIRE="1", HACKVS_SALLE="1") as base, sync_playwright() as p:
        api(base, "/api/pulse/demo/reinitialiser", {})
        codes = {x["id"]: x["code"] for x in api(base, "/api/pulse/console/personas")}
        nav = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

        def page(taille: dict):
            pg = nav.new_context(viewport=taille).new_page()
            pg.set_default_timeout(30_000)
            return pg

        def prendre(pg, nom: str) -> None:
            pg.wait_for_timeout(700)
            pg.screenshot(path=str(DOSSIER / f"{nom}.png"))
            boutons[nom] = pg.evaluate(LIBELLES)

        tel = page(TELEPHONE)
        tel.goto(base + f"/app?code={codes['s01']}#acces")
        prendre(tel, "01-app-acces")
        tel.click("text=Continuer")
        tel.wait_for_selector("h1:has-text('Mes actions')")
        prendre(tel, "02-app-mes-actions")
        tel.click("nav.onglets >> text=Demandes")
        tel.wait_for_selector("[data-ask]")
        prendre(tel, "03-app-demandes")
        for o in ("souvenirs",):
            lien = tel.locator(f"nav.onglets a[data-o='{o}']")
            if lien.count():
                lien.click()
                prendre(tel, f"04-app-{o}")

        for chemin, nom in (("/etabli", "10-etabli"), ("/suivi", "11-suivi"), ("/console", "12-console"),
                            ("/projection", "13-projection"), ("/feuille-de-route", "14-feuille-de-route"),
                            ("/preflight", "15-preflight"), ("/confidentialite", "16-confidentialite")):
            pg = page(BUREAU)
            pg.goto(base + chemin)
            prendre(pg, nom)
            if chemin == "/suivi":
                for vue in ("cherche", "assembler", "tableau"):
                    pg.click(f"#vues [data-vue={vue}]")
                    prendre(pg, f"11-suivi-{vue}")

        regie = page(TELEPHONE)
        regie.goto(base + "/salle/regie")
        regie.click("#ouvrir")
        regie.locator("#etat:has-text('ouverte')").wait_for()
        prendre(regie, "20-salle-regie")
        ecran = page(BUREAU)
        ecran.goto(base + "/salle/ecran?sans-bascule")
        ecran.locator("#qr img").wait_for()
        prendre(ecran, "21-salle-ecran")
        participant = page(TELEPHONE)
        participant.goto(api(base, "/api/pulse/console/salle")["url"])
        participant.locator("[data-capacite]").first.wait_for()
        prendre(participant, "22-salle-telephone")

        lien = api(base, "/api/pulse/console/decouverte", {"origine": "stand"})["url"].split("://", 1)[1].split("/", 1)[1]
        invite = page(TELEPHONE)
        invite.goto(f"{base}/{lien}")
        invite.locator("#entreprise").wait_for()
        prendre(invite, "30-decouverte")
        api(base, "/api/pulse/console/salle/purger", {})
        nav.close()
    (DOSSIER / "boutons.json").write_text(json.dumps(boutons, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(boutons)} écrans capturés dans {DOSSIER}")


if __name__ == "__main__":
    main()
