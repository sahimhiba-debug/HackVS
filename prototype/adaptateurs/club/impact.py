"""Échelle d'impact d'une relation — définie sur les FAITS de la mémoire, jamais estimée.

Niveaux CUMULATIFS (chacun implique le précédent) :
- CONTACT     : une interaction a eu lieu (rencontre, introduction acceptée, suivi, résultat) ;
- CONNEXION   : les DEUX ont consenti ou un membre l'a déclarée (introduction acceptée, rencontre confirmée, suivi, résultat) ;
- ACTIVATION  : un résultat UTILE ou une affaire en cours a été déclaré ;
- PERSISTANCE : activation + interactions étalées sur au moins `duree_min` jours + relation encore ACTUELLE.
Compté à part (non cumulatif) :
- EFFET RÉSEAU : la relation a servi d'appui à une présentation acceptée par l'intermédiaire (OPPORTUNITE_OUVERTE).

Chaque niveau distingue ce qui repose sur des faits DÉCLARÉS/OBSERVÉS et ce qui ne repose que sur des faits SIMULÉS
(démo) : une soirée simulée ne produit que des contacts simulés.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire
from plateforme.optimisation import cle

from .reseau import ETATS_NON_ACTUELS, _etat

NIVEAUX = ("CONTACT", "CONNEXION", "ACTIVATION", "PERSISTANCE")
_CONTACT = {"RENCONTRE", "RENCONTRE_CONFIRMEE", "INTRO_ACCEPTEE", "SUIVI", "RESULTAT"}
_CONNEXION = {"RENCONTRE_CONFIRMEE", "INTRO_ACCEPTEE", "SUIVI", "RESULTAT"}
_REEL = {Statut.DECLARE, Statut.OBSERVE, Statut.VERIFIE}


def _atteint(evs: list[Evt], maintenant: date, duree_min: int) -> dict[str, Optional[bool]]:
    """Pour chaque niveau : None (non atteint), False (atteint par des faits SIMULÉS seulement), True (faits réels)."""
    def niveau(pred) -> Optional[bool]:
        ok = [e for e in evs if pred(e)]
        return None if not ok else any(e.statut in _REEL for e in ok)

    res: dict[str, Optional[bool]] = {
        "CONTACT": niveau(lambda e: e.type in _CONTACT),
        "CONNEXION": niveau(lambda e: e.type in _CONNEXION),
        "ACTIVATION": niveau(lambda e: e.type == "RESULTAT" and e.donnees.get("resultat") in ("utile", "affaire_en_cours")),
    }
    interactions = [e.le for e in evs if e.type in _CONTACT]
    etale = bool(interactions) and (max(interactions) - min(interactions)).days >= duree_min
    actuelle = _etat(evs, maintenant)["etat"] not in ETATS_NON_ACTUELS
    res["PERSISTANCE"] = res["ACTIVATION"] if (res["ACTIVATION"] is not None and etale and actuelle) else None
    for i in range(1, len(NIVEAUX)):             # cumulatif : un niveau n'est atteint que si le précédent l'est
        if res[NIVEAUX[i - 1]] is None:
            res[NIVEAUX[i]] = None
    return res


def entonnoir(m: Memoire, maintenant: date, paires: Optional[set[str]] = None, duree_min: int = 90) -> dict:
    """Entonnoir sur un ensemble de paires (défaut : toutes celles qui ont au moins un contact)."""
    par_paire: dict[str, list[Evt]] = {}
    via: set[str] = set()
    for e in m.evenements(jusqu_au=maintenant):
        if len(e.acteurs) >= 2:
            par_paire.setdefault(cle(*e.acteurs[:2]), []).append(e)
        if e.type == "OPPORTUNITE_OUVERTE" and e.donnees.get("via"):
            via |= {cle(e.donnees["via"], x) for x in e.acteurs}    # la relation intermédiaire–x a servi d'appui
    cibles = sorted(paires if paires is not None else par_paire)
    compte = {n: {"reel": 0, "simule_seulement": 0} for n in NIVEAUX}
    effet = {"reel": 0, "simule_seulement": 0}
    for k in cibles:
        evs = sorted(par_paire.get(k, []), key=lambda e: (e.le, e.seq))
        a = _atteint(evs, maintenant, duree_min)
        for n in NIVEAUX:
            if a[n] is not None:
                compte[n]["reel" if a[n] else "simule_seulement"] += 1
        if k in via and a["CONNEXION"] is not None:
            effet["reel" if a["CONNEXION"] else "simule_seulement"] += 1
    return {"paires": len(cibles), "niveaux": compte, "effet_reseau": effet, "duree_persistance_jours": duree_min,
            "definitions": {"CONTACT": "une interaction a eu lieu",
                            "CONNEXION": "les deux ont consenti, ou un membre a déclaré la rencontre",
                            "ACTIVATION": "résultat utile ou affaire en cours déclaré",
                            "PERSISTANCE": f"activation, interactions étalées sur ≥ {duree_min} jours, relation encore actuelle",
                            "EFFET_RESEAU": "la relation a servi d'appui à une présentation acceptée"}}


def entonnoir_evenement(m: Memoire, maintenant: date, run_id: str, duree_min: int = 90) -> dict:
    """Qu'a produit UNE soirée ? Les paires qu'elle a fait se rencontrer, suivies jusqu'à aujourd'hui."""
    paires = {cle(*e.acteurs[:2]) for e in m.evenements("RENCONTRE", jusqu_au=maintenant) if e.donnees.get("run_id") == run_id}
    return entonnoir(m, maintenant, paires, duree_min) | {"run_id": run_id}
