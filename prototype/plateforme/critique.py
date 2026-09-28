"""Critique (objections) et gardien (politique), déterministes. Un LLM peut s'ajouter comme critique supplémentaire ;
ses objections seraient marquées INFÉRÉ et ne pourraient pas lever un blocage du gardien.

Position de chaque agent : SOUTIEN | PRUDENCE | BLOCAGE. Le désaccord est une donnée : il est conservé, pas lissé.
"""
from __future__ import annotations

from collections import Counter
from typing import Callable, Literal

from pydantic import BaseModel

from .affirmations import Registre, Statut
from .optimisation import Probleme, Solution, cle

Position = Literal["SOUTIEN", "PRUDENCE", "BLOCAGE"]


class Objection(BaseModel):
    code: str
    gravite: Literal["info", "materielle", "bloquante"]
    message: str
    ouverte: bool = True


class Avis(BaseModel):
    agent: str
    position: Position
    objections: list[Objection] = []


def critique(pb: Probleme, sol: Solution, preuves: dict[str, list[str]], reg: Registre,
             sensibilite: list[dict] | None = None) -> Avis:
    obj: list[Objection] = []
    servis = {p for _, a, b in sol.rencontres for p in (a, b)}
    non_servis = [p for p in pb.participants if p not in servis]
    if non_servis:
        obj.append(Objection(code="non_servis", gravite="materielle",
                             message=f"{len(non_servis)} participant(s) sur {len(pb.participants)} sans rencontre utile"))
    faibles = []
    for _, a, b in sol.rencontres:
        st = {reg.get(i).statut for i in preuves.get(cle(a, b), []) if i in reg}
        if st and st <= {Statut.INFERE, Statut.SYNTHETIQUE, Statut.SIMULE}:
            faibles.append(cle(a, b))
    if faibles:
        obj.append(Objection(code="preuves_non_verifiees", gravite="materielle",
                             message=f"{len(faibles)} rencontre(s) sur {len(sol.rencontres)} reposent uniquement sur des affirmations "
                                     "inférées ou synthétiques (aucune n'est VÉRIFIÉE)"))
    charge = Counter(p for _, a, b in sol.rencontres for p in (a, b))
    if charge and sol.rencontres and max(charge.values()) == pb.tours and pb.tours > 1:
        n = sum(1 for v in charge.values() if v == pb.tours)
        obj.append(Objection(code="concentration", gravite="info", message=f"{n} participant(s) occupé(s) à tous les tours"))
    for s in sensibilite or []:
        if s["part_changee"] > 0.3:
            obj.append(Objection(code="fragilite", gravite="materielle",
                                 message=f"un poids {s['terme']} ×{s['facteur']} change {int(100 * s['part_changee'])} % des rencontres"))
    pos: Position = "PRUDENCE" if any(o.gravite != "info" for o in obj) else "SOUTIEN"
    return Avis(agent="critique", position=pos, objections=obj)


RegleGardien = Callable[[Solution], list[Objection]]


def gardien(sol: Solution, regles: list[RegleGardien]) -> Avis:
    obj = [o for r in regles for o in r(sol)]
    return Avis(agent="gardien", position="BLOCAGE" if any(o.gravite == "bloquante" for o in obj) else "SOUTIEN", objections=obj)


class Mediation(BaseModel):
    decision: Literal["PROPOSER_A_L_HUMAIN", "BLOQUER", "DEMANDER_PLUS_DE_PREUVES", "S_ABSTENIR"]
    raisons: list[str]


def mediateur(verdicts: list, avis: list[Avis], sol: Solution) -> Mediation:
    echecs = [f"{v.niveau} {v.nom}" for v in verdicts if v.etat == "FAIL"]
    if not sol.rencontres:
        return Mediation(decision="S_ABSTENIR", raisons=["aucune rencontre possible sous ces contraintes"] + echecs)
    if echecs:
        return Mediation(decision="BLOQUER", raisons=echecs)
    if any(a.position == "BLOCAGE" for a in avis):
        return Mediation(decision="BLOQUER", raisons=[o.message for a in avis for o in a.objections if o.gravite == "bloquante"])
    raisons = [f"{a.agent} : {o.message}" for a in avis for o in a.objections if o.gravite == "materielle"]
    return Mediation(decision="PROPOSER_A_L_HUMAIN", raisons=raisons or ["aucune objection matérielle"])
