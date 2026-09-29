"""Échéancier d'extinction : que devient le réseau si le Club ne fait RIEN — et quelles relations raviver d'abord.

Chaque relation actuelle a une date d'extinction CONNUE : dernière interaction + JOURS_AVANT_STALE (règle du produit).
La projection applique ces extinctions dans l'ordre chronologique, sans prédire aucun comportement (hypothèse
pessimiste : aucune interaction spontanée). On obtient QUAND le réseau perd des membres ou se coupe.

Prévention : parmi les relations qui s'éteindraient avant l'horizon, on choisit celles dont le ravivement préserve le
plus de réseau (gain structurel MARGINAL sur le réseau projeté, glouton, budget d'attention par membre).
Règle produit : l'importance structurelle ne justifie PAS une relance. Chaque ravivement indique s'il existe une raison
prouvée (aide dans un sens au moins) ; sinon, l'action proposée est une invitation commune à un prochain événement.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import networkx as nx

from plateforme.optimisation import cle

from .interventions import _composantes, indicateurs_actuels
from .temporel import changements


def projeter(g_act: nx.Graph, membres: list[str], echeances: dict[str, date], maintenant: date, horizon: int,
             ravivees: frozenset[str] = frozenset()) -> tuple[nx.Graph, list[dict]]:
    """Réseau à l'horizon (relations éteintes retirées sauf ravivées) et chronologie des changements structurels."""
    g = g_act.subgraph(membres).copy()
    g.add_nodes_from(membres)
    fin = maintenant + timedelta(days=horizon)
    dates = sorted({d for k, d in echeances.items() if maintenant < d <= fin and k not in ravivees})
    chronologie = []
    for d in dates:
        avant = g.copy()
        for a, b in list(g.edges()):
            k = cle(a, b)
            if echeances.get(k) == d and k not in ravivees:
                g.remove_edge(a, b)
        ev = changements(avant, g, membres)
        if ev:
            chronologie.append({"le": d.isoformat(), "evenements": ev})
    return g, chronologie


def _gain(g: nx.Graph, a: str, b: str, comp: tuple) -> tuple[int, int, int]:
    ident, taille, vivant = comp
    isoles = (g.degree(a) == 0) + (g.degree(b) == 0)
    ca, cb = ident[a], ident[b]
    reunis = int(ca != cb and taille[ca] >= 3 and taille[cb] >= 3)
    croissance = 0 if ca == cb else max(0, taille[ca] + taille[cb] - taille[vivant])
    return isoles, croissance, reunis


def prevenir(g_act: nx.Graph, membres: list[str], echeances: dict[str, date], maintenant: date, horizon: int,
             k: int, plafond: int = 1, variante: str = "INCLUSION") -> list[str]:
    """Glouton : à chaque pas, la relation menacée dont le ravivement évite le plus de perte sur le réseau projeté.
    INCLUSION : éviter d'abord que des membres perdent toute relation ; COHESION : préserver d'abord le plus grand groupe.
    Les deux sont en conflit mesuré (EXP-C, EXP-F) : l'humain choisit."""
    g, _ = projeter(g_act, membres, echeances, maintenant, horizon)
    fin = maintenant + timedelta(days=horizon)
    menacees = sorted(k_ for k_, d in echeances.items() if maintenant < d <= fin and g_act.has_edge(*k_.split("|")))
    choisies: list[str] = []
    n: dict[str, int] = {}
    while len(choisies) < k:
        possibles = [x for x in menacees if x not in choisies and all(n.get(y, 0) < plafond for y in x.split("|"))]
        if not possibles:
            break
        comp = _composantes(g)
        ordre = (0, 1, 2) if variante == "INCLUSION" else (1, 2, 0)
        meilleure = min(possibles, key=lambda x: (tuple(-_gain(g, *x.split("|"), comp)[i] for i in ordre), echeances[x], x))  # noqa: B023
        if _gain(g, *meilleure.split("|"), comp) == (0, 0, 0):
            break                                   # rien ne se perd de plus : ne rien raviver de superflu
        g.add_edge(*meilleure.split("|"))
        choisies.append(meilleure)
        for y in meilleure.split("|"):
            n[y] = n.get(y, 0) + 1
    return choisies


def echeancier(g_act: nx.Graph, membres: list[str], echeances: dict[str, date], maintenant: date, horizon: int = 90,
               k: int = 3, plafond: int = 1, aides: Optional[set[str]] = None) -> dict:
    sans, chrono = projeter(g_act, membres, echeances, maintenant, horizon)
    choix = prevenir(g_act, membres, echeances, maintenant, horizon, k, plafond)
    avec, chrono_avec = projeter(g_act, membres, echeances, maintenant, horizon, frozenset(choix))
    premiere_coupure = next((c["le"] for c in chrono if any(e["type"] in ("PONT_DISPARU", "MEMBRE_ISOLE") for e in c["evenements"])), None)
    return {
        "nature": "PROJECTION (règle des 90 jours appliquée aux faits ; aucune interaction future supposée)",
        "horizon_jours": horizon, "aujourd_hui": indicateurs_actuels(g_act, membres),
        "sans_action": {"a_l_horizon": indicateurs_actuels(sans, membres), "chronologie": chrono, "premiere_perte": premiere_coupure},
        "avec_ravivements": {"a_l_horizon": indicateurs_actuels(avec, membres), "chronologie": chrono_avec},
        "ravivements": [{"paire": x.split("|"), "s_eteint_le": echeances[x].isoformat(),
                         "raison_prouvee": (x in aides) if aides is not None else None,
                         "action": ("relance fondée sur l'aide prouvée" if aides is not None and x in aides
                                    else "aucune raison prouvée : inviter les deux au prochain événement, pas de relance")}
                        for x in choix],
        "hypotheses": ["dernière interaction + 90 jours = extinction (règle du produit, non mesurée)",
                       "aucune interaction spontanée d'ici l'horizon (projection pessimiste)",
                       "une relation ravivée reste actuelle jusqu'à l'horizon"]}
