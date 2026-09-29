"""Intervention MINIMALE sur le réseau ACTUEL (idée I-01) : quelles k actions changent le plus la structure du réseau
— ou faut-il ne rien faire ?

Actions candidates (toutes fondées sur une aide PROUVÉE, consentement et refus respectés) :
- INTRODUCTION : deux membres sans relation actuelle, l'un peut aider l'autre ;
- RAVIVER : une relation passée (> 90 jours sans interaction) et une raison NOUVELLE et prouvée de la reprendre ;
- (les présentations par un intermédiaire restent dans les relances : elles sont proposées d'abord à l'intermédiaire.)

Choix glouton par gain structurel MARGINAL, dans l'ordre lexicographique (pas de pondération arbitraire) :
1. membres aujourd'hui sans aucune relation actuelle qui en obtiennent une ;
2. groupes du réseau actuel réunis (pont) ;
3. aide réciproque, puis force de la preuve.
Budget d'attention : au plus `plafond` sollicitations par membre et par plan (au-delà : silence).
C'est une SIMULATION : chaque action est supposée acceptée ; rien n'est écrit ni envoyé ; l'humain décide.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import networkx as nx

from app.matching import meme_organisation
from app.models import Profil
from app.soiree import calculer_aides
from plateforme.memoire import Memoire
from plateforme.optimisation import cle

from .reseau import etats_par_paire, graphe_actuel, graphe_de_confiance


@dataclass
class Candidate:
    type: str                      # INTRODUCTION | RAVIVER
    a: str
    b: str
    valeur: float                  # somme des aides prouvées (0,5 partielle, 1 forte) dans les deux sens
    reciproque: bool
    preuves: list[dict] = field(default_factory=list)


def candidates(profils: list[Profil], besoins_publies: list, tax, g_actuel: nx.Graph, etats: dict[str, str],
               aides: Optional[dict] = None) -> list[Candidate]:
    membres = [p for p in profils if p.type == "membre_club" and p.accepte_introductions and p.disponible]
    aides = aides if aides is not None else calculer_aides(membres, besoins_publies, tax)
    par_id = {p.id: p for p in membres}
    res: dict[str, Candidate] = {}
    for (i, j), aide in sorted(aides.items()):
        k = cle(i, j)
        if k in res or g_actuel.has_edge(i, j) or meme_organisation(par_id[i], par_id[j]):
            continue
        etat = etats.get(k, "AUCUNE")
        if etat == "DECLINEE":                     # un refus n'est jamais contourné
            continue
        inverse = aides.get((j, i))
        valeur = aide["valeur"] + (inverse["valeur"] if inverse else 0)
        preuves = [{"aide": j, "aide_a": i, "besoin": aide["besoin"], "preuve": aide["preuve"], "nature": aide["nature_preuve"]}]
        if inverse:
            preuves.append({"aide": i, "aide_a": j, "besoin": inverse["besoin"], "preuve": inverse["preuve"],
                            "nature": inverse["nature_preuve"]})
        a, b = sorted((i, j))
        res[k] = Candidate(type="RAVIVER" if etat == "A_RAVIVER" else "INTRODUCTION", a=a, b=b, valeur=valeur,
                           reciproque=bool(inverse), preuves=preuves)
    return sorted(res.values(), key=lambda c: (c.a, c.b))


def _composantes(g: nx.Graph) -> tuple[dict[str, int], dict[int, int], int]:
    ident, taille = {}, {}
    for n, comp in enumerate(sorted(nx.connected_components(g), key=lambda c: (-len(c), min(c)))):
        taille[n] = len(comp)
        for x in comp:
            ident[x] = n
    return ident, taille, 0   # la composante 0 est le « réseau vivant » (le plus grand groupe actuel)


def _gain(g: nx.Graph, c: Candidate, comp: Optional[tuple] = None) -> tuple[int, int, int]:
    """(isolé relié AU RÉSEAU VIVANT, membres qui rejoignent le réseau vivant, isolés reliés).
    Relier deux isolés entre eux crée un îlot de deux que personne ne peut présenter plus loin : effet de second
    ordre mesuré par le benchmark (variante ablation STRUCTURE_V1) ; il ne passe qu'après les ponts."""
    ident, taille, vivant = comp or _composantes(g)
    isoles = (g.degree(c.a) == 0) + (g.degree(c.b) == 0)
    ca, cb = ident[c.a], ident[c.b]
    # accroissement du plus grand groupe (fusion avec lui, ou deux groupes qui deviennent ensemble le plus grand)
    rejoignent = 0 if ca == cb else max(0, taille[ca] + taille[cb] - taille[vivant])
    isole_au_vivant = int(isoles == 1 and vivant in (ca, cb) and taille[vivant] > 1)
    return isole_au_vivant, rejoignent, isoles


def _rang(g: nx.Graph, c: Candidate, comp: tuple, variante: str) -> tuple:
    au_vivant, rejoignent, isoles = _gain(g, c, comp)
    if variante == "V1":           # ablation : isolés d'abord, sans regarder à quoi on les relie
        return (-isoles, -int(rejoignent > 0), -c.reciproque, -c.valeur, c.a, c.b)
    if variante == "COHESION":     # réunir les groupes au réseau vivant d'abord
        return (-rejoignent, -isoles, -c.reciproque, -c.valeur, c.a, c.b)
    return (-au_vivant, -rejoignent, -isoles, -c.reciproque, -c.valeur, c.a, c.b)   # INCLUSION ; égalité : identifiants


def choisir(g_actuel: nx.Graph, cands: list[Candidate], k: int, plafond: int = 1, variante: str = "INCLUSION") -> list[dict]:
    """Glouton sur le gain MARGINAL (le graphe est mis à jour après chaque choix). Déterministe.
    INCLUSION : relier d'abord les membres sans relation actuelle AU réseau vivant ; COHESION : réunir d'abord les
    groupes ; V1 : ablation (benchmark seulement). Les deux premières sont en CONFLIT mesuré : l'humain choisit."""
    g = g_actuel.copy()
    sollicitations: dict[str, int] = {}
    choisies, restantes = [], list(cands)
    while len(choisies) < k:
        possibles = [c for c in restantes if sollicitations.get(c.a, 0) < plafond and sollicitations.get(c.b, 0) < plafond]
        if not possibles:
            break
        comp = _composantes(g)
        meilleure = min(possibles, key=lambda c: _rang(g, c, comp, variante))  # noqa: B023 (évalué immédiatement)
        au_vivant, rejoignent, isoles = _gain(g, meilleure, comp)
        # PONT = relie deux groupes existants (même définition que reseau.simuler)
        pont = isoles == 0 and comp[0][meilleure.a] != comp[0][meilleure.b]
        g.add_edge(meilleure.a, meilleure.b)
        for x in (meilleure.a, meilleure.b):
            sollicitations[x] = sollicitations.get(x, 0) + 1
        restantes.remove(meilleure)
        choisies.append({"type": meilleure.type, "paire": [meilleure.a, meilleure.b], "isoles_relies": isoles,
                         "rejoignent_le_reseau_vivant": rejoignent, "pont": pont,
                         "reciproque": meilleure.reciproque, "valeur": meilleure.valeur, "preuves": meilleure.preuves})
    return choisies


def indicateurs_actuels(g: nx.Graph, membres: list[str]) -> dict:
    """Indicateurs FACTUELS de l'activation du réseau (idée I-02) : aucun score composite."""
    h = g.subgraph(membres).copy()
    h.add_nodes_from(membres)
    relies = sum(1 for n in h if h.degree(n) > 0)
    return {"membres": len(membres), "avec_relation_actuelle": relies, "sans_relation_actuelle": len(membres) - relies,
            "groupes_actuels": sum(1 for c in nx.connected_components(h) if len(c) > 1),
            "plus_grand_groupe": max((len(c) for c in nx.connected_components(h)), default=0),
            "relations_actuelles": h.number_of_edges()}


def plan(m: Memoire, profils: list[Profil], besoins_publies: list, tax, maintenant: date, k: int = 5,
         plafond: int = 1, g_actuel: Optional[nx.Graph] = None) -> dict:
    g = g_actuel if g_actuel is not None else graphe_actuel(m, maintenant, graphe_de_confiance(m, maintenant))
    membres = sorted(p.id for p in profils if p.type == "membre_club")
    g = g.copy()
    g.add_nodes_from(membres)
    cands = candidates(profils, besoins_publies, tax, g, etats_par_paire(m, maintenant))
    avant_i = indicateurs_actuels(g, membres)
    options = {}
    for variante in ("INCLUSION", "COHESION"):
        actions = choisir(g, cands, k, plafond, variante)
        apres = g.copy()
        apres.add_edges_from(tuple(a["paire"]) for a in actions)
        options[variante] = {"actions": actions, "apres": indicateurs_actuels(apres, membres)}
    if not cands:
        decision, raison = "NE_RIEN_FAIRE", "aucune action fondée sur une aide prouvée n'est possible (consentement, refus, preuves)"
    elif all(a["isoles_relies"] == 0 and not a["pont"] and not a["rejoignent_le_reseau_vivant"]
             for o in options.values() for a in o["actions"]):
        decision, raison = "PROPOSER_A_L_HUMAIN", "actions utiles aux membres, sans effet sur la structure du réseau"
    else:
        decision, raison = "PROPOSER_A_L_HUMAIN", ("deux plans en conflit mesuré : INCLUSION relie d'abord les membres sans "
                                                  "relation actuelle, COHESION réunit d'abord les groupes ; à vous de choisir")
    return {"nature": "SIMULATION", "decision": decision, "raison": raison, "options": options,
            "candidates": len(cands), "budget": k, "plafond_par_membre": plafond, "avant": avant_i,
            "hypotheses": ["chaque action est supposée acceptée par les deux membres",
                           "« actuel » = interaction depuis moins de 90 jours (hypothèse de produit)"]}
