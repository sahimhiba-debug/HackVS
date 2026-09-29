"""Frontière de Pareto des plans d'intervention : « il n'existe pas de plan qui maximise tout ».

Objectifs (définis sur le réseau ACTUEL après le plan, hypothèse : toutes les actions acceptées) :
- INCLUSION   : membres sans relation actuelle qui en obtiennent une ;
- COHÉSION    : taille du plus grand groupe après le plan ;
Axes MESURÉS puis abandonnés (quasi constants d'un plan à l'autre, donc front artificiel) : diversité sectorielle
(97 % des aides prouvées relient déjà deux secteurs) et non-redondance (presque aucune paire candidate n'a de contact
actuel en commun dans un réseau clairsemé). Voir competition/EXPERIMENT_LOG.md (EXP-C).
- RÉCIPROCITÉ : actions où chacun peut aider l'autre (preuves dans les deux sens).

Plans candidats : glouton à gain marginal pour de nombreuses pondérations (simplexe) des 4 objectifs normalisés ;
chaque plan est ensuite ÉVALUÉ sur tous les axes ; seuls les plans NON DOMINÉS sont gardés (doublons fusionnés).
Plans nommés : les extrêmes de chaque axe et l'ÉQUILIBRE (plus petit regret maximal normalisé, Tchebychev).
On ne fabrique pas de plan : si deux noms désignent le même plan, ils sont fusionnés et on le dit.
"""
from __future__ import annotations

import itertools

import networkx as nx

from .interventions import Candidate, _composantes

AXES = ("inclusion", "cohesion", "reciprocite", "cohesion_robuste")


def arbre_des_ponts(g: nx.Graph) -> tuple[dict[str, int], dict[int, int], nx.Graph, int]:
    """Groupes ROBUSTES (2-arête-connexes : restent reliés si N'IMPORTE QUELLE relation s'éteint) et arbre des ponts.
    Ajouter une relation u–v fusionne tous les groupes robustes du chemin u→v dans cet arbre (théorie des graphes :
    l'arête crée un cycle qui supprime ces ponts) ; entre deux composantes distinctes, elle est elle-même un pont."""
    ponts = list(nx.bridges(g))
    h = g.copy()
    h.remove_edges_from(ponts)
    ident, taille = {}, {}
    for i, comp in enumerate(nx.connected_components(h)):
        taille[i] = len(comp)
        for x in comp:
            ident[x] = i
    arbre = nx.Graph()
    arbre.add_nodes_from(taille)
    arbre.add_edges_from((ident[a], ident[b]) for a, b in ponts)
    return ident, taille, arbre, max(taille.values(), default=0)


def gain_robuste(a: str, b: str, ponts: tuple) -> int:
    """Accroissement du plus grand groupe robuste si la relation a–b est ajoutée (exact, sans recalcul du graphe)."""
    ident, taille, arbre, maxi = ponts
    ia, ib = ident[a], ident[b]
    if ia == ib or not nx.has_path(arbre, ia, ib):
        return 0
    return max(0, sum(taille[x] for x in nx.shortest_path(arbre, ia, ib)) - maxi)


def plus_grand_groupe_robuste(g: nx.Graph, membres: list[str]) -> int:
    h = g.subgraph(membres).copy()
    h.add_nodes_from(membres)
    return arbre_des_ponts(h)[3]


def _gains(g: nx.Graph, c: Candidate, comp: tuple, ponts: tuple) -> tuple[float, ...]:
    ident, taille, vivant = comp
    isoles = (g.degree(c.a) == 0) + (g.degree(c.b) == 0)
    ca, cb = ident[c.a], ident[c.b]
    croissance = 0 if ca == cb else max(0, taille[ca] + taille[cb] - taille[vivant])
    return (isoles, croissance, float(c.reciproque), gain_robuste(c.a, c.b, ponts))


def glouton(g0: nx.Graph, cands: list[Candidate], k: int, poids: tuple[float, ...],
            plafond: int = 1) -> list[Candidate]:
    g, n, choix, restantes = g0.copy(), {}, [], list(cands)
    while len(choix) < k:
        possibles = [c for c in restantes if n.get(c.a, 0) < plafond and n.get(c.b, 0) < plafond]
        if not possibles:
            break
        comp, ponts = _composantes(g), arbre_des_ponts(g)
        gains = {id(c): _gains(g, c, comp, ponts) for c in possibles}
        maxi = [max(gains[id(c)][i] for c in possibles) or 1.0 for i in range(len(AXES))]
        meilleure = min(possibles, key=lambda c: (-sum(w * gains[id(c)][i] / maxi[i] for i, w in enumerate(poids)),
                                                  -c.valeur, c.a, c.b))
        g.add_edge(meilleure.a, meilleure.b)
        for x in (meilleure.a, meilleure.b):
            n[x] = n.get(x, 0) + 1
        restantes.remove(meilleure)
        choix.append(meilleure)
    return choix


def evaluer(g0: nx.Graph, membres: list[str], plan: list[Candidate]) -> dict[str, float]:
    apres = g0.copy()
    apres.add_nodes_from(membres)
    apres.add_edges_from((c.a, c.b) for c in plan)
    isoles_avant = sum(1 for x in membres if g0.degree(x) == 0) if len(g0) else len(membres)
    isoles_apres = sum(1 for x in membres if apres.degree(x) == 0)
    return {"inclusion": isoles_avant - isoles_apres,
            "cohesion": max(len(c) for c in nx.connected_components(apres.subgraph(membres))),
            "reciprocite": sum(c.reciproque for c in plan),
            "cohesion_robuste": plus_grand_groupe_robuste(apres, membres)}


def domine(u: dict, v: dict) -> bool:
    return all(u[a] >= v[a] for a in AXES) and any(u[a] > v[a] for a in AXES)


def simplexe(pas: int = 4) -> list[tuple[float, ...]]:
    return [tuple(x / pas for x in w) for w in itertools.product(range(pas + 1), repeat=len(AXES)) if sum(w) == pas]


def frontiere(g0: nx.Graph, membres: list[str], cands: list[Candidate], k: int,
              plafond: int = 1, pas: int = 4, plans_supplementaires: list[list[Candidate]] | None = None) -> dict:
    """Front des plans NON DOMINÉS parmi tous les plans générés (pondérations + plans heuristiques fournis). C'est une
    APPROXIMATION du vrai front (la recherche exhaustive est combinatoire) : on le dit dans la sortie."""
    if not cands:   # rien de prouvé à proposer : pas de « plan vide idéal » baptisé de quatre noms (défaut trouvé)
        return {"nature": "SIMULATION", "decision": "NE_RIEN_FAIRE", "raison": "aucune action fondée sur une aide prouvée",
                "plans_explores": 0, "front": [], "ideal": {}, "un_plan_atteint_l_ideal": False, "plans_nommes": []}
    g0 = g0.copy()
    g0.add_nodes_from(membres)
    vus: dict[tuple, dict] = {}
    generes = [(w, glouton(g0, cands, k, w, plafond)) for w in simplexe(pas)]
    generes += [("heuristique", p) for p in plans_supplementaires or []]
    for _origine, plan in generes:
        cle_plan = tuple(sorted((c.a, c.b) for c in plan))
        if cle_plan not in vus:
            vus[cle_plan] = {"paires": [list(p) for p in cle_plan], "objectifs": evaluer(g0, membres, plan), "origines": 1}
        else:
            vus[cle_plan]["origines"] += 1
    plans = list(vus.values())
    front = [p for p in plans if not any(domine(q["objectifs"], p["objectifs"]) for q in plans)]
    ideal = {a: max(p["objectifs"][a] for p in front) for a in AXES} if front else {}
    nadir = {a: min(p["objectifs"][a] for p in front) for a in AXES} if front else {}

    def regret(p: dict) -> float:
        return max((ideal[a] - p["objectifs"][a]) / ((ideal[a] - nadir[a]) or 1) for a in AXES)

    noms: dict[str, int] = {}
    if front:
        for a in AXES:
            noms[a.upper()] = max(range(len(front)), key=lambda i: (front[i]["objectifs"][a], -regret(front[i])))
        noms["EQUILIBRE"] = min(range(len(front)), key=lambda i: (regret(front[i]), i))
    fusionnes: dict[int, list[str]] = {}
    for nom, i in noms.items():
        fusionnes.setdefault(i, []).append(nom)
    return {"nature": "SIMULATION", "decision": "PROPOSER_A_L_HUMAIN", "plans_explores": len(plans), "front": front, "ideal": ideal,
            "un_plan_atteint_l_ideal": any(all(p["objectifs"][a] == ideal[a] for a in AXES) for p in front),
            "plans_nommes": [{"noms": v, **front[i]} for i, v in sorted(fusionnes.items())],
            "hypotheses": ["toutes les actions supposées acceptées", "pondérations explorées sur un simplexe (pas 1/%d)" % pas,
                            "front APPROCHÉ : non dominé parmi les plans générés, pas une énumération exhaustive"]}
