"""Le lanceur du jour J, DE BOUT EN BOUT : « 1 - Lancer Club Pulse.command » puis « 2 - Arrêter et effacer.command »,
lancés pour de vrai (bash), avec un faux Bureau temporaire portant zéro, une ou deux fausses vidéos.

Ce qui est simulé (macOS absent de la CI) : `tailscale`, `open`, `pbcopy`, `pmset`, `caffeinate` sont de petits scripts
qui notent leurs arguments ; l'adresse publique pointe vers un port fermé (le voyant doit être ROUGE, le verdict
« PASSER EN v1 »). Tout le reste est réel : le prototype (demo-tunnel.sh), le serveur du deck, la check-list, la purge.
Rien n'est écrit dans le dépôt : film, journal, jeton et secret vont dans des dossiers temporaires."""
import json
import os
import shutil
import socket
import subprocess
import urllib.request
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[2]
LANCER = RACINE / "1 - Lancer Club Pulse.command"
ARRETER = RACINE / "2 - Arrêter et effacer.command"
pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash absent")

STUBS = {
    # STUB_TS_BLOQUE=1 : comme un Funnel non autorisé, « funnel --bg » affiche une adresse à visiter et ATTEND
    "tailscale": '#!/bin/bash\necho "tailscale $*" >> "$CLUBPULSE_DOSSIER/stubs.log"\n'
                 '[ "${STUB_TS_BLOQUE:-0}" = 1 ] && [ "$1 $2" = "funnel --bg" ] && exec sleep 301\nexit 0\n',
    "ipconfig": '#!/bin/bash\necho 127.0.0.1\n',
    "open": '#!/bin/bash\necho "open $*" >> "$CLUBPULSE_DOSSIER/stubs.log"\n',
    "pbcopy": '#!/bin/bash\ncat > "$CLUBPULSE_DOSSIER/presse-papiers"\n',
    "pmset": "#!/bin/bash\necho \"Now drawing from 'AC Power'\"\n",
    # comme le vrai : options, puis la commande (ou rien : il attend) — l'arrêt doit l'abattre avec son groupe
    "caffeinate": '#!/bin/bash\nwhile [ "${1:-}" != "${1#-}" ]; do shift; done\n[ $# -gt 0 ] && exec "$@"\nexec sleep 86400\n',
}


def _port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _video(chemin: Path) -> Path:
    chemin.write_bytes(b"\x00\x00\x00\x20ftypisom" + os.urandom(64) + b"\x00" * (2 * 1024 * 1024))
    return chemin


@pytest.fixture
def jour_j(tmp_path):
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for nom, corps in STUBS.items():
        (stubs / nom).write_text(corps)
        (stubs / nom).chmod(0o755)
    bureau, dossier = tmp_path / "Desktop", tmp_path / "clubpulse"
    bureau.mkdir()
    port, port_deck = _port_libre(), _port_libre()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("HACKVS_", "CLUBPULSE_", "PUBLIC_BASE_URL"))}
    env |= {"PATH": f"{stubs}:{env['PATH']}", "NO_COLOR": "1", "CLUBPULSE_BUREAU": str(bureau), "CLUBPULSE_DOSSIER": str(dossier),
            "CLUBPULSE_FILM_DECK": str(tmp_path / "deck" / "film.mp4"), "CLUBPULSE_VAR": str(tmp_path / "var"),
            "CLUBPULSE_PORT": str(port), "CLUBPULSE_PORT_DECK": str(port_deck),
            "CLUBPULSE_URL_PUBLIQUE": f"https://127.0.0.1:{_port_libre()}", "CLUBPULSE_ATTENTE_PUBLIQUE": "1",
            "HACKVS_FOIRE": "1", "HACKVS_SEMANTIQUE": "0"}

    def lancer(script: Path, **en_plus: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(script)], env=env | en_plus, capture_output=True, text=True, timeout=240, cwd=tmp_path)

    yield {"bureau": bureau, "dossier": dossier, "deck": tmp_path / "deck" / "film.mp4", "port": port, "port_deck": port_deck,
           "lancer": lancer}
    lancer(ARRETER)                                                    # quoi qu'il arrive, rien ne reste allumé


def _libre(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def test_une_video_le_film_copie_tout_demarre_check_list_puis_tout_s_eteint(jour_j):
    film = _video(jour_j["bureau"] / "Film Club Pulse.mp4")
    avant = (film.read_bytes(), film.stat().st_mtime_ns)
    r = jour_j["lancer"](LANCER)
    out = r.stdout
    assert "Film — Film Club Pulse.mp4" in out and "copié dans le deck" in out, out
    assert jour_j["deck"].read_bytes() == avant[0]
    jeton = (jour_j["dossier"] / "jeton").read_text().strip()
    assert (jour_j["dossier"] / "presse-papiers").read_text() == jeton                # copié dans le presse-papiers
    assert jeton not in out and jeton not in r.stderr                                  # jamais affiché
    stubs = (jour_j["dossier"] / "stubs.log").read_text()
    assert f"tailscale funnel --bg {jour_j['port']}" in stubs
    assert f"http://127.0.0.1:{jour_j['port']}/salle/regie" in stubs and f"http://127.0.0.1:{jour_j['port_deck']}/v2.html" in stubs
    lignes = out.splitlines()
    assert any("● VERT" in x and "Serveur local" in x for x in lignes), out
    assert any("● VERT" in x and "Deck" in x for x in lignes), out
    assert any("● VERT" in x and "Mac sur secteur" in x for x in lignes), out
    assert any("● VERT" in x and "Salle réinitialisée" in x for x in lignes), out
    assert any("● ROUGE" in x and "Adresse publique" in x for x in lignes), out           # tunnel simulé : injoignable
    verdict = next(x for x in lignes if x.startswith(("FEU VERT v2", "PASSER EN v1")))
    assert verdict.startswith("PASSER EN v1") and "Adresse publique" in verdict
    page = json.load(urllib.request.urlopen(f"http://127.0.0.1:{jour_j['port']}/preflight.json", timeout=10))
    assert page["verdict"] == "PASSER EN v1"                                           # la page dit la même chose
    assert (jour_j["dossier"] / "logs" / "prototype.log").exists()

    groupes = {f.name: int(f.read_text().splitlines()[0]) for f in (jour_j["dossier"] / "pids").iterdir()}   # numéro, puis heure de démarrage
    assert set(groupes) == {"prototype", "deck", "caffeinate"}
    a = jour_j["lancer"](ARRETER)
    assert "Tout est éteint et effacé." in a.stdout, a.stdout + a.stderr
    assert "tailscale funnel reset" in (jour_j["dossier"] / "stubs.log").read_text()
    assert _libre(jour_j["port"]) and _libre(jour_j["port_deck"])
    assert not list((jour_j["dossier"] / "pids").iterdir())
    assert (film.read_bytes(), film.stat().st_mtime_ns) == avant                        # le film du Bureau : intact
    for pid in groupes.values():                                                      # chaque groupe, enfants compris
        with pytest.raises(ProcessLookupError):
            os.killpg(pid, 0)


def test_aucune_video_voyant_rouge_et_plan_b_rappele(jour_j):
    out = jour_j["lancer"](LANCER).stdout
    assert "FILM ABSENT DU BUREAU" in out and "plan B raconté" in out, out
    assert not jour_j["deck"].exists()
    assert "Tout est éteint et effacé." in jour_j["lancer"](ARRETER).stdout


def test_deux_videos_voyant_rouge_avec_la_liste_et_aucune_copie(jour_j):
    _video(jour_j["bureau"] / "film-v1.mp4")
    _video(jour_j["bureau"] / "film-v2.mov")
    out = jour_j["lancer"](LANCER).stdout
    assert "PLUSIEURS VIDÉOS SUR LE BUREAU" in out and "film-v1.mp4" in out and "film-v2.mov" in out, out
    assert not jour_j["deck"].exists()
    assert "Tout est éteint et effacé." in jour_j["lancer"](ARRETER).stdout


# ------------------------------------------------------------------ AUDIT JOUR J : I2, I5, I6
V1 = RACINE / "3 - Passer en v1.command"


def test_audit_i2_un_vieux_fichier_pid_ne_fait_jamais_tuer_un_processus_etranger(jour_j):
    """Le Mac redémarre sans « Arrêter » : les numéros de processus des fichiers pids/ désignent alors d'autres
    programmes. Un double-clic ne doit tuer que NOS processus (numéro ET heure de démarrage)."""
    etranger = subprocess.Popen(["sleep", "300"], start_new_session=True)       # chef de son groupe, comme une app
    try:
        pids = jour_j["dossier"] / "pids"
        pids.mkdir(parents=True)
        (pids / "prototype").write_text(f"{etranger.pid}\n")                    # ancien format, sans heure
        (pids / "deck").write_text(f"{etranger.pid}\nMon Jan  1 00:00:00 2024\n")  # heure qui ne correspond pas
        jour_j["lancer"](ARRETER)
        assert etranger.poll() is None, "un processus étranger a été tué par l'arrêt"
        (pids / "prototype").write_text(f"{etranger.pid}\n")
        jour_j["lancer"](LANCER)
        assert etranger.poll() is None, "un processus étranger a été tué par le lancement"
    finally:
        etranger.kill()


def test_audit_i5_un_tunnel_qui_attend_ne_fige_pas_le_lanceur(jour_j):
    r = jour_j["lancer"](LANCER, STUB_TS_BLOQUE="1", CLUBPULSE_ATTENTE_TUNNEL="2")
    tunnel = next(x for x in r.stdout.splitlines() if "Tunnel" in x)
    assert "● ROUGE" in tunnel and "tunnel.log" in tunnel, r.stdout
    assert subprocess.run(["pgrep", "-f", "sleep 301"], capture_output=True).returncode != 0      # le tunnel figé a été abattu
    assert r.stdout.splitlines()[-1].startswith(("FEU VERT v2", "PASSER EN v1", "RÉPARER D'ABORD")), r.stdout


def test_audit_i6_passer_en_v1_sans_rien_taper(jour_j):
    """« PASSER EN v1 » doit être exécutable : un troisième double-clic arrête le prototype du tunnel, relance la démo v1
    joignable sur le point d'accès du Mac, ouvre l'Établi et le deck v1, et dit l'adresse du téléphone."""
    _video(jour_j["bureau"] / "film.mp4")
    jour_j["lancer"](LANCER)
    r = jour_j["lancer"](V1, CLUBPULSE_IP="127.0.0.1")
    assert r.returncode == 0, r.stdout + r.stderr
    port = jour_j["port"]
    assert urllib.request.urlopen(f"http://127.0.0.1:{port}/etabli", timeout=10).status == 200
    stubs = (jour_j["dossier"] / "stubs.log").read_text()
    assert "tailscale funnel reset" in stubs
    assert f"http://127.0.0.1:{port}/etabli" in stubs and f"http://127.0.0.1:{jour_j['port_deck']}/index.html" in stubs
    assert f"http://127.0.0.1:{port}/app" in r.stdout                           # le téléphone de Pauline
    assert "Tout est éteint et effacé." in jour_j["lancer"](ARRETER).stdout
    assert _libre(port)
