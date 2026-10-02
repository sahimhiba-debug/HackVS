"""Les sept livrables de présentation (docs/presentation/*.md) → un seul PDF, via HTML + Chromium headless."""
import html
import sys
from datetime import date
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

RACINE = Path("/home/user/HackVS/docs/presentation")
FICHIERS = sorted(RACINE.glob("0*_*.md"))
SORTIE = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE.parent.parent / "CLUB_PULSE_PRESENTATION.pdf"

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
body { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 10.2pt; line-height: 1.42; color: #141923; }
h1 { font-size: 20pt; color: #CD2128; margin: 0 0 10pt; page-break-before: always; }
h1.premiere { page-break-before: avoid; }
h2 { font-size: 13.5pt; margin: 16pt 0 6pt; border-bottom: 1.5px solid #CD2128; padding-bottom: 2pt; }
h3 { font-size: 11.5pt; margin: 12pt 0 4pt; }
p { margin: 5pt 0; }
blockquote { margin: 6pt 0 6pt 10pt; padding: 4pt 10pt; border-left: 3px solid #CD2128; background: #FDEDEE; }
blockquote p { margin: 3pt 0; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.8pt; background: #F3F4F6; padding: 0 2px; }
pre { font-family: "DejaVu Sans Mono", monospace; font-size: 8.4pt; background: #F3F4F6; padding: 6pt; white-space: pre-wrap; }
table { border-collapse: collapse; width: 100%; font-size: 8.6pt; margin: 6pt 0; page-break-inside: auto; }
th, td { border: 1px solid #C9CDD3; padding: 3pt 4pt; vertical-align: top; text-align: left; }
th { background: #F3F4F6; }
tr { page-break-inside: avoid; }
ul, ol { margin: 4pt 0 4pt 16pt; padding: 0; }
li { margin: 2pt 0; }
hr { border: 0; border-top: 1px solid #C9CDD3; margin: 10pt 0; }
.couverture { height: 240mm; display: flex; flex-direction: column; justify-content: center; }
.couverture .sur { color: #CD2128; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; font-size: 10pt; }
.couverture h1 { font-size: 30pt; color: #141923; page-break-before: avoid; margin: 8pt 0; }
.couverture p { color: #4B5563; font-size: 11pt; }
.couverture ol { margin-top: 16pt; font-size: 11pt; }
.pied { color: #6B7280; font-size: 8.5pt; }
"""

parties = []
for f in FICHIERS:
    texte = f.read_text(encoding="utf-8")
    corps = markdown.markdown(texte, extensions=["tables", "fenced_code", "sane_lists"])
    parties.append(corps)

sommaire = "".join(f"<li>{html.escape(f.stem.replace('_', ' '))}</li>" for f in FICHIERS)
couverture = f"""
<div class="couverture">
  <div class="sur">Club Pulse — Hack VS 2026</div>
  <h1>Présentation finale<br>Dossier de mise en scène</h1>
  <p>Jury Hack VS / Club des Affaires · CERM Martigny · 10 minutes</p>
  <ol>{sommaire}</ol>
  <p class="pied">Généré le {date.today().isoformat()} depuis <code>docs/presentation/</code> (commit de la branche
  <code>claude/modest-bohr-xvk53n</code>). Contenu seulement : le deck visuel se fait côté design à partir de
  06_SLIDE_CONTENT. Chiffres marqués [GEL] à remplir après le tag <code>gel-demo</code>.</p>
</div>
"""
page = f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{couverture}{''.join(parties)}</body></html>"

with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = nav.new_page()
    pg.set_content(page, wait_until="load")
    pg.pdf(path=str(SORTIE), format="A4", print_background=True, prefer_css_page_size=True,
           display_header_footer=True, header_template="<span></span>",
           footer_template="<div style='font-size:7.5pt;color:#6B7280;width:100%;text-align:center;font-family:DejaVu Sans,Arial'>"
                           "Club Pulse — présentation finale · <span class='pageNumber'></span> / <span class='totalPages'></span></div>",
           margin={"top": "18mm", "bottom": "20mm", "left": "16mm", "right": "16mm"})
    nav.close()
print(SORTIE)
