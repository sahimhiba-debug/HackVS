"""Version imprimable du script v2 : une ligne par moment, une colonne par intervenant, les chronos de chaque acte.

    python3 docs/presentation/outils/script_imprimable.py            # → livrables/SCRIPT_v2_IMPRIMABLE.html (+ .pdf si Playwright)

Source unique : 03_SCRIPT_ORAL_v2.md (rien n'est réécrit à la main). Ce qui est en citation (`>`) va dans la colonne V1
(« à dire ») ; une indication entre crochets qui nomme V2 va dans la colonne V2 ; les autres indications vont dans la
colonne « à l'écran / action ». Les chronos sont ceux des titres d'acte (02_STRUCTURE_v2.md)."""
import html
import os
import re
from pathlib import Path

ICI = Path(__file__).resolve().parent
PRES = ICI.parent
SOURCE = PRES / "03_SCRIPT_ORAL_v2.md"
SORTIE = PRES / "livrables" / "SCRIPT_v2_IMPRIMABLE.html"
ACTE = re.compile(r"^## (Acte \d+) — (.+?) · ([\d:]+–[\d:]+) · (.+)$")


def _en_ligne(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return re.sub(r"\[([^\]]+)\]", r"<i class='geste'>[\1]</i>", t)


def lire() -> list[dict]:
    actes, ligne, suite = [], None, None
    for brut in SOURCE.read_text(encoding="utf-8").splitlines():
        m = ACTE.match(brut)
        if m:
            actes.append({"acte": m[1], "titre": m[2], "chrono": m[3], "qui": m[4], "lignes": []})
            ligne = None
            continue
        if not actes or brut.startswith("## ") or brut.strip() == "---":
            if brut.startswith("## ") and actes:
                actes.append(None)     # fin des actes (pense-bête)
            continue
        if actes[-1] is None:
            continue
        s = brut.strip()
        if suite is not None:                       # indication entre crochets sur plusieurs lignes
            suite += " " + s
            if not s.endswith("]"):
                continue
            s, suite = suite, None
        elif s.startswith("[") and not s.endswith("]"):
            suite = s
            continue
        if s.startswith(">"):
            texte = s[1:].strip()
            if ligne is None:
                ligne = {"v1": [], "v2": [], "ecran": []}
                actes[-1]["lignes"].append(ligne)
            if texte:
                ligne["v1"].append(texte)
            elif ligne["v1"]:
                ligne["v1"].append("")          # paragraphe
        elif s.startswith("[") or s.startswith("**Plan B"):
            ligne = {"v1": [], "v2": [], "ecran": []}
            actes[-1]["lignes"].append(ligne)
            texte = s.strip("[]") if s.startswith("[") and s.endswith("]") else s
            (ligne["v2"] if re.search(r"\bV2\b", texte) else ligne["ecran"]).append(texte)
        elif s and ligne is not None and not s.startswith(">"):
            (ligne["v2"] if ligne["v2"] else ligne["ecran"]).append(s)
    return [a for a in actes if a]


def _cellule(morceaux: list[str]) -> str:
    paras, cur = [], []
    for m in morceaux + [""]:
        if m:
            cur.append(m)
        elif cur:
            paras.append(" ".join(cur))
            cur = []
    return "".join(f"<p>{_en_ligne(p)}</p>" for p in paras)


def rendre(actes: list[dict]) -> str:
    corps = []
    for a in actes:
        corps.append(f"<tr class='acte'><td colspan='4'><span class='chrono'>{a['chrono']}</span> {a['acte']} — "
                     f"{html.escape(a['titre'])} <span class='qui'>· {html.escape(a['qui'])}</span></td></tr>")
        for i, l in enumerate(a["lignes"]):
            debut = a["chrono"].split("–")[0] if i == 0 else ""
            corps.append(f"<tr><td class='t'>{debut}</td><td class='v1'>{_cellule(l['v1'])}</td>"
                         f"<td class='v2'>{_cellule(l['v2'])}</td><td class='ec'>{_cellule(l['ecran'])}</td></tr>")
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Script v2 imprimable</title>
<style>
@page {{ size: A4 landscape; margin: 12mm; }}
:root {{ --encre: #141923; --rouge: #CD2128; --gris: #5b6270; --trait: #d9dce1; --fond: #fff; --acte: #f2f3f5; }}
body {{ font: 11pt/1.4 -apple-system, "Helvetica Neue", Arial, sans-serif; color: var(--encre); background: var(--fond); margin: 0 16px; }}
h1 {{ font-size: 16pt; margin: 8px 0 2px; }} .sous {{ color: var(--gris); font-size: 9.5pt; margin: 0 0 10px; }}
table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
th {{ text-align: left; font-size: 9pt; text-transform: uppercase; letter-spacing: .04em; color: var(--gris);
      border-bottom: 2px solid var(--encre); padding: 4px 6px; }}
td {{ vertical-align: top; padding: 5px 6px; border-bottom: 1px solid var(--trait); }}
td p {{ margin: 0 0 5px; }}
col.t {{ width: 6%; }} col.v1 {{ width: 50%; }} col.v2 {{ width: 22%; }} col.ec {{ width: 22%; }}
tr.acte td {{ background: var(--acte); font-weight: 700; border-top: 2px solid var(--encre); padding: 6px; }}
tr {{ break-inside: avoid; }} thead {{ display: table-header-group; }}
.chrono, td.t {{ font-family: Menlo, "JetBrains Mono", monospace; color: var(--rouge); font-weight: 700; }}
.qui {{ color: var(--gris); font-weight: 400; }}
td.v1 {{ font-size: 12pt; }} td.v2, td.ec {{ font-size: 9.5pt; color: #2b3240; }}
.geste {{ color: var(--gris); font-style: italic; font-size: .9em; }}
code {{ font-family: Menlo, monospace; font-size: .9em; }}
.coeur {{ margin-top: 14px; border: 2px solid var(--rouge); padding: 8px 12px; break-inside: avoid; }}
.coeur h2 {{ font-size: 11pt; margin: 0 0 4px; color: var(--rouge); }} .coeur li {{ margin: 2px 0; }}
</style></head><body>
<h1>Club Pulse — script oral v2 (cible 18:00)</h1>
<p class="sous">Généré depuis <code>docs/presentation/03_SCRIPT_ORAL_v2.md</code> par <code>outils/script_imprimable.py</code>.
Colonne V1 : ce qui se dit, et seulement ça. Entre crochets : ne se dit pas. Chronos : début de chaque acte (02_STRUCTURE_v2).</p>
<table><colgroup><col class="t"><col class="v1"><col class="v2"><col class="ec"></colgroup>
<thead><tr><th>Chrono</th><th>V1 — à dire</th><th>V2 — régie, écrans</th><th>À l'écran / action</th></tr></thead>
<tbody>{"".join(corps)}</tbody></table>
<div class="coeur"><h2>Par cœur, mot pour mot</h2><ul>
<li>« Et après ? » (trois fois : acte 1, après le film, avant le reçu)</li>
<li>« Cette année, la Foire fait son cinéma. Nous aussi. »</li>
<li>« En dessous de trois, le Club ne compte pas : il protège. » (trois <b>entreprises</b>)</li>
<li>« Un pilote de 45 jours avec 50 membres volontaires parmi vos 173 représentants. » — « Oui, non, ou pas cette fois. »</li>
<li>« Regardez votre téléphone : vous avez un reçu. »</li>
<li>« La Foire crée la rencontre. Club Pulse crée l'après. » — « Si Jean-Marc dit oui, c'est que c'est oui. »</li>
<li>Si on demande où tourne la démo : « la démo est servie depuis notre machine, à Martigny, via un tunnel chiffré ».
« Le relais ne peut pas lire les données » : <b>seulement</b> sur Tailscale Funnel, jamais sur le secours Cloudflare.</li>
</ul></div>
</body></html>
"""


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
        pg.pdf(path=str(cible), format="A4", landscape=True, print_background=True, prefer_css_page_size=True)
        b.close()
    return cible


if __name__ == "__main__":
    actes = lire()
    SORTIE.write_text(rendre(actes), encoding="utf-8")
    print(SORTIE, "·", len(actes), "actes ·", sum(len(a["lignes"]) for a in actes), "lignes")
    print(pdf(SORTIE) or "PDF non produit (Playwright absent) : ouvrir le .html dans Chrome, puis Imprimer")
