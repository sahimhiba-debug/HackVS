"""Banc MÉTIER de la tâche IA réellement utilisée par Club Pulse : `comprendre_action` (« Agir à plusieurs → Comprendre
ma demande »). Mesure le modèle, pas une démonstration.

    python -m eval.banc_comprendre_action                 # exige APERTUS_* ; écrit eval/resultats_comprendre_action.md (+ .json)
    python -m eval.banc_comprendre_action --sortie X.md

Protocole (fixé AVANT toute exécution d'Apertus) :
- cas FICTIFS et attentes : `eval/cas_comprendre_action.json` (empreinte SHA-256 publiée avec les résultats) ;
- chaque cas = UN appel par le chemin du PRODUIT : `Intelligence.comprendre_action` avec le fournisseur `Apertus` du
  produit (même prompt versionné, même schéma strict, même validation, même budget de temps) ; une Intelligence neuve
  par cas (ni disjoncteur ni rejeu) ; la sortie BRUTE du modèle est enregistrée ;
- trois verdicts par cas :
  * « modèle juste » : la sortie du modèle est ACCEPTÉE par la validation du produit ET conforme aux attentes ;
  * « produit juste » : ce que le membre voit finalement (sortie du modèle, ou repli déterministe si elle est rejetée)
    est conforme — c'est la garantie que la validation + le repli apportent ;
  * « règles seules » (référence) : la forme déterministe actuelle, sans modèle ;
- conformité : rôles = EXACTEMENT l'un des ensembles acceptables (une exigence inventée est une erreur) ; jour et heures
  attendus, ou null quand le texte ne dit rien (rien ne doit être inventé) ; livrable et durée quand le cas l'exige ;
- un appel en panne, hors délai ou rejeté n'est JAMAIS compté comme « modèle juste ».
Limite connue, dite dans le rapport : le schéma du produit impose au moins une exigence ; pour les cas où il faut
s'abstenir, le modèle ne PEUT pas être juste — seul le repli peut l'être."""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

PROTO = Path(__file__).resolve().parents[1]
if str(PROTO) not in sys.path:
    sys.path.insert(0, str(PROTO))

from app.taxonomy import charger_taxonomie  # noqa: E402
from intelligence.ia import Apertus, Intelligence, prompt  # noqa: E402

CAS = PROTO / "eval" / "cas_comprendre_action.json"
SORTIE = PROTO / "eval" / "resultats_comprendre_action.md"
VARIABLES = ("APERTUS_BASE_URL", "APERTUS_API_KEY", "APERTUS_MODEL")


def charger() -> tuple[list[dict], date, str]:
    brut = CAS.read_bytes()
    d = json.loads(brut)
    return d["cas"], date.fromisoformat(d["jour_du_banc"]), hashlib.sha256(brut).hexdigest()


def conforme(sortie: dict, cas: dict) -> tuple[bool, str]:
    """(juste ?, raison) — la sortie telle que le membre la verrait."""
    exig = sortie.get("exigences") or []
    roles = sorted(x.get("role") for x in exig)
    acceptables = [sorted(r) for r in cas["roles"]]
    if roles not in acceptables:
        return False, f"rôles {roles or '∅'} au lieu de " + " ou ".join(str(a or "∅") for a in acceptables)
    f = sortie.get("fenetre") or {}
    if cas["jour"] != "*" and f.get("jour") != cas["jour"]:
        return False, f"jour {f.get('jour')} au lieu de {cas['jour']}"
    if cas["heures"] != "*":
        attendu = (None, None) if cas["heures"] is None else tuple(cas["heures"])
        if (f.get("debut"), f.get("fin")) != attendu:
            return False, f"heures {f.get('debut')}–{f.get('fin')} au lieu de {attendu[0]}–{attendu[1]}"
    if cas.get("livrable") and not any(x.get("livrable") for x in exig):
        return False, "livrable attendu absent"
    if cas.get("duree") and any(x.get("duree_min") != cas["duree"] for x in exig):
        return False, f"durée {[x.get('duree_min') for x in exig]} au lieu de {cas['duree']}"
    if not exig and not sortie.get("manquant"):
        return False, "aucune exigence et aucune question posée"
    return True, ""


class Enregistreur:
    """Enveloppe du fournisseur, côté banc : garde la sortie BRUTE et la durée de chaque complétion (le produit n'en sait rien)."""

    def __init__(self, f: Any):
        self.f, self.nom, self.modele = f, f.nom, f.modele
        self.brut: Optional[str] = None
        self.ms: Optional[float] = None
        self.erreur: Optional[str] = None

    def completer(self, systeme_txt: str, message: str, schema: Optional[dict]) -> str:
        t = time.perf_counter()
        try:
            self.brut = self.f.completer(systeme_txt, message, schema)
            return self.brut
        except Exception as e:
            self.erreur = type(e).__name__ + (f" ({getattr(e, 'cause', '')})" if getattr(e, "cause", "") else "")
            raise
        finally:
            self.ms = round((time.perf_counter() - t) * 1000, 1)


def stats(v: list[float]) -> Optional[dict]:
    if not v:
        return None
    s = sorted(v)
    return {"n": len(s), "mediane": round(statistics.median(s), 1), "p95": round(s[max(1, -(-95 * len(s) // 100)) - 1], 1),
            "min": round(s[0], 1), "max": round(s[-1], 1)}


def executer(fabrique: Any = None) -> dict:
    """`fabrique()` → un fournisseur neuf par cas (défaut : l'Apertus du produit, depuis l'environnement)."""
    tax = charger_taxonomie()
    cas, jour, empreinte = charger()
    fabrique = fabrique or Apertus
    lignes = []
    debut = datetime.now(timezone.utc)
    for c in cas:
        regles = Intelligence(tax, None).comprendre_action(c["texte"], jour)
        enr = Enregistreur(fabrique())
        rep = Intelligence(tax, enr).comprendre_action(c["texte"], jour)
        accepte = not rep.appel.repli and rep.appel.statut in ("OK", "INCERTAIN")
        juste_produit, raison_produit = conforme(rep.sortie, c)
        juste_regles, raison_regles = conforme(regles.sortie, c)
        lignes.append({"id": c["id"], "categorie": c["categorie"], "texte": c["texte"], "statut": rep.appel.statut,
                       "cause_rejet": None if accepte else (rep.appel.erreur or enr.erreur),
                       "modele_juste": accepte and juste_produit, "raison_modele": raison_produit if accepte else "sortie non utilisée",
                       "produit_juste": juste_produit, "raison_produit": raison_produit,
                       "regles_justes": juste_regles, "raison_regles": raison_regles,
                       "latence_ms": enr.ms if enr.brut is not None else None,
                       "sortie_brute": (enr.brut or "")[:1500], "sortie_produit": {k: rep.sortie.get(k) for k in ("exigences", "fenetre", "manquant")}})
    fin = datetime.now(timezone.utc)
    n = len(lignes)
    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROTO, capture_output=True, text=True).stdout.strip()
    return {"contexte": {"debut_utc": debut.isoformat(timespec="seconds"), "fin_utc": fin.isoformat(timespec="seconds"),
                         "commit": git or "inconnu", "cas_sha256": empreinte, "jour_du_banc": jour.isoformat(),
                         "endpoint": (os.environ.get("APERTUS_BASE_URL") or "").rstrip("/") + "/chat/completions",
                         "modele": os.environ.get("APERTUS_MODEL"), "budget_s": os.environ.get("APERTUS_BUDGET_S", "12"),
                         "prompt": prompt("comprendre_action")[1]},
            "totaux": {"cas": n, "acceptees": sum(x["statut"] in ("OK", "INCERTAIN") and x["cause_rejet"] is None for x in lignes),
                       "rejetees": sum(x["statut"] == "REJETE" for x in lignes),
                       "indisponibles": sum(x["statut"] == "INDISPONIBLE" for x in lignes),
                       "modele_justes": sum(x["modele_juste"] for x in lignes), "produit_justes": sum(x["produit_juste"] for x in lignes),
                       "regles_justes": sum(x["regles_justes"] for x in lignes),
                       "latence_ms": stats([x["latence_ms"] for x in lignes if x["latence_ms"] is not None])},
            "cas": lignes}


def rapport(r: dict) -> str:
    c, t = r["contexte"], r["totaux"]
    n = t["cas"]
    pct = lambda k: f"{t[k]}/{n} ({round(100 * t[k] / n)} %)"  # noqa: E731
    cats: dict[str, list] = {}
    for x in r["cas"]:
        cats.setdefault(x["categorie"], []).append(x)
    lat = t["latence_ms"]
    out = [
        "# Banc métier — `comprendre_action` (Apertus, chemin du produit)", "",
        "> Produit par `python -m eval.banc_comprendre_action`. Cas FICTIFS ; attentes fixées avant exécution",
        f"> (`eval/cas_comprendre_action.json`, SHA-256 `{c['cas_sha256'][:16]}…`). Mesure le MODÈLE sur UNE tâche du produit ;",
        "> ne démontre pas une qualité générale. La démonstration de scène tourne sans modèle.", "",
        f"- Période : {c['debut_utc']} → {c['fin_utc']} (UTC) ; commit `{c['commit']}` ; jour simulé {c['jour_du_banc']}",
        f"- Endpoint `{c['endpoint']}` ; modèle `{c['modele']}` ; prompt `{c['prompt']}` ; budget {c['budget_s']} s par appel ; 1 appel par cas", "",
        "## Résultats", "",
        "| | réussis |", "|---|---|",
        f"| **Modèle juste** (sortie acceptée par la validation ET conforme) | **{pct('modele_justes')}** |",
        f"| Produit juste (ce que voit le membre : modèle, ou repli si rejeté) | {pct('produit_justes')} |",
        f"| Référence : règles seules, sans modèle | {pct('regles_justes')} |", "",
        f"Sorties du modèle : {t['acceptees']} acceptées, {t['rejetees']} rejetées par la validation, {t['indisponibles']} indisponibles"
        " (délai, erreur). Échecs du modèle : " + str(n - t["modele_justes"]) + ".", "",
        "Latence d'une complétion (appels ayant répondu) : " + (f"n = {lat['n']}, médiane {lat['mediane']} ms, p95 {lat['p95']} ms,"
                                                               f" min {lat['min']} ms, max {lat['max']} ms." if lat else "aucune."),
        "Mesure séquentielle, un appel par cas, depuis l'environnement de développement (voir aussi `make latence-ia`).", "",
        "## Par catégorie", "", "| Catégorie | cas | modèle juste | produit juste | règles seules |", "|---|---|---|---|---|"]
    for k, v in cats.items():
        out.append(f"| {k} | {len(v)} | {sum(x['modele_juste'] for x in v)} | {sum(x['produit_juste'] for x in v)} | {sum(x['regles_justes'] for x in v)} |")
    out += ["", "Limite de conception : le schéma impose au moins une exigence. Pour « ne pas inventer » et « hors périmètre », "
            "le modèle ne peut donc jamais y être juste ; ces cas mesurent ce que la validation et le repli rattrapent.", "",
            "## Cas par cas", "", "| Cas | Catégorie | Statut | Modèle | Pourquoi | Produit | Latence (ms) |", "|---|---|---|---|---|---|---|"]
    for x in r["cas"]:
        pourquoi = x["raison_modele"] if x["cause_rejet"] is None else f"rejeté : {x['cause_rejet']}"
        out.append(f"| {x['id']} | {x['categorie']} | {x['statut']} | {'✓' if x['modele_juste'] else '✗'} | {pourquoi or '—'} |"
                   f" {'✓' if x['produit_juste'] else '✗ ' + x['raison_produit']} | {x['latence_ms'] if x['latence_ms'] is not None else '—'} |")
    out += ["", "Sorties BRUTES du modèle, cas par cas : `eval/resultats_comprendre_action.json`.", ""]
    return "\n".join(out)


if __name__ == "__main__":
    sortie = Path(sys.argv[sys.argv.index("--sortie") + 1]) if "--sortie" in sys.argv else SORTIE
    manque = [k for k in VARIABLES if not os.environ.get(k)]
    if manque:
        print("NON EXÉCUTÉ : " + ", ".join(manque) + " absente(s). Rien n'est appelé, rien n'est écrit.")
        sys.exit(2)
    res = executer()
    texte = rapport(res)
    cle = os.environ["APERTUS_API_KEY"]
    if cle in texte or cle in json.dumps(res):
        print("ARRÊT : la clé apparaîtrait dans le rapport. Rien n'est écrit.")
        sys.exit(3)
    sortie.write_text(texte, encoding="utf-8")
    sortie.with_suffix(".json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(texte)
