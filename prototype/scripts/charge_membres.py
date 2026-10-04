"""ANNÉE 1 · LOT 11 — TEST DE CHARGE à N membres SIMULÉS (500 puis 1 000) : un vrai serveur uvicorn sur un monde
synthétique de N membres (`HACKVS_TAILLE_MONDE`, données générées, aucune personne réelle), N comptes activés par
leur code d'invitation (au rythme permis par la limite d'accès du serveur : 300 par minute), puis N membres en
parallèle (16 fils) qui lisent leurs écrans, écrivent une note privée (une écriture par membre, puis une relecture),
et répondent à leurs demandes s'ils en ont, pendant que la console relit l'Établi. Mesures : p50 / p95 / max par
route, erreurs, cohérence finale (chaque « oui » accepté a son reçu).

    python scripts/charge_membres.py --n 500 --json ../docs/annee-1/qualite/charge_500.json
    python scripts/charge_membres.py --n 1000 --json ../docs/annee-1/qualite/charge_1000.json

Code de sortie 1 : une erreur, un « oui » sans reçu, un compte non activé, ou un budget p95 dépassé.

Ce qui n'est PAS mesuré : de vrais téléphones, un vrai réseau (boucle locale), un modèle de langage (aucun configuré),
PostgreSQL (journal SQLite en fichier, configuration du pilote à petite échelle)."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import platform
import secrets
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
CONSOLE = {"X-Pulse-Console": "1", "Content-Type": "application/json"}


def _port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Mesures:
    def __init__(self) -> None:
        self.t: dict[str, list[float]] = defaultdict(list)
        self.erreurs: dict[str, int] = defaultdict(int)
        self.verrou = threading.Lock()

    def appel(self, base: str, route: str, chemin: str, corps=None, entetes=None, accepter=(200,)):
        h = {"Content-Type": "application/json"} | (entetes or {})
        req = urllib.request.Request(base + chemin, data=json.dumps(corps).encode() if corps is not None else None, headers=h)
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                statut, corps_r = r.status, r.read()
        except urllib.error.HTTPError as e:
            statut, corps_r = e.code, e.read()
        dt = (time.perf_counter() - t0) * 1000
        with self.verrou:
            self.t[route].append(dt)
            if statut not in accepter:
                self.erreurs[f"{route} {statut}"] += 1
        return statut, (json.loads(corps_r) if corps_r else None)


def _p(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--n", type=int, default=500)
    a.add_argument("--fils", type=int, default=16)
    a.add_argument("--json")
    o = a.parse_args()
    secret = secrets.token_hex(24)
    os.environ["HACKVS_TAILLE_MONDE"] = str(o.n)
    from intelligence import monde_demo as md
    from intelligence.reglages import Reglages
    profils = [p.id for p in md.construire(sophie_profilee=False, recherches_autres=md.BESOINS_SUIVANTS).profils]
    cle = Reglages.depuis_env({"HACKVS_SECRET": secret}).secret
    codes = {pid: hmac.new(cle, pid.encode(), hashlib.sha256).hexdigest()[:6].upper() for pid in profils}

    port, tmp = _port(), tempfile.mkdtemp()
    env = {**os.environ, "HACKVS_SECRET": secret, "HACKVS_ESSAIS_DB": str(Path(tmp) / "journal.db"), "HACKVS_SEMANTIQUE": "0",
           "HACKVS_DB": ":memory:", "HACKVS_DECISIONS_DB": ":memory:", "HACKVS_CYCLE_DB": ":memory:", "HACKVS_MODE": "demo",
           "HACKVS_ANCIEN_PROTOTYPE": "0", "HACKVS_FOIRE": "1", "HACKVS_TAILLE_MONDE": str(o.n)}
    t_lancement = time.perf_counter()
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
                           cwd=RACINE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    m = Mesures()
    try:
        while True:
            try:
                urllib.request.urlopen(base + "/etabli", timeout=2).read()
                break
            except Exception:
                if srv.poll() is not None or time.perf_counter() - t_lancement > 300:
                    raise SystemExit("le serveur n'a pas démarré") from None
                time.sleep(0.2)
        demarrage_s = time.perf_counter() - t_lancement
        _, etat = m.appel(base, "console capacites", "/api/pulse/console/capacites", entetes=CONSOLE)
        membres_serveur = len(profils)

        # 1. activation : au rythme de la limite d'accès du serveur (300 par minute), jamais au-delà
        sessions: dict[str, str] = {}
        t0 = time.perf_counter()
        for i, pid in enumerate(profils):
            cible = t0 + i * (60.0 / 290)
            if (attente := cible - time.perf_counter()) > 0:
                time.sleep(attente)
            st, r = m.appel(base, "POST /acces", "/api/pulse/acces", {"code": codes[pid]})
            if st == 200:
                sessions[pid] = r["session"]
        activation_s = time.perf_counter() - t0

        # 2. N membres en parallèle : leurs écrans, leurs demandes (oui à la première), pendant que la console relit
        ouis: list[tuple[str, str]] = []
        fin = threading.Event()

        def console():
            while not fin.is_set():
                m.appel(base, "console capacites", "/api/pulse/console/capacites", entetes=CONSOLE)
                m.appel(base, "console suivi", "/api/pulse/console/suivi", entetes=CONSOLE, accepter=(200, 404))
                time.sleep(0.5)

        def membre(pid: str):
            h = {"X-Pulse-Session": sessions[pid]}
            m.appel(base, "GET /moi/actions", "/api/pulse/moi/actions", entetes=h)
            _, asks = m.appel(base, "GET /moi/asks", "/api/pulse/moi/asks", entetes=h)
            m.appel(base, "GET /moi/donnees", "/api/pulse/moi/donnees", entetes=h)
            m.appel(base, "GET /moi/souvenirs", "/api/pulse/moi/souvenirs", entetes=h)
            # une ÉCRITURE par membre (note privée, fictive) puis une relecture : l'index des claims est invalidé à chaque
            # écriture (audit des lots 11-12, I4) — la charge n'est plus presque uniquement en lecture
            m.appel(base, "POST /moi/notes", "/api/pulse/moi/notes", {"texte": "Note privée de test de charge (fictive)."}, entetes=h)
            m.appel(base, "GET /moi/donnees (après écriture)", "/api/pulse/moi/donnees", entetes=h)
            for ask in (asks or [])[:1]:
                attributs = {k: v for k, v in ask["minimums"].items()}
                st, _ = m.appel(base, "POST /asks/reponse", f"/api/pulse/moi/asks/{ask['id']}/reponse",
                                {"oui": True, "attributs": attributs}, entetes=h, accepter=(200, 404))
                if st == 200:
                    with m.verrou:
                        ouis.append((pid, ask["id"]))

        tc = threading.Thread(target=console, daemon=True)
        tc.start()
        t1 = time.perf_counter()
        with ThreadPoolExecutor(o.fils) as ex:
            list(ex.map(membre, list(sessions)))
        parallele_s = time.perf_counter() - t1
        fin.set()
        tc.join(timeout=5)

        # 3. cohérence : chaque « oui » accepté a son reçu, chez ce membre
        sans_recu = 0
        for pid, _ in ouis:
            _, d = m.appel(base, "GET /moi/donnees", "/api/pulse/moi/donnees", entetes={"X-Pulse-Session": sessions[pid]})
            sans_recu += not d["consentements"]
        res = {
            "membres_simules": membres_serveur, "comptes_actives": len(sessions), "fils": o.fils,
            "demarrage_s": round(demarrage_s, 1), "activation_s": round(activation_s, 1), "phase_parallele_s": round(parallele_s, 1),
            "ouis_acceptes": len(ouis), "ouis_sans_recu": sans_recu, "erreurs": dict(m.erreurs),
            "routes": {r: {"n": len(xs), "p50_ms": round(statistics.median(xs), 1), "p95_ms": round(_p(xs, 0.95), 1),
                           "max_ms": round(max(xs), 1)} for r, xs in sorted(m.t.items())},
            "machine": f"{platform.system()} {platform.machine()}, Python {platform.python_version()}, {os.cpu_count()} cœurs",
            "date": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "etat_initial_capacites": len(etat or []),
        }
        # 4. budgets (docs/annee-1/qualite/budgets.json) : le pire p95 de chaque famille de routes
        budgets = json.loads((RACINE.parent / "docs/annee-1/qualite/budgets.json").read_text(encoding="utf-8"))["api_p95_ms"]
        familles = {"lecture_membre": lambda r: r.startswith("GET /moi/"), "reponse_demande": lambda r: r == "POST /asks/reponse",
                    "ecriture_membre": lambda r: r == "POST /moi/notes",
                    "console": lambda r: r.startswith("console ")}
        budget = budgets.get(str(o.n))
        res["budgets"] = None if budget is None else {
            f: {"p95_pire_ms": max((v["p95_ms"] for r, v in res["routes"].items() if test(r)), default=0.0),
                "budget_ms": budget[f]} for f, test in familles.items()}
        for b in (res["budgets"] or {}).values():
            b["respecte"] = b["p95_pire_ms"] <= b["budget_ms"]
    finally:
        srv.terminate()
        srv.wait(timeout=10)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    if o.json:
        Path(o.json).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    budgets_ok = all(b["respecte"] for b in (res["budgets"] or {}).values())
    return 0 if not res["erreurs"] and not res["ouis_sans_recu"] and res["comptes_actives"] == membres_serveur and budgets_ok else 1


if __name__ == "__main__":
    sys.exit(main())
