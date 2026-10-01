"""LATENCE RÉELLE d'Apertus, mesurée (pas estimée) — preuve technique SÉPARÉE de la démonstration.

    python scripts/mesurer_latence_apertus.py              # n = 30 par profil ; écrit docs/audit/latence_apertus.md (+ .json)
    python scripts/mesurer_latence_apertus.py --n 50
    python scripts/mesurer_latence_apertus.py --sortie X.md

Configuration (environnement uniquement) : APERTUS_API_KEY (lue, jamais écrite), APERTUS_BASE_URL, APERTUS_MODEL,
APERTUS_DELAI_S (délai du produit, défaut 30 s). Sans l'une des trois premières : rien n'est appelé, rien n'est écrit,
code de sortie 2.

Ce qui est mesuré, appels SÉQUENTIELS (un à la fois), sans aucune nouvelle tentative (une erreur reste une erreur) :
- profil « tâche du produit » : `Intelligence.comprendre_action` avec le fournisseur `Apertus` du produit — même prompt
  versionné, même schéma strict, mêmes `temperature` 0 et `max_tokens` 900, même délai — sur 5 formulations FICTIVES
  tournantes. Pour chaque appel : durée HTTP (envoi → réponse complète) et durée de bout en bout (préparation,
  appel, validation de la sortie par le produit), statut HTTP, issue du produit (sortie ACCEPTÉE ou REJETÉE → repli
  déterministe), jetons produits si l'API les rapporte ;
- profil « court » : la requête json_schema de la sonde (une ligne en entrée, une ligne en sortie) — ordre de grandeur
  du temps fixe d'un aller-retour.
Un appel d'échauffement par profil est fait et consigné, mais exclu des statistiques. Statistiques sur les appels
RÉUSSIS (HTTP 200) : moyenne, médiane, p95 (rang le plus proche), min, max ; erreurs et délais dépassés comptés à part.
Ce qui n'est PAS mesuré : la démonstration (elle tourne sans modèle, en forme déterministe), la qualité des sorties,
la charge concurrente, un vrai téléphone ni le Wi-Fi de la salle."""
from __future__ import annotations

import json
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

PROTO = Path(__file__).resolve().parents[1]
RACINE = PROTO.parent
sys.path.insert(0, str(PROTO))
SORTIE = RACINE / "docs" / "audit" / "latence_apertus.md"
JOUR = date(2026, 10, 6)                                         # date simulée de la démonstration (fictive)
TEXTES = [                                                       # formulations FICTIVES, aucune donnée réelle
    "Présenter nos tisanes en allemand jeudi après-midi à des visiteurs germanophones, il faut un stand et quelqu'un qui parle allemand.",
    "Faire goûter notre nouveau sirop à une dizaine de personnes samedi matin, on cherche un lieu avec une table.",
    "Tester notre étiquette de vin auprès de trois inconnus vendredi entre 14h et 16h.",
    "Montrer notre fromage à des restaurateurs mercredi soir, il faudrait une cuisine et une personne qui sait cuisiner.",
    "Prendre des photos de nos produits pour le site lundi, il manque un photographe et un fond neutre.",
]
VARIABLES = ("APERTUS_BASE_URL", "APERTUS_API_KEY", "APERTUS_MODEL")


def stats(valeurs: list[float]) -> Optional[dict]:
    if not valeurs:
        return None
    s = sorted(valeurs)
    rang = max(1, -(-95 * len(s) // 100))                        # p95 au rang le plus proche : ceil(0,95 n)
    return {"n": len(s), "moyenne": round(statistics.fmean(s), 1), "mediane": round(statistics.median(s), 1),
            "p95": round(s[rang - 1], 1), "min": round(s[0], 1), "max": round(s[-1], 1)}


class Chrono:
    """Client HTTP du produit, chronométré : chaque POST est mesuré et consigné (statut, durée, jetons) — jamais
    l'en-tête d'autorisation ni le contenu."""

    def __init__(self, client: Any):
        self.client = client
        self.mesures: list[dict] = []

    def post(self, url: str, **kw: Any) -> Any:
        t = time.perf_counter()
        try:
            r = self.client.post(url, **kw)
        except Exception as e:
            self.mesures.append({"http_ms": round((time.perf_counter() - t) * 1000, 1), "statut": None,
                                 "erreur": type(e).__name__})
            raise
        m: dict = {"http_ms": round((time.perf_counter() - t) * 1000, 1), "statut": r.status_code}
        if r.status_code == 200:
            try:
                u = r.json().get("usage") or {}
                m["jetons_sortie"], m["jetons_entree"] = u.get("completion_tokens"), u.get("prompt_tokens")
            except ValueError:
                pass
        else:
            m["erreur"] = f"HTTP {r.status_code}"
        self.mesures.append(m)
        return r


def mesurer(n: int = 30, env: Optional[dict] = None, http: Any = None) -> dict:
    e = dict(os.environ if env is None else env)
    manque = [k for k in VARIABLES if not e.get(k)]
    if manque:
        raise SystemExit(2)
    from app.taxonomy import charger_taxonomie
    from intelligence import ia
    if http is None:
        import httpx
        http = httpx.Client(timeout=httpx.Timeout(float(e.get("APERTUS_DELAI_S", "30")), connect=10.0))
    chrono = Chrono(http)
    tax = charger_taxonomie()
    anciens = {k: os.environ.get(k) for k in (*VARIABLES, "APERTUS_DELAI_S")}
    os.environ.update({k: e[k] for k in (*VARIABLES, "APERTUS_DELAI_S") if e.get(k)})
    try:
        class UneTentative(ia.Apertus):
            TENTATIVES = 1                                       # aucune nouvelle tentative : on mesure, on ne masque pas

        def tache(i: int) -> dict:
            avant = len(chrono.mesures)
            t = time.perf_counter()
            # une Intelligence NEUVE par appel : ni disjoncteur ni rejeu ne peuvent court-circuiter la mesure
            rep = ia.Intelligence(tax, UneTentative(http=chrono)).comprendre_action(TEXTES[i % len(TEXTES)], JOUR)
            m = chrono.mesures[avant] if len(chrono.mesures) > avant else {"http_ms": None, "statut": None, "erreur": "aucun appel HTTP"}
            return {**m, "bout_en_bout_ms": round((time.perf_counter() - t) * 1000, 1), "issue": rep.appel.statut,
                    "repli": rep.appel.repli, "cause": rep.appel.erreur, "texte": i % len(TEXTES),
                    "appels_http": len(chrono.mesures) - avant}

        def court() -> dict:
            corps = {"model": e["APERTUS_MODEL"], "temperature": 0, "max_tokens": 60,
                     "messages": [{"role": "user", "content": "Dans quel canton se trouve Sion ?"}],
                     "response_format": {"type": "json_schema", "json_schema": {"name": "reponse", "strict": True, "schema": {
                         "type": "object", "additionalProperties": False, "required": ["canton"],
                         "properties": {"canton": {"type": "string", "enum": ["VS", "VD", "GE"]}}}}}}
            try:
                chrono.post(e["APERTUS_BASE_URL"].rstrip("/") + "/chat/completions", json=corps,
                            headers={"Authorization": f"Bearer {e['APERTUS_API_KEY']}", "Content-Type": "application/json"})
            except Exception:
                pass
            return dict(chrono.mesures[-1])

        debut = datetime.now(timezone.utc)
        brut = {"tache": [tache(i) for i in range(n + 1)], "court": [court() for _ in range(n + 1)]}
        fin = datetime.now(timezone.utc)
    finally:
        for k, v in anciens.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def resume(lignes: list[dict]) -> dict:
        mesurees = lignes[1:]                                    # l'échauffement est exclu
        ok = [x for x in mesurees if x.get("statut") == 200]
        r = {"appels": len(mesurees), "reussis": len(ok), "erreurs_http": sum(1 for x in mesurees if x.get("statut") not in (200, None)),
             "delais_ou_reseau": sum(1 for x in mesurees if x.get("statut") is None),
             "causes": sorted({str(x.get("erreur")) for x in mesurees if x.get("erreur")}),
             "http_ms": stats([x["http_ms"] for x in ok]), "echauffement_ms": lignes[0].get("http_ms")}
        jetons = [x["jetons_sortie"] for x in ok if isinstance(x.get("jetons_sortie"), int)]
        r["jetons_sortie"] = stats([float(j) for j in jetons])
        if "bout_en_bout_ms" in lignes[0]:
            r["bout_en_bout_ms"] = stats([x["bout_en_bout_ms"] for x in ok])
            r["acceptees"] = sum(1 for x in ok if not x.get("repli"))
            r["rejetees"] = sum(1 for x in ok if x.get("repli"))
            r["causes_rejet"] = sorted({str(x.get("cause")) for x in ok if x.get("repli") and x.get("cause")})
        return r

    def git() -> str:
        try:
            return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RACINE, capture_output=True, text=True).stdout.strip()
        except OSError:
            return "inconnu"

    return {"contexte": {
        "debut_utc": debut.isoformat(timespec="seconds"), "fin_utc": fin.isoformat(timespec="seconds"),
        "endpoint": e["APERTUS_BASE_URL"].rstrip("/") + "/chat/completions", "modele": e["APERTUS_MODEL"],
        "delai_s": float(e.get("APERTUS_DELAI_S", "30")), "appels_par_profil": n, "sequentiel": True, "nouvelles_tentatives": 0,
        "commit": git(), "python": platform.python_version(), "systeme": platform.platform(), "processeurs": os.cpu_count(),
        "charge": [round(x, 2) for x in os.getloadavg()],
        "reseau": "via le proxy HTTPS sortant de l'environnement" if e.get("HTTPS_PROXY") else "accès direct",
        "prompt": ia.prompt("comprendre_action")[1]},
        "tache": resume(brut["tache"]), "court": resume(brut["court"]), "brut": brut}


def rapport(r: dict) -> str:
    c = r["contexte"]

    def ligne(nom: str, s: Optional[dict]) -> str:
        return f"| {nom} | " + (" | ".join(str(s[k]) for k in ("n", "moyenne", "mediane", "p95", "min", "max")) if s else "— | — | — | — | — | —") + " |"

    t, k = r["tache"], r["court"]
    out = [
        "# Latence réelle d'Apertus — mesure technique (séparée de la démonstration)", "",
        "> Produit par `make latence-ia` (`prototype/scripts/mesurer_latence_apertus.py`). La démonstration n'appelle AUCUN",
        "> modèle : elle tourne en forme déterministe. Cette mesure ne dit rien de la qualité des sorties.", "",
        "## Contexte exact", "",
        f"- Période : {c['debut_utc']} → {c['fin_utc']} (UTC) ; commit `{c['commit']}`",
        f"- Endpoint : `{c['endpoint']}`" + (" (API d'inférence CSCS, compatible OpenAI)" if "cscs.ch" in c["endpoint"] else "")
        + f" ; modèle `{c['modele']}`",
        f"- {c['appels_par_profil']} appels mesurés par profil + 1 échauffement exclu ; séquentiels ; aucune nouvelle tentative ;"
        f" délai {c['delai_s']} s (celui du produit)",
        f"- Client : Python {c['python']}, {c['systeme']}, {c['processeurs']} processeurs, charge {c['charge']} ; réseau {c['reseau']}",
        f"- Profil « tâche du produit » : `comprendre_action` (prompt `{c['prompt']}`, schéma strict, `max_tokens` 900), 5 formulations fictives",
        "- Profil « court » : une question d'une ligne, sortie json_schema d'un champ (`max_tokens` 60)", "",
        "## Résultats (millisecondes, appels réussis seulement)", "",
        "| Mesure | n | moyenne | médiane | p95 | min | max |", "|---|---|---|---|---|---|---|",
        ligne("Tâche du produit — HTTP (envoi → réponse complète)", t["http_ms"]),
        ligne("Tâche du produit — bout en bout (dont validation)", t.get("bout_en_bout_ms")),
        ligne("Court — HTTP", k["http_ms"]), "",
        "## Erreurs et sorties", "",
        f"- Tâche du produit : {t['reussis']}/{t['appels']} réussis ; {t['erreurs_http']} erreur(s) HTTP ; {t['delais_ou_reseau']} délai(s) dépassé(s) ou"
        f" erreur(s) réseau{(' — ' + ', '.join(t['causes'])) if t['causes'] else ''}",
        f"- Sorties validées par le produit : {t.get('acceptees', 0)} acceptées, {t.get('rejetees', 0)} rejetées (→ repli déterministe)"
        + (f" — causes : {'; '.join(t['causes_rejet'])}" if t.get("causes_rejet") else ""),
        f"- Court : {k['reussis']}/{k['appels']} réussis ; {k['erreurs_http']} erreur(s) HTTP ; {k['delais_ou_reseau']} délai(s) ou erreur(s) réseau"
        f"{(' — ' + ', '.join(k['causes'])) if k['causes'] else ''}",
        "- Jetons produits par appel (tâche) : " + (f"médiane {t['jetons_sortie']['mediane']}, p95 {t['jetons_sortie']['p95']},"
                                                       f" max {t['jetons_sortie']['max']}" if t["jetons_sortie"] else "non rapportés par l'API"),
        f"- Échauffement (exclu) : tâche {t['echauffement_ms']} ms, court {k['echauffement_ms']} ms", "",
        "Mesures brutes, appel par appel : `docs/audit/latence_apertus.json` (statut, durées, jetons — ni clé ni contenu).", "",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 30
    sortie = Path(sys.argv[sys.argv.index("--sortie") + 1]) if "--sortie" in sys.argv else SORTIE
    if any(not os.environ.get(k) for k in VARIABLES):
        print("rien mesuré : " + ", ".join(k for k in VARIABLES if not os.environ.get(k)) + " absente(s). Aucun fichier écrit.")
        sys.exit(2)
    res = mesurer(n)
    texte = rapport(res)
    if os.environ["APERTUS_API_KEY"] in texte or os.environ["APERTUS_API_KEY"] in json.dumps(res):
        print("ARRÊT : la clé apparaîtrait dans le rapport. Aucun fichier écrit.")
        sys.exit(3)
    sortie.write_text(texte, encoding="utf-8")
    sortie.with_suffix(".json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(texte)
