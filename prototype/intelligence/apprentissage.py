"""APPRENDRE sans entraîner : une activation dont l'effet est CONFIRMÉ par le bénéficiaire devient un MOTIF vérifié.

Un motif ne dit pas « A connaît B ». Il dit : « dans ce contexte, cette combinaison de capacités, par cette
séquence d'actions, a débloqué ce type de besoin — confirmé par la personne aidée, à telle date ».
Il est réutilisé pour une situation future semblable (même capacités), avec :
- sa fraîcheur (un motif de plus d'un an n'est plus proposé tel quel) ;
- ses confirmations (plusieurs bénéficiaires ⇒ preuve plus solide) ;
- ce qui DIFFÈRE du contexte d'origine (secteur, langue) : dit, jamais masqué ;
- sa provenance (activation d'origine) — sans jamais nommer le bénéficiaire d'origine.
Aucun poids, aucun modèle : la mémoire est un journal d'événements lisible et rejouable.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Optional

from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

FRAICHEUR_JOURS = 365           # hypothèse de produit : au-delà, un motif est « à revalider »


def _id(*parts: str) -> str:
    return "m" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:10]


def enregistrer(m: Memoire, le: date, *, type_: str, secteur: Optional[str], concepts: list[str], sequence: list[str],
                contributions: list[dict], contributeurs: list[str], resultat: str, activation: str,
                statut: Statut = Statut.SIMULE) -> str:
    if resultat not in ("debloque", "partiel"):
        raise ValueError("seul un effet confirmé (débloqué ou partiel) devient un motif")
    mid = _id(activation, json.dumps(sorted(concepts)))
    m.ajouter(Evt(type="MOTIF_VERIFIE", le=le, acteurs=contributeurs, statut=statut,
                  donnees={"motif_id": mid, "type": type_, "secteur": secteur, "concepts": sorted(concepts),
                           "sequence": sequence, "contributions": contributions, "resultat": resultat,
                           "activation": activation}))
    return mid


def confirmer_reutilisation(m: Memoire, le: date, motif_id: str, activation: str, resultat: str,
                            statut: Statut = Statut.SIMULE) -> None:
    """Un nouveau bénéficiaire confirme qu'un motif réutilisé l'a aidé : la preuve s'accumule."""
    if resultat not in ("debloque", "partiel", "non"):
        raise ValueError("verdict inconnu")
    m.ajouter(Evt(type="MOTIF_RECONFIRME", le=le, statut=statut,
                  donnees={"motif_id": motif_id, "activation": activation, "resultat": resultat}))


def motifs(m: Memoire, aujourd_hui: date) -> list[dict]:
    reconf: dict[str, list[dict]] = {}
    for e in m.evenements("MOTIF_RECONFIRME"):
        reconf.setdefault(e.donnees["motif_id"], []).append({"le": e.le.isoformat(), "resultat": e.donnees["resultat"]})
    res = []
    for e in m.evenements("MOTIF_VERIFIE"):
        if e.le > aujourd_hui:
            continue
        d = e.donnees
        confs = [{"le": e.le.isoformat(), "resultat": d["resultat"]}] + reconf.get(d["motif_id"], [])
        positives = [c for c in confs if c["resultat"] in ("debloque", "partiel")]
        derniere = max(date.fromisoformat(c["le"]) for c in positives)
        age = (aujourd_hui - derniere).days
        res.append(d | {"le": e.le.isoformat(), "contributeurs": list(e.acteurs), "confirmations": len(positives),
                        "echecs": len(confs) - len(positives), "age_jours": age, "frais": age <= FRAICHEUR_JOURS,
                        "statut": e.statut.value})
    return res


def chercher(m: Memoire, concepts: set[str], aujourd_hui: date, secteur: Optional[str] = None,
             connus: Optional[list[dict]] = None) -> list[dict]:
    """Motifs frais qui couvrent au moins une des capacités demandées, avec les différences de contexte.
    `connus` : motifs déjà calculés pour CETTE analyse (même mémoire, même date) — évite de relire le journal par demande."""
    res = []
    for x in (motifs(m, aujourd_hui) if connus is None else connus):
        communs = concepts & set(x["concepts"])
        if not communs or not x["frais"] or x["echecs"] >= x["confirmations"]:
            continue
        diff = []
        if secteur and x["secteur"] and secteur != x["secteur"]:
            diff.append(f"confirmé dans le secteur « {x['secteur']} », ici « {secteur} » : à vérifier")
        res.append(x | {"couvre": sorted(communs), "differences": diff})
    return sorted(res, key=lambda x: (-len(x["couvre"]), -x["confirmations"], x["age_jours"], x["motif_id"]))
