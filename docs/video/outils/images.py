"""Les IMAGES de la vidéo de présélection → docs/video/images/*.mp4 (1920 × 1080, 30 i/s, H.264, sans son).

    cd prototype && python ../docs/video/outils/images.py [deck] [app] [cartes]

- deck   : le deck v3 (mode nuit, motion design) rejoué SANS interaction, slide par slide ; en « mode vidéo » :
           aucun code à scanner, aucune consigne de régie, aucune source technique, des mots simples.
- app    : l'application réelle, monde FICTIF, IA éteinte : la salle (constellation + un vrai téléphone, les autres
           simulés), la demande, les trois boutons, le reçu, le retrait anonyme et la recomposition ; la console
           (« Le Club cherche », passe découverte, Suivi, « Ce que votre Club pourrait assembler »).
- cartes : le titre et le fond de la carte de fin (le texte de l'équipe est incrusté au montage, depuis equipe.txt).

À lancer ici (Linux, Chromium de Playwright) ; le Mac n'en a pas besoin : les clips sont dans le dépôt."""
from __future__ import annotations

import contextlib
import functools
import http.server
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
VIDEO = ICI.parent
RACINE = VIDEO.parents[1]
DECK = RACINE / "docs" / "presentation" / "deck"
IMAGES = VIDEO / "images"
sys.path.insert(0, str(RACINE / "prototype"))

from playwright.sync_api import sync_playwright  # noqa: E402

CHROMIUM = "/opt/pw-browsers/chromium"
W, H = 1920, 1080
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
CONSOLE = {"X-Pulse-Console": "1", "Content-Type": "application/json"}

# ───────────────────────────────────────────────────────────── le deck en mode vidéo
CSS_VIDEO = """
.qr-grand, .qr-moyen, .source, .alerte, #repet, #bascule, .r-note, #ecran-absent, .reperes, #chrono, .chrono { display: none !important; }
[class*="progres"], [id*="progres"], #indic, .indic { display: none !important; }
"""
JS_VIDEO = r"""
(() => {
  document.body.classList.add("video");
  const t = (sel, txt) => { const e = document.querySelector(sel); if (e) e.textContent = txt; };
  const p = document.querySelectorAll('[data-id="preuves"] .chiffre > span');
  if (p[0]) p[0].textContent = "daté, numéroté, et on peut le retirer — chaque oui en laisse un";
  if (p[1]) p[1].textContent = "simulés en même temps, sur notre ordinateur : 0 erreur";
  t("#ch-tally-l", "vraies demandes reçues hier à la Foire — on n'en montre que des totaux");
  if (p[3]) p[3].textContent = "bonne réponse du premier coup pour l'IA suisse. Avec ou sans IA, le Club marche pareil.";
  document.querySelectorAll('[data-id="ou"] .statuts span').forEach(s => { if (s.textContent.includes("testé")) s.textContent = "construits"; });
  const h = document.querySelector('[data-id="suisse"] .preuve h3'); if (h) h.textContent = "Apertus, l'IA suisse, à Lugano.";
  const e = document.querySelector('[data-id="ou"] .etiq'); if (e) e.textContent = "Où nous en sommes";
})();
"""

# (nom, [étapes]) ; étape : ("aller", id, pas) · ("suivant",) · ("attendre", ms) · ("debut",) marque le début du clip
CLIPS_DECK = [
    ("01-carte", [("aller", "1", 0), ("debut",), ("attendre", 7000)]),
    ("02-foire", [("aller", "1", 0), ("attendre", 400), ("debut",), ("attendre", 300), ("suivant",), ("attendre", 3600),
                  ("suivant",), ("attendre", 4200)]),
    ("02-hier", [("aller", "stat", 0), ("debut",), ("attendre", 4200), ("suivant",), ("attendre", 3800)]),
    ("02-et-apres", [("aller", "stat", 1), ("debut",), ("attendre", 200), ("suivant",), ("attendre", 4000)]),
    ("03-cinema", [("aller", "2", 0), ("debut",), ("attendre", 200), ("suivant",), ("attendre", 5200)]),
    ("03-et-apres", [("aller", "8", 0), ("debut",), ("attendre", 3600)]),
    ("04-jean-marc", [("aller", "8", 0), ("debut",), ("attendre", 3000)]),
    ("05-anneau", [("aller", "cote-club", 0), ("debut",), ("attendre", 5600)]),
    ("05-chiffres", [("aller", "chiffres-club", 0), ("debut",), ("attendre", 3200), ("suivant",), ("attendre", 3000),
                     ("suivant",), ("attendre", 4200)]),
    ("06-science", [("aller", "science", 0), ("debut",), ("attendre", 2200), ("suivant",), ("attendre", 3600),
                    ("suivant",), ("attendre", 3600), ("suivant",), ("attendre", 3600)]),
    ("06-preuves", [("aller", "preuves", 0), ("debut",), ("attendre", 1200), ("suivant",), ("attendre", 3600),
                    ("suivant",), ("attendre", 3600), ("suivant",), ("attendre", 3600)]),
    ("06-ia", [("aller", "preuves", 3), ("debut",), ("attendre", 600), ("suivant",), ("attendre", 6000)]),
    ("07-ou", [("aller", "ou", 0), ("debut",), ("attendre", 5000)]),
    ("07-frise", [("aller", "jalons", 0), ("debut",), ("attendre", 3600), ("suivant",), ("attendre", 3200),
                  ("suivant",), ("attendre", 3200), ("suivant",), ("attendre", 3600)]),
    ("07-suisse", [("aller", "suisse", 0), ("debut",), ("attendre", 2800), ("suivant",), ("attendre", 2800),
                   ("suivant",), ("attendre", 3400)]),
    ("07-demande", [("aller", "demande", 0), ("debut",), ("attendre", 3200), ("suivant",), ("attendre", 4200)]),
    ("08-recu", [("aller", "18", 0), ("debut",), ("attendre", 2000), ("suivant",), ("attendre", 4400)]),
    ("08-phrase", [("aller", "19", 0), ("debut",), ("attendre", 6400)]),
    ("01-titre", [("aller", "21", 0), ("js", "const e = document.querySelector('[data-id=\"21\"] .etiq'); e.textContent = 'Hack VS 2026 · le défi du Club des Affaires de la Foire du Valais'; e.style.bottom = 'auto'; e.style.top = '600px'"),
                  ("debut",), ("attendre", 6000)]),
    ("08-fin", [("aller", "21", 0), ("js", "document.querySelector('[data-id=\"21\"] .etiq').style.display = 'none'"),
                ("debut",), ("attendre", 8000)]),
]


@contextlib.contextmanager
def servir(dossier: Path):
    class Calme(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Calme, directory=str(dossier)))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()


def en_mp4(webm: Path, sortie: Path, debut: float, duree: float | None = None, filtre: str | None = None) -> None:
    vf = filtre or f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x05070B,setsar=1,fps=30"
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{debut:.3f}", "-i", str(webm)]
    if duree:
        cmd += ["-t", f"{duree:.3f}"]
    cmd += ["-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", str(sortie)]
    subprocess.run(cmd, check=True)


def clips_deck(navigateur, base: str, seulement: set[str] | None = None) -> None:
    for nom, etapes in CLIPS_DECK:
        if seulement and nom not in seulement:
            continue
        with tempfile.TemporaryDirectory() as td:
            ctx = navigateur.new_context(viewport={"width": W, "height": H}, record_video_dir=td,
                                         record_video_size={"width": W, "height": H}, reduced_motion="no-preference")
            t0 = time.monotonic()
            pg = ctx.new_page()
            erreurs: list[str] = []
            pg.on("pageerror", lambda e: erreurs.append(str(e)))
            pg.goto(f"{base}/v3.html?app=http://127.0.0.1:9")
            pg.evaluate("Promise.resolve(window.pret).then(() => true)")
            pg.add_style_tag(content=CSS_VIDEO)
            pg.wait_for_timeout(600)
            pg.evaluate(JS_VIDEO)
            debut = 0.0
            for e in etapes:
                if e[0] == "aller":
                    pg.evaluate("([i, p]) => allerA(i, p)", [e[1], e[2]])
                    pg.wait_for_timeout(50)
                    pg.evaluate("window.points && window.points.finir()") if e[1] not in ("1",) else None
                elif e[0] == "js":
                    pg.evaluate(e[1])
                elif e[0] == "suivant":
                    pg.keyboard.press("ArrowRight")
                elif e[0] == "attendre":
                    pg.wait_for_timeout(e[1])
                elif e[0] == "debut":
                    pg.wait_for_timeout(700)                    # la slide d'arrivée est posée, l'animation de la page finie
                    debut = time.monotonic() - t0
            fin = time.monotonic() - t0
            video = pg.video.path()
            ctx.close()
            assert not erreurs, (nom, erreurs)
            en_mp4(Path(video), IMAGES / f"{nom}.mp4", debut, fin - debut)
        print(f"  {nom}.mp4 · {fin - debut:.1f} s")


# ───────────────────────────────────────────────────────────── cartes (titre, fond de fin)
CARTE = """<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>
@font-face{{font-family:J;font-weight:200 800;src:url("{deck}/assets/fonts/plus-jakarta-sans-latin-wght-normal.woff2")}}
html,body{{margin:0;width:1920px;height:1080px;background:#05070B;color:#F3F1EC;font-family:J,"Plus Jakarta Sans",system-ui,sans-serif;overflow:hidden}}
canvas{{position:absolute;inset:0}}
.bloc{{position:absolute;left:160px;top:{top}px;display:flex;align-items:center;gap:48px;opacity:0;transform:translateY(24px);animation:m 720ms cubic-bezier(.22,1,.36,1) 240ms forwards}}
.logo{{width:190px;height:190px;border-radius:44px;background:#CD2128;display:grid;place-items:center}}
.logo i{{display:block;width:96px;height:96px;border-radius:50%;border:22px solid #fff;border-left-color:transparent;transform:rotate(-30deg)}}
h1{{margin:0;font-weight:800;font-size:132px;letter-spacing:-.045em;line-height:1}} p{{margin:18px 0 0;font-size:44px;color:#D6DAE1;font-weight:600}}
.sous{{position:absolute;left:160px;top:{top2}px;font-size:40px;color:#AEB6C2;font-weight:600;opacity:0;animation:m 720ms cubic-bezier(.22,1,.36,1) 720ms forwards}}
@keyframes m{{to{{opacity:1;transform:none}}}}
</style></head><body><canvas id=c width=1920 height=1080></canvas>
<div class=bloc><div class=logo><i></i></div><div><h1>Club Pulse</h1><p>Club des Affaires · Foire du Valais</p></div></div>
<div class=sous>{sous}</div>
<script>
const c=document.getElementById("c"),g=c.getContext("2d");let r=7;const rnd=()=>(r=(r*16807)%2147483647)/2147483647;
const P=Array.from({{length:140}},()=>({{x:rnd()*1920,y:rnd()*1080,s:.4+rnd()*1.2,p:rnd()*6.3,a:.15+rnd()*.5}}));
function f(t){{g.fillStyle="#05070B";g.fillRect(0,0,1920,1080);for(const q of P){{const x=q.x+Math.sin(t/1000*q.s+q.p)*8,y=q.y+Math.cos(t/1300*q.s+q.p)*6;
g.globalAlpha=q.a;g.fillStyle="#FFD6AA";g.beginPath();g.arc(x,y,2.2,0,6.3);g.fill();g.globalAlpha=q.a*.25;g.beginPath();g.arc(x,y,7,0,6.3);g.fill();}}
g.globalAlpha=1;requestAnimationFrame(f);}}requestAnimationFrame(f);
</script></body></html>"""


def cartes(navigateur, base: str) -> None:
    for nom, top, sous, duree in (("01-titre", 330, "Hack VS 2026 · Défi du Club des Affaires de la Foire du Valais", 6.0),
                                  ("08-fin", 150, "", 8.0)):
        html = CARTE.format(deck=base, top=top, top2=top + 290, sous=sous)
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "c.html").write_text(html, encoding="utf-8")
            ctx = navigateur.new_context(viewport={"width": W, "height": H}, record_video_dir=td,
                                         record_video_size={"width": W, "height": H})
            t0 = time.monotonic()
            pg = ctx.new_page()
            pg.goto(f"{base}/__carte__/{nom}.html") if False else pg.set_content(html)
            pg.wait_for_timeout(300)
            debut = time.monotonic() - t0
            pg.wait_for_timeout(int(duree * 1000))
            video = pg.video.path()
            ctx.close()
            en_mp4(Path(video), IMAGES / f"{nom}.mp4", debut, duree)
        print(f"  {nom}.mp4 · {duree:.1f} s")


# ───────────────────────────────────────────────────────────── l'application (monde fictif, IA éteinte)
def post(base: str, chemin: str, corps=None, h=None, methode: str | None = None):
    r = urllib.request.Request(base + chemin, data=json.dumps(corps or {}).encode() if methode != "GET" else None,
                               headers={**CONSOLE, **(h or {})}, method=methode)
    return json.load(urllib.request.urlopen(r))


def composer(ecran: Path, tel: Path, sortie: Path, debut: float, duree: float, decalage_tel: float) -> None:
    """L'écran de la salle à gauche, le téléphone à droite, sur le fond du deck (1920 × 1080)."""
    filtre = (f"color=c=0x05070B:s={W}x{H}:r=30[f];"
              f"[0:v]scale=1300:-2,setsar=1[e];[1:v]scale=-2:960,setsar=1[t];"
              f"[f][e]overlay=60:(H-h)/2:shortest=1[a];[a][t]overlay=1420:60:shortest=1,fps=30[v]")
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", f"{debut:.3f}", "-t", f"{duree:.3f}", "-i", str(ecran),
                    "-ss", f"{debut - decalage_tel:.3f}", "-t", f"{duree:.3f}", "-i", str(tel),
                    "-filter_complex", filtre, "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-t", f"{duree:.3f}", str(sortie)], check=True)


def salle(navigateur) -> None:
    from tests.test_e2e_scene import serveur
    with serveur(HACKVS_FOIRE="1", HACKVS_SALLE="1", HACKVS_SALLE_MIN="2") as base, tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        post(base, "/api/pulse/console/salle/purger")
        lien = post(base, "/api/pulse/console/salle/ouvrir")["url"]
        jeton = lien.split("#s=", 1)[1]
        ce = navigateur.new_context(viewport={"width": W, "height": H}, record_video_dir=str(tdp / "e"),
                                    record_video_size={"width": W, "height": H})
        t0 = time.monotonic()
        ecran = ce.new_page()
        ecran.goto(f"{base}/salle/ecran?mode=nuit&sans-bascule")
        ecran.add_style_tag(content="#qr { visibility: hidden !important; }")      # aucun code à scanner dans la vidéo
        ecran.wait_for_timeout(1500)
        ct = navigateur.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                                    has_touch=True, record_video_dir=str(tdp / "t"), record_video_size={"width": 390, "height": 844})
        dt = time.monotonic() - t0                       # le téléphone commence à filmer plus tard que l'écran
        tel = ct.new_page()
        marques = {}
        lien_tel = lien.replace("http://testserver", base) if lien.startswith("http://testserver") else lien
        if not lien_tel.startswith("http"):
            lien_tel = base + lien_tel
        caps = ["voiture", "salle", "allemand", "traiteur", "informatique", "materiel"]
        passes = []
        marques["arrivees"] = time.monotonic() - t0
        for i in range(30):                                # 30 téléphones SIMULÉS arrivent
            passes.append((caps[i % 6], post(base, "/api/pulse/salle/entrer", {"jeton": jeton})["passe"]))
            post(base, "/api/pulse/salle/declarer", {"capacite": caps[i % 6], "consentement": True},
                 {"X-Pulse-Salle": passes[-1][1]})
            time.sleep(0.12)
        marques["tel"] = time.monotonic() - t0
        tel.goto(lien_tel)                                 # le VRAI téléphone, filmé : deux gestes
        tel.wait_for_timeout(1200)
        tel.click("[data-capacite=voiture]")
        tel.wait_for_timeout(700)
        tel.check("#consens")
        tel.wait_for_timeout(600)
        tel.click("#valider")
        tel.locator("[data-role=recu]").wait_for()
        tel.wait_for_timeout(2200)
        marques["lancer"] = time.monotonic() - t0
        post(base, "/api/pulse/console/salle/lancer")
        tel.locator("[data-choix=oui]").wait_for()
        tel.wait_for_timeout(3500)                         # la demande est arrivée : on la lit
        marques["oui"] = time.monotonic() - t0
        tel.locator("[data-choix=oui]").click()
        tel.locator("[data-role=message]").wait_for()
        tel.wait_for_timeout(1500)
        concernes = [p for c, p in passes if c in ("voiture", "salle", "allemand")]
        for p in concernes[:5]:
            post(base, "/api/pulse/salle/repondre", {"choix": "oui"}, {"X-Pulse-Salle": p})
            time.sleep(0.4)
        ecran.locator("[data-role=anneau][data-fermee=true]").wait_for()
        tel.wait_for_timeout(3500)
        marques["retrait"] = time.monotonic() - t0
        tel.locator("#retirer").click()
        tel.locator("[data-role=message]:has-text('Personne ne sera prévenu')").wait_for()
        ecran.locator(".fil >> text=recomposition").wait_for()
        tel.wait_for_timeout(5000)
        marques["fin"] = time.monotonic() - t0
        ve, vt = ecran.video.path(), tel.video.path()
        ct.close()
        ce.close()
        m = marques
        en_mp4(Path(ve), IMAGES / "04-constellation.mp4", m["arrivees"], m["tel"] - m["arrivees"] + 1.0)
        composer(Path(ve), Path(vt), IMAGES / "04-demande.mp4", m["tel"], m["oui"] - m["tel"], dt)
        composer(Path(ve), Path(vt), IMAGES / "04-boutons.mp4", m["oui"] - 3.0, 5.0, dt)
        composer(Path(ve), Path(vt), IMAGES / "04-recu.mp4", m["oui"] + 2.0, m["retrait"] - m["oui"] - 2.0, dt)
        composer(Path(ve), Path(vt), IMAGES / "04-retrait.mp4", m["retrait"] - 0.5, m["fin"] - m["retrait"] + 0.5, dt)
        print("  04-constellation, 04-demande, 04-boutons, 04-recu, 04-retrait :", json.dumps({k: round(v, 1) for k, v in m.items()}))


def console(navigateur) -> None:
    from tests.test_e2e_scene import serveur
    with serveur(HACKVS_FOIRE="1") as base, tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        ctx = navigateur.new_context(viewport={"width": 1600, "height": 900}, device_scale_factor=1.2,
                                     record_video_dir=str(tdp / "c"), record_video_size={"width": 1600, "height": 900})
        t0 = time.monotonic()
        pg = ctx.new_page()
        m = {}
        pg.goto(base + "/suivi")
        pg.locator("[data-tuile]").first.wait_for()
        pg.wait_for_timeout(800)
        m["suivi"] = time.monotonic() - t0
        pg.wait_for_timeout(5500)
        m["cherche"] = time.monotonic() - t0
        pg.click("#vues >> text=Le Club cherche")
        pg.wait_for_timeout(4500)
        m["passe"] = time.monotonic() - t0
        pg.locator("[data-metier] [data-inviter]").first.click()
        pg.locator("[data-role=invitation] textarea[data-langue=DE]").wait_for()
        pg.locator("[data-role=invitation]").scroll_into_view_if_needed()
        pg.wait_for_timeout(4500)
        m["assembler"] = time.monotonic() - t0
        pg.click("#vues [data-vue=assembler]")
        pg.locator("[data-role=assemblables]:has-text('8 sur 9')").wait_for()
        pg.wait_for_timeout(3500)
        pg.mouse.wheel(0, 400)
        pg.wait_for_timeout(3000)
        m["fin"] = time.monotonic() - t0
        lien = pg.input_value("[data-role=invitation] textarea[data-langue=FR]") if pg.locator("[data-role=invitation] textarea[data-langue=FR]").count() else ""
        v = pg.video.path()
        ctx.close()
        en_mp4(Path(v), IMAGES / "05-suivi.mp4", m["suivi"], m["cherche"] - m["suivi"])
        en_mp4(Path(v), IMAGES / "05-cherche.mp4", m["cherche"], m["passe"] - m["cherche"])
        en_mp4(Path(v), IMAGES / "05-assembler.mp4", m["assembler"], m["fin"] - m["assembler"])
        # le passe découverte, vu par l'invité sur son téléphone (ouvert depuis l'invitation)
        import re
        u = re.search(r"https?://\S+/decouverte#passe=\S+", lien)
        ct = navigateur.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                                    record_video_dir=str(tdp / "t"), record_video_size={"width": 390, "height": 844})
        t1 = time.monotonic()
        tel = ct.new_page()
        tel.goto(u.group(0).replace("http://testserver", base) if u else base + "/decouverte")
        tel.wait_for_timeout(1500)
        d = time.monotonic() - t1
        tel.wait_for_timeout(3500)
        tel.mouse.wheel(0, 400)
        tel.wait_for_timeout(3000)
        f = time.monotonic() - t1
        vt = tel.video.path()
        ct.close()
        # console à gauche (l'invitation), téléphone de l'invité à droite
        filtre = (f"color=c=0x05070B:s={W}x{H}:r=30[f];[0:v]scale=1300:-2,setsar=1[e];[1:v]scale=-2:960,setsar=1[t];"
                  f"[f][e]overlay=60:(H-h)/2:shortest=1[a];[a][t]overlay=1420:60:shortest=1,fps=30[v]")
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
                        "-ss", f"{m['cherche'] + 0.5:.3f}", "-t", f"{min(f - d, m['passe'] - m['cherche'] - 0.5):.3f}", "-i", str(v),   # avant l'invitation : ni code ni lien à l'écran
                        "-ss", f"{d:.3f}", "-t", f"{f - d:.3f}", "-i", str(vt),
                        "-filter_complex", filtre, "-map", "[v]", "-an", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                        str(IMAGES / "05-passe.mp4")], check=True)
        print("  05-suivi, 05-cherche, 05-passe, 05-assembler :", json.dumps({k: round(x, 1) for k, x in m.items()}))


def main(argv: list[str]) -> int:
    quoi = set(argv) or {"deck", "app", "cartes"}
    seulement = {a for a in argv if a[:2].isdigit()}
    IMAGES.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROMIUM, args=["--autoplay-policy=no-user-gesture-required"])
        with servir(DECK) as base:
            if "deck" in quoi or seulement:
                clips_deck(b, base, seulement or None)
        if "app" in quoi or "salle" in quoi:
            salle(b)
        if "app" in quoi or "console" in quoi:
            console(b)
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
