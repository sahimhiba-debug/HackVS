"""RESUME_JURY.html → RESUME_JURY.pdf (une page A4), avec le Chromium de Playwright. À lancer ici, pas sur le Mac."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

VIDEO = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page()
    pg.goto((VIDEO / "RESUME_JURY.html").as_uri())
    pg.pdf(path=str(VIDEO / "RESUME_JURY.pdf"), format="A4", prefer_css_page_size=True, print_background=True)
    b.close()
n = (VIDEO / "RESUME_JURY.pdf").read_bytes().count(b"/Type /Page\n") or (VIDEO / "RESUME_JURY.pdf").read_bytes().count(b"/Type /Page")
print("RESUME_JURY.pdf", n, "page(s)")
sys.exit(0)
