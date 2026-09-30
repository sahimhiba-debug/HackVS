"""Règles fines des REÇUS et du RETRAIT, écrites pour tuer les mutants SURVIVANTS de la campagne d'ouverture de la
Phase 3 (code du re-consentement) : chaque test distingue le comportement voulu d'une variante fausse que la suite
laissait passer. Données FICTIVES."""
from datetime import timedelta

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.essai import Plage

TAX = charger_taxonomie()
A, B = "delegation_acheteurs", "atelier_cyber"
VENDREDI = md.JOUR_SCENE + timedelta(days=1)


@pytest.fixture
def club():
    return Demo(TAX).club


def _salle_de_markus_pour_deux_capacites(c):
    b = c.banc
    o = b.publier_offre(md.MARKUS, "lieu", "Salle polyvalente", 1, c.jour, VENDREDI, attributs={"places": 40},
                        plages=[Plage(jour=VENDREDI, debut="13:00", fin="18:00")])
    for f in (A, B):                                         # la MÊME pièce, consentie pour deux finalités
        p = c.capacites.patron(f)
        b.consentir_finalite(md.MARKUS, f, "salle", o, p.portee("salle"), p.fenetre.jour)
    return o


def test_un_retrait_ne_touche_que_sa_finalite_meme_piece_meme_personne(club):
    """recus : le retrait cherché est un RETRAIT, de CETTE finalité, de CETTE pièce — pas un autre accord de la même
    pièce, ni le retrait d'une autre finalité."""
    _salle_de_markus_pour_deux_capacites(club)
    club.retirer_consentement(md.MARKUS, B)
    etats = {r["finalite"]: (r["etat"], r["retire_le"]) for r in club.capacites.recus(md.MARKUS)}
    assert etats[A] == ("valable", None)
    assert etats[B] == ("consentement retiré", club.jour.isoformat())


def test_le_numero_d_accord_se_compte_par_finalite_et_par_piece(club):
    """recus : « accord n » compte les accords d'UN emplacement d'UNE finalité, pas tous ceux du membre."""
    _salle_de_markus_pour_deux_capacites(club)
    assert [(r["finalite"], r["accord"]) for r in club.capacites.recus(md.MARKUS)] == [(A, 1), (B, 1)]


def test_le_recu_d_un_consentement_qui_ne_vaut_plus_le_dit(club):
    """recus : un consentement dont le membre ne peut plus assurer la pièce (cas 3 et 7) n'est pas « valable »."""
    club.repondre_ask(md.PAULINE, club.asks_pour(md.PAULINE)[0][1], True, {"places": 14})
    club.modifier_profil(md.ANNA, disponible=False)
    r = club.capacites.recus(md.ANNA)[0]
    assert (r["etat"], r["revocable"]) == ("le membre ne peut plus assurer cette pièce", False)


def test_retirer_ne_retire_pas_deux_fois_une_piece_deja_retiree(club):
    """retirer : la pièce née de la réponse est retirée avec le consentement — sauf si son auteur l'a DÉJÀ retirée :
    aucun second fait « offre retirée »."""
    club.repondre_ask(md.PAULINE, club.asks_pour(md.PAULINE)[0][1], True, {"places": 14})
    oid = club.capacites.instance(club.capacites.patron(A)).liaisons["minibus"]
    club.banc.retirer_offre(md.PAULINE, oid)                  # retirée directement, le consentement court encore
    club.retirer_consentement(md.PAULINE, A)
    assert [e.donnees["offre"] for e in club.journal.evenements("OFFRE_RETIREE")].count(oid) == 1
