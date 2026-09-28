"""Joue le parcours de démonstration dans un vrai navigateur et enregistre des captures.

Usage : python scripts/parcours_demo.py [--url http://localhost:8000] [--sortie docs/captures]
Sert de test de fumée avant une présentation : échoue si une étape ne s'affiche pas.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BESOIN = ("On lance nos jus d'abricot en Suisse alémanique. Je cherche un transporteur frigorifique "
          "qui livre Zurich deux fois par semaine, idéalement germanophone, et pas un concurrent.")


def lancer(url: str, sortie: Path, largeur: int, hauteur: int, suffixe: str) -> None:
    sortie.mkdir(parents=True, exist_ok=True)
    exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe if os.path.exists(exe) else None)
        page = nav.new_page(viewport={"width": largeur, "height": hauteur}, device_scale_factor=1)
        erreurs: list[str] = []
        page.on("pageerror", lambda e: erreurs.append(str(e)))
        page.goto(url)
        page.request.post(url.rstrip("/") + "/api/demo/reinitialiser")
        page.reload()
        expect(page.locator(".badge.demo")).to_be_visible()
        page.screenshot(path=sortie / f"01_accueil{suffixe}.png")

        page.fill("#texte", BESOIN)
        page.click("#btn-analyser")
        expect(page.locator("#bloc-criteres")).to_be_visible()
        expect(page.locator(".critere.principal")).to_contain_text("Transport frigorifique")
        page.wait_for_timeout(600)
        page.locator("#bloc-criteres").screenshot(path=sortie / f"02_criteres{suffixe}.png")

        page.click("#btn-rechercher")
        expect(page.locator(".carte").first).to_contain_text("Julien Morand")
        page.wait_for_timeout(600)
        page.locator("#bloc-resultats").screenshot(path=sortie / f"03_contacts{suffixe}.png")

        page.locator("#comparaison summary").click()
        expect(page.locator(".colonne").nth(1)).to_contain_text("Froidtech")
        page.locator("#comparaison").screenshot(path=sortie / f"04_comparaison{suffixe}.png")

        page.locator(".carte").first.get_by_role("button", name="Demander une introduction").click()
        expect(page.locator("#message")).to_have_value(__import__("re").compile("Bonjour Julien"))
        page.locator("#bloc-intro").screenshot(path=sortie / f"05_introduction{suffixe}.png")

        page.click("#btn-envoyer")
        expect(page.locator(".intro")).to_contain_text("En attente")
        page.get_by_role("button", name="Simuler : Julien accepte").click()
        expect(page.locator(".intro .etat")).to_contain_text("Acceptée")
        page.fill(".intro input[type=date]", "2026-10-15")
        page.get_by_role("button", name="Planifier la rencontre").click()
        expect(page.locator(".intro .etat")).to_contain_text("planifiée")
        page.wait_for_timeout(400)
        page.locator("#bloc-suivi").screenshot(path=sortie / f"06_suivi{suffixe}.png")

        # Cas d'abstention
        page.fill("#texte", "Nous cherchons quelqu'un pour nous accompagner vers la certification ISO 27001.")
        page.click("#btn-analyser")
        expect(page.locator(".critere.principal")).to_contain_text("ISO 27001")
        page.click("#btn-rechercher")
        expect(page.locator(".abstention")).to_be_visible()
        page.wait_for_timeout(600)
        page.locator("#bloc-resultats").screenshot(path=sortie / f"07_abstention{suffixe}.png")

        # Terme ambigu
        page.fill("#texte", "Je cherche quelqu'un pour la sécurité.")
        page.click("#btn-analyser")
        expect(page.locator(".question")).to_be_visible()
        page.wait_for_timeout(500)
        page.locator("#bloc-criteres").screenshot(path=sortie / f"08_ambiguite{suffixe}.png")

        page.request.post(url.rstrip("/") + "/api/demo/reinitialiser")
        nav.close()
        if erreurs:
            raise SystemExit(f"Erreurs JavaScript : {erreurs}")
        print(f"Parcours OK ({largeur}x{hauteur}) → {sortie}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--sortie", default=str(Path(__file__).resolve().parent.parent.parent / "docs" / "captures"))
    a = ap.parse_args()
    lancer(a.url, Path(a.sortie), 1280, 800, "")
    lancer(a.url, Path(a.sortie), 390, 844, "_mobile")
