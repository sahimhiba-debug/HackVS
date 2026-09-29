"""Mémoire des interventions : ce que chaque TYPE d'action du Club a réellement produit, d'après les faits.

Ce n'est PAS de l'apprentissage automatique : aucune estimation, aucune prédiction. Pour chaque intervention passée
(table de soirée, relance, présentation par un intermédiaire, introduction demandée par un membre), on suit la paire
concernée APRÈS la date de l'intervention sur l'échelle d'impact (impact.py), et on compte.
Les comptes sont ventilés par un CONTEXTE explicite (ex. table avec aide dans les deux sens / dans un seul) : c'est
l'aide à la décision « qu'est-ce qui a marché, pour nous, dans quel contexte ? ».
Règles d'honnêteté : des comptes, pas des taux, tant qu'un groupe compte moins de `n_min_taux` interventions ; les
faits SIMULÉS (démo) sont comptés à part et ne sont jamais présentés comme des résultats.
"""
from __future__ import annotations

from datetime import date

from plateforme.memoire import Evt, Memoire
from plateforme.optimisation import cle

from .impact import NIVEAUX, _atteint


def _interventions(m: Memoire, maintenant: date) -> list[dict]:
    res = []
    for e in m.evenements(jusqu_au=maintenant):
        if e.type == "RENCONTRE" and e.donnees.get("run_id"):
            sens = {(r["qui_est_aide"], r["qui_aide"]) for r in e.donnees.get("raisons", [])}
            ctx = "aide dans les deux sens" if len(sens) >= 2 else "aide dans un seul sens" if sens else "sans aide documentée"
            res.append({"type": "TABLE_SOIREE", "contexte": ctx, "paire": cle(*e.acteurs[:2]), "le": e.le, "evt": e})
        elif e.type in ("RELANCE_ACCEPTEE", "RELANCE_REFUSEE"):
            res.append({"type": "RELANCE", "contexte": e.donnees.get("raison", "type inconnu"), "paire": cle(*e.acteurs[:2]),
                        "le": e.le, "evt": e, "refusee": e.type == "RELANCE_REFUSEE"})
        elif e.type == "OPPORTUNITE_OUVERTE":
            res.append({"type": "PRESENTATION", "contexte": "par un intermédiaire", "paire": cle(*e.acteurs[:2]), "le": e.le, "evt": e})
        elif e.type == "INTRO_DEMANDEE":
            res.append({"type": "INTRODUCTION_MEMBRE", "contexte": "demandée par un membre", "paire": cle(*e.acteurs[:2]),
                        "le": e.le, "evt": e})
    return res


def bilan(m: Memoire, maintenant: date, duree_min: int = 90, n_min_taux: int = 10) -> dict:
    par_paire: dict[str, list[Evt]] = {}
    for e in m.evenements(jusqu_au=maintenant):
        if len(e.acteurs) >= 2:
            par_paire.setdefault(cle(*e.acteurs[:2]), []).append(e)
    groupes: dict[tuple, dict] = {}
    for iv in _interventions(m, maintenant):
        g = groupes.setdefault((iv["type"], iv["contexte"]), {
            "type": iv["type"], "contexte": iv["contexte"], "interventions": 0, "refusees": 0,
            "apres": {n: {"reel": 0, "simule_seulement": 0} for n in NIVEAUX}})
        g["interventions"] += 1
        if iv.get("refusee"):
            g["refusees"] += 1
            continue
        # la suite de CETTE paire à partir de l'intervention (les faits antérieurs ne comptent pas comme un résultat)
        suite = sorted((e for e in par_paire.get(iv["paire"], []) if e.le >= iv["le"] and e.type != "RELANCE_ACCEPTEE"),
                       key=lambda e: (e.le, e.seq))
        a = _atteint(suite, maintenant, duree_min)
        for n in NIVEAUX:
            if a[n] is not None:
                g["apres"][n]["reel" if a[n] else "simule_seulement"] += 1
    lignes = []
    for g in sorted(groupes.values(), key=lambda g: (g["type"], g["contexte"])):
        suivies = g["interventions"] - g["refusees"]
        g["taux_affichables"] = suivies >= n_min_taux
        if g["taux_affichables"]:
            g["taux_activation_reelle"] = round(g["apres"]["ACTIVATION"]["reel"] / suivies, 2)
        lignes.append(g)
    return {"le": maintenant.isoformat(), "groupes": lignes, "n_min_taux": n_min_taux,
            "nature": "COMPTES de faits observés après chaque intervention ; aucune prédiction ; simulé compté à part"}
