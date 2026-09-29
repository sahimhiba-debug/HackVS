"""Enregistre la vidéo de démonstration à partir de la VRAIE scène (/demo/stage), de façon reproductible.

    python scripts/enregistrer_video.py [--url http://localhost:8000]

Si aucune URL n'est donnée, lance le serveur localement (mode démo, bases en mémoire, sans IA locale) puis l'arrête.
Le texte à l'écran vient de competition/video/captions.json (source unique de la voix off). Sous-titres incrustés
dans la page par un calque ; aucune image n'est retouchée. Sortie : competition/video/demo.webm + captures clés dans
competition/evidence/. Utilise le ffmpeg embarqué par Playwright (enregistrement WebM natif) ; aucun autre outil.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
PROTO = RACINE / "prototype"
VIDEO = RACINE / "competition" / "video"
PREUVES = RACINE / "competition" / "evidence"

CALQUE = """
(() => {
  let c = document.getElementById('sous-titre');
  if (!c) {
    c = document.createElement('div'); c.id = 'sous-titre';
    c.style.cssText = 'position:fixed;left:50%;transform:translateX(-50%);bottom:86px;max-width:1100px;width:calc(100% - 64px);' +
      'background:rgba(17,17,17,.88);color:#fff;font:600 24px/1.35 "Helvetica Neue",Arial,sans-serif;padding:14px 22px;' +
      'border-radius:8px;z-index:99;text-align:center;transition:opacity .3s';
    document.body.appendChild(c);
  }
  c.textContent = TEXTE; c.style.opacity = TEXTE ? 1 : 0;
})();
"""


def attendre(url: str, s: float = 60) -> None:
    fin = time.time() + s
    while time.time() < fin:
        try:
            urllib.request.urlopen(url + "/api/stage", timeout=2)
            return
        except OSError:
            time.sleep(0.5)
    raise SystemExit(f"serveur injoignable : {url}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--rapide", action="store_true", help="durées divisées par 4 (vérification)")
    a = ap.parse_args()
    serveur = None
    url = a.url
    if not url:
        url = "http://127.0.0.1:8793"
        env = {**os.environ, "HACKVS_SEMANTIQUE": "0", "HACKVS_DB": ":memory:", "HACKVS_DECISIONS_DB": ":memory:", "HACKVS_CYCLE_DB": ":memory:"}
        serveur = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8793"], cwd=PROTO, env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        attendre(url)
        enregistrer(url, a.rapide)
    finally:
        if serveur:
            serveur.terminate()


def enregistrer(url: str, rapide: bool) -> None:
    from playwright.sync_api import sync_playwright
    cfg = json.loads((VIDEO / "captions.json").read_text(encoding="utf-8"))
    L, H = cfg["format"]["largeur"], cfg["format"]["hauteur"]
    tmp = VIDEO / "_brut"
    shutil.rmtree(tmp, ignore_errors=True)
    PREUVES.mkdir(parents=True, exist_ok=True)
    exe = next(iter(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome")), None)
    journal = []
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        ctx = br.new_context(viewport={"width": L, "height": H}, record_video_dir=str(tmp), record_video_size={"width": L, "height": H})
        pg = ctx.new_page()
        erreurs = []
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(url + "/demo/stage")
        pg.wait_for_selector("#carte h1")
        pg.click("#reinit")
        pg.wait_for_function("document.querySelector('#horloge').textContent.includes('étape 0/')")
        t0 = time.time()
        for plan in cfg["plans"]:
            actuelle = int(pg.inner_text("#horloge").split("étape ")[1].split("/")[0])
            while actuelle < plan["etape"]:
                pg.click("#suiv")
                actuelle += 1
                pg.wait_for_function(f"document.querySelector('#horloge').textContent.includes('étape {actuelle}/')", timeout=30000)
            pg.evaluate("window.scrollTo(0, 0)")
            if plan.get("clic"):                        # clic RÉEL sur une relation du graphe (contrefactuel interactif)
                pg.locator(f'line.lien-zone[aria-label*="{plan["clic"]}"]').first.dispatch_event("click")
                pg.wait_for_function("document.querySelector('#carte').innerText.includes('VOTRE SIMULATION') || "
                                     "document.querySelector('#carte').innerText.includes('Votre simulation')")
            pg.evaluate(CALQUE.replace("TEXTE", json.dumps(plan["texte"])))
            duree = plan["duree"] / (4 if rapide else 1)
            if plan.get("defiler"):
                pas = 20
                hauteur = pg.evaluate("document.documentElement.scrollHeight - innerHeight")
                pg.wait_for_timeout(int(duree * 1000 * 0.35))
                for i in range(1, pas + 1):
                    pg.evaluate(f"window.scrollTo({{top: {hauteur * i / pas}, behavior: 'instant'}})")
                    pg.wait_for_timeout(int(duree * 1000 * 0.55 / pas))
                pg.wait_for_timeout(int(duree * 1000 * 0.10))
            else:
                pg.wait_for_timeout(int(duree * 1000))
            if not rapide and not plan.get("fin"):
                pg.evaluate("window.scrollTo(0, 0)")
                nom = f"scene_{plan['etape']:02d}" + ("_clic" if plan.get("clic") else "")
                pg.screenshot(path=str(PREUVES / f"{nom}.png"))
            journal.append({"etape": plan["etape"], "debut_s": round(time.time() - t0 - duree, 1), "duree_s": duree, "texte": plan["texte"]})
        chemin = pg.video.path()
        ctx.close()
        br.close()
    if erreurs:
        raise SystemExit(f"erreurs JavaScript pendant l'enregistrement : {erreurs}")
    sortie = VIDEO / ("demo_rapide.webm" if rapide else "demo.webm")
    shutil.move(chemin, sortie)
    shutil.rmtree(tmp, ignore_errors=True)
    (VIDEO / ("timeline_mesuree_rapide.json" if rapide else "timeline_mesuree.json")).write_text(
        json.dumps(journal, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{sortie} ({sortie.stat().st_size / 1e6:.1f} Mo), {len(journal)} plans, {sum(j['duree_s'] for j in journal):.0f} s")


if __name__ == "__main__":
    main()
