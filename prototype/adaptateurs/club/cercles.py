"""Micro-cercles : une nouvelle COMBINAISON de 3 à 5 personnes où chacune aide ou est aidée, avec preuves.

Glouton déterministe et explicable (pas de boîte noire) : à partir d'un membre, on ajoute à chaque pas le membre qui
apporte le plus d'aides PROUVÉES avec le groupe (dans les deux sens), en préférant, à égalité, celui qui n'est pas déjà
relié au groupe (nouveauté, ponts). Personne n'y entre « pour faire nombre » : un membre sans aide interne est retiré.
C'est une PROPOSITION : chaque membre doit accepter ; le format de groupe n'est couvert par aucun consentement existant.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import networkx as nx

from app.models import Profil
from app.soiree import calculer_aides


def proposer(depart: str, profils: list[Profil], besoins_publics: list, tax, g: nx.Graph, theme: str,
             taille_max: int = 5, taille_min: int = 3, exclure: Optional[set[str]] = None,
             maintenant: Optional[date] = None, profil_ancien_jours: int = 365) -> dict:
    par_id = {p.id: p for p in profils}
    if depart not in par_id:
        return {"decision": "S_ABSTENIR", "raison": "membre inconnu"}
    ecartes = {p.id: "n'accepte pas les introductions" for p in profils if not p.accepte_introductions and p.id != depart}
    admis = [p for p in profils if (p.accepte_introductions or p.id == depart) and p.id not in (exclure or set())]
    ici = {p.id: p.model_copy(update={"accepte_introductions": True}) if p.id == depart else p for p in admis}
    aides = calculer_aides(list(ici.values()), besoins_publics, tax)       # (aidé, aidant) → preuve
    cercle = [depart]

    def apport(v: str) -> tuple[int, int]:
        n = sum(1 for c in cercle if (v, c) in aides) + sum(1 for c in cercle if (c, v) in aides)
        nouveau = sum(1 for c in cercle if not g.has_edge(v, c))
        return n, nouveau

    while len(cercle) < taille_max:
        cands = sorted((v for v in ici if v not in cercle), key=lambda v: (-apport(v)[0], -apport(v)[1], v))
        if not cands or apport(cands[0])[0] == 0:
            break
        cercle.append(cands[0])
    internes = {(i, j): a for (i, j), a in aides.items() if i in cercle and j in cercle}
    cercle = [m for m in cercle if any(m in k for k in internes)]
    if len(cercle) < taille_min:
        return {"decision": "S_ABSTENIR", "theme": theme,
                "raison": f"pas assez d'aides prouvées pour réunir {taille_min} personnes autour de « {theme} »",
                "membres": cercle}
    paires = [(a, b) for i, a in enumerate(cercle) for b in cercle[i + 1:]]
    nouvelles = [[a, b] for a, b in paires if not g.has_edge(a, b)]
    composantes = sorted({min(nx.node_connected_component(g, m)) if m in g else m for m in cercle})
    return {
        "decision": "PROPOSER_A_L_HUMAIN", "theme": theme, "membres": cercle,
        "noms": [par_id[m].nom for m in cercle],
        "aides": _vue_aides(internes, par_id),
        "nouveaux_liens": nouvelles, "groupes_relies": len(composantes),
        "ecartes": {"n'accepte pas les introductions": len(ecartes)},
        "inconnu": ["accord de chaque membre pour un format de groupe : à demander (aucun consentement existant ne le couvre)",
                    "disponibilités communes : non établies", "résultat : rien ne garantit qu'un cercle produise une collaboration"]
                   + _anciens(cercle, par_id, maintenant, profil_ancien_jours)
                   + [f"{a['aide']} → {a['aide_a']} : preuve seulement DÉDUITE d'un texte libre, à vérifier"
                      for a in _vue_aides(internes, par_id) if a["nature"] == "deduit"],
        "statut": "PROPOSITION",
    }


def _vue_aides(internes: dict, par_id: dict) -> list[dict]:
    return [{"aide": par_id[j].nom, "aide_a": par_id[i].nom, "besoin": a["besoin"], "preuve": a["preuve"],
             "nature": "declare" if a["nature_preuve"] == "declare" else "deduit"} for (i, j), a in sorted(internes.items())]


def _anciens(cercle: list[str], par_id: dict, maintenant: Optional[date], seuil: int) -> list[str]:
    res = []
    for m in cercle:
        maj = par_id[m].maj
        if maintenant and maj:
            age = (maintenant - date.fromisoformat(maj[:10])).days
            if age > seuil:
                res.append(f"profil de {par_id[m].nom} non mis à jour depuis {age} jours : son offre peut avoir changé")
    return res
