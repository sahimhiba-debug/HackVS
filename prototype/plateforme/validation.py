"""Échelle de validation. Aucun résultat important n'est final parce qu'un modèle l'affirme : il est vérifié par du
code INDÉPENDANT de celui qui l'a produit (le validateur ne réutilise pas le solveur ni la construction du problème).

L0 schéma · L1 types · L2 intégrité · L3 preuves · L4 politique · L5 contraintes du domaine · L6 faisabilité ·
L7 critique adverse · L8 revue humaine (toujours EN_ATTENTE : c'est l'humain qui décide).
"""
from __future__ import annotations

from datetime import date
from typing import Callable, Literal

from pydantic import BaseModel

from .affirmations import Registre, Statut
from .optimisation import Probleme, Solution, cle
from .specification import Domaine, ErreurSpec, SpecDecision, valider

Etat = Literal["PASS", "FAIL", "SKIP", "EN_ATTENTE"]


class Verdict(BaseModel):
    niveau: str
    nom: str
    etat: Etat
    details: list[str] = []


def l0_spec(spec: SpecDecision, domaine: Domaine) -> Verdict:
    try:
        valider(spec, domaine)
        return Verdict(niveau="L0", nom="spécification conforme au domaine", etat="PASS")
    except ErreurSpec as e:
        return Verdict(niveau="L0", nom="spécification conforme au domaine", etat="FAIL", details=[str(e)])


def l2_integrite(pb: Probleme, sol: Solution) -> Verdict:
    d = []
    connus = set(pb.participants)
    for t, a, b in sol.rencontres:
        if a == b:
            d.append(f"tour {t} : {a} rencontre lui-même")
        if a not in connus or b not in connus:
            d.append(f"tour {t} : participant inconnu ({a}, {b})")
        if not 1 <= t <= pb.tours:
            d.append(f"tour {t} hors de 1..{pb.tours}")
    return Verdict(niveau="L2", nom="intégrité des données", etat="FAIL" if d else "PASS", details=d)


def l3_preuves(sol: Solution, preuves: dict[str, list[str]], reg: Registre, spec: SpecDecision, jour: date) -> Verdict:
    d = []
    admis = set(spec.politique_preuve.statuts_admis)
    perimees = set(reg.perimees(jour, spec.politique_preuve.age_max_jours))
    for t, a, b in sol.rencontres:
        ids = preuves.get(cle(a, b), [])
        valables = [i for i in ids if i in reg and reg.get(i).statut in admis and i not in perimees]
        if len(valables) < spec.politique_preuve.preuves_minimum_par_proposition:
            d.append(f"{a}–{b} (tour {t}) : {len(valables)} preuve(s) admissible(s) sur {len(ids)}")
    return Verdict(niveau="L3", nom="chaque proposition rattachée à des affirmations admissibles", etat="FAIL" if d else "PASS", details=d)


def l5_structure(pb: Probleme, sol: Solution) -> Verdict:
    """Contraintes structurelles recalculées depuis la solution brute (pas depuis le solveur)."""
    d, vus_paires, par_tour = [], set(), {}
    for t, a, b in sol.rencontres:
        k = cle(a, b)
        if k in vus_paires:
            d.append(f"paire répétée : {k}")
        vus_paires.add(k)
        for p in (a, b):
            if p in par_tour.setdefault(t, set()):
                d.append(f"{p} deux fois au tour {t}")
            par_tour[t].add(p)
        if k in pb.exclues:
            d.append(f"paire interdite utilisée : {k} ({pb.exclues[k]})")
        if k not in pb.aretes:
            d.append(f"paire sans aide prouvée : {k}")
    return Verdict(niveau="L5", nom="contraintes structurelles (une par tour, paire unique, exclusions)", etat="FAIL" if d else "PASS", details=d)


def l6_faisabilite(sol: Solution) -> Verdict:
    if not sol.rencontres and sol.statut != "optimal":
        return Verdict(niveau="L6", nom="faisabilité", etat="FAIL", details=[f"solveur : {sol.statut}"])
    return Verdict(niveau="L6", nom="faisabilité", etat="PASS",
                   details=[f"statut {sol.statut}", "optimum prouvé" if sol.optimum_prouve else "optimum NON prouvé"])


def l8_humain() -> Verdict:
    return Verdict(niveau="L8", nom="revue humaine", etat="EN_ATTENTE", details=["aucune action sans approbation"])


ValidateurDomaine = Callable[[Solution], Verdict]


def echelle(spec, domaine, pb, sol, preuves, reg, jour, domaine_validateurs: list[ValidateurDomaine]) -> list[Verdict]:
    v = [l0_spec(spec, domaine), l2_integrite(pb, sol), l3_preuves(sol, preuves, reg, spec, jour), l5_structure(pb, sol)]
    v += [f(sol) for f in domaine_validateurs]
    v += [l6_faisabilite(sol)]
    return v


def statuts_utilises(sol: Solution, preuves: dict[str, list[str]], reg: Registre) -> dict[str, int]:
    ids = sorted({i for _, a, b in sol.rencontres for i in preuves.get(cle(a, b), []) if i in reg})
    return reg.comptes(ids)


__all__ = ["Verdict", "echelle", "l8_humain", "statuts_utilises", "Statut"]
