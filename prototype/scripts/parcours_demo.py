"""Joue la démonstration dans un vrai navigateur (Chromium) et enregistre captures + vidéo.

Usage (serveur lancé) :
  python scripts/parcours_demo.py --url http://localhost:8000 [--sortie ../docs/captures] [--video]

Parcours « scène » (deux membres fictifs, une seule base) :
  Sophie exprime un besoin → critères → aperçu → publie dans la Bourse
  → Julien le voit apparaître en direct dans SA Bourse, avec la raison → propose son aide
  → Sophie accepte (coordonnées partagées) → Julien planifie → rencontre → Sophie clôt « résolu grâce à Julien ».
Puis cas limites dans l'application seule : abstention, ambiguïté, hors catalogue, mobile.
Échoue (code ≠ 0) si une étape n'apparaît pas ou si une erreur JavaScript survient : sert de test de fumée.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ICI = Path(__file__).resolve().parent
EXE = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
BESOIN = ("On lance nos jus d'abricot en Suisse alémanique. Je cherche un transporteur frigorifique "
          "qui livre Zurich deux fois par semaine, idéalement germanophone, et pas un concurrent.")


def lancer_navigateur(pw, lent: bool = False):
    # slow_mo ralentit chaque action : la vidéo reste lisible pour un humain.
    return pw.chromium.launch(executable_path=EXE if os.path.exists(EXE) else None, slow_mo=300 if lent else 0)


def sans_null(texte: str, ou: str) -> None:
    if re.search(r"(^|\n)\s*(null|undefined|NaN)\s*(\n|$)", texte):
        raise SystemExit(f"Valeur technique affichée à l'écran ({ou})")


def scene(pw, url: str, sortie: Path, video: bool) -> None:
    nav = lancer_navigateur(pw, lent=video)
    ctx = nav.new_context(viewport={"width": 1600, "height": 900}, device_scale_factor=1,
                          record_video_dir=str(sortie / "_video") if video else None,
                          record_video_size={"width": 1600, "height": 900} if video else None)
    page = ctx.new_page()
    erreurs: list[str] = []
    page.on("pageerror", lambda e: erreurs.append(str(e)))
    page.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
    page.request.post(url + "/api/demo/reinitialiser")
    page.goto(url + "/scene")
    g, d = page.frame_locator("#cadre-g"), page.frame_locator("#cadre-d")

    def pause(ms: int) -> None:  # pauses de lecture, seulement pour la vidéo
        if video:
            page.wait_for_timeout(ms)
    expect(g.locator("#texte")).to_be_visible()
    expect(d.locator("#vue-bourse h1")).to_contain_text("pour l'instant")
    page.wait_for_timeout(800)
    page.screenshot(path=sortie / "10_scene_depart.png")

    # 1. Sophie écrit et analyse
    pause(1500)
    if video:
        g.locator("#texte").press_sequentially(BESOIN, delay=28)
    else:
        g.locator("#texte").fill(BESOIN)
    page.wait_for_timeout(400)
    pause(800)
    g.locator("#btn-analyser").click()
    expect(g.locator(".critere.principal")).to_contain_text("Transport frigorifique")
    expect(g.locator("#zone-apercu .carte").first).to_contain_text("Julien Morand")
    page.wait_for_timeout(700)
    g.locator("#bloc-criteres").scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    page.screenshot(path=sortie / "11_scene_criteres.png")
    pause(4000)
    g.locator("#bloc-apercu").scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    page.screenshot(path=sortie / "12_scene_apercu.png")
    pause(4000)

    # 2. Publication → apparaît en direct chez Julien
    g.locator("#btn-enregistrer").click()
    expect(d.locator(".opportunite")).to_be_visible(timeout=8000)
    expect(d.locator(".opportunite h2")).to_contain_text("Sophie")
    page.wait_for_timeout(1600)
    page.screenshot(path=sortie / "13_scene_bourse_julien.png")
    pause(5000)

    # 3. Julien propose son aide
    d.get_by_role("button", name="Proposer mon aide").click()
    expect(d.locator("#message")).to_have_value(re.compile("Bourse du Club"))
    page.wait_for_timeout(500)
    page.screenshot(path=sortie / "14_scene_proposition.png")
    pause(3000)
    d.locator("#dialogue-envoyer").click()
    expect(d.locator(".opportunite .etat-relation")).to_contain_text("attente")

    # 4. Sophie reçoit et accepte
    expect(g.locator("#vue-besoins .relation.a-faire")).to_contain_text("Julien Morand", timeout=8000)
    g.locator("#vue-besoins .relation.a-faire").scroll_into_view_if_needed()
    page.wait_for_timeout(600)
    page.screenshot(path=sortie / "15_scene_offre_recue.png")
    pause(3000)
    g.get_by_role("button", name="Accepter et partager nos coordonnées").click()
    expect(d.locator(".opportunite .etat-relation")).to_contain_text("acceptée", timeout=8000)
    expect(d.locator(".opportunite h2")).to_contain_text("Sophie")
    pause(2500)

    # 5. Julien planifie, rencontre, Sophie clôt le besoin
    d.locator("#tab-suivi").click()
    d.locator(".relation input[type=date]").fill("2026-10-15")
    d.get_by_role("button", name="Planifier la rencontre").click()
    expect(d.locator(".relation .etat")).to_contain_text("planifiée")
    d.get_by_role("button", name="La rencontre a eu lieu").click()
    d.get_by_role("button", name="Affaire en cours").click()
    expect(d.locator(".relation .etat")).to_contain_text("Affaire en cours")
    g.get_by_role("button", name="Résolu grâce à Julien").click()
    expect(g.locator("#detail-besoin .surtitre")).to_contain_text("Résolu", timeout=8000)
    page.wait_for_timeout(1200)
    page.screenshot(path=sortie / "16_scene_resolu.png")
    pause(3500)
    sans_null(g.locator("main").inner_text(), "scène gauche")
    sans_null(d.locator("main").inner_text(), "scène droite")
    ctx.close()
    nav.close()
    if video:
        videos = list((sortie / "_video").glob("*.webm"))
        if videos:
            shutil.move(str(videos[0]), sortie / "demo_scene.webm")
        shutil.rmtree(sortie / "_video", ignore_errors=True)
    if erreurs:
        raise SystemExit(f"Erreurs JavaScript (scène) : {erreurs}")
    print("Scène OK")


def cas_limites(pw, url: str, sortie: Path, largeur: int, hauteur: int, suffixe: str) -> None:
    nav = lancer_navigateur(pw)
    page = nav.new_page(viewport={"width": largeur, "height": hauteur})
    erreurs: list[str] = []
    page.on("pageerror", lambda e: erreurs.append(str(e)))
    page.request.post(url + "/api/demo/reinitialiser")
    page.goto(url + "/?membre=p00&vue=nouveau")
    expect(page.locator(".badge.demo")).to_be_visible()
    expect(page.locator("#texte")).to_be_visible()
    page.wait_for_timeout(300)
    page.screenshot(path=sortie / f"20_accueil{suffixe}.png")

    def analyser(texte: str):
        page.locator("#texte").fill(texte)
        page.locator("#btn-analyser").click()
        expect(page.locator("#zone-editeur .editeur")).to_be_visible()

    analyser("Nous cherchons quelqu'un pour nous accompagner vers la certification ISO 27001.")
    expect(page.locator(".abstention")).to_be_visible()
    page.wait_for_timeout(500)
    page.locator("#bloc-apercu").screenshot(path=sortie / f"21_abstention{suffixe}.png")

    analyser("Je cherche quelqu'un pour la sécurité.")
    expect(page.locator(".question")).to_be_visible()
    page.wait_for_timeout(400)
    page.locator("#bloc-criteres").screenshot(path=sortie / f"22_ambiguite{suffixe}.png")

    analyser("Je ne cherche pas un installateur frigorifique mais un transporteur frigorifique pour livrer Genève.")
    expect(page.locator(".critere.exclusion")).to_contain_text("Installation")
    expect(page.locator("#zone-apercu .carte").first).to_be_visible()
    page.wait_for_timeout(500)
    page.locator("#bloc-criteres").screenshot(path=sortie / f"23_negation{suffixe}.png")
    # Modifier un critère rend les résultats visiblement obsolètes
    page.locator(".critere .retirer").nth(1).click()
    expect(page.locator("#zone-apercu .bandeau-obsolete")).to_be_visible()
    page.locator("#bloc-apercu").screenshot(path=sortie / f"24_obsolete{suffixe}.png")

    analyser("Je cherche un apiculteur pour polliniser mes vergers d'abricotiers.")
    expect(page.locator("#zone-apercu .carte").first).to_contain_text("Rucher")
    page.wait_for_timeout(500)
    page.locator("#bloc-apercu").screenshot(path=sortie / f"25_hors_catalogue{suffixe}.png")

    sans_null(page.locator("main").inner_text(), "nouveau besoin")
    page.locator("#tab-profil").click()
    expect(page.locator("#vue-profil h1")).to_contain_text("Sophie")
    page.screenshot(path=sortie / f"26_profil{suffixe}.png")
    page.request.post(url + "/api/demo/reinitialiser")
    nav.close()
    if erreurs:
        raise SystemExit(f"Erreurs JavaScript ({largeur}px) : {erreurs}")
    print(f"Cas limites OK ({largeur}x{hauteur})")


def club_profil_pitch(pw, url: str, sortie: Path) -> None:
    """Vue du Club (historique fictif), profil en 30 secondes, support de présentation."""
    nav = lancer_navigateur(pw)
    page = nav.new_page(viewport={"width": 1440, "height": 900})
    erreurs: list[str] = []
    page.on("pageerror", lambda e: erreurs.append(str(e)))
    page.request.post(url + "/api/demo/historique")
    page.goto(url + "/club")
    expect(page.locator(".manque").first).to_contain_text("ISO 27001")
    page.wait_for_timeout(700)
    page.screenshot(path=sortie / "30_club.png")
    page.locator(".bloc.deux").screenshot(path=sortie / "30_club_recruter.png")
    sans_null(page.locator("main").inner_text(), "vue du Club")

    # Acte 2 : « le Club se répare ». Yann complète son profil ; la demande ISO en attente le trouve.
    yann = nav.new_page(viewport={"width": 1280, "height": 900})
    yann.on("pageerror", lambda e: erreurs.append(str(e)))
    yann.goto(url + "/?membre=p10&vue=profil")
    yann.locator("#texte-profil").fill("Nous accompagnons les PME valaisannes vers la certification ISO 27001. "
                                       "Nous intervenons en Valais et en Suisse romande.")
    yann.locator("#btn-proposer-profil").click()
    expect(yann.locator(".proposition")).to_contain_text("ISO 27001")
    yann.get_by_role("button", name="Valider et enregistrer mon profil").click()
    expect(yann.locator("#vue-profil .fiche")).to_contain_text("ISO 27001")
    yann.locator("#tab-bourse").click()
    expect(yann.locator(".opportunite")).to_contain_text("ISO 27001")
    yann.wait_for_timeout(1200)
    yann.screenshot(path=sortie / "33_bourse_yann_iso.png")
    expect(page.locator(".recruter")).not_to_contain_text("ISO 27001", timeout=8000)  # la vue du Club se met à jour seule
    page.wait_for_timeout(600)
    page.locator(".bloc.deux").screenshot(path=sortie / "32_club_repare.png")
    yann.close()

    page.request.post(url + "/api/demo/reinitialiser")
    page.goto(url + "/?membre=p15&vue=profil")
    page.locator("#texte-profil").fill("Nous créons des films d'entreprise et des photos de produits. Nous intervenons en Valais "
                                       "et en Suisse romande. Nous parlons français, allemand et anglais. Nous cherchons un partenaire "
                                       "pour la traduction. Nous ne faisons pas d'impression.")
    page.locator("#btn-proposer-profil").click()
    expect(page.locator(".proposition")).to_contain_text("Photo et vidéo")
    page.wait_for_timeout(600)
    page.locator("#vue-profil section.bloc").screenshot(path=sortie / "31_profil_30s.png")
    page.get_by_role("button", name="Valider et enregistrer mon profil").click()
    expect(page.locator("#vue-profil .fiche")).to_contain_text("Nous créons des films")

    page.goto(url + "/presentation#1")
    for n in (1, 4, 6, 8):
        page.goto(url + f"/presentation#{n}")
        page.reload()
        page.wait_for_timeout(500)
        page.screenshot(path=sortie / f"40_pitch_{n:02d}.png")
    page.request.post(url + "/api/demo/reinitialiser")
    nav.close()
    if erreurs:
        raise SystemExit(f"Erreurs JavaScript (club/profil/pitch) : {erreurs}")
    print("Club, profil et présentation OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--sortie", default=str(ICI.parent.parent / "docs" / "captures"))
    ap.add_argument("--video", action="store_true", help="enregistre demo_scene.webm")
    a = ap.parse_args()
    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        scene(pw, a.url.rstrip("/"), sortie, a.video)
        cas_limites(pw, a.url.rstrip("/"), sortie, 1280, 800, "")
        cas_limites(pw, a.url.rstrip("/"), sortie, 390, 844, "_mobile")
        club_profil_pitch(pw, a.url.rstrip("/"), sortie)
