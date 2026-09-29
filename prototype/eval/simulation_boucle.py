"""EXP-N — La boucle d'organisation jouée sur plusieurs mois (données GÉNÉRÉES, acceptation SIMULÉE).

Chaque mois : diagnostic → plan ÉQUILIBRE du front → décision enregistrée → chaque action est acceptée avec une
probabilité déclarée (tirage reproductible ; une action acceptée = INTRO_ACCEPTEE déclarée) → +30 jours.
Comparaison au même réseau sans action. Vérifie aussi que le bilan prévu/réalisé retrouve exactement les acceptations.

    python -m eval.simulation_boucle [--reseaux 5] [--mois 3] [--sortie eval/resultats_simulation_boucle.md]
"""
from __future__ import annotations

import argparse
import random
import statistics
from datetime import timedelta
from pathlib import Path

from adaptateurs.club import boucle
from adaptateurs.club import cycle as cy
from adaptateurs.club import diagnostic as dg
from adaptateurs.club.pareto import plus_grand_groupe_robuste
from adaptateurs.club.reseau import graphe_actuel
from app.taxonomy import charger_taxonomie
from eval.perf_echelle import generer
from plateforme.affirmations import Statut
from plateforme.memoire import Evt

TAX = charger_taxonomie()


def etat(m, t, membres) -> dict:
    g = graphe_actuel(m, t)
    g.add_nodes_from(membres)
    return {"relies": sum(1 for x in membres if g.degree(x) > 0), "robuste": plus_grand_groupe_robuste(g, membres)}


def jouer(graine: int, mois: int, taux: float | None) -> dict:
    """taux=None : aucune action (baseline)."""
    profils, m, t = generer(120, graine)
    membres = sorted(p.id for p in profils if p.type == "membre_club")
    rnd = random.Random(graine * 7 + int((taux or 0) * 100))
    acceptees = 0
    for _ in range(mois):
        if taux is not None:
            d = dg.diagnostic(m, profils, cy.besoins_publies(m, t), TAX, t, k=5)
            plans = {n: p for p in d["agir"]["plans_nommes"] for n in p["noms"]}
            plan = plans.get("EQUILIBRE")
            if plan and plan["paires"]:
                boucle.enregistrer(m, t, plan, "organisation (simulation)", membres)
                for a, b in plan["paires"]:
                    if rnd.random() < taux:
                        m.ajouter(Evt(type="INTRO_ACCEPTEE", le=t + timedelta(days=3), acteurs=[a, b], statut=Statut.DECLARE,
                                      donnees={"simulation": "acceptation tirée au sort", "graine": graine}))
                        acceptees += 1
        t = t + timedelta(days=30)
    fin = etat(m, t, membres)
    h = boucle.historique(m, t, membres)
    return fin | {"acceptees": acceptees, "realisees_selon_bilan": h["comptes"]["REALISEE"], "decisions": h["decisions"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reseaux", type=int, default=5)
    ap.add_argument("--mois", type=int, default=3)
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    lignes = ["# La boucle sur plusieurs mois — SYNTHETIC (acceptation SIMULÉE)", "",
              f"{a.reseaux} réseaux GÉNÉRÉS de 120 membres ; {a.mois} mois ; plan ÉQUILIBRE (5 actions) chaque mois.", "",
              "| Scénario | Membres reliés (fin) | Plus grand groupe robuste (fin) | Actions acceptées | Réalisées selon le bilan |",
              "|---|---|---|---|---|"]
    for nom, taux in (("SANS ACTION", None), ("BOUCLE, 30 % acceptées", 0.3), ("BOUCLE, 60 % acceptées", 0.6), ("BOUCLE, 100 % acceptées", 1.0)):
        runs = [jouer(1100 + s, a.mois, taux) for s in range(a.reseaux)]
        lignes.append(f"| {nom} | {statistics.mean(r['relies'] for r in runs):.1f} | {statistics.mean(r['robuste'] for r in runs):.1f} | "
                      f"{statistics.mean(r['acceptees'] for r in runs):.1f} | {statistics.mean(r['realisees_selon_bilan'] for r in runs):.1f} |")
    lignes += ["", "Le bilan prévu/réalisé doit retrouver EXACTEMENT les actions acceptées (contrôle d'intégrité de la boucle)."]
    texte = "\n".join(lignes) + "\n"
    print(texte)
    if a.sortie:
        Path(a.sortie).write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
