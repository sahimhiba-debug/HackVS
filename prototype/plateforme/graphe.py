"""Graphe du monde (NetworkX, en mémoire, reconstruit depuis les données de l'exécution). Métriques FACTUELLES :
composantes, isolés, ponts, points d'articulation. Pas de classement de personnes."""
from __future__ import annotations

import random

import networkx as nx


def construire(noeuds: list[str], aretes: list[tuple[str, str]]) -> nx.Graph:
    g = nx.Graph()
    g.add_nodes_from(noeuds)
    g.add_edges_from(aretes)
    return g


def metriques(g: nx.Graph) -> dict:
    comps = list(nx.connected_components(g))
    return {"noeuds": g.number_of_nodes(), "aretes": g.number_of_edges(), "composantes": len(comps),
            "plus_grande_composante": max((len(c) for c in comps), default=0),
            "isoles": sum(1 for n in g if g.degree(n) == 0), "ponts": sum(1 for _ in nx.bridges(g)),
            "points_d_articulation": sum(1 for _ in nx.articulation_points(g))}


def selection_retrait(g: nx.Graph, n: int, regle: str, graine: int = 0) -> list[str]:
    """Nœuds à retirer pour un test de stress. « articulation » : ceux dont le retrait coupe le graphe (fait
    structurel, pas un jugement sur la personne) ; « aleatoire » : tirage reproductible."""
    if regle == "articulation":
        return sorted(nx.articulation_points(g))[:n]
    return sorted(random.Random(graine).sample(sorted(g.nodes), min(n, g.number_of_nodes())))
