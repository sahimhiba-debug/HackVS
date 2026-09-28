"""Compilateur de décision : intention en langage naturel → spécification typée.

Version déterministe : une grammaire de motifs fournie par l'ADAPTATEUR (le cœur ne connaît aucun mot du domaine).
Le compilateur ne devine pas : ce qu'il ne reconnaît pas est listé, et s'il ne reconnaît aucun objectif il s'abstient.
Un compilateur par LLM peut être branché ensuite ; sa sortie passera par exactement la même validation (L0).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Callable

from pydantic import BaseModel

from .affirmations import Statut
from .specification import Domaine, ErreurSpec, Objectif, PolitiquePreuve, ResultatCompilation, SpecDecision, valider


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


class Regle(BaseModel):
    """Si `motif` apparaît, appliquer `effet` (ajouter/retirer un terme, fixer un paramètre)."""
    motif: str
    effet: str            # « objectif:nom[:poids] » | « retirer_contrainte:nom » | « ajouter_contrainte:nom » | « parametre:nom »
    libelle: str


class Grammaire(BaseModel):
    domaine: str
    objectifs_par_defaut: list[str] = []
    contraintes_par_defaut: list[str] = []
    parametres_par_defaut: dict[str, int] = {}
    statuts_admis: list[Statut] = [Statut.VERIFIE, Statut.DECLARE]
    regles: list[Regle]


def compiler(intention: str, grammaire: Grammaire, domaine: Domaine,
             revue: Callable[[SpecDecision], list[str]] | None = None) -> ResultatCompilation:
    n = norm(intention)
    objectifs: dict[str, float] = {}
    contraintes = list(grammaire.contraintes_par_defaut)
    parametres = dict(grammaire.parametres_par_defaut)
    reconnu: list[str] = []
    consomme: list[tuple[int, int]] = []
    for r in grammaire.regles:
        m = re.search(r.motif, n)
        if not m:
            continue
        consomme.append(m.span())
        reconnu.append(r.libelle)
        genre, _, reste = r.effet.partition(":")
        if genre == "objectif":
            nom, _, poids = reste.partition(":")
            objectifs[nom] = max(objectifs.get(nom, 0), float(poids or 1))
        elif genre == "retirer_contrainte":
            contraintes = [c for c in contraintes if c != reste]
        elif genre == "ajouter_contrainte" and reste not in contraintes:
            contraintes.append(reste)
        elif genre == "parametre":
            nombre = re.search(r"\d+", m.group(0))
            if nombre:
                parametres[reste] = int(nombre.group(0))
    mots = [w for w in re.findall(r"[a-z0-9]{4,}", n)]
    non_reconnu = [w for w in mots if not any(d <= n.find(w) < f for d, f in consomme)]
    # Un mot du vocabulaire du DOMAINE resté incompris (« consentement », « langue »…) : on ne devine pas, on escalade.
    vocab = {m for t in list(domaine.contraintes) + list(domaine.objectifs) for m in t.split("_") if len(m) >= 5}
    sensibles = sorted({w for w in non_reconnu for v in vocab if w.startswith(v[:6])})
    if sensibles:
        return ResultatCompilation(decision="ESCALADER_A_L_HUMAIN", reconnu=reconnu, non_reconnu=non_reconnu,
                                   raison=f"vous mentionnez {', '.join(sensibles)} : je n'ai pas compris ce que vous voulez en faire")
    # Une demande de lever une contrainte OBLIGATOIRE escalade toujours, même sans objectif reconnu :
    # s'abstenir en silence cacherait à l'humain qu'on a tenté de contourner la politique.
    levees = [c for c in domaine.contraintes_obligatoires if c not in contraintes]
    if levees:
        return ResultatCompilation(decision="ESCALADER_A_L_HUMAIN", reconnu=reconnu, non_reconnu=non_reconnu,
                                   raison=f"spécification refusée par la politique : contrainte obligatoire levée ({', '.join(levees)})")
    if not objectifs:
        if not grammaire.objectifs_par_defaut:
            return ResultatCompilation(decision="S_ABSTENIR", reconnu=reconnu, non_reconnu=non_reconnu,
                                       raison="aucun objectif reconnu : reformulez (ex. « maximiser les rencontres utiles »)")
        objectifs = {o: 1.0 for o in grammaire.objectifs_par_defaut}
    spec = SpecDecision(intention=intention, domaine=grammaire.domaine,
                        objectifs=[Objectif(nom=k, poids=v) for k, v in objectifs.items()],
                        contraintes_dures=contraintes, parametres=parametres,
                        politique_preuve=PolitiquePreuve(statuts_admis=grammaire.statuts_admis))
    try:
        valider(spec, domaine)
    except ErreurSpec as e:
        return ResultatCompilation(decision="ESCALADER_A_L_HUMAIN", spec=spec, reconnu=reconnu, non_reconnu=non_reconnu,
                                   raison=f"spécification refusée par la politique : {e}")
    return ResultatCompilation(decision="AGIR", spec=spec, reconnu=reconnu, non_reconnu=non_reconnu)
