"""Collisions d'événements (scénario adversarial n° 16) et plan devenu faux entre approbation et enregistrement.
Données FICTIVES."""
import json
from datetime import date

import pytest

from adaptateurs.club import cycle as cy
from adaptateurs.club.adaptateur import AdaptateurClub
from app.models import Profil
from app.taxonomy import DATA_DIR, charger_taxonomie
from plateforme import action as ac
from plateforme import memoire as me
from plateforme import pipeline as pl
from plateforme.affirmations import Statut
from plateforme.execution import Journal

TAX = charger_taxonomie()
P = [Profil(**p) for p in json.loads((DATA_DIR / "profils_demo.json").read_text(encoding="utf-8"))["profils"]]
J0 = date(2026, 10, 3)


def _plan_approuve(m, j, demande="tout le monde au moins une rencontre utile, 3 tours"):
    ad = AdaptateurClub(lambda: (P, [], cy.relations(m, m.maintenant(J0)), "demo"), TAX)
    r = pl.executer(ad, demande, j, sensibilite=False)
    ac.decider(j, r.run_id, ac.DecisionHumaine(verdict="APPROUVER", par="org"))
    return r


def test_deux_soirees_le_meme_jour_ne_placent_personne_a_deux_tables():
    m, j = me.Memoire(), Journal()
    r1 = _plan_approuve(m, j)
    r2 = _plan_approuve(m, j, "tout le monde au moins une rencontre utile, 2 tours")
    cy.enregistrer_soiree(m, j, r1.run_id, "Soirée A", J0)
    with pytest.raises(cy.ErreurCycle, match="même jour"):
        cy.enregistrer_soiree(m, j, r2.run_id, "Soirée B", J0)
    assert len(m.evenements("EVENEMENT_TENU")) == 1
    cy.enregistrer_soiree(m, j, r2.run_id, "Soirée B", date(2026, 10, 10))   # un autre jour : permis


def test_un_plan_devenu_faux_apres_approbation_n_est_pas_enregistre():
    m, j = me.Memoire(), Journal()
    r = _plan_approuve(m, j)
    _, a, b = r.retenue["rencontres"][0]
    m.ajouter(me.Evt(type="INTRO_DEMANDEE", le=J0, acteurs=[a, b], statut=Statut.OBSERVE, donnees={"relation_id": "x"}))
    m.ajouter(me.Evt(type="INTRO_DECLINEE", le=J0, acteurs=[a, b], statut=Statut.OBSERVE, donnees={"relation_id": "x"}))
    with pytest.raises(cy.ErreurCycle, match="périmé"):
        cy.enregistrer_soiree(m, j, r.run_id, "Soirée", J0)
    assert not m.evenements("RENCONTRE")
