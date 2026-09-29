"""Diagnostic du réseau pour l'ORGANISATION : la boucle complète, en une vue.

comprendre (état, entonnoir d'impact) → diagnostiquer (phénomènes, par priorité) → voir venir (ce qui s'éteint dans
`horizon` jours) → générer et simuler des interventions (front de Pareto : aucun plan ne maximise tout) → décision
HUMAINE → observer (ce qui a changé) → se souvenir (bilan des interventions passées).

Rien n'est écrit ni envoyé. Tout ce qui est projeté ou simulé l'est explicitement. Les observations sont agrégées ; les
identifiants ne figurent que dans les actions proposées à l'organisation (jamais dans une vue membre).
"""
from __future__ import annotations

from datetime import date, timedelta

import networkx as nx

from app.models import Profil
from app.soiree import calculer_aides
from plateforme.memoire import Memoire, graphe
from plateforme.optimisation import cle

from . import bilan as bi
from . import boucle
from . import extinction as ex
from . import impact, invitations, pareto, sante, temporel
from .interventions import candidates, indicateurs_actuels
from .reseau import etats_par_paire, graphe_actuel

# Ordre de priorité (choix de produit, déclaré) : d'abord ce qui prive déjà des membres de toute relation, puis ce qui
# peut couper le réseau, puis ce qui l'appauvrit.
PRIORITE = ["ISOLEMENT", "PASSAGE_UNIQUE", "PONT_FRAGILE", "FRAGMENTATION", "SUR_SOLLICITATION", "CONCENTRATION",
            "VIEILLISSEMENT", "ENTRE_SOI"]


def diagnostic(m: Memoire, profils: list[Profil], besoins_publies: list, tax, maintenant: date, k: int = 5,
               horizon: int = 30, fenetre: int = 30) -> dict:
    membres = sorted(p.id for p in profils if p.type == "membre_club")
    g_act = graphe_actuel(m, maintenant)
    g_act.add_nodes_from(membres)
    secteurs = {p.id: (p.secteurs or [""])[0] for p in profils}
    debut = maintenant - timedelta(days=fenetre)
    sollic: dict[str, int] = {}
    for e in m.evenements("INTRO_DEMANDEE", jusqu_au=maintenant):
        if e.le >= debut and len(e.acteurs) >= 2:
            sollic[e.acteurs[1]] = sollic.get(e.acteurs[1], 0) + 1
    obs = sante.phenomenes(graphe(m, maintenant), g_act, membres, secteurs, sollic)
    obs["phenomenes"].sort(key=lambda p: PRIORITE.index(p["phenomene"]) if p["phenomene"] in PRIORITE else len(PRIORITE))

    ouverts = [p for p in profils if p.type == "membre_club" and p.accepte_introductions and p.disponible]
    aides_brutes = calculer_aides(ouverts, besoins_publies, tax)       # UNE fois (mesure : appelé deux fois auparavant)
    cands = candidates(profils, besoins_publies, tax, g_act, etats_par_paire(m, maintenant), aides_brutes)
    decisions = m.evenements("DECISION_ORGANISATION", jusqu_au=maintenant)
    precedent = decisions[-1].donnees["paires"] if decisions else None      # hystérésis (EXP-O) : continuité avec l'humain
    plans = pareto.frontiere(g_act, membres, cands, k, precedent=precedent)
    ids_ouverts = {p.id for p in ouverts}
    actifs = sorted(x for x in ids_ouverts if g_act.degree(x) > 0)
    en_sommeil = sorted(x for x in ids_ouverts if g_act.degree(x) == 0)
    plans["invitations"] = invitations.choisir(en_sommeil, actifs, {frozenset(x) for x in aides_brutes}, budget=k, capacite=1)
    aides = {cle(i, j) for i, j in aides_brutes}
    ech = {x: d for x, d in ex.echeances(m, maintenant).items() if g_act.has_edge(*x.split("|"))}
    sollicitables = {p.id for p in ouverts}
    a_venir = {"INCLUSION": ex.echeancier(g_act, membres, ech, maintenant, horizon, k=3, plafond=2, aides=aides,
                                          sollicitables=sollicitables)}
    a_venir["COHESION_ravivements"] = [x.split("|") for x in ex.prevenir(g_act, membres, ech, maintenant, horizon, 3, 2, "COHESION",
                                                                          sollicitables=sollicitables)]

    observer = temporel.depuis(m, membres, debut, maintenant)
    _actions_maintenant(observer, cands, en_sommeil, actifs, aides_brutes, g_act)

    rien = not obs["phenomenes"] and not cands and not a_venir["INCLUSION"]["ravivements"]
    return {
        "le": maintenant.isoformat(),
        "decision": "NE_RIEN_FAIRE" if rien else "PROPOSER_A_L_HUMAIN",
        "comprendre": {"etat": indicateurs_actuels(g_act, membres), "entonnoir": impact.entonnoir(m, maintenant)},
        "diagnostiquer": obs,
        "voir_venir": a_venir,
        "agir": plans,
        "observer": observer,
        "se_souvenir": {"interventions": bi.bilan(m, maintenant), "decisions": boucle.historique(m, maintenant, membres)},
        "principes": ["aucune écriture, aucun envoi : l'humain décide",
                      "projections pessimistes (aucune interaction spontanée) ; simulations supposant les actions acceptées",
                      "aucune relance sans raison prouvée ; sinon invitation à un événement",
                      "comptes plutôt que taux sur de petits nombres ; simulé séparé du réel"],
    }


def _actions_maintenant(observer: dict, cands: list, en_sommeil: list[str], actifs: list[str], aides_brutes, g_act) -> None:
    """Chaque changement observé reçoit des ACTIONS PROUVÉES possibles maintenant — ou le silence, dit comme tel."""
    aides = {frozenset(x) for x in aides_brutes}
    for ev in observer["evenements"]:
        actions: list[dict] = []
        if ev["type"] == "MEMBRE_ISOLE":
            for x in ev["membres"]:
                hotes = sorted(y for y in actifs if frozenset((x, y)) in aides)
                if hotes and x in en_sommeil:
                    actions.append({"action": "INVITER", "membre": x, "rencontres_prouvees_possibles": len(hotes)})
        elif ev["type"] == "RELATION_ENDORMIE":
            for a, b in ev["paires"]:
                if frozenset((a, b)) in aides:
                    actions.append({"action": "RAVIVER_AVEC_RAISON", "paire": [a, b]})
        elif ev["type"] in ("PONT_DISPARU", "NOUVEAU_GROUPE"):
            comp = {x: i for i, c in enumerate(nx.connected_components(g_act)) for x in c}
            ponts = [c for c in cands if comp.get(c.a) != comp.get(c.b)]
            actions += [{"action": "RECRÉER_UN_PONT", "paire": [c.a, c.b]} for c in ponts[:3]]
        ev["actions_prouvees"] = actions
        ev["si_aucune"] = "silence : aucune action fondée sur une preuve n'est possible pour ce changement" if not actions else None
