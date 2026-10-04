"""La vidéo de présélection : script → prompteur, sous-titres, montage, vérifications, version HTML de secours.

Bibliothèque standard seulement (le Mac a python3) ; ffmpeg/ffprobe font le travail lourd.

    python3 docs/video/outils/video.py prompteur              # docs/video/prompteur.html
    python3 docs/video/outils/video.py srt-cible              # docs/video/sous-titres-cible.srt (durées visées)
    python3 docs/video/outils/video.py mots                   # aucun mot interdit dans ce qui se dit (code 0 / 1)
    python3 docs/video/outils/video.py monter [--voix DOSSIER] [--film FICHIER] [--ffmpeg F --ffprobe F] [--sortie F]
    python3 docs/video/outils/video.py verifier FICHIER.mp4   # les vérifications seules, sur une vidéo déjà montée

C'est `docs/video/monter.sh` qui appelle `monter` sur le Mac."""
from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
VIDEO = ICI.parent                                 # docs/video
RACINE = VIDEO.parents[1]
SCRIPT = VIDEO / "SCRIPT_VIDEO.md"
IMAGES = VIDEO / "images"
SORTIE = VIDEO / "out" / "club-pulse-presentation.mp4"
EQUIPE = Path(os.environ.get("CLUBPULSE_EQUIPE") or VIDEO / "equipe.txt")

W, H, IPS = 1920, 1080, 30
AVANT, APRES = 0.6, 0.8                           # respiration avant / après chaque voix (secondes)
APRES_FIN = 2.6                                   # la carte de fin reste à l'écran après « Merci. » (< 3 s de silence)
LUFS = -16
DUREE_MIN, DUREE_MAX = 600, 720                   # 10 à 12 minutes
SILENCE_MAX = 3.0
TAILLE_MAX_MO = 400                               # au-delà, l'envoi en ligne devient pénible

# Mots qu'un jury non technique ne doit ni entendre ni lire (et rien qui suppose notre machine allumée).
MOTS_INTERDITS = [r"tunnel\w*", r"cscs", r"serveurs?", r"tests?", r"test[ée]\w*", r"e2e", r"hmac", r"json", r"api",
                  r"qr", r"https?", r"url", r"localhost", r"jetons?", r"iframe", r"backend", r"frontend", r"algorithme\w*",
                  r"scannez", r"levez", r"sortez"]
RE_INTERDIT = re.compile(r"(?<![\w-])(" + "|".join(MOTS_INTERDITS) + r")(?![\w-])", re.I)


# ───────────────────────────────────────────────────────────── le script
def lire_script(chemin: Path = SCRIPT) -> list[dict]:
    """Les 8 séquences : numéro, titre, durée visée, plans (images), phrases dites."""
    t = chemin.read_text(encoding="utf-8")
    seqs = []
    for bloc in re.split(r"^(?=## \d\d )", t, flags=re.M)[1:]:
        lignes = bloc.splitlines()
        m = re.match(r"## (\d\d) — (.+?) · (\d+):(\d\d)", lignes[0])
        if not m:
            raise SystemExit(f"titre de séquence illisible : {lignes[0]}")
        images = []
        for l in lignes:
            if l.startswith("Images :"):
                for x in l[len("Images :"):].split(","):
                    x = x.strip()
                    nom, _, fixe = x.partition("=")
                    images.append({"nom": nom, "fixe": float(fixe) if fixe else None})
        dites = [l[1:].strip() for l in lignes if l.startswith(">")]
        seqs.append({"num": m.group(1), "titre": m.group(2), "cible": int(m.group(3)) * 60 + int(m.group(4)),
                     "images": images, "phrases": dites})
    if [s["num"] for s in seqs] != [f"{k:02d}" for k in range(1, 9)]:
        raise SystemExit("il faut exactement 8 séquences, numérotées 01 à 08")
    return seqs


def propre(phrase: str) -> str:
    """Ce qui s'affiche : sans les « / » de pause."""
    return re.sub(r"\s*/\s*", " ", phrase).strip()


def mots_interdits(textes: list[str]) -> list[str]:
    trouves = []
    for t in textes:
        for m in RE_INTERDIT.finditer(t):
            trouves.append(f"« {m.group(0)} » dans : {t}")
    return trouves


# ───────────────────────────────────────────────────────────── sous-titres
def _hms(s: float, sep: str = ",") -> str:
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{sep}{ms % 1000:03d}"


def _couper(phrase: str, largeur: int = 44) -> list[str]:
    """Une phrase → des sous-titres d'au plus deux lignes de `largeur` caractères."""
    morceaux = [p.strip() for p in re.split(r"(?<=[.?!:])\s+(?=[«A-ZÀ-ÖØ-Þ0-9])", phrase) if p.strip()]
    cartons = []
    for m in morceaux:
        if len(m) <= largeur * 2:
            cartons.append(m)
            continue
        mots, cour = m.split(), ""
        for w in mots:                                    # trop long : on coupe au mot, en cartons de deux lignes
            if len(cour) + len(w) + 1 > largeur * 2 - 4 and cour:
                cartons.append(cour)
                cour = w
            else:
                cour = f"{cour} {w}".strip()
        if cour:
            cartons.append(cour)
    sortie = []
    for c in cartons:                                    # deux lignes équilibrées
        if len(c) > largeur:
            mots = c.split()
            meilleur = min(range(1, len(mots)), key=lambda k: abs(len(" ".join(mots[:k])) - len(" ".join(mots[k:]))))
            c = " ".join(mots[:meilleur]) + "\n" + " ".join(mots[meilleur:])
        sortie.append(c)
    return sortie


def cartons_sequence(seq: dict, debut: float, duree: float) -> list[tuple[float, float, str]]:
    """Répartit la voix d'une séquence entre ses cartons, au prorata du nombre de caractères (et des pauses « / »)."""
    cartons = []
    for ph in seq["phrases"]:
        pauses = ph.count("/")
        cs = _couper(propre(ph))
        for k, c in enumerate(cs):
            cartons.append((c, len(c) + (12 * pauses if k == len(cs) - 1 else 0) + 6))
    total = sum(p for _, p in cartons) or 1
    t, sortie = debut, []
    for c, p in cartons:
        d = duree * p / total
        sortie.append((t, t + d - 0.04, c))
        t += d
    return sortie


def ecrire_srt(cartons: list[tuple[float, float, str]], chemin: Path) -> None:
    lignes = []
    for k, (a, b, c) in enumerate(cartons, 1):
        lignes += [str(k), f"{_hms(a)} --> {_hms(b)}", c, ""]
    chemin.write_text("\n".join(lignes), encoding="utf-8")


def plan_cible(seqs: list[dict], film: float = 201.0) -> list[dict]:
    """La chronologie avec les durées VISÉES (avant enregistrement) : sert au SRT de référence et au prompteur."""
    t, plan = 0.0, []
    for s in seqs:
        voix = s["cible"] - (0 if s["num"] != "03" else 0)
        plan.append({"num": s["num"], "debut_voix": t + AVANT, "voix": voix - AVANT - APRES})
        t += voix + (film + 2.4 if s["num"] == "03" else 0)
    return plan


def srt_cible() -> Path:
    seqs = lire_script()
    cartons = []
    for s, p in zip(seqs, plan_cible(seqs)):
        cartons += cartons_sequence(s, p["debut_voix"], p["voix"])
    chemin = VIDEO / "sous-titres-cible.srt"
    ecrire_srt(cartons, chemin)
    return chemin


# ───────────────────────────────────────────────────────────── prompteur
def prompteur() -> Path:
    seqs = lire_script()
    blocs = []
    for s in seqs:
        ph = "".join(f"<p>{html.escape(p).replace(' / ', ' <span class=pause>/</span> ')}</p>" for p in s["phrases"])
        note = ("<p class=note>Ensuite le film passe avec son propre son : n'enregistrez que ces deux phrases.</p>"
                if s["num"] == "03" else "")
        blocs.append(f'<section data-n="{s["num"]}"><h2><b>{s["num"]}.m4a</b> {html.escape(s["titre"])}'
                     f'<i>environ {s["cible"] // 60}:{s["cible"] % 60:02d}</i></h2>{ph}{note}</section>')
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prompteur vidéo</title><style>
:root{{--fond:#05070B;--encre:#F3F1EC;--doux:#AEB6C2;--rouge:#FF5A61}}
body{{margin:0;background:var(--fond);color:var(--encre);font:600 44px/1.45 -apple-system,system-ui,sans-serif}}
section{{display:none;max-width:1100px;margin:0 auto;padding:48px 32px 160px}} section.on{{display:block}}
h2{{font-size:28px;color:var(--doux);font-weight:600;display:flex;gap:18px;align-items:baseline;border-bottom:2px solid #2A3342;padding-bottom:14px}}
h2 b{{color:var(--rouge);font-family:ui-monospace,monospace}} h2 i{{margin-left:auto;font-style:normal}}
p{{margin:0 0 .7em}} .pause{{color:var(--rouge);padding:0 .2em}} .note{{font-size:28px;color:var(--doux)}}
nav{{position:fixed;left:0;right:0;bottom:0;display:flex;gap:12px;justify-content:center;padding:16px;background:#0D1119;border-top:2px solid #2A3342;font-size:24px}}
button{{font:inherit;padding:10px 26px;border-radius:999px;border:2px solid #8A93A1;background:none;color:var(--encre)}}
#chrono{{font-family:ui-monospace,monospace;min-width:5em;text-align:center;align-self:center}}
@media (max-width:700px){{body{{font-size:30px}}}}
</style></head><body>
{''.join(blocs)}
<nav><button id=av>← Précédente</button><button id=go>Chrono</button><span id=chrono>0:00</span><button id=ap>Suivante →</button></nav>
<script>
const S=[...document.querySelectorAll("section")];let i=0,t0=null,tm=null;
function voir(n){{i=Math.max(0,Math.min(S.length-1,n));S.forEach((s,k)=>s.classList.toggle("on",k===i));scrollTo(0,0);location.hash=S[i].dataset.n;}}
function chrono(){{if(tm){{clearInterval(tm);tm=null;return;}}t0=Date.now();tm=setInterval(()=>{{const s=Math.floor((Date.now()-t0)/1000);document.getElementById("chrono").textContent=Math.floor(s/60)+":"+String(s%60).padStart(2,"0");}},250);}}
document.getElementById("av").onclick=()=>voir(i-1);document.getElementById("ap").onclick=()=>voir(i+1);document.getElementById("go").onclick=chrono;
addEventListener("keydown",e=>{{if(e.key==="ArrowRight"||e.key==="PageDown")voir(i+1);if(e.key==="ArrowLeft"||e.key==="PageUp")voir(i-1);if(e.key===" "){{e.preventDefault();chrono();}}}});
voir(Math.max(0,S.findIndex(s=>s.dataset.n===location.hash.slice(1))));
</script></body></html>"""
    chemin = VIDEO / "prompteur.html"
    chemin.write_text(page, encoding="utf-8")
    return chemin


# ───────────────────────────────────────────────────────────── ffmpeg
class FF:
    def __init__(self, ffmpeg: str, ffprobe: str):
        self.ffmpeg, self.ffprobe = ffmpeg, ffprobe

    def run(self, *args: str, sortie: bool = False) -> str:
        cmd = [self.ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "error" if not sortie else "info", *args]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit("ffmpeg a échoué :\n  " + " ".join(cmd) + "\n" + r.stderr[-3000:])
        return r.stderr

    def duree(self, f: Path) -> float:
        r = subprocess.run([self.ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                           capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except ValueError:
            raise SystemExit(f"durée illisible : {f}\n{r.stderr}")

    def a_son(self, f: Path) -> bool:
        r = subprocess.run([self.ffprobe, "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                            "-of", "csv=p=0", str(f)], capture_output=True, text=True)
        return bool(r.stdout.strip())


VCODEC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(IPS)]   # intermédiaires : vite, presque sans perte
ACODEC = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
CADRE = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x05070B,setsar=1,fps={IPS}"


def _plan_video(ff: FF, images: list[dict], duree: float, tmp: Path, nom: str) -> Path:
    """Les plans d'une séquence, calés sur `duree` : chaque plan reçoit une part proportionnelle à sa longueur ;
    trop court → sa dernière image se prolonge ; trop long → il est coupé. Un plan « =N » garde N secondes."""
    fichiers = []
    for im in images:
        f = IMAGES / im["nom"]
        if not f.exists():
            raise SystemExit(f"image manquante : {f}")
        fichiers.append((f, ff.duree(f), im["fixe"]))
    fixe = sum(x for _, _, x in fichiers if x)
    libre = max(0.5, duree - fixe)
    poids = sum(d for _, d, x in fichiers if not x) or 1
    morceaux = []
    for k, (f, d, x) in enumerate(fichiers):
        part = x if x else libre * d / poids
        sortie = tmp / f"{nom}-{k}.mp4"
        ff.run("-i", str(f), "-vf", f"{CADRE},tpad=stop_mode=clone:stop_duration={max(0.0, part - d) + 1:.3f}",
               "-t", f"{part:.3f}", "-an", *VCODEC, str(sortie))
        morceaux.append(sortie)
    liste = tmp / f"{nom}-liste.txt"
    liste.write_text("".join(f"file '{m.as_posix()}'\n" for m in morceaux), encoding="utf-8")
    sortie = tmp / f"{nom}-video.mp4"
    ff.run("-f", "concat", "-safe", "0", "-i", str(liste), "-t", f"{duree:.3f}", *VCODEC, str(sortie))
    return sortie


def _voix(ff: FF, f: Path, total: float, tmp: Path, nom: str, avant: float = AVANT) -> Path:
    """La voix normalisée vers -16 LUFS, posée après `avant` secondes, complétée de silence jusqu'à `total`."""
    sortie = tmp / f"{nom}-voix.wav"
    ms = int(avant * 1000)
    ff.run("-i", str(f), "-af", f"loudnorm=I={LUFS}:TP=-1.5:LRA=11,aresample=48000,adelay={ms}|{ms},apad",
           "-ac", "2", "-ar", "48000", "-t", f"{total:.3f}", str(sortie))
    return sortie


def _assembler(ff: FF, video: Path, audio: Path, sortie: Path) -> Path:
    ff.run("-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy", *ACODEC, "-shortest", str(sortie))
    return sortie


def lire_equipe() -> tuple[list[str], str]:
    """docs/video/equipe.txt : les lignes « Équipe : … » et « Contact : … » de la carte de fin."""
    noms, contact = [], ""
    if EQUIPE.exists():
        for l in EQUIPE.read_text(encoding="utf-8").splitlines():
            l = l.strip()
            if l.lower().startswith("équipe :") or l.lower().startswith("equipe :"):
                noms = [x.strip() for x in l.split(":", 1)[1].split(",") if x.strip()]
            elif l.lower().startswith("contact :"):
                contact = l.split(":", 1)[1].strip()
    return noms, contact


def _ass(cartons: list[tuple[float, float, str]], fin: tuple[float, float], chemin: Path) -> None:
    """Un seul fichier ASS : les sous-titres (bas de l'écran) et la carte de fin (équipe, contact)."""
    noms, contact = lire_equipe()
    def e(s: str) -> str:
        return s.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", "\\N")
    entete = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sous,Helvetica,50,&H00F3F1EC,&H00FFFFFF,&H00000000,&HA0000000,1,0,0,0,100,100,0,0,3,14,0,2,160,160,54,1
Style: Fin,Helvetica,56,&H00F3F1EC,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,7,160,160,0,1
Style: FinPetit,Helvetica,42,&H00C2B6AE,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,160,160,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def t(s: float) -> str:
        cs = int(round(s * 100))
        return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"
    lignes = [f"Dialogue: 0,{t(a)},{t(b)},Sous,,0,0,0,,{e(c)}" for a, b, c in cartons if a < fin[0] - 0.05]
    a, b = fin
    equipe = " · ".join(noms) if noms else "L'équipe Club Pulse"
    lignes.append(f"Dialogue: 1,{t(a)},{t(b)},Fin,,0,0,0,,{{\\pos(160,690)\\fad(240,0)}}{e(equipe)}")
    if contact:
        lignes.append(f"Dialogue: 1,{t(a)},{t(b)},FinPetit,,0,0,0,,{{\\pos(160,780)\\fad(240,0)}}{e(contact)}")
    chemin.write_text(entete + "\n".join(lignes) + "\n", encoding="utf-8")


def chercher_film() -> Path:
    """Même détection que le lanceur : la SEULE vidéo posée directement sur le Bureau."""
    sys.path.insert(0, str(RACINE / "prototype"))
    from app import jour_j as jj  # noqa: E402
    r = jj.chercher_film(jj.bureau())
    if r["couleur"] == "rouge" or not r.get("source"):
        raise SystemExit("FILM : " + r["message"] + "\n(ou indiquez-le : ./docs/video/monter.sh --film /chemin/du/film.mp4)")
    print(f"  film : {r['message']}")
    return Path(r["source"])


def monter(voix: Path, film: Path | None, ff: FF, sortie: Path, garder: bool = False) -> Path:
    seqs = lire_script()
    trouves = mots_interdits([propre(p) for s in seqs for p in s["phrases"]])
    if trouves:
        raise SystemExit("MOTS INTERDITS dans le script :\n  " + "\n  ".join(trouves))
    manquants = [f"{s['num']}.m4a" for s in seqs if not (voix / f"{s['num']}.m4a").exists()]
    if manquants:
        raise SystemExit(f"VOIX MANQUANTES dans {voix} : " + ", ".join(manquants))
    film = film or chercher_film()
    tmp = Path(tempfile.mkdtemp(prefix="clubpulse-video-"))
    print(f"  dossier de travail : {tmp}")
    morceaux, cartons, t = [], [], 0.0
    film_debut = film_fin = 0.0
    fin = (0.0, 0.0)
    for s in seqs:
        n = s["num"]
        f_voix = voix / f"{n}.m4a"
        d_voix = ff.duree(f_voix)
        apres = APRES_FIN if n == "08" else APRES
        total = AVANT + d_voix + apres
        print(f"  séquence {n} · {s['titre']} : voix {d_voix:.1f} s")
        images = [im for im in s["images"] if im["nom"] != "FILM"]
        if n == "03":                                   # annonce · film (son du film) · « Et après ? »
            idx = [im["nom"] for im in s["images"]].index("FILM")
            avant_film, apres_film = images[:idx], images[idx:]
            v = _plan_video(ff, avant_film, total, tmp, f"{n}a")
            morceaux.append(_assembler(ff, v, _voix(ff, f_voix, total, tmp, f"{n}a"), tmp / f"{n}a.mp4"))
            cartons += cartons_sequence(s, t + AVANT, d_voix)
            t += total
            d_film = ff.duree(film)
            filmv = tmp / "film.mp4"
            son = ["-af", f"loudnorm=I={LUFS}:TP=-1.5:LRA=11,aresample=48000"] if ff.a_son(film) else []
            entrees = ["-i", str(film)] if son else ["-i", str(film), "-f", "lavfi", "-t", f"{d_film:.3f}",
                                                    "-i", "anullsrc=r=48000:cl=stereo"]
            ff.run(*entrees, "-vf", CADRE, *son, *VCODEC, *ACODEC, "-shortest", str(filmv))
            film_debut, film_fin = t, t + d_film
            morceaux.append(filmv)
            t += d_film
            silence = tmp / "silence.wav"
            ff.run("-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "2.4", str(silence))
            v = _plan_video(ff, apres_film, 2.4, tmp, f"{n}b")
            morceaux.append(_assembler(ff, v, silence, tmp / f"{n}b.mp4"))
            t += 2.4
            continue
        if n == "08":                                   # la carte de fin couvre « Merci. » et la respiration finale
            fin_fixe = 2.0 + APRES_FIN
            images = [dict(im, fixe=fin_fixe) if im["nom"] == "08-fin.mp4" else im for im in images]
            fin = (t + total - fin_fixe, t + total)
        v = _plan_video(ff, images, total, tmp, n)
        morceaux.append(_assembler(ff, v, _voix(ff, f_voix, total, tmp, n), tmp / f"{n}.mp4"))
        cartons += cartons_sequence(s, t + AVANT, d_voix)
        t += total

    liste = tmp / "tout.txt"
    liste.write_text("".join(f"file '{m.as_posix()}'\n" for m in morceaux), encoding="utf-8")
    brut = tmp / "brut.mp4"
    ff.run("-f", "concat", "-safe", "0", "-i", str(liste), "-c", "copy", str(brut))
    srt = sortie.with_suffix(".srt")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    ecrire_srt(cartons, srt)
    ass = tmp / "incrustation.ass"
    _ass(cartons, fin, ass)
    print("  incrustation des sous-titres et encodage final…")
    chemin_ass = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    ff.run("-i", str(brut), "-vf", f"ass='{chemin_ass}'", "-c:v", "libx264", "-preset", "medium", "-crf", "23",
           "-maxrate", "3500k", "-bufsize", "7000k", "-pix_fmt", "yuv420p", "-r", str(IPS), "-c:a", "copy",
           "-movflags", "+faststart", str(sortie))
    (sortie.parent / "chronologie.json").write_text(json.dumps(
        {"film": [round(film_debut, 2), round(film_fin, 2)], "fin": [round(fin[0], 2), round(fin[1], 2)],
         "duree": round(t, 2)}, indent=2), encoding="utf-8")
    if not garder:
        shutil.rmtree(tmp, ignore_errors=True)
    return sortie


# ───────────────────────────────────────────────────────────── vérifications
def verifier(ff: FF, f: Path) -> bool:
    ok = True
    def ligne(bon: bool, texte: str) -> None:
        nonlocal ok
        ok = ok and bon
        print(f"  [{'OK' if bon else 'KO'}] {texte}")
    d = ff.duree(f)
    ligne(DUREE_MIN <= d <= DUREE_MAX, f"durée totale {int(d // 60)} min {d % 60:04.1f} s (attendu : 10 à 12 minutes)")
    chrono = {}
    cj = f.parent / "chronologie.json"
    if cj.exists():
        chrono = json.loads(cj.read_text(encoding="utf-8"))
    film = chrono.get("film", [0, 0])
    err = ff.run("-i", str(f), "-af", f"silencedetect=noise=-45dB:d={SILENCE_MAX}", "-f", "null", "-", sortie=True)
    silences = []
    for m in re.finditer(r"silence_start: ([\d.]+)[\s\S]*?silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", err):
        a, b, dd = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if not (a >= film[0] - 0.5 and b <= film[1] + 0.5):     # les silences voulus DANS le film ne comptent pas
            silences.append(f"{a:.1f}–{b:.1f} s ({dd:.1f} s)")
    ligne(not silences, "aucun silence de plus de 3 s" + ("" if not silences else " — trouvés : " + ", ".join(silences)))
    seqs = lire_script()
    textes = [propre(p) for s in seqs for p in s["phrases"]]
    srt = f.with_suffix(".srt")
    if srt.exists():
        textes += [l for l in srt.read_text(encoding="utf-8").splitlines() if l and "-->" not in l and not l.isdigit()]
    trouves = mots_interdits(textes)
    ligne(not trouves, "aucun mot interdit dans le script ni les sous-titres" + ("" if not trouves else " — " + " ; ".join(trouves)))
    mo = f.stat().st_size / 1024 / 1024
    ligne(mo <= TAILLE_MAX_MO, f"taille {mo:.0f} Mo (maximum {TAILLE_MAX_MO} Mo pour un envoi en ligne)")
    err = ff.run("-i", str(f), "-af", "loudnorm=I=-16:print_format=json", "-f", "null", "-", sortie=True)
    m = re.search(r'"input_i"\s*:\s*"(-?[\d.]+)"', err)
    if m:
        i = float(m.group(1))
        ligne(abs(i - LUFS) <= 2.0, f"son {i:.1f} LUFS (visé : {LUFS}, ± 2)")
    noms, contact = lire_equipe()
    ligne(bool(contact) and "COMPLÉTER" not in contact.upper(), f"carte de fin : équipe « {', '.join(noms)} », contact « {contact} »"
          + ("" if contact and "COMPLÉTER" not in contact.upper() else " — à compléter dans docs/video/equipe.txt"))
    r = subprocess.run([ff.ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height",
                        "-of", "csv=p=0", str(f)], capture_output=True, text=True)
    ligne(r.stdout.strip() == f"h264,{W},{H}", f"image {r.stdout.strip()} (attendu : h264,{W},{H})")
    return ok


# ───────────────────────────────────────────────────────────── secours HTML
def secours(ff: FF, f: Path, chemin: Path | None = None, pas: float = 2.0) -> Path:
    """Un seul fichier HTML, sans rien d'extérieur : une image toutes les `pas` secondes, le son, les sous-titres,
    un bouton Lecture (les navigateurs bloquent le son automatique)."""
    chemin = chemin or f.with_name("club-pulse-presentation-secours.html")
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        ff.run("-i", str(f), "-vf", f"fps=1/{pas},scale=960:-2", "-q:v", "6", str(tdp / "i%04d.jpg"))
        ff.run("-i", str(f), "-vn", "-c:a", "aac", "-b:a", "64k", "-ac", "1", str(tdp / "son.m4a"))
        images = [base64.b64encode(p.read_bytes()).decode() for p in sorted(tdp.glob("i*.jpg"))]
        son = base64.b64encode((tdp / "son.m4a").read_bytes()).decode()
    cartons = []
    srt = f.with_suffix(".srt")
    if srt.exists():
        for b in srt.read_text(encoding="utf-8").strip().split("\n\n"):
            l = b.splitlines()
            if len(l) >= 3:
                a, z = [x.strip() for x in l[1].split("-->")]
                sec = lambda s: int(s[0:2]) * 3600 + int(s[3:5]) * 60 + int(s[6:8]) + int(s[9:12]) / 1000
                cartons.append([sec(a), sec(z), "\n".join(l[2:])])
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Club Pulse — présentation</title><style>
body{{margin:0;background:#05070B;color:#F3F1EC;font:600 20px/1.4 -apple-system,system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh}}
#cadre{{position:relative;width:min(100vw,calc(100vh*16/9));aspect-ratio:16/9;background:#05070B}}
#img{{width:100%;height:100%;object-fit:contain;display:block}}
#st{{position:absolute;left:8%;right:8%;bottom:5%;text-align:center;white-space:pre-line;font-size:clamp(14px,2.4vw,30px)}}
#st span{{background:rgba(0,0,0,.72);padding:.15em .5em;border-radius:6px;box-decoration-break:clone;-webkit-box-decoration-break:clone}}
#lecture{{position:absolute;inset:0;margin:auto;width:220px;height:84px;border-radius:999px;border:0;background:#CD2128;color:#fff;font:800 30px system-ui;cursor:pointer}}
nav{{display:flex;gap:16px;align-items:center;padding:12px;width:min(100vw,calc(100vh*16/9));box-sizing:border-box}}
nav button{{font:inherit;color:#F3F1EC;background:none;border:2px solid #8A93A1;border-radius:999px;padding:6px 18px;cursor:pointer}}
input[type=range]{{flex:1}}
</style></head><body>
<div id="cadre"><img id="img" alt="Image de la présentation"><div id="st"></div><button id="lecture">▶ Lecture</button></div>
<nav><button id="pp">▶</button><input id="barre" type="range" min="0" max="1000" value="0" aria-label="Position"><span id="tps">0:00</span></nav>
<audio id="son" preload="auto" src="data:audio/mp4;base64,{son}"></audio>
<script>
const I={json.dumps(images)}, C={json.dumps(cartons, ensure_ascii=False)}, PAS={pas};
const son=document.getElementById("son"), img=document.getElementById("img"), st=document.getElementById("st"), b=document.getElementById("lecture"), pp=document.getElementById("pp"), barre=document.getElementById("barre");
let dern=-1;
function maj(){{const t=son.currentTime, k=Math.min(I.length-1,Math.floor(t/PAS));
  if(k!==dern){{img.src="data:image/jpeg;base64,"+I[k];dern=k;}}
  const c=C.find(c=>t>=c[0]&&t<=c[1]); st.innerHTML=c?"<span>"+c[2].replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/\\n/g,"<br>")+"</span>":"";
  if(son.duration) barre.value=Math.round(1000*t/son.duration);
  document.getElementById("tps").textContent=Math.floor(t/60)+":"+String(Math.floor(t%60)).padStart(2,"0");}}
function jouer(){{son.play().then(()=>{{b.style.display="none";pp.textContent="❚❚";}}).catch(()=>{{b.style.display="block";}});}}
b.onclick=jouer; pp.onclick=()=>{{if(son.paused)jouer();else{{son.pause();pp.textContent="▶";}}}};
barre.oninput=()=>{{if(son.duration)son.currentTime=son.duration*barre.value/1000;maj();}};
son.ontimeupdate=maj; son.onended=()=>{{pp.textContent="▶";}};
addEventListener("keydown",e=>{{if(e.key===" "){{e.preventDefault();pp.click();}}}});
maj(); jouer();
</script></body></html>"""
    chemin.write_text(page, encoding="utf-8")
    return chemin



# ───────────────────────────────────────────────────────────── résumé d'une page pour le jury
def resume() -> Path:
    """docs/video/RESUME_JURY.html (A4, une page) : le problème, la solution, ce qu'y gagne le Club, la demande, l'équipe.
    Les chiffres sont ceux de PREUVES.md ; l'équipe et le contact viennent de equipe.txt. PDF : Safari → Fichier →
    Exporter au format PDF (ou `python3 docs/video/outils/pdf.py` là où Playwright est installé)."""
    noms, contact = lire_equipe()
    e = html.escape
    equipe = e(", ".join(noms) if noms else "L'équipe Club Pulse")
    contact = e(contact) if contact and "COMPLÉTER" not in contact.upper() else "contact : à compléter dans docs/video/equipe.txt"
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Club Pulse — résumé pour le jury</title><style>
@page{{size:A4;margin:14mm 16mm}} *{{box-sizing:border-box}}
body{{margin:0;font:400 10.6pt/1.42 -apple-system,"Helvetica Neue",Arial,sans-serif;color:#14171C}}
header{{display:flex;align-items:center;gap:14px;border-bottom:2px solid #CD2128;padding-bottom:10px;margin-bottom:12px}}
.logo{{width:44px;height:44px}} h1{{font-size:22pt;margin:0;letter-spacing:-.02em}} header p{{margin:2px 0 0;color:#5B6370}}
h2{{font-size:11.5pt;margin:12px 0 4px;color:#CD2128;text-transform:uppercase;letter-spacing:.06em}}
p{{margin:0 0 6px}} ul{{margin:0 0 6px;padding-left:18px}} li{{margin:2px 0}}
.chiffres{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:8px 0}}
.chiffres div{{border:1px solid #D9DDE3;border-radius:8px;padding:6px 8px}} .chiffres b{{display:block;font-size:17pt;letter-spacing:-.02em}}
.demande{{border:2px solid #14171C;border-radius:10px;padding:8px 12px;margin-top:6px}}
.fin{{margin-top:12px;font-weight:700;font-size:12pt}} footer{{margin-top:10px;border-top:1px solid #D9DDE3;padding-top:6px;color:#5B6370;font-size:9pt}}
</style></head><body>
<header><svg class="logo" viewBox="0 0 24 24"><rect x=".5" y=".5" width="23" height="23" rx="7" fill="#CD2128"/><circle cx="12" cy="12" r="7" fill="none" stroke="#FFF" stroke-width="2.7" stroke-linecap="round" stroke-dasharray="33 11" transform="rotate(-90 12 12)"/><circle cx="7.05" cy="7.05" r="1.8" fill="#FFF"/></svg>
<div><h1>Club Pulse</h1><p>Club des Affaires · Foire du Valais — Hack VS 2026</p></div></header>

<h2>Le problème</h2>
<p>À la Foire, on échange des cartes de visite et on dit « on s'appelle ». Ensuite, rien ne se passe, et personne ne le
mesure. Entre deux événements, le Club ne sait pas où en sont les partenariats. Ses membres pourraient s'entraider
toute l'année, mais personne n'ose demander, ni dire non.</p>

<h2>La solution</h2>
<ul>
<li><b>Une demande précise, aux bonnes personnes.</b> Exemple : accueillir des acheteurs germanophones. Il faut un
minibus, une salle et un interprète. Seuls les membres qui peuvent aider reçoivent la demande.</li>
<li><b>Trois boutons : oui, non, ou pas cette fois.</b> Personne ne voit qui a dit non.</li>
<li><b>Chaque oui laisse un reçu</b>, daté et numéroté, que le membre peut retirer quand il veut. Si quelqu'un se
retire, on ne dit pas qui, et le Club trouve quelqu'un d'autre.</li>
<li><b>L'IA est suisse et facultative</b> (Apertus, à Lugano). Sur 26 questions préparées, elle a donné la bonne
réponse une fois : nos règles l'arrêtent quand elle se trompe. Avec ou sans IA, le Club marche pareil.</li>
</ul>

<h2>Ce qu'y gagne le Club</h2>
<div class="chiffres"><div><b>145</b>entreprises</div><div><b>173</b>représentants</div><div><b>8 sur 9</b>projets types possibles avec les seuls membres</div><div><b>1</b>pièce manquante : un interprète</div></div>
<ul>
<li>Il voit enfin où en sont les collaborations, et combien d'entreprises travaillent ensemble pour la première fois.
Toujours en chiffres globaux, jamais de noms.</li>
<li>Il sait quel métier lui manque, et peut inviter un non-membre avec un passe découverte de 90 jours.</li>
<li>Déjà fait : 22 chantiers construits, un validé sur le terrain, huit prévus ; 80 téléphones simulés en même temps
sans erreur ; 21 vraies demandes reçues à la Foire (on n'en montre que des totaux).</li>
</ul>

<h2>La demande</h2>
<div class="demande"><p><b>Un pilote de 45 jours avec 50 membres volontaires</b>, de début janvier à mi-février 2027,
pendant les Mondiaux de ski de Crans-Montana. Les critères de réussite sont écrits à l'avance et seront validés avec
le Club. Oui, non, ou pas cette fois.</p></div>

<p class="fin">La Foire crée la rencontre. Club Pulse crée l'après. Si Jean-Marc dit oui, c'est que c'est oui.</p>
<footer><b>L'équipe :</b> {equipe} · {contact}<br>Monde de démonstration fictif : aucun membre réel n'apparaît dans la vidéo.</footer>
</body></html>"""
    chemin = VIDEO / "RESUME_JURY.html"
    chemin.write_text(page, encoding="utf-8")
    return chemin

# ───────────────────────────────────────────────────────────── entrée
def _ff(args: argparse.Namespace) -> FF:
    ffm = args.ffmpeg or shutil.which("ffmpeg")
    ffp = args.ffprobe or shutil.which("ffprobe")
    if not ffm or not ffp:
        raise SystemExit("ffmpeg introuvable. Avec conda : conda install -y -c conda-forge ffmpeg")
    return FF(ffm, ffp)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("prompteur")
    sp.add_parser("srt-cible")
    sp.add_parser("mots")
    sp.add_parser("resume")
    m = sp.add_parser("monter")
    m.add_argument("--voix", type=Path, default=VIDEO / "voix")
    m.add_argument("--film", type=Path)
    m.add_argument("--sortie", type=Path, default=SORTIE)
    m.add_argument("--garder", action="store_true", help="garder le dossier de travail")
    v = sp.add_parser("verifier")
    v.add_argument("fichier", type=Path, nargs="?", default=SORTIE)
    s = sp.add_parser("secours")
    s.add_argument("fichier", type=Path, nargs="?", default=SORTIE)
    for x in (m, v, s):
        x.add_argument("--ffmpeg")
        x.add_argument("--ffprobe")
    a = p.parse_args(argv)
    if a.cmd == "prompteur":
        print(prompteur())
    elif a.cmd == "resume":
        print(resume())
    elif a.cmd == "srt-cible":
        print(srt_cible())
    elif a.cmd == "mots":
        seqs = lire_script()
        t = mots_interdits([propre(x) for s in seqs for x in s["phrases"]])
        print("\n".join(t) if t else "aucun mot interdit")
        return 1 if t else 0
    elif a.cmd == "monter":
        ff = _ff(a)
        if a.film and not a.film.exists():
            raise SystemExit(f"film introuvable : {a.film}")
        resume()
        f = monter(a.voix, a.film, ff, a.sortie, a.garder)
        print(f"\n  VIDÉO : {f}\n\n  Vérifications :")
        ok = verifier(ff, f)
        h = secours(ff, f)
        print(f"\n  Secours HTML (un seul fichier) : {h} · {h.stat().st_size / 1024 / 1024:.0f} Mo")
        print("\n  " + ("TOUT EST VERT." if ok else "AU MOINS UNE VÉRIFICATION EST ROUGE : voir ci-dessus."))
        return 0 if ok else 1
    elif a.cmd == "verifier":
        return 0 if verifier(_ff(a), a.fichier) else 1
    elif a.cmd == "secours":
        print(secours(_ff(a), a.fichier))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
