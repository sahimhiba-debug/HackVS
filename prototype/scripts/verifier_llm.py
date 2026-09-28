"""Vérifie l'analyse par un LLM (Claude ou Apertus) contre l'API RÉELLE et mesure son comportement.

Prérequis (jamais commités) :
  Claude  : HACKVS_LLM=claude  + ANTHROPIC_API_KEY ; réseau vers api.anthropic.com
  Apertus : HACKVS_LLM=apertus + APERTUS_API_KEY + APERTUS_BASE_URL + APERTUS_MODEL ; réseau vers le fournisseur
Appels : 40 (jeux base + adversarial). Rien ne part sans --confirmer.

  python scripts/verifier_llm.py            # affiche l'estimation et ce qui manque
  python scripts/verifier_llm.py --confirmer

Produit : eval/resultats_base_claude.md, eval/resultats_adversarial_claude.md, eval/telemetrie_claude.json
Mesures : conformité des critères, succès@3 / violations / abstention (mêmes définitions que les règles),
latence (médiane, max), premier critère affiché, jetons, coût estimé, taux de repli, accord avec les règles.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

# Tarifs publics par million de jetons (entrée, sortie), à revérifier avant d'annoncer un coût.
TARIFS = {"claude-opus-5": (5.0, 25.0), "claude-sonnet-5": (2.0, 10.0), "claude-haiku-4-5": (1.0, 5.0)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirmer", action="store_true")
    a = ap.parse_args()
    os.environ.setdefault("HACKVS_LLM", "claude")
    f = os.environ["HACKVS_LLM"]
    modele = os.environ.get("HACKVS_CLAUDE_MODEL", "claude-opus-5") if f == "claude" else os.environ.get("APERTUS_MODEL", "?")
    manque = []
    if f == "claude":
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            manque.append("ANTHROPIC_API_KEY absente de l'environnement")
        try:
            import anthropic  # noqa: F401
        except ImportError:
            manque.append("paquet `anthropic` non installé (pip install -r requirements.txt)")
    else:
        manque += [f"{k} absente de l'environnement" for k in ("APERTUS_API_KEY", "APERTUS_BASE_URL", "APERTUS_MODEL") if not os.environ.get(k)]
    from app.parser_llm import systeme
    from app.taxonomy import charger_taxonomie
    jetons_systeme = len(systeme(charger_taxonomie())) // 3.5
    prix_in, prix_out = TARIFS.get(modele, (5.0, 25.0))
    estimation = 40 * ((jetons_systeme + 60) * prix_in + 350 * prix_out) / 1e6
    print(f"Fournisseur : {f} · modèle : {modele} · 40 appels · ≈ {int(jetons_systeme)} jetons de consigne par appel")
    print(f"Coût estimé : ≈ {estimation:.2f} USD (tarifs Claude, à revérifier)" if f == "claude" else "Coût : selon le contrat du fournisseur (jetons mesurés)")
    if manque:
        print("Impossible de lancer :\n  - " + "\n  - ".join(manque))
        sys.exit(2)
    if not a.confirmer:
        print("Relancez avec --confirmer pour exécuter les appels.")
        return

    from eval.run_eval import en_markdown, evaluer
    tout = []
    for jeu in ("base", "adversarial"):
        res = evaluer(claude=True, jeu=jeu)
        (RACINE / "eval" / f"resultats_{jeu}_claude.md").write_text(en_markdown(res), encoding="utf-8")
        tout += res["telemetrie_claude"]
        print(jeu, json.dumps({k: res[k] for k in ("criteres_corrects", "moteur", "reference", "preuves_verifiees")}, ensure_ascii=False))
    ok = [t for t in tout if t.get("analyseur") == f]
    lat = [t["latence_ms"] for t in ok]
    ent = sum(t.get("tokens_entree") or 0 for t in ok)
    sor = sum(t.get("tokens_sortie") or 0 for t in ok)
    synthese = {
        "modele": modele, "appels": len(tout), "replis_sur_regles": len(tout) - len(ok),
        "latence_ms_mediane": statistics.median(lat) if lat else None, "latence_ms_max": max(lat) if lat else None,
        "premier_critere_ms_median": statistics.median([t["premier_critere_ms"] for t in ok if t.get("premier_critere_ms")] or [0]),
        "jetons_entree": ent, "jetons_sortie": sor,
        "cout_usd_estime": round((ent * prix_in + sor * prix_out) / 1e6, 4) if f == "claude" else None,
        "accord_avec_regles": f"{sum(t['accord_regles'] for t in tout)}/{len(tout)}",
    }
    (RACINE / "eval" / f"telemetrie_{f}.json").write_text(json.dumps({"synthese": synthese, "appels": tout}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(synthese, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
