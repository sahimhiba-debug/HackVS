"""Entraînement aux questions du jury : une page locale (double-clic, sans réseau) et le top 20 imprimable sur une page.

    python3 docs/presentation/outils/qa_entrainement.py
      → docs/presentation/qa/qa-entrainement.html   (questions de qa/qa.json, intégrées à la page)
      → docs/presentation/qa/TOP20.html et TOP20.pdf (si Playwright), une page A4

Source : qa/qa.json (six jurys simulés, 03.10 ; voir 07_QA_JURY_COMPLET.md)."""
import html
import json
import os
import re
from pathlib import Path

QA = Path(__file__).resolve().parent.parent / "qa"


def page_entrainement(questions: list[dict]) -> str:
    donnees = json.dumps(questions, ensure_ascii=False).replace("</", "<\\/")
    return """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Questions du jury</title>
<style>
:root { --fond: #f2f3f5; --carte: #fff; --encre: #141923; --doux: #5b6270; --rouge: #CD2128; --vert: #1F8A4C; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --fond: #0b0d12; --carte: #171a21; --encre: #f4f5f7; --doux: #9aa1ad; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--fond); color: var(--encre); font: 18px/1.45 -apple-system, "Helvetica Neue", Arial, sans-serif; }
main { max-width: 860px; margin: 0 auto; padding: 16px; }
h1 { font-size: 22px; margin: 8px 0; }
.outils { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 8px 0 16px; }
select, button { font: inherit; font-size: 16px; padding: 8px 12px; border-radius: 10px; border: 1px solid var(--doux); background: var(--carte); color: var(--encre); }
button.principal { background: var(--rouge); color: #fff; border-color: var(--rouge); font-weight: 700; }
.carte { background: var(--carte); border-radius: 16px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,.08); }
.jury { color: var(--doux); font-size: 15px; } .q { font-size: 26px; font-weight: 800; margin: 8px 0 16px; }
.chrono { font: 700 34px Menlo, monospace; } .chrono.fini { color: var(--rouge); }
.reponse { margin-top: 16px; } .reponse[hidden] { display: none; }
.r { font-size: 20px; } .meta { font-size: 14px; color: var(--doux); margin-top: 12px; } .meta b { color: var(--encre); }
.piege { border-left: 4px solid var(--rouge); padding-left: 10px; margin-top: 10px; font-size: 15px; }
.compte { color: var(--doux); font-size: 14px; }
</style></head>
<body><main>
<h1>Questions du jury — entraînement</h1>
<p class="compte">Une question au hasard. Réponds à voix haute en 15 à 30 secondes, puis compare. Espace : révéler ·
→ : question suivante.</p>
<div class="outils">
  <select id="jury" aria-label="Jury"><option value="">Tous les jurys</option></select>
  <label><input type="checkbox" id="top"> top 20 seulement</label>
  <button class="principal" id="suivante">Question suivante →</button>
  <button id="reveler">Révéler la réponse</button>
  <span class="chrono" id="chrono" aria-live="off">0:30</span>
</div>
<div class="carte">
  <div class="jury" id="qui"></div>
  <div class="q" id="question"></div>
  <div class="reponse" id="reponse" hidden>
    <div class="r" id="r"></div>
    <div class="piege" id="piege"></div>
    <div class="meta"><b>Preuve</b> : <span id="preuve"></span></div>
  </div>
</div>
<p class="compte" id="compte"></p>
</main>
<script>
const QS = """ + donnees + """;
const $ = (s) => document.querySelector(s);
const jurys = [...new Set(QS.map((q) => q.jury))];
for (const j of jurys) { const o = document.createElement("option"); o.value = j; o.textContent = j; $("#jury").appendChild(o); }
let pile = [], vues = 0, minuteur = null, fin = 0;
function filtre() { return QS.filter((q) => (!$("#jury").value || q.jury === $("#jury").value) && (!$("#top").checked || q.top20)); }
function melanger() { pile = filtre().slice(); for (let i = pile.length - 1; i > 0; i--) { const k = Math.floor(Math.random() * (i + 1)); [pile[i], pile[k]] = [pile[k], pile[i]]; } }
function chrono() {
  clearInterval(minuteur); fin = performance.now() + 30000;
  minuteur = setInterval(() => { const r = Math.max(0, Math.ceil((fin - performance.now()) / 1000));
    $("#chrono").textContent = `0:${String(r).padStart(2, "0")}`; $("#chrono").classList.toggle("fini", r === 0);
    if (r === 0) clearInterval(minuteur); }, 200);
}
function suivante() {
  if (!pile.length) melanger();
  const q = pile.pop(); if (!q) { $("#question").textContent = "Aucune question pour ce filtre."; return; }
  vues += 1;
  $("#qui").textContent = q.jury + (q.top20 ? " · top 20" : "");
  $("#question").textContent = q.q; $("#r").textContent = q.r;
  $("#piege").textContent = "Ne pas dire : " + q.ne_pas_dire; $("#preuve").textContent = q.preuve;
  $("#reponse").hidden = true; $("#compte").textContent = `${vues} question(s) cette séance · ${filtre().length} dans ce filtre`;
  chrono();
}
function reveler() { $("#reponse").hidden = false; clearInterval(minuteur); }
$("#suivante").addEventListener("click", suivante); $("#reveler").addEventListener("click", reveler);
$("#jury").addEventListener("change", () => { melanger(); suivante(); }); $("#top").addEventListener("change", () => { melanger(); suivante(); });
addEventListener("keydown", (e) => { if (e.key === " ") { e.preventDefault(); reveler(); } else if (e.key === "ArrowRight") suivante(); });
melanger(); suivante();
</script>
</body></html>
"""


def page_top20(md: str) -> str:
    corps = []
    for bloc in md.split("\n\n"):
        b = html.escape(bloc.strip())
        if not b:
            continue
        b = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", b)
        b = re.sub(r"_(\(.+?\))_", r"<i>\1</i>", b)
        b = re.sub(r"`(.+?)`", r"<code>\1</code>", b)
        corps.append(f"<h1>{b[2:]}</h1>" if b.startswith("# ") else f"<p>{b.replace('  ' + chr(10), '<br>').replace(chr(10), ' ')}</p>")
    return ("<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>Top 20 du jury</title><style>@page { size: A4; margin: 8mm; } body { font: 7.6pt/1.27 -apple-system, Arial, sans-serif;"
            " color: #141923; background: #fff; margin: 0 16px; } h1 { font-size: 12pt; margin: 0 0 3px; } p { margin: 0 0 3.5px; }"
            " i { color: #5b6270; } b { color: #141923; } code { font-size: 7pt; }</style></head><body>" + "".join(corps) + "</body></html>")


def pdf(source: Path) -> Path | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    cible = source.with_suffix(".pdf")
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:                        # Chromium préinstallé hors du cache Playwright
            b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"))
        pg = b.new_page()
        pg.goto(source.as_uri())
        pg.pdf(path=str(cible), format="A4", print_background=True, prefer_css_page_size=True)
        b.close()
    return cible


if __name__ == "__main__":
    qs = json.loads((QA / "qa.json").read_text(encoding="utf-8"))
    (QA / "qa-entrainement.html").write_text(page_entrainement(qs), encoding="utf-8")
    top = QA / "TOP20.html"
    top.write_text(page_top20((QA / "TOP20.md").read_text(encoding="utf-8")), encoding="utf-8")
    print(len(qs), "questions ·", QA / "qa-entrainement.html", "·", pdf(top) or top)
