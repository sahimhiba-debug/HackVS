"""F29 / F24 — un `kill -9` en pleine démonstration, puis la relance avec la MÊME configuration (`make demo` : journal
fichier + secret stable) : l'état, les sessions, le passe juré et le rejeu IA reviennent intacts.

Le serveur est un VRAI processus uvicorn tué par SIGKILL (aucun arrêt propre). Le « modèle » est un faux fournisseur
local (HTTP sur 127.0.0.1, compatible chat/completions) : avant le kill, un récit est réellement PROPOSÉ PAR LE MODÈLE ;
après la relance, le fournisseur pointe vers une adresse MORTE — le récit doit revenir du journal (CACHE_REPLAY), sans
appel. Données FICTIVES."""
import contextlib
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PROTO = Path(__file__).resolve().parents[1]
CONSOLE = {"X-Pulse-Console": "1"}
SECRET = "s" * 8 + "-secret-de-demonstration-stable-pour-ce-test"
A = "delegation_acheteurs"


def _port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _FauxModele(BaseHTTPRequestHandler):
    """Raconte le premier fait reçu (« état : … » → « État : … ».), lié à F1 ; toute autre tâche : un objet vide."""
    appels = 0

    def do_POST(self):  # noqa: N802
        corps = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        message = corps["messages"][-1]["content"]
        try:
            faits = json.loads(message)["faits"]
            t = faits[0]["texte"]
            sortie = {"phrases": [{"texte": t[0].upper() + t[1:] + ".", "faits": [faits[0]["id"]]}]}
            type(self).appels += 1
        except (ValueError, KeyError, TypeError, IndexError):
            sortie = {}
        rep = json.dumps({"choices": [{"message": {"content": json.dumps(sortie, ensure_ascii=False)}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(rep)))
        self.end_headers()
        self.wfile.write(rep)

    def log_message(self, *a):
        pass


def _demarrer(env: dict) -> tuple[subprocess.Popen, str]:
    port = _port()
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=PROTO, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    limite = time.monotonic() + 60
    while time.monotonic() < limite:
        assert srv.poll() is None, "le serveur s'est arrêté au démarrage"
        try:
            urllib.request.urlopen(base + "/etabli", timeout=1)
            return srv, base
        except urllib.error.HTTPError:
            return srv, base
        except OSError:
            time.sleep(0.1)
    srv.kill()
    raise RuntimeError("serveur non démarré")


def _api(base: str, chemin: str, corps=None, entetes=None, methode=None):
    req = urllib.request.Request(base + chemin, method=methode or ("POST" if corps is not None else "GET"),
                                 data=None if corps is None else json.dumps(corps).encode(),
                                 headers={"Content-Type": "application/json", **(entetes or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


@contextlib.contextmanager
def _faux_modele():
    srv = HTTPServer(("127.0.0.1", 0), _FauxModele)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()


def _env(tmp_path: Path, modele: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("APERTUS_", "HACKVS_"))}
    return env | {"HACKVS_MODE": "demo", "HACKVS_SEMANTIQUE": "0", "HACKVS_DB": ":memory:", "HACKVS_DECISIONS_DB": ":memory:",
                  "HACKVS_CYCLE_DB": ":memory:", "HACKVS_ESSAIS_DB": str(tmp_path / "club_pulse.db"), "HACKVS_SECRET": SECRET,
                  "APERTUS_BASE_URL": modele, "APERTUS_API_KEY": "cle-de-test", "APERTUS_MODEL": "faux-modele"}


def test_kill_9_puis_relance_etat_sessions_passe_jure_et_rejeu_ia_intacts(tmp_path):
    with _faux_modele() as modele:
        srv, base = _demarrer(_env(tmp_path, modele))
        try:
            _api(base, "/api/pulse/demo/suivant", {}, CONSOLE)             # étape 1 : Sophie active son compte, son action
            etape = _api(base, "/api/pulse/demo/suivant", {}, CONSOLE)["etape"]
            code = next(p["code"] for p in _api(base, "/api/pulse/console/personas", entetes=CONSOLE) if p["id"] == "n01")
            sophie = {"X-Pulse-Session": _api(base, "/api/pulse/acces", {"code": code})["session"]}
            profil = _api(base, "/api/pulse/moi/profil", entetes=sophie)
            passe = _api(base, "/api/pulse/console/jure", {"persona": "s14", "minutes": 30}, CONSOLE)
            jure = {"X-Pulse-Session": _api(base, "/api/pulse/jure", {"jeton": passe["url"].split("jure=", 1)[1]})["session"]}
            en_attente = _api(base, "/api/pulse/console/jure", {"persona": "s01", "minutes": 30}, CONSOLE)["url"].split("jure=", 1)[1]
            recit = _api(base, f"/api/pulse/console/capacites/{A}/recit", {}, CONSOLE)
            assert recit["ia"]["issue"] == "MODEL_CALLED" and _FauxModele.appels == 1, recit["ia"]
            _api(base, "/api/pulse/console/ia", {"actif": False}, CONSOLE)
            avant = {k: _api(base, f"/api/pulse/console/{k}", entetes=CONSOLE) for k in ("capacites", "essais")}
        finally:
            os.kill(srv.pid, signal.SIGKILL)                               # aucun arrêt propre
            srv.wait()

    srv, base = _demarrer(_env(tmp_path, "http://127.0.0.1:9"))             # même journal, même secret ; modèle MORT
    try:
        assert {k: _api(base, f"/api/pulse/console/{k}", entetes=CONSOLE) for k in avant} == avant
        assert _api(base, "/api/pulse/etat", entetes=CONSOLE)["etape"] == etape        # la régie reprend où elle était
        assert _api(base, "/api/pulse/moi/profil", entetes=sophie) == profil           # session et compte de Sophie
        assert _api(base, "/api/pulse/moi/date", entetes=jure)["date"]                 # session du juré
        assert _api(base, "/api/pulse/jure", {"jeton": en_attente})["session"]         # passe émis, pas encore scanné
        assert _api(base, "/api/pulse/console/ia", entetes=CONSOLE)["actif"] is False  # l'interrupteur IA
        _api(base, "/api/pulse/console/ia", {"actif": True}, CONSOLE)
        rejoue = _api(base, f"/api/pulse/console/capacites/{A}/recit", {}, CONSOLE)
        assert rejoue["ia"]["issue"] == "CACHE_REPLAY" and rejoue["phrases"] == recit["phrases"], rejoue["ia"]
    finally:
        srv.kill()
        srv.wait()


def test_make_demo_lance_un_journal_fichier_et_un_secret_stable_hors_depot():
    """La configuration exercée ci-dessus est CELLE de `make demo` (sinon le test prouverait un autre lancement)."""
    racine = PROTO.parent
    recette = racine.joinpath("Makefile").read_text(encoding="utf-8").split("\ndemo:", 1)[1].split("\n\n", 1)[0]
    assert "HACKVS_ESSAIS_DB=var/club_pulse.db" in recette
    assert 'HACKVS_SECRET="$$(cat var/secret_demo)"' in recette and "secrets.token_urlsafe" in recette
    assert "prototype/var/" in racine.joinpath(".gitignore").read_text(encoding="utf-8").splitlines()   # jamais committé


def test_reinitialisation_puis_kill_9_le_monde_rendu_est_celui_d_apres_la_reinitialisation(tmp_path):
    """R2 (contre-expertise) : un monde A vécu (quatre étapes : une action existe), la console réinitialise (monde B, une
    étape), `kill -9`, relance : c'est B qui revient — rien de A, et l'ancien journal reste clos (aucun fait de A
    n'est réapparu dans le fichier)."""
    import sqlite3
    srv, base = _demarrer(_env(tmp_path, "http://127.0.0.1:9"))
    try:
        _api(base, "/api/pulse/demo/aller/4", {}, CONSOLE)                       # monde A : accords réunis
        essais_a = _api(base, "/api/pulse/console/essais", entetes=CONSOLE)["essais"]
        assert essais_a, "le monde A doit contenir une action"
        _api(base, "/api/pulse/demo/reinitialiser", {}, CONSOLE)
        _api(base, "/api/pulse/demo/suivant", {}, CONSOLE)                      # monde B : une étape
        b = {k: _api(base, f"/api/pulse/console/{k}", entetes=CONSOLE) for k in ("capacites", "essais")}
        etape_b = _api(base, "/api/pulse/etat", entetes=CONSOLE)["etape"]
    finally:
        os.kill(srv.pid, signal.SIGKILL)
        srv.wait()
    srv, base = _demarrer(_env(tmp_path, "http://127.0.0.1:9"))
    try:
        assert _api(base, "/api/pulse/etat", entetes=CONSOLE)["etape"] == etape_b == 1
        assert {k: _api(base, f"/api/pulse/console/{k}", entetes=CONSOLE) for k in b} == b
        # les identifiants d'essai sont DÉTERMINISTES (porteur, question, position) : B recrée le même essai que A à
        # l'étape 1. Ce qui distingue A : ses étapes 2 à 4 et l'autorisation de son action (accords réunis)
        assert [e["etat"] for e in essais_a] == ["AUTORISE"]
        with sqlite3.connect(tmp_path / "club_pulse.db") as db:
            contenu = " ".join(d for (d,) in db.execute("SELECT donnees FROM evenements"))
        assert '"vers": "AUTORISE"' not in contenu.replace('"vers":"', '"vers": "'), "un fait du monde A est revenu"
        etapes = [int(x) for x in __import__("re").findall(r'"etape": ?(\d+)', contenu)]
        assert etapes == [1], etapes                                             # DEMO_ETAPE : seulement celle de B
    finally:
        srv.kill()
        srv.wait()
