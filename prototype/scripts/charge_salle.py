"""TEST DE CHARGE du mode salle : N téléphones simulés (80 par défaut) — scan, capacité + consentement, relectures,
réponse à la demande, un retrait — puis cohérence finale. Mesure p50 / p95 par route, les erreurs, et vérifie que
l'écran géant dit exactement ce que les téléphones ont fait.

    python scripts/charge_salle.py --local                                   # serveur local neuf (mesure de PREUVES.md)
    python scripts/charge_salle.py --url https://<domaine> --jeton <HACKVS_CONSOLE_JETON> --n 80   # serveur déployé

ATTENTION : purge la salle au début et à la fin. Aucun nom, aucune donnée personnelle : des passes et des capacités."""
import argparse
import json
import random
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CAPS = ["voiture", "salle", "allemand", "traiteur", "informatique", "materiel"]
PIECES = {"voiture", "salle", "allemand"}


class Client:
    def __init__(self, base: str, jeton: str):
        self.base, self.console = base.rstrip("/"), {"X-Pulse-Console": jeton}
        self.mesures: dict[str, list[float]] = defaultdict(list)
        self.erreurs: Counter = Counter()
        self._v = threading.Lock()

    def appel(self, nom: str, chemin: str, corps=None, entetes=None, attendu=(200,)):
        t = time.perf_counter()
        req = urllib.request.Request(self.base + chemin, method="GET" if corps is None else "POST",
                                     data=None if corps is None else json.dumps(corps).encode(),
                                     headers={"Content-Type": "application/json", **(entetes or {})})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                code, data = r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            code, data = e.code, {}
        except Exception as e:                                      # réseau : compté, jamais masqué
            code, data = type(e).__name__, {}
        with self._v:
            self.mesures[nom].append((time.perf_counter() - t) * 1000)
            if code not in attendu:
                self.erreurs[f"{nom} → {code}"] += 1
        return data


def telephone(c: Client, jeton: str, i: int, rng: random.Random) -> dict:
    passe = c.appel("entrer", "/api/pulse/salle/entrer", {"jeton": jeton}).get("passe")
    if not passe:
        return {"ok": False}
    h = {"X-Pulse-Salle": passe}
    cap = CAPS[i % len(CAPS)]
    c.appel("declarer", "/api/pulse/salle/declarer", {"capacite": cap, "consentement": True}, h)
    c.appel("moi", "/api/pulse/salle/moi", entetes=h)
    return {"ok": True, "h": h, "cap": cap, "choix": rng.choice(["oui", "oui", "oui", "non", "pas cette fois"])}


def mesurer(base: str, jeton: str, n: int, graine: int = 7) -> dict:
    c = Client(base, jeton)
    c.appel("purger", "/api/pulse/console/salle/purger", {}, c.console)
    jeton_salle = c.appel("ouvrir", "/api/pulse/console/salle/ouvrir", {}, c.console)["url"].split("#s=", 1)[1]
    debut = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n) as ex:
        tels = list(ex.map(lambda i: telephone(c, jeton_salle, i, random.Random(graine + i)), range(n)))
    c.appel("lancer", "/api/pulse/console/salle/lancer", {}, c.console)
    concernes = [t for t in tels if t["ok"] and t["cap"] in PIECES]

    def repondre(t):
        c.appel("moi", "/api/pulse/salle/moi", entetes=t["h"])
        c.appel("repondre", "/api/pulse/salle/repondre", {"choix": t["choix"]}, t["h"])
    with ThreadPoolExecutor(max_workers=n) as ex:
        list(ex.map(repondre, concernes))
    fournit = next((t for t in concernes if t["choix"] == "oui"), None)
    if fournit:
        c.appel("retirer", "/api/pulse/salle/retirer", {}, fournit["h"], attendu=(200, 409))   # 409 : il était en réserve
    duree = time.perf_counter() - debut
    e = c.appel("ecran", "/api/pulse/console/salle", entetes=c.console)
    oui = sum(t["choix"] == "oui" for t in concernes)

    def egal(montre, vrai: int) -> bool:
        """L'écran dit « < 3 » sous le seuil (k-anonymat) : c'est cohérent si le vrai nombre est entre 1 et 2."""
        return montre == vrai or (isinstance(montre, str) and montre.startswith("<") and 0 < vrai < int(montre[1:]))
    par_cap = Counter(t["cap"] for t in tels if t["ok"])
    rep = Counter(t["choix"] for t in concernes)
    verifs = {"participants": egal(e.get("participants"), n),
              "capacites": all(egal(x["n"], par_cap.get(x["id"], 0)) for x in e.get("capacites", [])),
              "reponses": all(egal(e.get("reponses", {}).get(k), rep.get(k, 0)) for k in ("oui", "non", "pas cette fois"))}
    attendu = {"participants": n, "capacites": dict(par_cap), "reponses": dict(rep)}
    obtenu = {"participants": e.get("participants"), "capacites": {x["id"]: x["n"] for x in e.get("capacites", [])},
              "reponses": e.get("reponses")}
    coherent = all(verifs.values()) and bool(e.get("demande", {}).get("fermee")) == all(
        any(t["cap"] == p and t["choix"] == "oui" for t in concernes) for p in PIECES)
    c.appel("purger", "/api/pulse/console/salle/purger", {}, c.console)
    vide = c.appel("ecran", "/api/pulse/console/salle", entetes=c.console).get("participants") == 0
    q = lambda xs, p: round(statistics.quantiles(xs, n=100)[p - 1], 1) if len(xs) >= 2 else round(xs[0], 1)  # noqa: E731
    return {"n": n, "duree_s": round(duree, 2), "requetes": sum(len(v) for v in c.mesures.values()),
            "par_route": {k: {"n": len(v), "p50_ms": q(v, 50), "p95_ms": q(v, 95)} for k, v in sorted(c.mesures.items())},
            "erreurs": dict(c.erreurs), "oui": oui, "attendu": attendu, "obtenu": obtenu, "coherent": coherent,
            "anneau_ferme": bool(e.get("demande", {}).get("fermee")), "purge_verifiee": vide}


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--url")
    a.add_argument("--jeton", default="1")
    a.add_argument("--n", type=int, default=80)
    a.add_argument("--local", action="store_true")
    x = a.parse_args()
    if x.local:
        from tests.test_e2e_scene import serveur
        with serveur(HACKVS_SALLE="1", HACKVS_SALLE_PLAFOND=str(max(80, x.n))) as base:
            r = mesurer(base, x.jeton, x.n) | {"cible": "serveur local (uvicorn, 1 processus, cette machine)"}
    else:
        r = mesurer(x.url, x.jeton, x.n) | {"cible": x.url}
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0 if r["coherent"] and not r["erreurs"] and r["purge_verifiee"] else 1


if __name__ == "__main__":
    sys.exit(main())
