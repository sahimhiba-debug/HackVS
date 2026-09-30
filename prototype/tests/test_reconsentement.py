"""RE-CONSENTEMENT (correctif de sémantique, avant la Phase 3). Le retrait tue DÉFINITIVEMENT la claim et son
consentement pour cette finalité ; mais une NOUVELLE déclaration avec un NOUVEAU consentement reste possible (accord
n+1). L'ancien accord ne ressuscite jamais, ni en silence ni sur demande : l'historique montre deux consentements
distincts, le premier toujours révoqué. Avant ce correctif, la personne retirée était exclue à jamais de la finalité.
Données FICTIVES."""
import dataclasses
from datetime import timedelta

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import NICOLAS, Demo
from intelligence.erreurs import Conflit
from intelligence.essai import Plage

TAX = charger_taxonomie()
A = "delegation_acheteurs"
VENDREDI = md.JOUR_SCENE + timedelta(days=1)


@pytest.fixture
def club():
    c = Demo(TAX).club
    c.reglages = dataclasses.replace(c.reglages, plafond_jours=0)      # le plafond d'attention n'est pas l'objet ici
    return c


def _repondre(c, pid, places):
    ask = next(a for _, a in c.asks_pour(pid) if a.startswith(A))
    return c.repondre_ask(pid, ask, True, {"places": places})


def test_retrait_puis_nouvelle_declaration_deux_consentements_distincts(club):
    _repondre(club, md.PAULINE, 14)
    premiere = club.capacites.instance(club.capacites.patron(A)).liaisons["minibus"]
    club.retirer_consentement(md.PAULINE, A)
    assert club.banc.etat_offre(premiere) == "retiree"                   # la claim née de la réponse est morte
    assert any(a.startswith(A) for _, a in club.asks_pour(md.PAULINE))  # …mais la personne peut répondre à nouveau
    inst = _repondre(club, md.PAULINE, 16)
    assert inst.statut == "ACTIVE" and inst.liaisons["minibus"] != premiere
    recus = club.capacites.recus(md.PAULINE)
    assert [(r["accord"], r["etat"], r["offre"]) for r in recus] == [
        (1, "consentement retiré", "Un minibus de 12 places ou plus"), (2, "valable", "Un minibus de 12 places ou plus")]
    assert recus[0]["retire_le"] == club.jour.isoformat() and recus[1]["retire_le"] is None
    assert recus[0]["reference"] != recus[1]["reference"]
    miens = [e for e in club.journal.evenements("ACCORD", "RETRAIT") if e.acteurs == [md.PAULINE] and e.donnees.get("finalite") == A]
    assert [e.type for e in miens] == ["ACCORD", "RETRAIT", "ACCORD"]


def test_l_ancien_accord_ne_ressuscite_jamais(club):
    _repondre(club, md.PAULINE, 14)
    premiere = club.capacites.instance(club.capacites.patron(A)).liaisons["minibus"]
    club.retirer_consentement(md.PAULINE, A)
    _repondre(club, md.PAULINE, 16)
    club.retirer_consentement(md.PAULINE, A)                              # le second aussi : les deux sont révoqués
    assert [r["etat"] for r in club.capacites.recus(md.PAULINE)] == ["consentement retiré", "consentement retiré"]
    assert club.capacites.instance(club.capacites.patron(A)).statut == "DEGRADED"
    p = club.capacites.patron(A)
    with pytest.raises(Conflit, match="déclarez-en une nouvelle"):
        club.banc.consentir_finalite(md.PAULINE, A, "minibus", premiere, p.portee("minibus"), VENDREDI)


def test_une_piece_qui_sert_ailleurs_reste_vivante_mais_exclue_de_cette_finalite(club):
    _repondre(club, md.PAULINE, 14)
    salle = club.capacites.instance(club.capacites.patron(A)).liaisons["salle"]
    club.retirer_consentement(NICOLAS, A)
    assert club.banc.etat_offre(salle) == "active"                       # publiée hors de la demande : elle vit pour le reste
    p = club.capacites.patron(A)
    with pytest.raises(Conflit, match="déclarez-en une nouvelle"):
        club.banc.consentir_finalite(NICOLAS, A, "salle", salle, p.portee("salle"), VENDREDI)
    assert club.capacites.instance(p).liaisons.get("salle") != salle    # jamais recomposée avec l'ancienne pièce
    nouvelle = club.banc.publier_offre(NICOLAS, "lieu", "Salle de la distillerie, nouvelle déclaration", 1, club.jour, VENDREDI,
                                       attributs={"places": 24}, plages=[Plage(jour=VENDREDI, debut="13:00", fin="18:00")])
    club.banc.consentir_finalite(NICOLAS, A, "salle", nouvelle, p.portee("salle"), VENDREDI)
    inst = club.capacites.instance(p)
    assert inst.statut == "ACTIVE" and inst.liaisons["salle"] == nouvelle
    assert [r["etat"] for r in club.capacites.recus(NICOLAS)] == ["consentement retiré", "valable"]
