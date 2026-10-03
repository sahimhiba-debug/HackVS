"""TABLEAU DE BORD DU SECRÉTARIAT (P3 n°10) — une page, ce qui demande une action du secrétariat cette semaine.

Assemblé depuis ce qui existe (Le Club cherche, Suivi, passes découverte, annonces, associés) : agrégats seulement,
aucun nom ; tout décompte venant de moins de trois entreprises s'affiche « < 3 ». Une demande est « bloquée » quand
elle attend une réponse depuis au moins SEUIL_BLOQUEE jours (de l'horloge du monde, simulée en démonstration)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import annonces, associe, club_cherche, liens

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

SEUIL_BLOQUEE = 3


def calculer(c: "ClubPulse") -> dict:
    k = c.reglages.k_anonymat
    cherche = club_cherche.calculer(c)
    demandes = [d for g in cherche["metiers"] for d in g["demandes"]]
    bloquees = [d for d in demandes if d["age_jours"] >= SEUIL_BLOQUEE]
    inv = c.decouverte.statistiques(None, k) if getattr(c, "decouverte", None) is not None else {}
    return {
        "monde": "monde de démonstration", "k": k,
        "demandes_sans_reponse": len(demandes),                # une demande ne désigne personne : dite telle quelle
        "demandes_bloquees": len(bloquees), "seuil_bloquee_jours": SEUIL_BLOQUEE,
        "metiers_manquants": [{"metier": g["libelle"], "demandes": g["nombre"], "age_max_jours": g["age_max_jours"]}
                              for g in cherche["metiers"]],
        "invites_actifs": inv.get("actifs", 0),
        "nouveaux_liens": liens.nouveaux(c, None)["nouveaux"],
        "annonces": annonces.agregats(c),
        "associes": associe.agregats(c)["associes"],
        "regle": f"Agrégats seulement, aucun nom. Tout décompte venant de moins de {k} entreprises s'affiche « < {k} ».",
    }
