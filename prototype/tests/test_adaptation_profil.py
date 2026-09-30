"""Cas 3 et 7 de l'inspection du pivot (A4) : un fait déclaré dans le PROFIL — retirer une compétence, se déclarer
indisponible, ne plus souhaiter être sollicité·e — dégrade les accords et les consentements concernés, comme un
changement d'offre. Avant ce correctif, l'essai restait AUTORISÉ et la capacité ACTIVE (sonde de l'inspection).
Le motif montré est GÉNÉRIQUE : il ne dit pas lequel des trois (ni qui, sur les écrans communs). Données FICTIVES."""
import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.erreurs import Conflit

TAX = charger_taxonomie()
A = "delegation_acheteurs"


def _essai_autorise():
    d = Demo(TAX)
    for _ in range(4):                                       # accords réunis : AUTORISÉ
        d.suivant()
    c, eid = d.club, d.ctx["essai"]
    assert c.banc.etat(eid) == "AUTORISE"
    return c, eid


@pytest.mark.parametrize("changement", [{"retirer_capacite": "traduction"}, {"disponible": False}, {"accepte": False}],
                         ids=["competence_retiree", "indisponible", "non_sollicitable"])
def test_un_changement_de_profil_degrade_l_accord_de_l_essai(changement):
    c, eid = _essai_autorise()
    c.modifier_profil(md.LEA, **changement)
    assert c.banc.etat(eid) in ("A_ADAPTER", "IMPOSSIBLE")
    raison = c.banc.couverture(eid)[md.LEA]
    assert raison is not None and "ne peut plus assurer" in raison
    for mot in ("indisponible", "sollicit", "compétence"):
        assert mot not in raison                              # générique : ne dit pas lequel des trois
    with pytest.raises(Conflit):
        c.banc.lancer(c.banc.porteur(eid), eid, c.banc.version(eid))


def test_redevenir_disponible_rouvre_une_reprise_choisie_par_le_porteur():
    c, eid = _essai_autorise()
    c.modifier_profil(md.LEA, disponible=False)
    c.modifier_profil(md.LEA, disponible=True)
    assert c.banc.etat(eid) == "A_ADAPTER"                    # rien n'est relancé tout seul
    assert any(a["type"] == "reprendre" for a in c.banc.alternatives(eid))


@pytest.mark.parametrize("changement", [{"retirer_capacite": "traduction"}, {"disponible": False}, {"accepte": False}],
                         ids=["competence_retiree", "indisponible", "non_sollicitable"])
def test_un_changement_de_profil_degrade_la_capacite(changement):
    c = Demo(TAX).club
    ask = c.capacites.instance(c.capacites.patron(A)).ask
    c.repondre_ask(md.PAULINE, ask.id, True, {"places": 14})
    assert c.capacites.instance(c.capacites.patron(A)).statut == "ACTIVE"
    c.modifier_profil(md.ANNA, **changement)                  # l'interprète de la capacité
    inst = c.capacites.instance(c.capacites.patron(A))
    assert inst.statut == "DEGRADED"
    assert inst.perdus == ["interp : le membre ne peut plus assurer cette pièce"]
