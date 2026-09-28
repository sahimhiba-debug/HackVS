"""Certificat de décision : dérivé UNIQUEMENT des enregistrements structurés d'une exécution (aucun texte libre de LLM)."""
from __future__ import annotations

from .execution import ExecutionDecision


def certificat(run: ExecutionDecision) -> dict:
    retenue = run.retenue or {}
    verdicts = run.verdicts
    objections = [o for a in run.avis for o in a["objections"]]
    statuts = run.graphe.get("statuts_des_preuves_utilisees", {})
    return {
        "run_id": run.run_id, "cree_le": run.cree_le, "parent_id": run.parent_id, "intervention": run.intervention,
        "demande": run.demande,
        "compilation": {"decision": run.compilation.get("decision"), "reconnu": run.compilation.get("reconnu", []),
                        "non_reconnu": run.compilation.get("non_reconnu", []), "raison": run.compilation.get("raison", "")},
        "plan": {"etapes": [e.nom for e in run.etapes], "agents_llm": run.budget.appels_llm,
                 "appels_solveur": run.budget.appels_solveur, "strategie_contexte": run.strategie_contexte},
        "preuves": {"par_statut": statuts, "non_soutenues": next((len(v["details"]) for v in verdicts if v["niveau"] == "L3"), 0)},
        "contraintes": {"validees": sum(1 for v in verdicts if v["etat"] == "PASS"),
                        "echouees": [f"{v['niveau']} {v['nom']}" for v in verdicts if v["etat"] == "FAIL"],
                        "en_attente": [f"{v['niveau']} {v['nom']}" for v in verdicts if v["etat"] == "EN_ATTENTE"]},
        "optimisation": {"solveur": run.versions.get("solveur"), "statut": retenue.get("statut"),
                         "optimum_prouve": retenue.get("optimum_prouve"), "points_pareto": len(run.frontiere),
                         "objectifs": retenue.get("objectifs", {}), "rencontres": len(retenue.get("rencontres", []))},
        "critique": {"objections": len(objections), "materielles": sum(1 for o in objections if o["gravite"] == "materielle"),
                     "ouvertes": sum(1 for o in objections if o["ouverte"])},
        "gardien": next((a["position"] for a in run.avis if a["agent"] == "gardien"), None),
        "inconnus": [o["message"] for o in objections if o["code"] in ("preuves_non_verifiees", "non_servis")],
        "mediation": run.mediation, "humain": {"approbation": "REQUISE", "decision": run.decision_humaine},
        "rejouable": bool(run.spec), "empreinte_instantane": run.instantane_empreinte[:16],
        "empreinte_resultat": run.resultat_empreinte[:16],
        "duree_totale_ms": round(sum(e.duree_ms for e in run.etapes), 1),
    }
