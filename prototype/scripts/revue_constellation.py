"""REVUE de la constellation (écran géant du mode salle) : une séance SIMULÉE de ~30 s, rendue dans Chromium headless,
en vidéo (WebM) et en PNG de chaque moment, modes jour et nuit → docs/presentation/deck/review/constellation/.

    cd prototype && python scripts/revue_constellation.py

Séance : arrivées en rafale (36 téléphones), lancement de la demande, des oui, fermeture de l'anneau, un retrait,
la recomposition, le tableau final ; plus l'écran sous le seuil (2 participants). Données FICTIVES (aucun nom)."""
import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright  # noqa: E402

from tests.test_e2e_scene import serveur  # noqa: E402

SORTIE = Path(__file__).resolve().parents[2] / "docs" / "presentation" / "deck" / "review" / "constellation"
CONSOLE = {"X-Pulse-Console": "1", "Content-Type": "application/json"}


def post(base, chemin, corps=None, h=None):
    r = urllib.request.Request(base + chemin, data=json.dumps(corps or {}).encode(), headers={**CONSOLE, **(h or {})})
    return json.load(urllib.request.urlopen(r))


def seance(base, page, dossier: Path, mode: str) -> dict:
    post(base, "/api/pulse/console/salle/purger")
    jeton = post(base, "/api/pulse/console/salle/ouvrir")["url"].split("#s=", 1)[1]
    page.goto(f"{base}/salle/ecran?mode={mode}&sans-bascule")
    page.wait_for_timeout(1200)
    caps = ["voiture", "salle", "allemand", "traiteur", "informatique", "materiel"]
    passes = []
    for i in range(2):
        passes.append((caps[i], post(base, "/api/pulse/salle/entrer", {"jeton": jeton})["passe"]))
        post(base, "/api/pulse/salle/declarer", {"capacite": caps[i], "consentement": True}, {"X-Pulse-Salle": passes[-1][1]})
    page.wait_for_timeout(1600)
    page.screenshot(path=str(dossier / "0-seuil.png"))
    for i in range(2, 36):
        passes.append((caps[i % 6], post(base, "/api/pulse/salle/entrer", {"jeton": jeton})["passe"]))
        post(base, "/api/pulse/salle/declarer", {"capacite": caps[i % 6], "consentement": True}, {"X-Pulse-Salle": passes[-1][1]})
        time.sleep(0.05)
    page.wait_for_timeout(3500)
    page.screenshot(path=str(dossier / "1-arrivees.png"))
    post(base, "/api/pulse/console/salle/lancer")
    page.wait_for_timeout(2200)
    page.screenshot(path=str(dossier / "2-lancement.png"))
    concernes = [(c, p) for c, p in passes if c in ("voiture", "salle", "allemand")]
    for _c, p in concernes[:2]:                                     # deux oui (voiture, salle)
        post(base, "/api/pulse/salle/repondre", {"choix": "oui"}, {"X-Pulse-Salle": p})
    page.wait_for_timeout(500)
    page.screenshot(path=str(dossier / "3-oui-halo.png"))
    page.wait_for_timeout(1800)
    for c, p in concernes[2:]:                                     # les autres : oui, non, pas cette fois (seuls les oui se voient)
        choix = "oui" if c != "materiel" and hash(p) % 3 else "non"
        post(base, "/api/pulse/salle/repondre", {"choix": choix}, {"X-Pulse-Salle": p})
        time.sleep(0.15)
    page.wait_for_timeout(2500)
    page.screenshot(path=str(dossier / "4-fermeture.png"))
    post(base, "/api/pulse/console/salle/retrait")
    page.wait_for_timeout(700)
    page.screenshot(path=str(dossier / "5-retrait.png"))
    page.wait_for_timeout(2200)
    page.screenshot(path=str(dossier / "6-recomposition.png"))
    post(base, "/api/pulse/console/salle/afficher", {"vue": "bilan"})
    page.wait_for_timeout(2600)
    page.screenshot(path=str(dossier / "7-tableau-final.png"))
    return {"ips": page.evaluate("document.body.dataset.ips"), "rendu": page.evaluate("document.body.dataset.rendu || 'anime'")}


def main() -> None:
    mesures = {}
    with serveur(HACKVS_SALLE="1") as base, sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        for mode in ("nuit", "jour"):
            dossier = SORTIE / mode
            shutil.rmtree(dossier, ignore_errors=True)
            dossier.mkdir(parents=True)
            ctx = b.new_context(viewport={"width": 1600, "height": 900}, record_video_dir=str(dossier), record_video_size={"width": 1600, "height": 900})
            page = ctx.new_page()
            erreurs: list[str] = []
            page.on("pageerror", lambda e, erreurs=erreurs: erreurs.append(str(e)))
            mesures[mode] = seance(base, page, dossier, mode) | {"erreurs": erreurs}
            video = page.video.path()
            ctx.close()
            Path(video).rename(dossier / f"seance-{mode}.webm")
        b.close()
    (SORTIE / "mesures.json").write_text(json.dumps(mesures, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(mesures, ensure_ascii=False))


if __name__ == "__main__":
    main()
