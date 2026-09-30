"""Enregistre UNE exécution réelle et continue de la démonstration (aucun montage) : la régie montre l'écran commun et
les deux téléphones ; ce script agit dans chaque téléphone comme le ferait la personne, et joue depuis la console les
membres absents de la scène (affiché « joué »). La valeur choisie « par le jury » est un paramètre (--heure).

    python -m uvicorn app.main:app --port 8767   (mode démo, bases en mémoire)
    python scripts/enregistrer_demo.py --url http://127.0.0.1:8767 --sortie ../docs/audit/club-pulse-pivot/captures --commit $(git rev-parse --short HEAD)

Produit `demo_action.webm` (1920×1080, VP8) et `demo_action.json` (étapes, horodatage de chacune, délais mesurés).
La vidéo prouve une exécution enregistrée ; elle ne prouve pas une réaction en direct à un choix nouveau du jury."""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from playwright.sync_api import sync_playwright  # noqa: E402

from intelligence.demo import BESOIN_SOPHIE, FICHE_DE  # noqa: E402

CONSOLE = {"Content-Type": "application/json", "X-Pulse-Console": "1"}


def api(base: str, chemin: str, corps=None):
    req = urllib.request.Request(base + chemin, data=json.dumps(corps).encode() if corps is not None else None, headers=CONSOLE)
    return json.loads(urllib.request.urlopen(req).read())


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--url", default="http://127.0.0.1:8767")
    a.add_argument("--sortie", default=str(RACINE / "captures"))
    a.add_argument("--commit", default="non indiqué")
    a.add_argument("--heure", default="17:00", help="la nouvelle heure de disponibilité de la voix allemande (choix du jury)")
    x = a.parse_args()
    base, sortie = x.url, Path(x.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    api(base, "/api/pulse/demo/reinitialiser", {})
    journal: list[dict] = []
    t0 = time.perf_counter()
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium") if Path("/opt/pw-browsers/chromium").exists() else p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-CH", record_video_dir=str(sortie / "tmp_video"),
                            record_video_size={"width": 1920, "height": 1080})
        pg = ctx.new_page()
        pg.set_default_timeout(30_000)
        pg.goto(base + f"/demo/regie?commit={x.commit}")
        pg.wait_for_function("() => window.pret === true")
        proj, s, lea = pg.frame_locator("#projection"), pg.frame_locator("#tel1"), pg.frame_locator("#tel2")

        def etape(titre: str, texte: str, joue: bool = False, pause: float = 2.5) -> None:
            pg.evaluate("([a, b, c]) => window.legende(a, b, c)", [titre, texte, joue])
            journal.append({"t_s": round(time.perf_counter() - t0, 1), "titre": titre, "texte": texte, "joue": joue})
            pg.wait_for_timeout(int(pause * 1000))

        def jouer(eid: str, qui: str) -> None:
            v = api(base, f"/api/pulse/console/essais/{eid}")["version"]
            api(base, f"/api/pulse/console/essais/{eid}/geste", {"membre": qui, "version": v, "accepte": True})

        try:
            deroule(x, base, pg, proj, s, lea, etape, jouer)
        except Exception:
            pg.screenshot(path=str(sortie / "echec.png"))
            raise
        video = pg.video
        ctx.close()
        b.close()
        chemin = Path(video.path()) if video else None
    if chemin:
        cible = sortie / "demo_action.webm"
        chemin.replace(cible)
        (sortie / "tmp_video").rmdir()
    (sortie / "demo_action.json").write_text(json.dumps({"commit": x.commit, "heure_jury": x.heure, "duree_s": round(time.perf_counter() - t0, 1),
                                                         "etapes": journal}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"vidéo : {sortie / 'demo_action.webm'} · {round(time.perf_counter() - t0)} s")
    return 0


def deroule(x, base, pg, proj, s, lea, etape, jouer) -> None:
        proj.locator("text=contributions proposées, dispersées").wait_for()
        etape("Avant", "Jeudi, pendant la Foire : des membres ont proposé leur voix, leur stand, leurs contacts — chacun avec ses horaires. "
              "Personne n'a rien demandé.", pause=7)
        etape("1. Le besoin", "Sophie a le produit. Elle écrit, avec ses mots, ce qu'elle ne peut pas faire seule.", pause=1)
        s.locator("nav.onglets >> text=Agir à plusieurs").click()
        s.locator("#besoin").type(BESOIN_SOPHIE, delay=18)
        s.locator("#comprendre").click()
        s.locator("#exigences .exigence >> nth=2").wait_for()
        etape("2. Ce qu'il faudrait réunir", "Trois exigences reprises de SES mots (une voix allemande qui remet la fiche demandée, un lieu, un "
              "public) — des règles simples, pas un modèle : c'est affiché. Sophie confirme.", pause=6)
        s.locator("button:has-text('Reprendre la suggestion')").click()
        s.locator("#chercher").click()
        s.locator("#projeter").click()                        # SON choix : montrer son action sur l'écran commun (rôles, sans noms)
        proj.locator("text=les 3 disponibilités se recouvrent de 16:00 à 17:30").wait_for()
        etape("3. La proposition", "Sophie choisit de la montrer sur l'écran commun. Aucune offre ne suffit seule : les disponibilités "
              "DÉCLARÉES se recouvrent de 16:00 à 17:30 ; le serveur retient le premier créneau, 16:00–16:45. Rien n'est encore envoyé.", pause=8)
        s.locator("#publier-proposition").click()
        s.locator("#creneau").wait_for()
        eid = s.locator("body").evaluate("() => location.hash.split('/')[1]")
        etape("4. Chacun décide", "Léa reçoit SA part sur SON téléphone : présenter en allemand et remettre une fiche. Elle accepte.", pause=1)
        lea.locator(f"a[href='#essai/{eid}']").click()
        lea.locator("#accepter").click()
        pg.wait_for_timeout(1500)
        for qui in ("s01", "s14"):
            jouer(eid, qui)
        proj.locator("text=Coopération prête").wait_for()
        etape("4. Chacun décide", "Pauline (lieu) et Markus (public) ne sont pas sur scène : leurs accords sont JOUÉS depuis la console, "
              "et l'écran commun l'affiche. Coopération prête : pas encore réalisée.", joue=True, pause=7)
        etape("5. Le jury change une condition", f"« Léa n'est disponible qu'à partir de {x.heure}. » Elle le déclare sur SON téléphone.", pause=1)
        lea.locator("summary:has-text('Ma disponibilité a changé')").click()
        lea.locator("#dispo-debut").fill(x.heure)
        lea.locator("#dispo-fin").fill("19:00")
        t1 = time.perf_counter()
        lea.locator("#changer-dispo").click()
        proj.locator("text=Ce qui vient de changer").wait_for()
        delai = round((time.perf_counter() - t1) * 1000)
        etape("6. Ce qui change", f"Visible sur l'écran commun en {delai} ms : la voix allemande ne couvre plus le créneau ; le lieu et le "
              "public restaient valables pour l'ancien créneau. Adaptations calculées par le serveur ; aucun lancement possible.", pause=9)
        s.locator("text=Une condition a changé").first.wait_for()
        alt = s.locator("button.alt").filter(has_text="45")                  # garder 45 min si une adaptation le permet
        (alt.first if alt.count() else s.locator("button.alt").first).click()
        s.locator("text=Créneau : 08.10 16:00").wait_for(state="detached")
        s.locator("#creneau").wait_for()
        creneau = s.locator("#creneau").inner_text().replace("Créneau : ", "")
        etape("7. Sophie choisit, chacun reconfirme", f"Nouveau créneau : {creneau}. Le moment change : TOUS reconfirment — "
              "personne n'est reconfirmé à sa place.", pause=2)
        lea.locator("#accepter").click()
        pg.wait_for_timeout(1200)
        for qui in ("s14", "s04", "s01"):                    # rôles absents de la scène : rejoués s'ils sont dans la nouvelle version
            try:
                jouer(eid, qui)
            except urllib.error.HTTPError:
                pass                                          # plus concerné (403) ou déjà décidé : le serveur refuse, on n'insiste pas
        proj.locator("text=Coopération prête").wait_for()
        etape("7. Sophie choisit, chacun reconfirme", "Nouveaux accords réunis sur la nouvelle version (joués pour les rôles absents).",
              joue=True, pause=3)
        s.locator("#lancer").click()
        etape("8. Un résultat concret", "Sophie engage l'action. Léa écrit la fiche en allemand et la transmet.", pause=1)
        lea.locator("#livraison").wait_for()
        lea.locator("#livraison").fill(FICHE_DE)
        lea.locator("#transmettre").click()
        s.locator("#fiche-e1").wait_for()
        etape("8. Un résultat concret", "La fiche apparaît sur le téléphone de Sophie. Transmise ≠ reçue : c'est Sophie qui confirme.", pause=3)
        s.locator("#recu-e1").click()
        proj.locator(".exig[data-palier='livrable reçu']").wait_for()
        etape("8. Un résultat concret", f"Réception de la fiche confirmée par la destinataire. La présentation, elle, est engagée pour "
              f"{creneau} — pas encore tenue : l'écran ne dit rien de plus que ce qui est prouvé.", pause=7)
        api(base, "/api/pulse/console/temps", {"jours": 30})
        proj.locator("text=aucun résultat n'a été déclaré").wait_for()
        etape("9. Trente jours plus tard (horloge SIMULÉE)", "La fiche reçue le reste. Personne n'a déclaré ce que la présentation a "
              "donné : le résultat reste inconnu — le silence n'est pas un succès. Les disponibilités étaient datées : rien n'est reconduit.",
              joue=True, pause=8)


if __name__ == "__main__":
    sys.exit(main())
