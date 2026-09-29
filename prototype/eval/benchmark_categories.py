"""Benchmark du matching PAR CATÉGORIE — moteur contre référence « mots-clés + mêmes filtres », cas par cas.

Partie 1 (classement, tous les jeux de cas écrits AVANT exécution ; aucun réglage sur les jeux réservés) :
un cas est RÉUSSI si le résultat est juste (succès@3 ou abstention attendue), sans violation, abstention correcte.
- WIN : moteur réussi, référence non ; LOSS : l'inverse ; TIE_OK / TIE_KO : les deux réussis / les deux ratés ;
- ABSTAIN : cas où l'abstention est la bonne réponse (compté à part : moteur juste ?) ;
- ADVERSARIAL : jeu adversarial (compté à part).
Partie 2 (comportements, vérifiés par des tests EXÉCUTÉS ici) : démarrage à froid, saturation, contradiction,
échec de réciprocité.

    python -m eval.benchmark_categories [--sortie eval/resultats_benchmark_categories.md]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from collections import Counter
from pathlib import Path

from eval.run_eval import JEUX, evaluer

RACINE = Path(__file__).resolve().parent.parent

COMPORTEMENTS = {
    "COLD START (nouveau membre)": "tests/test_explications.py::test_nouveau_membre_invisible_par_defaut_puis_visible_s_il_le_choisit",
    "SATURATION (membre sur-sollicité)": "tests/test_humain.py::test_budget_d_attention_un_membre_ne_recoit_pas_huit_relances_le_meme_jour",
    "CONTRADICTION (historique)": "tests/test_adversarial_reseau.py::test_un_refus_ancien_n_ecrase_pas_une_relation_devenue_vivante",
    "RECIPROCITY FAILURE (dite, pas inventée)": "tests/test_explications.py::test_nouveau_membre_reciprocite_prouvee_et_non_prouvee",
    "COHÉRENCE explication = décision": "tests/test_explications.py::test_coherence_decision_explication_sur_tous_les_membres",
}


def reussi(r: dict) -> bool:
    return r["abstention_ok"] and not r["violation"] and r["succes"] is not False


def classer(detail: list[dict]) -> Counter:
    c: Counter = Counter()
    for ligne in detail:
        m, ref = reussi(ligne["moteur"]), reussi(ligne["reference"])
        if ligne["moteur"]["succes"] is None:           # abstention attendue
            c["ABSTAIN_moteur_juste" if m else "ABSTAIN_moteur_faux"] += 1
        c["WIN" if m and not ref else "LOSS" if ref and not m else "TIE_OK" if m else "TIE_KO"] += 1
    return c


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    lignes = ["# Benchmark du matching par catégorie (données FICTIVES, cas écrits avant exécution)", "",
              "Moteur contre référence « mots-clés + mêmes filtres ». Réussi = bon résultat dans le top 3 (ou abstention "
              "attendue), sans violation de contrainte.", "",
              "| Jeu | Cas | WIN | LOSS | TIE (2 justes) | TIE (2 faux) | Abstentions attendues : moteur juste |",
              "|---|---|---|---|---|---|---|"]
    total: Counter = Counter()
    pertes = []
    for jeu in JEUX:
        r = evaluer(jeu=jeu)
        c = classer(r["detail"])
        total += c
        n_abs = c["ABSTAIN_moteur_juste"] + c["ABSTAIN_moteur_faux"]
        lignes.append(f"| {jeu}{' (ADVERSARIAL)' if jeu == 'adversarial' else ''} | {r['nb_cas']} | {c['WIN']} | {c['LOSS']} | "
                      f"{c['TIE_OK']} | {c['TIE_KO']} | {c['ABSTAIN_moteur_juste']}/{n_abs} |")
        pertes += [f"{jeu} / {x['id']} ({x['categorie']})" for x in r["detail"]
                   if not reussi(x["moteur"])]
    n_abs = total["ABSTAIN_moteur_juste"] + total["ABSTAIN_moteur_faux"]
    lignes.append(f"| **total** | {sum(total[k] for k in ('WIN', 'LOSS', 'TIE_OK', 'TIE_KO'))} | {total['WIN']} | {total['LOSS']} | "
                  f"{total['TIE_OK']} | {total['TIE_KO']} | {total['ABSTAIN_moteur_juste']}/{n_abs} |")
    lignes += ["", f"Cas où le moteur échoue ({len(pertes)}) :"] + [f"- {p}" for p in pertes] + ["",
               "## Comportements (tests exécutés maintenant)", "", "| Catégorie | Test | Résultat |", "|---|---|---|"]
    for nom, test in COMPORTEMENTS.items():
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", test], cwd=RACINE, capture_output=True, text=True)
        lignes.append(f"| {nom} | `{test.split('::')[1]}` | {'PASS' if p.returncode == 0 else 'FAIL'} |")
    texte = "\n".join(lignes) + "\n"
    print(texte)
    if a.sortie:
        Path(a.sortie).write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
