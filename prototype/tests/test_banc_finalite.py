"""Extensions du banc pour le registre des capacités : contraintes NUMÉRIQUES d'un emplacement (une offre ne couvre
que si elle DÉCLARE au moins autant) et consentement de FINALITÉ (le mécanisme de l'accord : empreinte de ce qui est
accepté + empreinte matérielle de l'offre, borné dans le temps). Données FICTIVES."""
from datetime import date, timedelta

import pytest

from intelligence.erreurs import Conflit, Interdit, Invalide
from intelligence.essai import Banc, Etape, Plage
from plateforme.memoire import Memoire

J = date(2026, 10, 6)


@pytest.fixture
def banc():
    jour = {"j": J}
    b = Banc(Memoire(), lambda: jour["j"], lambda pid: f"org-{pid}")
    b.jour = jour                                                  # type: ignore[attr-defined]
    return b


def _salle(b, places):
    return b.publier_offre("m1", "lieu", "Une salle", 1, J, J + timedelta(days=3), attributs={"places": places} if places else None,
                           plages=[Plage(jour=J + timedelta(days=3), debut="13:00", fin="18:00")])


def test_une_contrainte_numerique_n_est_couverte_que_si_l_offre_la_declare(banc):
    e = Etape(id="salle", nature="lieu", geste="Prêter une salle", duree_min=60, minimums={"places": 15})
    assert banc.offre_couvre(banc.offre(_salle(banc, 24)), e, J + timedelta(days=3)) is None
    assert banc.offre_couvre(banc.offre(_salle(banc, 12)), e, J + timedelta(days=3)) == "places : 12 déclaré(s), 15 demandé(s)"
    assert banc.offre_couvre(banc.offre(_salle(banc, None)), e, J + timedelta(days=3)) == "places : 0 déclaré(s), 15 demandé(s)"


def test_le_consentement_de_finalite_suit_l_offre_la_finalite_et_le_temps(banc):
    oid = _salle(banc, 24)
    portee = {"finalite": "f", "version": 1}
    banc.consentir_finalite("m1", "f", "salle", oid, portee, J + timedelta(days=3))
    dernier = lambda: banc.consentements_finalite("f")[-1]  # noqa: E731
    assert banc.raison_consentement(dernier(), portee) is None
    assert banc.raison_consentement(dernier(), portee | {"version": 2}) == "la finalité a changé depuis le consentement"
    banc.modifier_offre("m1", oid, attributs=None, conditions="seulement le matin")
    assert banc.raison_consentement(dernier(), portee) == "les conditions de l'offre ont changé depuis le consentement"
    banc.jour["j"] = J + timedelta(days=4)
    assert banc.raison_consentement(dernier(), portee) == "consentement expiré"


def test_on_ne_consent_que_pour_sa_propre_offre_active(banc):
    oid = _salle(banc, 24)
    with pytest.raises(Interdit):
        banc.consentir_finalite("m2", "f", "salle", oid, {}, J + timedelta(days=3))
    with pytest.raises(Invalide):
        banc.consentir_finalite("m1", "f", "salle", oid, {}, J - timedelta(days=1))
    banc.retirer_offre("m1", oid)
    with pytest.raises(Conflit):
        banc.consentir_finalite("m1", "f", "salle", oid, {}, J + timedelta(days=3))


def test_un_consentement_de_finalite_n_est_pas_un_accord_d_essai(banc):
    oid = _salle(banc, 24)
    banc.consentir_finalite("m1", "f", "salle", oid, {}, J + timedelta(days=3))
    assert banc.essais() == [] and banc.reservations(oid) == 0         # il ne réserve rien et n'engage aucun essai
