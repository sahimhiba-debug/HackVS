"""Scénarios adversariaux du réseau (liste du brief) non couverts ailleurs : relation expirée, opportunité devenue
ancienne, historique contradictoire (un refus ancien ne doit pas écraser une relation devenue vivante), refus récent."""
from datetime import date, timedelta

from adaptateurs.club import reseau
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

J0 = date(2026, 1, 5)


def _evt(m, typ, jours, st=Statut.OBSERVE, **donnees):
    m.ajouter(Evt(type=typ, le=J0 + timedelta(days=jours), acteurs=["a", "b"], statut=st, donnees=donnees))


def test_relation_expiree_devient_a_raviver():
    m = Memoire()
    _evt(m, "RENCONTRE", 0, Statut.DECLARE)
    assert reseau.etat_relation(m, "a", "b", J0 + timedelta(days=90))["etat"] == "SUIVI_EN_ATTENTE"
    assert reseau.etat_relation(m, "a", "b", J0 + timedelta(days=91))["etat"] == "A_RAVIVER"


def test_opportunite_devenue_ancienne_est_signalee():
    m = Memoire()
    _evt(m, "RENCONTRE", 0, Statut.DECLARE)
    _evt(m, "RESULTAT", 5, Statut.DECLARE, resultat="affaire_en_cours")
    assert reseau.etat_relation(m, "a", "b", J0 + timedelta(days=30))["etat"] == "OPPORTUNITE"
    assert reseau.etat_relation(m, "a", "b", J0 + timedelta(days=200))["etat"] == "A_RAVIVER"


def test_un_refus_ancien_n_ecrase_pas_une_relation_devenue_vivante():
    """Historique contradictoire : une introduction déclinée en janvier, puis une autre acceptée et une rencontre en
    mars. L'état courant suit les faits les plus RÉCENTS ; le refus reste visible dans l'historique."""
    m = Memoire()
    _evt(m, "INTRO_DEMANDEE", 0, relation_id="r1")
    _evt(m, "INTRO_DECLINEE", 1, relation_id="r1")
    _evt(m, "INTRO_DEMANDEE", 60, relation_id="r2")
    _evt(m, "INTRO_ACCEPTEE", 61, relation_id="r2")
    _evt(m, "RENCONTRE", 65, Statut.DECLARE, relation_id="r2")
    e = reseau.etat_relation(m, "a", "b", J0 + timedelta(days=66))
    assert e["etat"] == "RENCONTREE", e["etat"]
    assert "INTRO_DECLINEE" in [f["type"] for f in e["faits"]]


def test_un_refus_recent_reste_terminal():
    m = Memoire()
    _evt(m, "INTRO_DEMANDEE", 0, relation_id="r1")
    _evt(m, "INTRO_ACCEPTEE", 1, relation_id="r1")
    _evt(m, "INTRO_DEMANDEE", 30, relation_id="r2")
    _evt(m, "INTRO_DECLINEE", 31, relation_id="r2")
    assert reseau.etat_relation(m, "a", "b", J0 + timedelta(days=32))["etat"] == "DECLINEE"
