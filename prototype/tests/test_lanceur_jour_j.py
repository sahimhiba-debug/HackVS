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
    "tailscale": '#!/bin/bash\necho "tailscale $*" >> "$CLUBPULSE_DOSSIER/stubs.log"\n',
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

    def lancer(script: Path) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, timeout=240, cwd=tmp_path)

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

    groupes = {f.name: int(f.read_text()) for f in (jour_j["dossier"] / "pids").iterdir()}
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
