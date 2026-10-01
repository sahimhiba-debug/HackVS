"""Mesures de performance REPRODUCTIBLES de Club Pulse (pas des estimations).

    python scripts/mesurer_perf.py                 # tableau Markdown sur la sortie standard
    python scripts/mesurer_perf.py --json out.json # et les mesures brutes

Méthode :
- un VRAI serveur uvicorn (configuration de `make demo` : journal fichier temporaire, secret stable, IA absente,
  modèle sémantique coupé), lancé et tué par ce script ;
- démarrage à froid : du lancement du processus au premier 200 sur `/etabli`, N fois (journal neuf à chaque fois) ;
- latences HTTP par `urllib` depuis la même machine (boucle locale) : N requêtes séquentielles par point d'accès,
  moyenne, médiane, p95, max ;
- « après écriture » : une écriture (offre publiée) puis la lecture de l'Établi, qui recalcule (cache invalidé) ;
- « sous charge » : idem après 45 offres et 45 brouillons parasites — trois membres remplissent chacun le plafond de
  30 écritures par minute (scénario d'abus H2, borné par D2) ; la 31e écriture d'un membre doit recevoir 429.
Ce qui n'est PAS mesuré : un vrai téléphone, un vrai Wi-Fi, un modèle de langage (aucun n'est configuré).
"""
from __future__ import annotations

import json
import os
import platform
import secrets
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CONSOLE = {"X-Pulse-Console": "1", "Content-Type": "application/json"}


def _port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _env(journal: Path) -> dict:
    e = {k: v for k, v in os.environ.items() if not k.startswith(("APERTUS_", "HACKVS_"))}
    return e | {"HACKVS_MODE": "demo", "HACKVS_SEMANTIQUE": "0", "HACKVS_DB": ":memory:", "HACKVS_DECISIONS_DB": ":memory:",
                "HACKVS_CYCLE_DB": ":memory:", "HACKVS_ESSAIS_DB": str(journal), "HACKVS_SECRET": secrets.token_urlsafe(48)}


def _demarrer(journal: Path) -> tuple[subprocess.Popen, str, float]:
    port = _port()
    t0 = time.perf_counter()
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--no-access-log"], cwd=RACINE,
                         env=_env(journal), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    while True:
        if p.poll() is not None:
            raise RuntimeError("le serveur s'est arrêté au démarrage")
        try:
            with urllib.request.urlopen(base + "/etabli", timeout=1) as r:
                if r.status == 200:
                    return p, base, time.perf_counter() - t0
        except OSError:
            time.sleep(0.02)


def _req(base: str, chemin: str, corps=None, entetes=None, methode=None) -> tuple[int, float, bytes]:
    req = urllib.request.Request(base + chemin, data=None if corps is None else json.dumps(corps).encode(),
                                 headers=entetes or {}, method=methode or ("POST" if corps is not None else "GET"))
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as r:
        corps_r = r.read()
        return r.status, (time.perf_counter() - t0) * 1000, corps_r


def _stats(v: list[float]) -> dict:
    s = sorted(v)
    return {"n": len(s), "moyenne": round(statistics.fmean(s), 1), "mediane": round(statistics.median(s), 1),
            "p95": round(s[max(0, int(round(0.95 * len(s))) - 1)], 1), "max": round(s[-1], 1)}


def mesurer(n: int = 50, n_demarrages: int = 5) -> dict:
    res: dict = {"environnement": {"python": platform.python_version(), "machine": platform.machine(),
                                   "systeme": platform.platform(), "processeurs": os.cpu_count(),
                                   "charge_avant": [round(x, 2) for x in os.getloadavg()]}}
    with tempfile.TemporaryDirectory() as d:
        res["demarrage_ms"] = []
        for i in range(n_demarrages):
            p, _, t = _demarrer(Path(d) / f"froid{i}.db")
            res["demarrage_ms"].append(t * 1000)
            p.kill()
            p.wait()
        res["demarrage_ms"] = _stats(res["demarrage_ms"])

        p, base, _ = _demarrer(Path(d) / "journal.db")
        try:
            personas = json.loads(_req(base, "/api/pulse/console/personas", entetes=CONSOLE)[2])
            code = {x["id"]: x["code"] for x in personas}
            sess = {k: {"X-Pulse-Session": json.loads(_req(base, "/api/pulse/acces", {"code": c}, {"Content-Type": "application/json"})[2])["session"],
                        "Content-Type": "application/json"} for k, c in code.items() if k in ("n01", "s01", "s14")}
            points = {
                "Établi (registre, en cache)": (CONSOLE, "/api/pulse/console/capacites"),
                "Console : essais": (CONSOLE, "/api/pulse/console/essais"),
                "Écran commun": (CONSOLE, "/api/pulse/console/projection"),
                "Téléphone : demandes": (sess["s01"], "/api/pulse/moi/asks"),
                "Téléphone : mes actions": (sess["n01"], "/api/pulse/moi/actions"),
                "Téléphone : mes données": (sess["s01"], "/api/pulse/moi/donnees"),
                "Page /app (HTML)": ({}, "/app"),
            }
            res["latences_ms"] = {}
            for nom, (h, chemin) in points.items():
                _req(base, chemin, entetes=h)                                  # une lecture de chauffe
                res["latences_ms"][nom] = _stats([_req(base, chemin, entetes=h)[1] for _ in range(n)])

            def apres_ecriture(k: int) -> list[float]:
                v = []
                for i in range(k):
                    _req(base, "/api/pulse/moi/profil", {"disponible": i % 2 == 0}, sess["s01"], "PATCH")
                    v.append(_req(base, "/api/pulse/console/capacites", entetes=CONSOLE)[1])
                return v
            res["latences_ms"]["Établi après une écriture (recalcul)"] = _stats(apres_ecriture(max(10, n // 5)))

            # abus (H2) borné par le plafond D2 : 30 écritures / min / membre — chacun des trois membres le remplit
            for k in ("s14", "s01", "n01"):
                for i in range(15):
                    _req(base, "/api/pulse/moi/offres", {"nature": "objet", "quoi": f"Offre parasite {k} {i}", "au": "2026-10-10"}, sess[k])
                    _req(base, "/api/pulse/moi/essais", {"question": f"Question parasite fictive {k} {i} ?", "echeance": "2026-10-09"}, sess[k])
            try:
                _req(base, "/api/pulse/moi/offres", {"nature": "objet", "quoi": "Une de trop", "au": "2026-10-10"}, sess["s14"])
                res["plafond_ecritures"] = "NON APPLIQUÉ : la 31e écriture a été acceptée"
            except urllib.error.HTTPError as e:
                res["plafond_ecritures"] = f"31e écriture d'un membre dans la minute : {e.code}"
            res["latences_ms"]["Établi après une écriture, sous 90 parasites (3 membres au plafond d'une minute)"] = _stats(apres_ecriture(10))
        finally:
            p.kill()
            p.wait()
    return res


def tableau(res: dict) -> str:
    e = res["environnement"]
    lignes = [f"Environnement : Python {e['python']}, {e['machine']}, {e['processeurs']} processeurs, {e['systeme']} ; "
              f"charge moyenne avant la mesure (1/5/15 min) : {e['charge_avant']}.", "",
              "| Mesure | n | moyenne | médiane | p95 | max |", "|---|---|---|---|---|---|"]
    d = res["demarrage_ms"]
    lignes.append(f"| Démarrage à froid (processus → premier 200) | {d['n']} | {d['moyenne']} | {d['mediane']} | {d['p95']} | {d['max']} |")
    for nom, s in res["latences_ms"].items():
        lignes.append(f"| {nom} | {s['n']} | {s['moyenne']} | {s['mediane']} | {s['p95']} | {s['max']} |")
    lignes.append("")
    lignes.append(f"Plafond d'écritures : {res.get('plafond_ecritures', 'non mesuré')}.")
    return "\n".join(lignes) + "\n\nToutes les durées en millisecondes."


if __name__ == "__main__":
    r = mesurer()
    print(tableau(r))
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
