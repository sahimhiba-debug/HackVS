"""Diagnostic du réseau pour l'ORGANISATION : la boucle complète, en une vue.

comprendre (état, entonnoir d'impact) → diagnostiquer (phénomènes, par priorité) → voir venir (ce qui s'éteint dans
`horizon` jours) → générer et simuler des interventions (front de Pareto : aucun plan ne maximise tout) → décision
HUMAINE → observer (ce qui a changé) → se souvenir (bilan des interventions passées).

Rien n'est écrit ni envoyé. Tout ce qui est projeté ou simulé l'est explicitement. Les observations sont agrégées ; les
identifiants ne figurent que dans les actions proposées à l'organisation (jamais dans une vue membre).
"""
from __future__ import annotations

from datetime import date, timedelta

from app.models import Profil
from app.soiree import calculer_aides
from plateforme.memoire import Memoire, graphe
from plateforme.optimisation import cle

from . import bilan as bi
from . import extinction as ex
from . import impact, pareto, sante, temporel
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
    plans = pareto.frontiere(g_act, membres, cands, k)
    aides = {cle(i, j) for i, j in aides_brutes}
    ech = {x: d for x, d in ex.echeances(m, maintenant).items() if g_act.has_edge(*x.split("|"))}
    sollicitables = {p.id for p in ouverts}
    a_venir = {"INCLUSION": ex.echeancier(g_act, membres, ech, maintenant, horizon, k=3, plafond=2, aides=aides,
                                          sollicitables=sollicitables)}
    a_venir["COHESION_ravivements"] = [x.split("|") for x in ex.prevenir(g_act, membres, ech, maintenant, horizon, 3, 2, "COHESION",
                                                                          sollicitables=sollicitables)]

    rien = not obs["phenomenes"] and not cands and not a_venir["INCLUSION"]["ravivements"]
    return {
        "le": maintenant.isoformat(),
        "decision": "NE_RIEN_FAIRE" if rien else "PROPOSER_A_L_HUMAIN",
        "comprendre": {"etat": indicateurs_actuels(g_act, membres), "entonnoir": impact.entonnoir(m, maintenant)},
        "diagnostiquer": obs,
        "voir_venir": a_venir,
        "agir": plans,
        "observer": temporel.depuis(m, membres, debut, maintenant),
        "se_souvenir": bi.bilan(m, maintenant),
        "principes": ["aucune écriture, aucun envoi : l'humain décide",
                      "projections pessimistes (aucune interaction spontanée) ; simulations supposant les actions acceptées",
                      "aucune relance sans raison prouvée ; sinon invitation à un événement",
                      "comptes plutôt que taux sur de petits nombres ; simulé séparé du réel"],
    }
