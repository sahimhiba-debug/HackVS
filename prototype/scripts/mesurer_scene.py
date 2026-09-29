"""Red team de la PRÉSENTATION : parcourt /demo/stage dans un vrai navigateur et mesure, pour chaque étape, ce qu'un jury
subit : temps d'attente après le clic, nombre de mots à lire, part du contenu sous la ligne de flottaison, erreurs.

    python scripts/mesurer_scene.py [--url http://127.0.0.1:8794] [--largeur 1280 --hauteur 720] [--sortie ../competition/rehearsal/MESURES_SCENE.md]

Sans --url, démarre un serveur local éphémère (bases en mémoire). Chromium : celui de l'environnement si présent.
Lecture : ~200 mots par minute à voix haute ; au-delà de ~90 mots par étape, le public lit au lieu d'écouter.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROTO = Path(__file__).resolve().parents[1]


def _serveur(port: int) -> subprocess.Popen:
    env = {**os.environ, "HACKVS_SEMANTIQUE": "0", "HACKVS_DB": ":memory:", "HACKVS_DECISIONS_DB": ":memory:",
           "HACKVS_CYCLE_DB": ":memory:"}
    s = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=PROTO, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/stage", timeout=1)
            return s
        except OSError:
            time.sleep(0.5)
    s.kill()
    raise RuntimeError("serveur non démarré")


def mesurer(url: str, largeur: int, hauteur: int) -> list[dict]:
    from playwright.sync_api import sync_playwright
    chrome = "/opt/pw-browsers/chromium"
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome) if os.path.exists(chrome) else p.chromium.launch()
        pg = b.new_page(viewport={"width": largeur, "height": hauteur})
        erreurs: list[str] = []
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
        pg.goto(f"{url}/demo/stage")
        pg.request.post(f"{url}/api/stage/reinitialiser")
        pg.reload()
        pg.wait_for_selector("#carte h1")
        total = pg.evaluate("(async () => (await (await fetch('/api/stage')).json()).total)()")
        res = []
        for i in range(total + 1):
            if i:
                t0 = time.perf_counter()
                pg.click("#suiv")
                pg.wait_for_function(f"document.querySelector('#horloge').textContent.includes('étape {i}/')")
                attente = round((time.perf_counter() - t0) * 1000)
            else:
                attente = 0
            m = pg.evaluate("""() => {
                const c = document.querySelector('#carte'), nav = document.querySelector('.commandes');
                const bas = window.innerHeight - nav.getBoundingClientRect().height;
                const mots = c.innerText.split(/\\s+/).filter(Boolean).length;
                let visibles = 0;
                const marcheur = document.createTreeWalker(c, NodeFilter.SHOW_TEXT);
                while (marcheur.nextNode()) {
                  const n = marcheur.currentNode, r = document.createRange(); r.selectNodeContents(n);
                  const b = r.getBoundingClientRect();
                  if (b.height && b.top < bas) visibles += n.textContent.split(/\\s+/).filter(Boolean).length;
                }
                return {titre: (c.querySelector('h1') || {}).innerText || '', mots, visibles};
            }""")
            res.append({"etape": i, "titre": m["titre"].replace("\n", " "), "attente_ms": attente, "mots": m["mots"],
                        "sous_la_ligne_%": max(0, round(100 * (1 - m["visibles"] / m["mots"]))) if m["mots"] else 0})
        res.append({"erreurs": erreurs})
        b.close()
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="")
    ap.add_argument("--largeur", type=int, default=1280)
    ap.add_argument("--hauteur", type=int, default=720)
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    serveur = None if a.url else _serveur(8795)
    try:
        r = mesurer(a.url or "http://127.0.0.1:8795", a.largeur, a.hauteur)
    finally:
        if serveur:
            serveur.kill()
    erreurs = r.pop()["erreurs"]
    lignes = [f"# Mesures de la scène ({a.largeur}×{a.hauteur}, navigateur réel)", "",
              "Produit par `scripts/mesurer_scene.py`. Lecture à voix haute ≈ 200 mots/min : au-delà de ~90 mots, le public lit.", "",
              "| Étape | Titre | Attente après clic | Mots | Sous la ligne de flottaison |", "|---|---|---|---|---|"]
    for x in r:
        alerte = " ⚠" if x["mots"] > 90 or x["sous_la_ligne_%"] > 30 or x["attente_ms"] > 1000 else ""
        lignes.append(f"| {x['etape']} | {x['titre']}{alerte} | {x['attente_ms']} ms | {x['mots']} | {x['sous_la_ligne_%']} % |")
    lignes += ["", f"Erreurs de console : {len(erreurs)}" + (f" — {erreurs[:3]}" if erreurs else "")]
    texte = "\n".join(lignes) + "\n"
    print(texte)
    if a.sortie:
        Path(a.sortie).write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
