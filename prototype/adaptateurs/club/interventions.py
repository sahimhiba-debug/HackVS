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
        preuves = [{"aide": j, "aide_a": i, "besoin": aide["besoin"], "preuve": aide["preuve"], "champ": aide["champ_preuve"],
                    "nature": aide["nature_preuve"]}]
        if inverse:
            preuves.append({"aide": i, "aide_a": j, "besoin": inverse["besoin"], "preuve": inverse["preuve"],
                            "champ": inverse["champ_preuve"], "nature": inverse["nature_preuve"]})
        a, b = sorted((i, j))
        res[k] = Candidate(type="RAVIVER" if etat == "A_RAVIVER" else "INTRODUCTION", a=a, b=b, valeur=valeur,
                           reciproque=bool(inverse), preuves=preuves)
    return sorted(res.values(), key=lambda c: (c.a, c.b))


def refus_motives(a: str, b: str, profils: list[Profil], besoins_publies: list, tax, g_actuel: nx.Graph,
                  etats: dict[str, str], aides: Optional[dict] = None) -> list[str]:
    """Pourquoi l'introduction a–b N'EST PAS proposable (liste vide = proposable). Mêmes règles que `candidates`,
    dans le même ordre ; la cohérence des deux est vérifiée par un test sur toutes les paires. Vue ORGANISATION :
    la raison de consentement ne dit pas lequel des deux a refusé."""
    par_id = {p.id: p for p in profils}
    if a == b:
        return ["une personne ne peut pas être présentée à elle-même"]
    pa, pb = par_id.get(a), par_id.get(b)
    if pa is None or pb is None or pa.type != "membre_club" or pb.type != "membre_club":
        return ["seuls des membres du Club peuvent être présentés l'un à l'autre"]
    raisons = []
    if not (pa.accepte_introductions and pa.disponible and pb.accepte_introductions and pb.disponible):
        raisons.append("consentement absent : l'un des deux ne souhaite pas être présenté (ou est indisponible)")
    if meme_organisation(pa, pb):
        raisons.append("même organisation : une introduction interne n'apporte rien au réseau")
    if g_actuel.has_edge(a, b):
        raisons.append("déjà en relation actuelle : rien à introduire")
    if etats.get(cle(a, b)) == "DECLINEE":
        raisons.append("introduction déjà refusée : un refus n'est jamais contourné")
    if not raisons:
        membres = [p for p in profils if p.type == "membre_club" and p.accepte_introductions and p.disponible]
        aides = aides if aides is not None else calculer_aides(membres, besoins_publies, tax)
        if (a, b) not in aides and (b, a) not in aides:
            raisons.append("aucune aide prouvée : aucun besoin publié de l'un ne correspond à une offre déclarée de l'autre")
    return raisons


def _concepts(p: Profil) -> set[str]:
    return set(p.secteurs) | {o.concept for o in p.offre + p.recherche if o.concept}


def relier_sans_preuve(x: str, profils: list[Profil], besoins_publies: list, tax, g_actuel: nx.Graph,
                       etats: dict[str, str]) -> dict:
    """Faut-il relier un membre à quelqu'un, n'importe qui ? Compte ce que l'organisation POURRAIT faire (chaque
    introduction possible améliorerait l'indicateur « membres isolés ») et ce qui est FONDÉ (aide prouvée).
    Mêmes règles que `candidates` via `refus_motives`. Montre aussi ce qu'une recommandation par ressemblance
    (Jaccard des concepts, la baseline « similarité » du benchmark) proposerait. Rien n'est écrit."""
    membres = [p for p in profils if p.type == "membre_club" and p.id != x]
    moi = next(p for p in profils if p.id == x)
    raisons: dict[str, int] = {}
    fondees, possibles = [], 0
    aides = calculer_aides([p for p in profils if p.type == "membre_club" and p.accepte_introductions and p.disponible],
                           besoins_publies, tax)
    for y in membres:
        r = refus_motives(x, y.id, profils, besoins_publies, tax, g_actuel, etats, aides)
        bloquant = [z for z in r if not z.startswith("aucune aide")]
        if not bloquant:
            possibles += 1                       # l'introduction serait techniquement possible (consentement, pas de refus)
        if not r:
            fondees.append(y.id)
        for z in r:
            raisons[z] = raisons.get(z, 0) + 1

    def jaccard(y: Profil) -> float:
        a, b = _concepts(moi), _concepts(y)
        return len(a & b) / len(a | b) if a | b else 0.0
    proches = sorted(((round(jaccard(y), 2), y.id) for y in membres if y.accepte_introductions), key=lambda t: (-t[0], t[1]))
    ressemblant = proches[0] if proches and proches[0][0] > 0 else None
    return {"membre": x, "introductions_possibles": possibles, "introductions_fondees": fondees,
            "raisons": dict(sorted(raisons.items(), key=lambda kv: -kv[1])),
            "par_ressemblance": {"membre": ressemblant[1], "ressemblance": ressemblant[0]} if ressemblant else None,
            "decision": "PROPOSER_A_L_HUMAIN" if fondees else "S_ABSTENIR",
            "ce_qui_changerait": "qu'un des deux publie un besoin auquel l'autre répond par une offre déclarée"}


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
