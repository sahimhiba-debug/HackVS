"""Référence simple : mêmes filtres durs + classement par mots-clés en commun.

C'est ce que ferait un annuaire classique avec une barre de recherche et des filtres.
Sert à mesurer ce que la compréhension du besoin apporte réellement.
"""
from __future__ import annotations

from .matching import _tokens, _public, filtres_durs, texte_profil
from .models import Besoin, Preuve, Profil, Resultat, Suggestion
from .taxonomy import Taxonomie


def rechercher_mots_cles(
    besoin: Besoin, demandeur: Profil, profils: list[Profil], tax: Taxonomie, limite: int = 5
) -> Resultat:
    requete = set(_tokens(besoin.texte))
    res = []
    for p in profils:
        if filtres_durs(besoin, demandeur, p, tax):
            continue
        communs = requete & set(_tokens(texte_profil(p)))
        if communs:
            res.append(Suggestion(
                profil=_public(p), niveau="partielle",
                preuves=[Preuve(critere="Mots en commun", champ="presentation", extrait=", ".join(sorted(communs)), nature="deduit")],
                score=float(len(communs)),
            ))
    res.sort(key=lambda s: (-s.score, s.profil.nom))
    return Resultat(
        mode="reference_mots_cles", suggestions=res[:limite], abstention=not res,
        message="" if res else "Aucun mot-clé en commun.",
    )
