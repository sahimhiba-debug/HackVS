"""JOUR J — « deux double-clics » (1 - Lancer Club Pulse.command, 2 - Arrêter et effacer.command, à la racine du dépôt).

- LE FILM : la seule vidéo posée directement sur le Bureau (~/Desktop) est copiée dans le deck
  (docs/presentation/deck/assets/film.mp4, ignoré par git). Aucune, plusieurs, une icône iCloud vide : voyant rouge,
  jamais de devinette. Un .mov : orange (Chrome ne le lit pas toujours).
- LE JETON de la console : créé une fois, rangé HORS du dépôt (~/.clubpulse/jeton, droits 600).
- LA CHECK-LIST : six voyants (film, serveur local, adresse publique, deck, secteur, salle) et une dernière ligne,
  « FEU VERT v2 » ou « PASSER EN v1 » avec la raison. Mêmes voyants dans le terminal (scripts/jour_j.py) et sur la page
  locale /preflight (app/main.py, cette machine seulement).

Bibliothèque standard seulement : le lanceur l'appelle avant même que le serveur tourne."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import socket
import ssl
import subprocess
import tempfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

EXTENSIONS = (".mp4", ".m4v", ".mov")
TAILLE_MIN = 1024 * 1024                 # un film de quelques minutes pèse des dizaines de Mo ; une icône iCloud, quelques Ko
DUREE_ATTENDUE_S = 201                   # 3:21, le montage final (05_FILM_INTEGRATION.md) ; écart > 10 s : décaler les repères
FILM_DU_DECK = "docs/presentation/deck/assets/film.mp4"
PLAN_B = "Sans film, le deck (v1 comme v2) bascule seul sur son plan B raconté : rien à faire."
ORDRE = ("film", "serveur", "public", "deck", "secteur", "salle")


@dataclass
class Voyant:
    cle: str
    couleur: str                          # vert | orange | rouge
    titre: str
    detail: str


def bureau() -> Path:
    return Path(os.environ.get("CLUBPULSE_BUREAU") or Path.home() / "Desktop")


def dossier() -> Path:
    return Path(os.environ.get("CLUBPULSE_DOSSIER") or Path.home() / ".clubpulse")


def racine() -> Path:
    return Path(__file__).resolve().parents[2]


def cible_film() -> Path:
    return Path(os.environ.get("CLUBPULSE_FILM_DECK") or racine() / FILM_DU_DECK)


# ------------------------------------------------------------------ le film
def _taille(n: int) -> str:
    return f"{n / 1024 / 1024:.0f} Mo" if n >= 1024 * 1024 else f"{n} octets"


def _est_video(nom: str) -> bool:
    return nom.lower().endswith(EXTENSIONS)


SF_DATALESS = 0x40000000                 # macOS 14+ : fichier évacué vers iCloud (nom et taille gardés, contenu absent)


def _hors_disque_st(st: object) -> bool:
    return bool(getattr(st, "st_flags", 0) & SF_DATALESS)


def _hors_disque(p: Path) -> bool:
    return _hors_disque_st(p.stat())


def chercher_film(dossier_bureau: Path) -> dict:
    """La vidéo du Bureau, directement sur le Bureau (pas dans les sous-dossiers). Ne devine jamais."""
    if not dossier_bureau.is_dir():
        return {"couleur": "rouge", "message": f"BUREAU INTROUVABLE ({dossier_bureau})", "source": None}
    try:
        entrees = sorted(dossier_bureau.iterdir(), key=lambda p: p.name.lower())
    except PermissionError:
        return {"couleur": "rouge", "source": None,
                "message": "ACCÈS AU BUREAU REFUSÉ : Réglages Système → Confidentialité → Fichiers et dossiers → Terminal → Bureau"}
    videos = [p for p in entrees if not p.name.startswith(".") and _est_video(p.name) and p.is_file()]
    nuages = [p for p in entrees if p.name.startswith(".") and p.name.endswith(".icloud") and _est_video(p.name[1:-len(".icloud")])]
    if nuages and not videos and len(nuages) == 1:
        return {"couleur": "rouge", "source": None,
                "message": f"LE FILM EST DANS iCloud, PAS SUR LE DISQUE ({nuages[0].name[1:-len('.icloud')]}) : "
                           "Finder → clic droit sur le film → « Télécharger maintenant »"}
    noms = [p.name for p in videos] + [p.name[1:-len(".icloud")] + " (iCloud, pas sur le disque)" for p in nuages]
    if not noms:
        return {"couleur": "rouge", "message": "FILM ABSENT DU BUREAU", "source": None}
    if len(noms) > 1:
        return {"couleur": "rouge", "source": None,
                "message": "PLUSIEURS VIDÉOS SUR LE BUREAU : " + " · ".join(noms) + " — n'en laisser qu'une"}
    film = videos[0]
    if _hors_disque(film):                      # AUDIT I3 : avant toute lecture (qui lancerait un téléchargement silencieux)
        return {"couleur": "rouge", "source": None,
                "message": f"LE FILM EST DANS iCloud, PAS SUR LE DISQUE ({film.name}) : "
                           "Finder → clic droit sur le film → « Télécharger maintenant »"}
    taille = film.stat().st_size
    if taille < TAILLE_MIN:
        return {"couleur": "rouge", "source": None,
                "message": f"FILM TROP PETIT ({film.name}, {_taille(taille)}) : icône iCloud ou copie incomplète"}
    try:
        with open(film, "rb") as f:
            tete = f.read(12)
    except OSError as e:
        return {"couleur": "rouge", "source": None, "message": f"FILM ILLISIBLE ({film.name}) : {e.strerror}"}
    if tete[4:8] != b"ftyp":
        return {"couleur": "rouge", "source": None, "message": f"{film.name} ne ressemble pas à une vidéo MP4 ou MOV"}
    if film.suffix.lower() == ".mov":
        return {"couleur": "orange", "source": film, "taille": taille,
                "message": f"{film.name} est un .mov : Chrome ne le lit pas toujours — l'exporter en MP4 (H.264) si possible"}
    return {"couleur": "vert", "source": film, "taille": taille, "message": f"{film.name} · {_taille(taille)}"}


def _empreinte(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def copier_film(source: Path, cible: Path) -> bool:
    """Une COPIE (le pitch ne dépend plus du Bureau), refaite seulement si le film a changé (taille ou empreinte)."""
    if cible.exists() and cible.stat().st_size == source.stat().st_size and _empreinte(cible) == _empreinte(source):
        return False
    cible.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=cible.parent, prefix=".film-", suffix=".part")
    os.close(fd)
    try:
        shutil.copyfile(source, tmp)
        os.replace(tmp, cible)                           # atomique : jamais un film à moitié copié dans le deck
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return True


def film_ignore_par_git(depot: Path) -> bool:
    """Le film ne doit JAMAIS être commité : il est ignoré par git, et pas suivi. Hors dépôt (code téléchargé en zip,
    audit I4) ou sans git : le .gitignore fait foi."""
    try:
        depot_git = subprocess.run(["git", "-C", str(depot), "rev-parse", "--is-inside-work-tree"], capture_output=True, timeout=10)
        if depot_git.returncode != 0:
            raise OSError("pas un dépôt git")
        ignore = subprocess.run(["git", "-C", str(depot), "check-ignore", "-q", FILM_DU_DECK], capture_output=True, timeout=10)
        suivi = subprocess.run(["git", "-C", str(depot), "ls-files", "--error-unmatch", FILM_DU_DECK], capture_output=True, timeout=10)
        return ignore.returncode == 0 and suivi.returncode != 0
    except (OSError, subprocess.TimeoutExpired):        # pas de git : on relit .gitignore
        lignes = (depot / ".gitignore").read_text(encoding="utf-8").splitlines() if (depot / ".gitignore").exists() else []
        return FILM_DU_DECK in (x.strip() for x in lignes)


def sonder_film(p: Path) -> dict:
    """Durée et codec si ffprobe est installé ; sinon rien (on passe)."""
    if not shutil.which("ffprobe"):
        return {}
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name:format=duration",
                            "-of", "json", str(p)], capture_output=True, text=True, timeout=20)
        d = json.loads(r.stdout or "{}")
        return {"duree_s": float(d.get("format", {}).get("duration") or 0) or None,
                "codec": (d.get("streams") or [{}])[0].get("codec_name")}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {}


def _duree(s: Optional[float]) -> str:
    return "" if not s else f"{int(s) // 60}:{int(s) % 60:02d}"


def _note(dossier_jj: Path) -> dict:
    try:
        return json.loads((dossier_jj / "film.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _detail_sonde(note: dict) -> str:
    morceaux = []
    if note.get("duree_s"):
        ecart = abs(note["duree_s"] - DUREE_ATTENDUE_S)
        morceaux.append(f"durée {_duree(note['duree_s'])}" + (f" (attendu ≈ {_duree(DUREE_ATTENDUE_S)} : décaler les repères)" if ecart > 10 else ""))
    if note.get("codec"):
        morceaux.append(f"codec {note['codec']}")
    return " · ".join(morceaux)


def _sans_film_du_bureau(r: dict, cible: Path) -> Voyant:
    """Rien à copier : le deck lit-il encore une copie précédente ? Alors ce n'est pas le plan B — le dire juste."""
    if cible.exists():
        copie = f"le deck garde sa copie précédente ({_taille(cible.stat().st_size)})"
        if r["message"] == "FILM ABSENT DU BUREAU":
            return Voyant("film", "orange", "Film", f"plus de film sur le Bureau : {copie} — vérifier que c'est le bon")
        return Voyant("film", "rouge", "Film", f"{r['message']} — {copie}")
    return Voyant("film", "rouge", "Film", r["message"] + ". " + PLAN_B)


def preparer_film(dossier_bureau: Path, cible: Path, depot: Path, dossier_jj: Path) -> Voyant:
    """Étape a du lanceur : trouver, vérifier, copier, noter (hors du dépôt) — et le dire en un voyant."""
    if not film_ignore_par_git(depot):
        return Voyant("film", "rouge", "Film", f"{FILM_DU_DECK} n'est PAS ignoré par git : copie refusée (le film ne doit jamais être commité)")
    r = chercher_film(dossier_bureau)
    if r["source"] is None:
        return _sans_film_du_bureau(r, cible)
    source: Path = r["source"]
    copie = copier_film(source, cible)
    note = {"source": source.name, "taille": r["taille"], **sonder_film(cible)}
    dossier_jj.mkdir(parents=True, exist_ok=True)
    (dossier_jj / "film.json").write_text(json.dumps(note), encoding="utf-8")
    morceaux = [r["message"], "copié dans le deck" if copie else "déjà à jour dans le deck", _detail_sonde(note)]
    return Voyant("film", r["couleur"], "Film", " · ".join(x for x in morceaux if x))


def voyant_film(dossier_bureau: Path, cible: Path, dossier_jj: Path) -> Voyant:
    """Pour la check-list : sans copier ni hacher (la page se rafraîchit toutes les 3 s)."""
    r = chercher_film(dossier_bureau)
    if r["source"] is None:
        return _sans_film_du_bureau(r, cible)
    if not cible.exists() or cible.stat().st_size != r["taille"]:
        return Voyant("film", "rouge", "Film", f"{r['message']} · PAS ENCORE COPIÉ dans le deck : relancer « 1 - Lancer Club Pulse »")
    note = _note(dossier_jj)
    sonde = _detail_sonde(note) if note.get("source") == r["source"].name else ""
    return Voyant("film", r["couleur"], "Film", " · ".join(x for x in (r["message"], "copié dans le deck", sonde) if x))


# ------------------------------------------------------------------ le jeton de la console
def jeton(dossier_jj: Path) -> str:
    """Créé s'il n'existe pas, rangé HORS du dépôt, droits 600 (dossier 700). Jamais affiché, jamais dans une URL."""
    d = dossier_jj.resolve()
    if d == racine() or racine() in d.parents:
        raise ValueError("le jeton ne se range jamais dans le dépôt")
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    f = d / "jeton"
    j = f.read_text(encoding="utf-8").strip() if f.exists() else ""
    if len(j) < 16:
        j = secrets.token_urlsafe(24)
        fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as sortie:
            sortie.write(j + "\n")
    os.chmod(f, 0o600)
    return j


# ------------------------------------------------------------------ voyants de la check-list
def contexte_ssl() -> ssl.SSLContext:
    """AUDIT B2 : le Python de python.org ne lit pas le trousseau de macOS — les autorités de certifi (installé avec
    httpx) rendent la sonde HTTPS juste ; à défaut, le magasin du système."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        return ssl.create_default_context()


def sonde_http(url: str, delai: float = 3.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=delai, context=contexte_ssl() if url.startswith("https:") else None) as r:
            return 200 <= r.status < 400
    except (OSError, urllib.error.URLError, ValueError):
        return False


def resoudre_public(hote: str) -> list[str]:
    """Le nom tel qu'Internet le voit (DNS public par HTTPS), pas tel que MagicDNS le donne à ce Mac."""
    req = urllib.request.Request(f"https://1.1.1.1/dns-query?name={hote}&type=A", headers={"Accept": "application/dns-json"})
    with urllib.request.urlopen(req, timeout=4, context=contexte_ssl()) as r:
        d = json.load(r)
    return [a["data"] for a in d.get("Answer", []) if a.get("type") == 1]


def obtenir_par_ip(ip: str, hote: str, chemin: str) -> Optional[int]:
    """GET https://hote/chemin en se connectant à l'adresse publique `ip` (SNI et Host = hote) : le chemin d'Internet."""
    try:
        with socket.create_connection((ip, 443), timeout=4) as s, contexte_ssl().wrap_socket(s, server_hostname=hote) as t:
            t.sendall(f"GET {chemin} HTTP/1.1\r\nHost: {hote}\r\nConnection: close\r\n\r\n".encode())
            return int(t.recv(64).split(b"\r\n", 1)[0].split()[1])
    except (OSError, ValueError, IndexError):
        return None


def _est_ip(hote: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET6 if ":" in hote else socket.AF_INET, hote)
        return True
    except OSError:
        return False


def sonde_publique(url: str, resoudre: Callable[[str], list[str]] = resoudre_public,
                   obtenir: Callable[[str, str, str], Optional[int]] = obtenir_par_ip,
                   sonde_locale: Callable[[str], bool] = sonde_http) -> tuple[str, str]:
    """AUDIT I1 : avec MagicDNS, le Mac joint son propre nom *.ts.net par le tailnet — un vert local ne prouve pas que les
    téléphones en 4G y arrivent. Vert seulement si l'adresse PUBLIQUE du nom (relais Funnel) répond."""
    u = urlparse(url)
    hote, chemin = u.hostname or "", u.path or "/"
    try:
        ips = [hote] if _est_ip(hote) else resoudre(hote)
    except (OSError, ValueError):
        if sonde_locale(url):
            return "orange", f"{url} répond depuis ce Mac, mais le DNS public est injoignable : confirmer avec un téléphone en 4G"
        return "rouge", f"{url} injoignable : tunnel Tailscale arrêté ou Mac hors réseau"
    if not ips:
        return "rouge", f"{hote} n'est pas publié sur Internet : Funnel désactivé pour ce Mac ? (console Tailscale)"
    for ip in ips:
        code = obtenir(ip, hote, chemin)
        if code is not None and 200 <= code < 400:
            return "vert", f"{url} · joignable depuis Internet (relais {ip})"
    return "rouge", f"{url} ne répond pas depuis Internet (relais {', '.join(ips)}) : tunnel arrêté ?"


def pmset() -> Optional[str]:
    if not shutil.which("pmset"):
        return None
    try:
        return subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None


def voyant_secteur(sortie: Optional[str]) -> Voyant:
    if sortie and "AC Power" in sortie:
        return Voyant("secteur", "vert", "Mac sur secteur", "branché")
    if sortie and "Battery Power" in sortie:
        return Voyant("secteur", "rouge", "Mac sur secteur", "SUR BATTERIE : brancher l'alimentation")
    return Voyant("secteur", "orange", "Mac sur secteur", "inconnu (pmset indisponible) : vérifier le câble à l'œil")


def voyant_salle(etat: Optional[dict]) -> Voyant:
    if etat is None:
        return Voyant("salle", "vert", "Salle réinitialisée", "vierge depuis le lancement")
    if etat.get("injoignable"):
        return Voyant("salle", "rouge", "Salle réinitialisée", "état de la salle illisible (serveur local arrêté ?)")
    if etat.get("invitee") or etat.get("demande") or etat.get("vue") == "bilan":
        return Voyant("salle", "rouge", "Salle réinitialisée", "la salle a déjà servi : régie → « Réinitialiser : tout effacer »")
    n = etat.get("participants")
    if isinstance(n, int) and n >= 3:           # AUDIT I8 : deux téléphones d'équipe s'affichent « < 3 » ; au-delà, inattendu
        return Voyant("salle", "orange", "Salle réinitialisée",
                      f"déjà {n} participants avant le pitch (répétition ? QR qui a fuité ?) : régie → « Réinitialiser : tout effacer »")
    ouverte = f"ouverte · participants : {etat.get('participants', 0)}" if etat.get("ouverte") else "pas encore ouverte (régie → « 1 · Ouvrir la salle »)"
    return Voyant("salle", "vert", "Salle réinitialisée", ouverte)


def controles(*, bureau: Path, cible: Path, dossier: Path, base_locale: str, base_publique: Optional[str], deck_url: str,
              salle: Optional[dict], sonde: Callable[[str], bool], pmset: Callable[[], Optional[str]],
              sonde_pub: Optional[Callable[[str], tuple[str, str]]] = None) -> list[Voyant]:
    urls = {"serveur": base_locale + "/sante", "deck": deck_url}
    url_pub = base_publique.rstrip("/") + "/sante" if base_publique else None
    sp = sonde_pub or (lambda u: ("vert", u) if sonde(u) else ("rouge", f"{u} injoignable : tunnel Tailscale arrêté ou Mac hors réseau"))
    with ThreadPoolExecutor(max_workers=3) as ex:                 # trois sondes en parallèle : la page reste vive
        futurs = {k: ex.submit(sonde, u) for k, u in urls.items()}
        pub = ex.submit(sp, url_pub) if url_pub else None
        ok = {k: f.result() for k, f in futurs.items()}
        public = pub.result() if pub else ("rouge", "PUBLIC_BASE_URL absent")
    vs = [voyant_film(bureau, cible, dossier),
          Voyant("serveur", "vert" if ok["serveur"] else "rouge", "Serveur local",
                 base_locale if ok["serveur"] else f"{base_locale} ne répond pas (journal : ~/.clubpulse/logs/prototype.log)"),
          Voyant("public", public[0], "Adresse publique", public[1]),
          Voyant("deck", "vert" if ok["deck"] else "rouge", "Deck", deck_url if ok["deck"] else f"{deck_url} ne répond pas"),
          voyant_secteur(pmset()),
          voyant_salle(salle)]
    return vs


def verdict(vs: list[Voyant]) -> tuple[str, list[str]]:
    """« FEU VERT v2 » si tout est vert. Le film n'entre pas dans le choix : v1 et v2 lisent le même film."""
    raisons = [f"{v.titre} : {v.detail}" for v in vs if v.cle != "film" and v.couleur != "vert"]
    film = next((v for v in vs if v.cle == "film"), None)
    notes = [PLAN_B] if film and PLAN_B in film.detail else []
    return ("FEU VERT v2" if not raisons else "PASSER EN v1"), raisons + notes


def en_dict(vs: list[Voyant]) -> dict:
    texte, raisons = verdict(vs)
    return {"voyants": [asdict(v) for v in vs], "verdict": texte, "raisons": raisons}


_ANSI = {"vert": "\033[1;32m", "orange": "\033[1;33m", "rouge": "\033[1;31m"}


def en_texte(vs: list[Voyant], couleurs: bool = True) -> str:
    def c(couleur: str, t: str) -> str:
        return f"{_ANSI[couleur]}{t}\033[0m" if couleurs else t
    lignes = ["", "Check-list Club Pulse (aussi sur http://127.0.0.1:8000/preflight)", ""]
    for v in vs:
        lignes.append(f"  {c(v.couleur, '● ' + v.couleur.upper())}{' ' * (9 - len(v.couleur))}{v.titre} — {v.detail}")
    texte, raisons = verdict(vs)
    lignes.append("")
    lignes += [f"  · {r}" for r in raisons]
    lignes.append(c("vert" if texte == "FEU VERT v2" else "rouge", texte) +
                  ("" if texte == "FEU VERT v2" else " — " + next((r for r in raisons if r != PLAN_B), "")))
    return "\n".join(lignes)
