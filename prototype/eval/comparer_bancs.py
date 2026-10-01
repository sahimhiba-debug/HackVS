"""Comparaison des fournisseurs sur le banc `comprendre_action` — des COMPTES, jamais un score composé ni un classement.

    python -m eval.comparer_bancs                          # lit eval/resultats_banc/*.json → eval/resultats_banc/comparaison.md
    python -m eval.comparer_bancs --dossier var/banc_dry_run   # même chose sur le dry-run

Refuse de comparer des résultats obtenus sur des cas différents (empreinte SHA-256 des cas) : une comparaison n'a de
sens que sur EXACTEMENT les mêmes 26 cas, le même prompt et la même validation."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

PROTO = Path(__file__).resolve().parents[1]
DOSSIER = PROTO / "eval" / "resultats_banc"


def charger(dossier: Path) -> list[dict]:
    res = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(dossier.glob("*.json"))]
    return [r for r in res if "contexte" in r and "cas" in r]


def _ms(s: Optional[dict], k: str) -> str:
    return f"{round(s[k])} ms" if s else "—"


def _cellule(x: dict) -> str:
    if not x["repondu"]:
        return f"indisponible ({x.get('erreur_fournisseur') or x['statut']})"
    if not x["validation_metier"]:
        return f"rejeté : {x.get('cause_rejet') or '?'}"
    return "✓ juste" if x["modele_juste"] else f"accepté FAUX : {x['raison_modele']}"


def comparer(resultats: list[dict]) -> str:
    if not resultats:
        return "# Comparaison des fournisseurs\n\nAucun résultat à comparer.\n"
    empreintes = {r["contexte"]["cas_sha256"] for r in resultats}
    prompts = {r["contexte"]["prompt"] for r in resultats}
    if len(empreintes) > 1 or len(prompts) > 1:
        raise SystemExit(f"REFUS : résultats obtenus sur des cas ou des prompts différents ({sorted(empreintes)}, {sorted(prompts)})")
    n = resultats[0]["totaux"]["cas"]
    lignes = ["# Comparaison des fournisseurs — banc `comprendre_action`", "",
              f"> Mêmes {n} cas (SHA-256 `{next(iter(empreintes))[:16]}…`), même prompt `{next(iter(prompts))}`, même validation du",
              "> produit. Des COMPTES par fournisseur ; aucun score composé, aucun classement. Une seule exécution par fournisseur :",
              "> les sorties d'un modèle varient d'un appel à l'autre (observé pour Apertus le 01.10) — voir les limites du banc.", "",
              "| Fournisseur | Modèle | Date (UTC) | Acceptées | Rejetées | Indisponibles | JSON lisible | Schéma respecté |"
              " Validation métier | Acceptées et justes | Acceptées mais FAUSSES | Replis | Contrainte serveur refusée | p50 | p95 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in resultats:
        c, t = r["contexte"], r["totaux"]
        lat = t.get("latence_ms")
        lignes.append(f"| {c.get('fournisseur')} | `{c.get('modele')}` | {c['debut_utc']} | {t['acceptees']}/{n} | {t['rejetees']} |"
                      f" {t['indisponibles']} | {t.get('json_valides', '—')}/{n} | {t.get('schema_valides', '—')}/{n} | {t['acceptees']}/{n} |"
                      f" {t['modele_justes']}/{n} | {t.get('acceptees_fausses', '—')} | {t.get('replis', '—')} |"
                      f" {t.get('sans_contrainte_serveur', '—')} | {_ms(lat, 'mediane')} | {_ms(lat, 'p95')} |")
    q = [("Sorties acceptées par la validation du produit", "acceptees"),
         ("« Hallucinations » métier : acceptées par la validation mais FAUSSES (rôle, jour, heure… inventés)", "acceptees_fausses"),
         ("Sorties conformes au schéma JSON de la tâche", "schema_valides"),
         ("Replis déterministes (rejet ou panne)", "replis")]
    lignes += ["", "## Les questions, en chiffres (lire chaque ligne pour elle-même)", ""]
    for titre, k in q:
        lignes.append(f"- {titre} : " + " · ".join(f"{r['contexte'].get('fournisseur')} {r['totaux'].get(k, '—')}" for r in resultats))
    lignes.append("- Latence médiane / p95 d'une complétion : " + " · ".join(
        f"{r['contexte'].get('fournisseur')} {_ms(r['totaux'].get('latence_ms'), 'mediane')} / {_ms(r['totaux'].get('latence_ms'), 'p95')}"
        for r in resultats))
    lignes += ["", "Plafond atteignable par TOUT modèle : 21/26 — c13 à c17 attendent une abstention, que le schéma du produit",
               "(au moins une exigence) rend impossible (voir docs/BANC_MULTI_FOURNISSEURS.md, limites).", "",
               "## Cas par cas", "",
               "| Cas | Attendu (rôles · jour · heures) | " + " | ".join(r["contexte"].get("fournisseur") or "?" for r in resultats) + " | Latences |",
               "|---|---|" + "---|" * len(resultats) + "---|"]
    par_id = [{x["id"]: x for x in r["cas"]} for r in resultats]
    for x0 in resultats[0]["cas"]:
        a = x0.get("attendu") or {}
        attendu = f"{' ou '.join('+'.join(sorted(s)) or '∅' for s in a.get('roles', []))} · {a.get('jour')} · {a.get('heures')}"
        cellules = [_cellule(p[x0["id"]]) if x0["id"] in p else "—" for p in par_id]
        lat = " / ".join(f"{p[x0['id']]['latence_ms']}" if x0["id"] in p and p[x0["id"]]["latence_ms"] is not None else "—" for p in par_id)
        lignes.append(f"| {x0['id']} | {attendu} | " + " | ".join(c.replace("|", "/") for c in cellules) + f" | {lat} |")
    lignes += ["", "Sorties brutes de chaque modèle : `<fournisseur>.json` dans le même dossier.", ""]
    return "\n".join(lignes)


if __name__ == "__main__":
    dossier = Path(sys.argv[sys.argv.index("--dossier") + 1]) if "--dossier" in sys.argv else DOSSIER
    texte = comparer(charger(dossier))
    (dossier / "comparaison.md").write_text(texte, encoding="utf-8")
    print(texte)
