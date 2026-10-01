"""Revue visuelle : rend chaque slide (état final, sans transition) en PNG numéroté ; signale erreurs JS et requêtes réseau.

    python3 docs/presentation/deck/revue.py docs/presentation/deck/review/final/nuit [échelle] [nuit|jour]   # échelle 2 = 3840×2160
Nécessite Playwright + Chromium (outillage E2E du dépôt)."""
import functools
import os
import http.server
import socketserver
import sys
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright
DECK = Path(__file__).resolve().parent; OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
SCALE = float(sys.argv[2]) if len(sys.argv) > 2 else 1
MODE = sys.argv[3] if len(sys.argv) > 3 else "nuit"
class Muet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Muet, directory=str(DECK))); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    try:
        b = p.chromium.launch()
    except Exception:                                   # Chromium préinstallé hors du cache Playwright
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"))
    pg = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=SCALE)
    errs, ext = [], []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.on("request", lambda r: (not r.url.startswith(f"http://127.0.0.1:{port}") and not r.url.startswith("data:")) and ext.append(r.url))
    pg.goto(f"http://127.0.0.1:{port}/index.html?statique&mode={MODE}"); pg.evaluate("window.pret"); pg.wait_for_timeout(2800)
    ids = pg.evaluate("window.SLIDES")
    for n, sid in enumerate(ids, 1):
        pg.evaluate(f"allerA('{sid}', 'max')"); pg.wait_for_timeout(150)
        pg.screenshot(path=str(OUT / f"{n:02d}-{sid}.png"))
    print("slides:", len(ids), "| erreurs:", errs, "| requêtes externes:", ext)
    b.close()
srv.shutdown()
