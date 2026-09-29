"""Boucle fermée : une décision d'organisation est enregistrée, puis confrontée aux FAITS (prévu contre réalisé).

1. `enregistrer` : le plan choisi par un humain (actions + projection, qui suppose 100 % d'acceptation) devient un fait
   DECISION_ORGANISATION de la mémoire.
2. `ecart` : on reconstruit le réseau actuel À LA DATE de la décision (journal rejouable), puis on regarde, action par
   action, ce qui s'est produit APRÈS : connexion réelle (faits déclarés/observés), refus, ou rien. Les objectifs sont
   recalculés avec les seules actions réalisées : c'est le « réalisé » à comparer au « prévu ».
3. `historique` : comptes cumulés sur toutes les décisions — pas de taux sous `n_min_taux` actions.
Aucune prédiction, aucun modèle : des faits comptés. Un fait SIMULÉ n'est jamais un résultat réalisé.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire
from plateforme.optimisation import cle

from .impact import _CONNEXION, _REEL, _atteint
from .interventions import Candidate
from .pareto import evaluer
from .reseau import graphe_actuel


ISSUES = ("REALISEE", "REFUSEE", "SIMULEE_SEULEMENT", "REMPLACEE", "SANS_SUITE_OBSERVEE")


class ErreurDecision(ValueError):
    pass


def enregistrer(m: Memoire, le: date, plan: dict, par: str, membres: list[str]) -> Evt:
    """`plan` : un plan du front ({"noms"?, "paires", "objectifs"}). Seules des paires de membres sont acceptées."""
    paires = [sorted(p) for p in plan.get("paires", [])]
    if not paires:
        raise ErreurDecision("un plan sans action ne s'enregistre pas : « ne rien faire » n'a rien à confronter")
    if any(len(set(p)) != 2 or not set(p) <= set(membres) for p in paires):
        raise ErreurDecision("action invalide : chaque action relie deux membres distincts du Club")
    return m.ajouter(Evt(type="DECISION_ORGANISATION", le=le, statut=Statut.DECLARE, acteurs=[],
                         donnees={"par": par, "noms": plan.get("noms", []), "paires": paires,
                                  "projection": plan.get("objectifs", {}),
                                  "hypothese": "projection supposant toutes les actions acceptées"}))


def _suite(m: Memoire, a: str, b: str, depuis: date, maintenant: date, jusqu_a: Optional[date] = None) -> list[Evt]:
    """Faits de la paire dans la FENÊTRE de la décision : [date de décision, décision suivante sur la même paire[."""
    k = cle(a, b)
    return sorted((e for e in m.evenements(jusqu_au=maintenant)
                   if len(e.acteurs) >= 2 and cle(*e.acteurs[:2]) == k and e.le >= depuis
                   and (jusqu_a is None or e.le < jusqu_a)), key=lambda e: (e.le, e.seq))


def _decision_suivante(m: Memoire, decision: Evt, a: str, b: str, maintenant: date) -> Optional[date]:
    """Date de la décision SUIVANTE qui reprend la même paire : un résultat n'est attribué qu'à la plus récente
    (défaut trouvé par EXP-N : une acceptation était créditée à deux décisions)."""
    suivantes = [e.le for e in m.evenements("DECISION_ORGANISATION", jusqu_au=maintenant)
                 if (e.le, e.seq) > (decision.le, decision.seq) and sorted([a, b]) in e.donnees.get("paires", [])]
    return min(suivantes) if suivantes else None


def ecart(m: Memoire, decision: Evt, maintenant: date, membres: list[str]) -> dict:
    d = decision.donnees
    actions: list[dict] = []
    for a, b in d["paires"]:
        suivante = _decision_suivante(m, decision, a, b, maintenant)
        suite = _suite(m, a, b, decision.le, maintenant, suivante)
        niv = _atteint(suite, maintenant, 90)
        decisifs = [e for e in suite if e.type == "INTRO_DECLINEE" or (e.type in _CONNEXION and e.statut in _REEL)]
        refus = bool(decisifs) and decisifs[-1].type == "INTRO_DECLINEE"   # le fait le plus RÉCENT gouverne
        issue = ("REFUSEE" if refus else "REALISEE" if niv["CONNEXION"] is True
                 else "SIMULEE_SEULEMENT" if niv["CONTACT"] is not None
                 else "REMPLACEE" if suivante is not None else "SANS_SUITE_OBSERVEE")
        actions.append({"paire": [a, b], "issue": issue,
                        "activation_reelle": niv["ACTIVATION"] is True})
    g0 = graphe_actuel(m, decision.le)                    # le réseau tel qu'il était le jour de la décision
    g0.add_nodes_from(membres)
    realisees = [Candidate("INTRODUCTION", x["paire"][0], x["paire"][1], 0, False) for x in actions if x["issue"] == "REALISEE"]
    obs = evaluer(g0, membres, realisees)
    prevu = d.get("projection", {})
    return {"decision_le": decision.le.isoformat(), "noms": d.get("noms", []), "actions": actions,
            "prevu": prevu, "realise": {k: obs[k] for k in ("inclusion", "cohesion")} | {"reciprocite": None},
            "comptes": {i: sum(x["issue"] == i for x in actions) for i in ISSUES},
            "note": "réalisé = actions avec une connexion RÉELLE après la décision ; la réciprocité réalisée n'est pas observable"}


def historique(m: Memoire, maintenant: date, membres: list[str], n_min_taux: int = 10) -> dict:
    decisions = m.evenements("DECISION_ORGANISATION", jusqu_au=maintenant)
    ecarts = [ecart(m, d, maintenant, membres) for d in decisions]
    total = sum(len(e["actions"]) for e in ecarts)
    comptes = {i: sum(e["comptes"][i] for e in ecarts) for i in ISSUES}
    taux: Optional[float] = round(comptes["REALISEE"] / total, 2) if total >= n_min_taux else None
    return {"decisions": len(ecarts), "actions": total, "comptes": comptes, "taux_realisation": taux,
            "n_min_taux": n_min_taux, "ecarts": ecarts,
            "lecture": ("pas encore assez d'actions pour un taux ; comptes seulement" if taux is None else
                        f"sur {total} actions décidées, {comptes['REALISEE']} ont produit une connexion réelle : les "
                        "projections (qui supposent 100 % d'acceptation) doivent être lues à cette aune")}
