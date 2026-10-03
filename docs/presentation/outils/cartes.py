"""Deux cartes imprimables d'UNE page (A4 portrait) pour le jour J :

- CARTE_REGIE_V2 : la carte de régie de V2 — les 4 boutons, leurs minutes, quoi faire si un écran ne répond pas ;
- CARTE_V1 : la carte de V1 — les phrases par cœur, les repères de chrono (touche R du deck) et les touches utiles.

    python3 docs/presentation/outils/cartes.py      # → livrables/CARTE_REGIE_V2.{html,pdf}, livrables/CARTE_V1.{html,pdf}

Les libellés des boutons sont ceux de prototype/web/pulse/salle-regie.html, les repères ceux de 02_STRUCTURE_v2.md
(vérifiés par prototype/tests/test_jour_j_cartes.py)."""
import html
import os
from pathlib import Path

ICI = Path(__file__).resolve().parent
LIVRABLES = ICI.parent / "livrables"
URL_REGIE = "https://clubpulse.tailfcbc50.ts.net/salle/regie"

BOUTONS = [  # (minute, libellé exact du bouton, ce qu'on doit voir)
    ("H-30", "1 · Ouvrir la salle (QR)", "« ouverte » dans la régie ; scanner avec ton téléphone, en 4G"),
    ("5:30", "1 bis · « Sortez vos téléphones » (en séance)", "quand V1 dit « Sortez vos téléphones » ; la minute de bascule part d'ici"),
    ("7:30", "2 · Lancer la demande vers la salle", "l'anneau se dessine à 3/4 sur l'écran du deck"),
    ("8:30", "3 · Déclencher un retrait (simulé en démonstration)", "une ligne se rétracte, « un composant n'est plus disponible », la réserve recompose"),
    ("9:00", "4 · Afficher le bilan (Suivi de la salle)", "le tableau final ; V1 conclut et avance"),
]
PANNES = [
    ("L'écran du deck dit « ne répond pas », ou reste noir", "Faire signe à V1 : <b>touche B</b> — la vidéo de 30 s. V1 dit : « Voici ce que vous auriez vu — une séance simulée, enregistrée hier soir. »"),
    ("Rien ne bouge après le bouton 2", "Faire signe à V1 : <b>⌘-R</b> (le deck recharge et revient sur la même slide). Toujours rien : <b>touche B</b>."),
    ("Moins de 5 téléphones une minute après « 1 bis »", "Ne rien faire : la démonstration scriptée prend le relais seule (bandeau « démonstration scriptée dans 5 s »)."),
    ("Aucun « oui » sur une pièce", "Répondre <b>Oui</b> avec ton téléphone de secours (QR scanné avant le pitch)."),
    ("Ta régie affiche « hors ligne » ou « refusé »", "Recharger la page ; recoller le jeton si elle le demande. Toujours rien : V1 passe à la vidéo (<b>touche B</b>)."),
]
PAR_COEUR = [
    "Et après ?  (trois fois : fin de l'acte 1, après le film, avant le reçu)",
    "Cette année, la Foire fait son cinéma. Nous aussi.",
    "En dessous de trois, le Club ne compte pas : il protège.  (trois entreprises)",
    "Un pilote de 45 jours avec 50 membres volontaires parmi vos 173 représentants.",
    "Oui, non, ou pas cette fois.",
    "Regardez votre téléphone : vous avez un reçu.",
    "La Foire crée la rencontre. Club Pulse crée l'après.",
    "Si Jean-Marc dit oui, c'est que c'est oui.",
]
REPERES = [  # 02_STRUCTURE_v2.md, « Points de contrôle (touche R du deck v2) »
    ("1:55", "« Et après ? » (1/3)", "couper la deuxième relance des mains levées"),
    ("5:30", "Fin du film", "respiration en une phrase de cinq mots"),
    ("7:30", "La demande part vers la salle", "lancer sans attendre plus de participants"),
    ("9:30", "Côté Club", "plan B constellation : vidéo (B), 30 s"),
    ("12:15", "La science de la demande", "sauter « Votre Club en chiffres » (garder « assembler »)"),
    ("14:00", "Où nous en sommes", "lire deux preuves sur quatre"),
    ("15:50", "La demande au Club", "sauter la slide « pile suisse »"),
    ("16:50", "Carte + reçu", "la phrase finale, puis noir"),
]
TOUCHES = [("→ · Espace · clic", "avancer"), ("← · clic droit", "reculer"), ("B", "sur « constellation » : la vidéo de secours"),
           ("⌘-R", "recharger : revient sur la même slide"), ("J", "jour / nuit"), ("N", "écran noir"), ("F", "plein écran")]

STYLE = """
@page { size: A4 portrait; margin: 11mm; }
:root { --encre: #141923; --rouge: #CD2128; --gris: #5b6270; --trait: #d9dce1; --fond: #fff; --doux: #f2f3f5; }
* { box-sizing: border-box; }
body { font: 11pt/1.38 -apple-system, "Helvetica Neue", Arial, sans-serif; color: var(--encre); background: var(--fond); margin: 0 16px; }
h1 { font-size: 20pt; margin: 4px 0 2px; } h2 { font-size: 12pt; margin: 14px 0 6px; color: var(--rouge); text-transform: uppercase; letter-spacing: .04em; }
.sous { color: var(--gris); font-size: 9.5pt; margin: 0 0 6px; }
table { width: 100%; border-collapse: collapse; } td { vertical-align: top; padding: 6px 6px; border-bottom: 1px solid var(--trait); }
.t { font-family: Menlo, "JetBrains Mono", monospace; font-weight: 700; color: var(--rouge); white-space: nowrap; width: 1%; }
.bouton { display: inline-block; border: 2px solid var(--encre); border-radius: 8px; padding: 3px 8px; font-weight: 700; }
.vu { color: var(--gris); font-size: 9.5pt; }
.panne td:first-child { font-weight: 700; width: 38%; }
.coeur li { font-size: 13pt; font-weight: 700; margin: 4px 0; }
.coeur { padding-left: 20px; margin: 0; }
.touches { display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px 16px; font-size: 10pt; }
.touches b { font-family: Menlo, monospace; display: inline-block; min-width: 190px; }
.cadre { background: var(--doux); border-radius: 10px; padding: 8px 12px; font-size: 10pt; margin-top: 8px; }
code { font-family: Menlo, monospace; font-size: 9.5pt; overflow-wrap: anywhere; }
"""


def _page(titre: str, corps: str) -> str:
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, '
            f'initial-scale=1"><title>{html.escape(titre)}</title><style>{STYLE}</style></head><body>{corps}</body></html>')


def carte_regie() -> str:
    lignes = "".join(f"<tr><td class='t'>{m}</td><td><span class='bouton'>{html.escape(b)}</span><div class='vu'>{html.escape(v)}</div></td></tr>"
                     for m, b, v in BOUTONS)
    pannes = "".join(f"<tr><td>{html.escape(q)}</td><td>{r}</td></tr>" for q, r in PANNES)
    return _page("Carte de régie V2", f"""
<h1>Carte de régie — V2</h1>
<p class="sous">Club Pulse · deck v2 · tu ne parles pas : tu appuies. V1 a la télécommande du deck.</p>
<div class="cadre">Ta régie : <code>{URL_REGIE}</code> — colle le jeton que Hiba t'envoie (une fois). L'écran de la salle
s'affiche <b>dans le deck</b> : personne ne change de fenêtre.</div>
<h2>Les boutons, dans l'ordre</h2>
<table>{lignes}</table>
<h2>Si un écran ne répond pas</h2>
<table class="panne">{pannes}</table>
<h2>Après le pitch</h2>
<p>Hiba double-clique sur <b>« 2 - Arrêter et effacer »</b> : la salle est effacée (c'est promis à la salle), le tunnel
fermé, tout s'éteint. Ne rien effacer à la main.</p>""")


def carte_v1() -> str:
    coeur = "".join(f"<li>« {html.escape(p.split('  (')[0])} »" + (f" <span class='vu'>({html.escape(p.split('  (')[1])}</span>" if "  (" in p else "") + "</li>"
                    for p in PAR_COEUR)
    reperes = "".join(f"<tr><td class='t'>{t}</td><td>{html.escape(r)}</td><td class='vu'>en retard de plus de 15 s → {html.escape(c)}</td></tr>"
                      for t, r, c in REPERES)
    touches = "".join(f"<div><b>{html.escape(k)}</b>{html.escape(v)}</div>" for k, v in TOUCHES)
    return _page("Carte de V1", f"""
<h1>Carte de V1</h1>
<p class="sous">Club Pulse · deck v2 · cible 18:00 · tu parles du début à la fin ; V2 tient la régie.</p>
<h2>Par cœur, mot pour mot</h2>
<ul class="coeur">{coeur}</ul>
<h2>Repères de chrono (touche R en répétition seulement)</h2>
<table>{reperes}</table>
<h2>Avant de monter</h2>
<p>La check-list doit dire <b>« FEU VERT v2 »</b>. « RÉPARER D'ABORD » : la raison est écrite. « PASSER EN v1 » :
double-clic sur <b>« 3 - Passer en v1 »</b>, puis le script v1.</p>
<h2>Touches du deck</h2>
<div class="touches">{touches}</div>
<div class="cadre">Si on demande où tourne la démo : « la démo est servie depuis notre machine, à Martigny, via un tunnel
chiffré ». « Le relais ne peut pas lire les données » : <b>seulement</b> sur Tailscale, jamais sur le secours Cloudflare.
<br>Ne jamais dire : « validé sur le terrain », « certifié », « Public AI » (dire « CSCS »), un nom de membre, une phrase Tally.</div>""")


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
    for nom, contenu in (("CARTE_REGIE_V2", carte_regie()), ("CARTE_V1", carte_v1())):
        f = LIVRABLES / f"{nom}.html"
        f.write_text(contenu, encoding="utf-8")
        print(f, "→", pdf(f) or "PDF non produit (Playwright absent) : ouvrir le .html dans Chrome, puis Imprimer")
