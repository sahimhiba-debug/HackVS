"""Prompteur local du pitch v2 : une seule page HTML, sans dépendance externe, ouverte en double-clic.

    python3 docs/presentation/outils/prompteur.py      # → docs/presentation/prompteur/prompteur.html

Source unique : 03_SCRIPT_ORAL_v2.md (le texte y est intégré : une page ouverte en double-clic ne peut pas lire de
fichier). Ce que dit V1 en gros ; les actions de V2 dans une colonne à part ; les indications de scène en petit ; les
phrases par cœur (en gras dans le script) surlignées ; un chrono par acte (cibles de 02_STRUCTURE_v2)."""
import html
import json
import re
from pathlib import Path

ICI = Path(__file__).resolve().parent
PRES = ICI.parent
SOURCE = PRES / "03_SCRIPT_ORAL_v2.md"
SORTIE = PRES / "prompteur" / "prompteur.html"
ACTE = re.compile(r"^## (Acte \d+) — (.+?) · ([\d:]+)–([\d:]+) · (.+)$")


def _s(t: str) -> int:
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def _ligne(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<mark>\1</mark>", t)
    t = re.sub(r"\[([^\]]+)\]", r"<i class='geste'>[\1]</i>", t)
    return t.replace(" / ", " <span class='pause'>/</span> ")


def lire() -> list[dict]:
    actes: list[dict] = []
    bloc: list[str] = []
    suite = None

    def vider():
        if bloc and actes:
            actes[-1]["blocs"].append({"type": "dit", "html": " ".join(_ligne(x) for x in bloc)})
        bloc.clear()
    for brut in SOURCE.read_text(encoding="utf-8").splitlines():
        m = ACTE.match(brut)
        if m:
            vider()
            actes.append({"acte": m[1], "titre": m[2], "debut": _s(m[3]), "fin": _s(m[4]), "qui": m[5], "blocs": []})
            continue
        if brut.startswith("## ") and actes:
            vider()
            break                                   # « Par cœur », « Pense-bête » : la fin des actes
        if brut.strip() == "---" or brut.startswith("## "):
            vider()
            continue
        if not actes:
            continue
        s = brut.strip()
        if suite is not None:
            suite += " " + s
            if not s.endswith("]"):
                continue
            s, suite = suite, None
        elif s.startswith("[") and not s.endswith("]"):
            vider()
            suite = s
            continue
        if s.startswith(">"):
            t = s[1:].strip()
            if t:
                bloc.append(t)
            else:
                vider()
        elif s.startswith("[") or s.startswith("**Plan B"):
            vider()
            texte = s[1:-1] if s.startswith("[") and s.endswith("]") else s
            genre = "v2" if re.search(r"\bV2\b", texte) else "scene"
            actes[-1]["blocs"].append({"type": genre, "html": _ligne(texte)})
        elif s:
            vider()
    vider()
    return actes


def rendre(actes: list[dict]) -> str:
    corps = []
    for k, a in enumerate(actes):
        corps.append(f"<section class='acte' data-k='{k}'><h2><span class='chr'>{a['debut'] // 60}:{a['debut'] % 60:02d}</span> "
                     f"{html.escape(a['acte'])} — {html.escape(a['titre'])} <small>{html.escape(a['qui'])}</small></h2>")
        for b in a["blocs"]:
            if b["type"] == "dit":
                corps.append(f"<div class='rang'><p class='dit'>{b['html']}</p><div class='cote'></div></div>")
            elif b["type"] == "v2":
                corps.append(f"<div class='rang'><p class='vide'></p><div class='cote v2'><b>V2</b> {b['html']}</div></div>")
            else:
                corps.append(f"<div class='rang'><p class='scene'>{b['html']}</p><div class='cote'></div></div>")
        corps.append("</section>")
    cibles = json.dumps([{"acte": a["acte"], "titre": a["titre"], "debut": a["debut"], "fin": a["fin"]} for a in actes])
    return PAGE.replace("{{CORPS}}", "\n".join(corps)).replace("{{CIBLES}}", cibles)


PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prompteur Club Pulse</title>
<style>
:root { --fond: #0b0d12; --texte: #f4f5f7; --doux: #9aa1ad; --rouge: #ff5a5f; --marque: #ffe58a; --v2: #8fd3ff; --taille: 44px; }
:root[data-theme="light"] { --fond: #ffffff; --texte: #141923; --doux: #5b6270; --rouge: #CD2128; --marque: #fff1a8; --v2: #0b5cad; }
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--fond); color: var(--texte); font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; }
#barre { position: fixed; top: 0; left: 0; right: 0; z-index: 3; display: flex; gap: 16px; align-items: center; flex-wrap: wrap;
         padding: 8px 16px; background: #000; color: #fff; font: 15px/1.3 Menlo, monospace; }
#barre b { color: #ffe58a; } #barre .ko { color: #ff5a5f; } #barre .ok { color: #7ee2a8; }
#aide { margin-left: auto; color: #9aa1ad; }
#guide { position: fixed; left: 0; right: 0; top: 38%; height: 0; border-top: 2px dashed rgba(255,90,95,.55); z-index: 2; pointer-events: none; }
#texte { padding: 45vh 16px 80vh; max-width: 1500px; margin: 0 auto; }
body.miroir #texte { transform: scaleX(-1); }
.acte h2 { font-size: calc(var(--taille) * .55); color: var(--doux); border-top: 1px solid var(--doux); padding-top: 18px; margin: 48px 0 18px; }
.acte h2 small { font-weight: 400; } .chr { color: var(--rouge); font-family: Menlo, monospace; }
.rang { display: grid; grid-template-columns: minmax(0, 1fr) minmax(160px, 26%); gap: 24px; }
.dit { font-size: var(--taille); line-height: 1.32; font-weight: 600; margin: 0 0 .6em; }
.scene, .vide { font-size: calc(var(--taille) * .42); color: var(--doux); font-style: italic; margin: 0 0 .8em; }
.cote { font-size: calc(var(--taille) * .42); line-height: 1.3; }
.cote.v2 { color: var(--v2); border-left: 4px solid var(--v2); padding-left: 10px; margin-bottom: .8em; }
.geste { color: var(--doux); font-weight: 400; font-size: .55em; }
.pause { color: var(--rouge); font-weight: 400; padding: 0 .15em; }
mark { background: var(--marque); color: #141923; padding: 0 .12em; border-radius: 4px; }
@media (max-width: 700px) { .rang { grid-template-columns: 1fr; } :root { --taille: 30px; } }
</style></head>
<body>
<div id="barre" role="status" aria-live="off">
  <span>⏱ <b id="total">0:00</b></span><span id="acte">—</span><span id="cible">—</span><span>vitesse <b id="vit">40</b></span>
  <span id="aide">Espace : lecture/pause · ↑↓ : vitesse · ←→ : acte · PgUp/PgDn : défiler · +/− : taille ·
    M : miroir · L : clair/sombre · 0 : chrono à zéro</span>
</div>
<div id="guide" aria-hidden="true"></div>
<main id="texte">
{{CORPS}}
</main>
<script>
const CIBLES = {{CIBLES}};
const $ = (s) => document.querySelector(s);
const actes = [...document.querySelectorAll(".acte")];
let lecture = false, vitesse = 40, taille = 44, t0 = null, cumul = 0, dernier = null, reste = 0;
const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const lire = (k, v) => { try { return localStorage.getItem("prompteur-" + k) ?? v; } catch (e) { return v; } };
const garder = (k, v) => { try { localStorage.setItem("prompteur-" + k, v); } catch (e) { /* sans stockage */ } };
vitesse = +lire("vitesse", 40); taille = +lire("taille", 44);
if (lire("miroir", "0") === "1") document.body.classList.add("miroir");
document.documentElement.dataset.theme = lire("theme", "dark");
function appliquer() { document.documentElement.style.setProperty("--taille", taille + "px"); $("#vit").textContent = vitesse; }
appliquer();
function ecoule() { return cumul + (lecture && t0 !== null ? (performance.now() - t0) / 1000 : 0); }
function acteCourant() {
  const ligne = innerHeight * 0.38; let k = 0;
  actes.forEach((a, i) => { if (a.getBoundingClientRect().top <= ligne) k = i; });
  return k;
}
function barre() {
  const t = ecoule(), k = acteCourant(), c = CIBLES[k];
  $("#total").textContent = mmss(t);
  $("#acte").textContent = `${c.acte} · ${c.titre}`;
  const retard = t - c.fin;
  $("#cible").innerHTML = `cible ${mmss(c.debut)}–${mmss(c.fin)} · ` + (t < c.debut ? `<span class="ok">en avance ${mmss(c.debut - t)}</span>`
    : retard > 0 ? `<span class="ko">en retard ${mmss(retard)}</span>` : `<span class="ok">reste ${mmss(c.fin - t)}</span>`);
}
function boucle(ts) {
  if (lecture) {
    if (dernier !== null) { reste += vitesse * (ts - dernier) / 1000; const px = Math.floor(reste); if (px) { scrollBy(0, px); reste -= px; } }
    dernier = ts;
  } else dernier = null;
  barre(); requestAnimationFrame(boucle);
}
requestAnimationFrame(boucle);
function basculer() { if (lecture) { cumul = ecoule(); t0 = null; lecture = false; } else { t0 = performance.now(); lecture = true; } }
function allerActe(d) { const k = Math.max(0, Math.min(actes.length - 1, acteCourant() + d));
  scrollTo({ top: scrollY + actes[k].getBoundingClientRect().top - innerHeight * 0.38 + 4 }); }
addEventListener("keydown", (e) => {
  const k = e.key;
  if (k === " ") { e.preventDefault(); basculer(); }
  else if (k === "ArrowUp") { e.preventDefault(); vitesse = Math.min(200, vitesse + 5); garder("vitesse", vitesse); appliquer(); }
  else if (k === "ArrowDown") { e.preventDefault(); vitesse = Math.max(5, vitesse - 5); garder("vitesse", vitesse); appliquer(); }
  else if (k === "ArrowRight") { e.preventDefault(); allerActe(1); }
  else if (k === "ArrowLeft") { e.preventDefault(); allerActe(-1); }
  else if (k === "+" || k === "=") { taille = Math.min(96, taille + 4); garder("taille", taille); appliquer(); }
  else if (k === "-") { taille = Math.max(20, taille - 4); garder("taille", taille); appliquer(); }
  else if (k === "m" || k === "M") { document.body.classList.toggle("miroir"); garder("miroir", document.body.classList.contains("miroir") ? "1" : "0"); }
  else if (k === "l" || k === "L") {
    const t = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = t; garder("theme", t);
  }
  else if (k === "0") { cumul = 0; t0 = lecture ? performance.now() : null; }
});
</script>
</body></html>
"""


if __name__ == "__main__":
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    a = lire()
    SORTIE.write_text(rendre(a), encoding="utf-8")
    print(SORTIE, "·", len(a), "actes ·", sum(len(x["blocs"]) for x in a), "blocs")
