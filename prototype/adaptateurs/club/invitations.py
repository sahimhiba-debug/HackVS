"""Invitation ciblée : qui le Club devrait-il inviter PERSONNELLEMENT à la prochaine soirée ?

Invités possibles : membres sans relation actuelle (dormants ou isolés) qui acceptent les introductions.
Présents supposés : membres ACTIFS (au moins une relation actuelle) — hypothèse déclarée.
Un invité est SERVI s'il peut rencontrer un présent avec qui une aide est PROUVÉE (dans un sens au moins), chaque
présent accueillant au plus `capacite` invités. Maximiser le nombre d'invités servis est un b-couplage biparti : résolu
EXACTEMENT par flot maximal (et non par un classement), puis on garde au plus `budget` invités.
"""
from __future__ import annotations

import networkx as nx


def choisir(invitables: list[str], presents: list[str], aides: set[frozenset], budget: int, capacite: int = 1,
            priorite: dict[str, int] | None = None) -> dict:
    """`aides` : paires (frozenset) avec aide prouvée ; `priorite` : plus petit = prioritaire à optimum égal (ex. isolés)."""
    f = nx.DiGraph()
    pres = set(presents)
    for x in sorted(invitables):
        hotes = sorted(y for y in pres if frozenset((x, y)) in aides)
        if hotes:
            # coût léger pour départager des solutions d'égale taille (priorité), sans changer le MAXIMUM
            f.add_edge("S", ("i", x), capacity=1, weight=(priorite or {}).get(x, 0))
            for y in hotes:
                f.add_edge(("i", x), ("h", y), capacity=1, weight=0)
    for y in sorted(pres):
        if f.has_node(("h", y)):
            f.add_edge(("h", y), "T", capacity=capacite, weight=0)
    if not f.number_of_edges():
        return {"invites": [], "servis": 0, "affectation": {}, "decision": "NE_RIEN_FAIRE",
                "raison": "aucun membre dormant n'a d'aide prouvée avec un membre actif"}
    # plafonner le flot au budget : arc source unique de capacité `budget`
    f.add_edge("S0", "S", capacity=budget, weight=0)
    flot = nx.max_flow_min_cost(f, "S0", "T")
    affect = {}
    for x in invitables:
        for (_, y), q in flot.get(("i", x), {}).items():
            if q:
                affect[x] = y
    invites = sorted(affect)
    return {"invites": invites, "servis": len(invites), "affectation": affect, "decision": "PROPOSER_A_L_HUMAIN",
            "hypotheses": ["les membres actifs sont supposés présents", f"chaque présent accueille au plus {capacite} invité(s)"]}


def servis(invites: list[str], presents: list[str], aides: set[frozenset], capacite: int = 1) -> int:
    """Nombre maximal d'invités d'un ensemble DONNÉ qui peuvent être servis (même flot : juge équitable des baselines)."""
    return choisir(invites, presents, aides, budget=len(invites), capacite=capacite)["servis"]
