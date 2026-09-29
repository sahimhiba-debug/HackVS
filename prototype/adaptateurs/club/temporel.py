"""Ce qui a CHANGÉ dans le réseau entre deux dates — et quelle intervention serait pertinente maintenant.

Comparaison de deux graphes ACTUELS (t0, t1) ; aucun événement n'est deviné : chacun est une différence de faits.
- RELATION_ENDORMIE : relation actuelle en t0, plus actuelle en t1 (sans refus) ;
- MEMBRE_ISOLE       : membre relié en t0, sans aucune relation actuelle en t1 ;
- PONT_DISPARU       : un groupe (≥ taille min) de t0 est coupé en plusieurs groupes (≥ taille min) en t1 ;
- NOUVEAU_GROUPE     : un groupe (≥ taille min) de t1 dont aucun membre n'appartenait à un groupe en t0.
Vue ORGANISATION : les événements portent des comptes et des tailles ; les identités ne sont exposées qu'à l'organisation.
"""
from __future__ import annotations

from datetime import date

import networkx as nx

from plateforme.memoire import Memoire

from .reseau import graphe_actuel


def _groupes(g: nx.Graph, membres: list[str], taille_min: int) -> list[frozenset]:
    h = g.subgraph(membres).copy()
    h.add_nodes_from(membres)
    return [frozenset(c) for c in nx.connected_components(h) if len(c) >= taille_min]


def changements(g0: nx.Graph, g1: nx.Graph, membres: list[str], declinees: set[frozenset] = frozenset(),
                taille_min: int = 3) -> list[dict]:
    ev = []
    endormies = sorted(tuple(sorted(e)) for e in g0.edges() if not g1.has_edge(*e) and frozenset(e) not in declinees
                       and e[0] in membres and e[1] in membres)
    if endormies:
        ev.append({"type": "RELATION_ENDORMIE", "nombre": len(endormies), "paires": [list(p) for p in endormies],
                   "intervention": "relance RAVIVER seulement si une raison NOUVELLE et prouvée existe ; sinon silence"})
    deg = lambda g, x: g.degree(x) if x in g else 0  # noqa: E731
    isoles = sorted(x for x in membres if deg(g0, x) > 0 and deg(g1, x) == 0)
    if isoles:
        ev.append({"type": "MEMBRE_ISOLE", "nombre": len(isoles), "membres": isoles,
                   "intervention": "plan INCLUSION : relier au réseau vivant par une aide prouvée"})
    grp0, grp1 = _groupes(g0, membres, taille_min), _groupes(g1, membres, taille_min)
    for c0 in grp0:
        morceaux = [c1 for c1 in grp1 if c1 & c0]
        if len(morceaux) >= 2:
            ev.append({"type": "PONT_DISPARU", "taille_avant": len(c0), "tailles_apres": sorted((len(c) for c in morceaux), reverse=True),
                       "intervention": "plan COHÉSION : recréer un pont (de préférence redondant) entre les morceaux"})
    dans_grp0 = set().union(*grp0) if grp0 else set()
    for c1 in grp1:
        if not c1 & dans_grp0:
            ev.append({"type": "NOUVEAU_GROUPE", "taille": len(c1),
                       "intervention": "le relier au réseau vivant avant qu'il ne devienne un silo"})
    return ev


def depuis(m: Memoire, membres: list[str], t0: date, t1: date, taille_min: int = 3) -> dict:
    from .reseau import paires_declinees
    declinees = {frozenset(p) for p in paires_declinees(m, t1)}
    ev = changements(graphe_actuel(m, t0), graphe_actuel(m, t1), membres, declinees, taille_min)
    return {"de": t0.isoformat(), "a": t1.isoformat(), "evenements": ev,
            "nature": "DIFFÉRENCE DE FAITS entre deux dates (« actuel » = interaction depuis moins de 90 jours, hypothèse)"}
