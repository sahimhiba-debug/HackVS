"""Observatoire du réseau : quelques PHÉNOMÈNES, pas un tableau de 30 indicateurs.

Chaque phénomène = observation (faits, formule) → interprétation → intervention possible. Vue ORGANISATION : les
observations sont agrégées et ne classent jamais des personnes (pas de notation sociale) ; les seuils sont des
hypothèses de produit, déclarées dans chaque sortie.

Entrées génériques (testables sur des réseaux générés) :
- g_hist  : graphe de toutes les relations connues (attribut `derniere` : date de la dernière interaction) ;
- g_act   : graphe des relations ACTUELLES (sous-graphe de g_hist) ;
- membres : identifiants ; secteurs : membre → famille de secteur ; sollicitations : membre → demandes reçues sur la période.
"""
from __future__ import annotations

from typing import Optional

import networkx as nx

SEUILS = {
    "isolement_part": 0.10,          # plus de 10 % des membres sans relation actuelle…
    "isolement_min": 3,              # …ou au moins 3 membres (ajouté APRÈS la 1re mesure : 6 isolés sur 60 passaient inaperçus)
    "concentration_top3": 0.50,      # 3 membres touchent plus de la moitié des relations actuelles
    "groupe_min": 3,                 # un « groupe » compte au moins 3 membres
    "vieillissement_part": 0.50,     # plus de la moitié des relations connues ne sont plus actuelles
    "sollicitations_max": 5,         # demandes reçues sur la période au-delà desquelles un membre est sur-sollicité
    "entre_soi_part": 0.80,          # plus de 80 % des relations actuelles dans la même famille de secteur
    "liens_min": 6,                  # en dessous, aucune proportion n'a de sens : on s'abstient
}


def _groupes(g: nx.Graph, taille_min: int) -> list[set]:
    return [c for c in nx.connected_components(g) if len(c) >= taille_min]


def phenomenes(g_hist: nx.Graph, g_act: nx.Graph, membres: list[str], secteurs: Optional[dict[str, str]] = None,
               sollicitations: Optional[dict[str, int]] = None, seuils: Optional[dict] = None) -> dict:
    s = SEUILS | (seuils or {})
    act = g_act.subgraph(membres).copy()
    act.add_nodes_from(membres)
    n, e = len(membres), act.number_of_edges()
    res = []

    def ajouter(code, observation, formule, interpretation, intervention, valeur):
        res.append({"phenomene": code, "observation": observation, "formule": formule, "valeur": valeur,
                    "interpretation": interpretation, "intervention_possible": intervention})

    if e < s["liens_min"]:
        return {"membres": n, "relations_actuelles": e, "phenomenes": [], "abstention":
                f"moins de {s['liens_min']} relations actuelles : aucune proportion n'est interprétable", "seuils": s}

    isoles = [x for x in act if act.degree(x) == 0]
    if len(isoles) >= s["isolement_min"] or len(isoles) / n > s["isolement_part"]:
        ajouter("ISOLEMENT", f"{len(isoles)} membres sur {n} sans aucune relation actuelle", "isolés / membres",
                "une partie du Club ne profite d'aucune relation vivante", "plan INCLUSION (relier au réseau vivant)",
                round(len(isoles) / n, 3))

    couverts = {frozenset(x) for x in act.edges() if {x[0], x[1]} & set(sorted(act, key=lambda y: (-act.degree(y), y))[:3])}
    part = len(couverts) / e
    if part > s["concentration_top3"]:
        ajouter("CONCENTRATION", f"3 membres touchent {len(couverts)} des {e} relations actuelles",
                "relations touchant les 3 membres les plus reliés / relations actuelles",
                "le réseau paraît large mais repose sur quelques personnes (fausse diversité, risque de sur-sollicitation)",
                "introductions qui NE passent PAS par ces membres ; budget d'attention", round(part, 3))

    groupes = _groupes(act, s["groupe_min"])
    if len(groupes) >= 2:
        tailles = sorted((len(c) for c in groupes), reverse=True)
        ajouter("FRAGMENTATION", f"{len(groupes)} groupes d'au moins {s['groupe_min']} membres sans aucune relation actuelle entre eux ({tailles})",
                "composantes connexes (≥ taille min) du graphe actuel", "des communautés vivent côte à côte sans se parler",
                "plan COHÉSION (ponts entre groupes)", len(groupes))

    fragiles, extremites = [], set()
    for a, b in nx.bridges(act):
        h = act.copy()
        h.remove_edge(a, b)
        ta, tb = len(nx.node_connected_component(h, a)), len(nx.node_connected_component(h, b))
        if min(ta, tb) >= s["groupe_min"]:
            fragiles.append(sorted((ta, tb)))
            extremites |= {a, b}
    if fragiles:
        ajouter("PONT_FRAGILE", f"{len(fragiles)} lien(s) entre deux groupes reposent sur UNE seule relation ({fragiles})",
                "ponts du graphe actuel dont la suppression sépare deux parties d'au moins taille min",
                "si cette relation s'endort, le réseau se coupe en deux", "créer une seconde relation entre les deux groupes (redondance)",
                len(fragiles))

    # Même classe que PONT_FRAGILE, portée par une PERSONNE : aucune relation n'est un pont, mais un seul membre relie
    # deux parties (point d'articulation). Contre-exemple trouvé en red team. La personne n'est jamais nommée.
    passages = []
    for x in sorted(nx.articulation_points(act)):
        if x in extremites:               # déjà signalé comme pont fragile : pas de double compte
            continue
        h = act.copy()
        h.remove_node(x)
        parts = sorted((len(c) for c in nx.connected_components(h) if len(c) >= s["groupe_min"]), reverse=True)
        if len(parts) >= 2:
            passages.append(parts[:2])
    if passages:
        ajouter("PASSAGE_UNIQUE", f"{len(passages)} fois, deux groupes ({sorted(passages)}) ne sont reliés que par UNE seule personne",
                "points d'articulation dont le retrait sépare deux parties d'au moins taille min (personne non nommée)",
                "si cette personne s'éloigne ou est sur-sollicitée, le réseau se coupe",
                "créer une relation directe entre les deux groupes, qui ne passe pas par cette personne", len(passages))

    if g_hist.number_of_edges():
        hist = g_hist.subgraph(membres).number_of_edges()
        part_v = 1 - e / hist if hist else 0.0
        if part_v > s["vieillissement_part"]:
            ajouter("VIEILLISSEMENT", f"{hist - e} relations connues sur {hist} ne sont plus actuelles",
                    "1 − relations actuelles / relations connues", "le Club a créé des relations qui s'éteignent",
                    "relances RAVIVER fondées sur une raison nouvelle", round(part_v, 3))

    if sollicitations:
        trop = [x for x, c in sollicitations.items() if c > s["sollicitations_max"]]
        if trop:
            ajouter("SUR_SOLLICITATION", f"{len(trop)} membre(s) ont reçu plus de {s['sollicitations_max']} demandes sur la période",
                    "membres dont les demandes reçues dépassent le seuil", "toujours les mêmes sont sollicités",
                    "budget d'attention ; orienter vers d'autres aidants prouvés", len(trop))

    if secteurs:
        meme = sum(1 for a, b in act.edges() if secteurs.get(a) and secteurs.get(a) == secteurs.get(b))
        if meme / e > s["entre_soi_part"]:
            ajouter("ENTRE_SOI", f"{meme} des {e} relations actuelles relient deux membres du même secteur",
                    "relations intra-secteur / relations actuelles", "le réseau renforce des silos professionnels",
                    "rencontres entre secteurs différents fondées sur une aide prouvée", round(meme / e, 3))

    return {"membres": n, "relations_actuelles": e, "phenomenes": res, "seuils": s,
            "nature": "OBSERVATION (faits du graphe) ; interprétations et seuils = hypothèses de produit"}


def sans_relation(g_act: nx.Graph, membres: list[str], a: str, b: str) -> dict:
    """CONTREFACTUEL : que devient le réseau actuel si la relation a–b disparaît (s'endort, se brouille) ?
    Calcul pur sur le graphe (rien n'est écrit). Les membres coupés de leur groupe sont listés : vue ORGANISATION."""
    from .pareto import plus_grand_groupe_robuste
    act = g_act.subgraph(membres).copy()
    act.add_nodes_from(membres)
    if not act.has_edge(a, b):
        return {"existe": False, "raison": "aucune relation actuelle entre ces deux membres"}

    def mesure(h: nx.Graph) -> dict:
        comps = sorted(nx.connected_components(h), key=lambda c: (-len(c), min(c)))
        return {"groupes": sum(1 for c in comps if len(c) > 1), "plus_grand_groupe": len(comps[0]) if comps else 0,
                "sans_relation": sum(1 for x in h if h.degree(x) == 0), "groupe_robuste": plus_grand_groupe_robuste(h, membres)}

    h = act.copy()
    h.remove_edge(a, b)
    groupe = nx.node_connected_component(act, a)                  # le groupe qui contient cette relation
    morceaux = sorted((c & groupe for c in nx.connected_components(h) if c & groupe), key=lambda c: (-len(c), min(c)))
    coupes = sorted(groupe - morceaux[0])                         # ceux qui se retrouvent hors de la plus grande partie
    return {"existe": True, "nature": "SIMULATION (contrefactuel sur le graphe actuel)", "paire": sorted((a, b)),
            "est_un_pont": len(morceaux) > 1,
            "avant": mesure(act), "apres": mesure(h), "coupes_de_leur_groupe": coupes, "taille_du_groupe": len(groupe)}


def relation_la_plus_critique(g_act: nx.Graph, membres: list[str]) -> Optional[tuple[str, str]]:
    """La relation actuelle dont la disparition coupe le plus de membres de leur groupe (égalité : identifiants)."""
    act = g_act.subgraph(membres).copy()
    act.add_nodes_from(membres)
    ponts = sorted(tuple(sorted(e)) for e in nx.bridges(act))
    if not ponts:
        return None
    return max(ponts, key=lambda e: len(sans_relation(act, membres, *e)["coupes_de_leur_groupe"]))   # max : 1re ex aequo
