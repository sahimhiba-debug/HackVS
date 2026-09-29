"""Atomicité : une commande qui écrit plusieurs faits les écrit TOUS ou AUCUN (transaction SQLite du journal).

Régression : `lancer` écrivait « EN_ATTENTE_ACCORD » puis levait sur le budget d'attention → activation bloquée
sans aucune sollicitation (état partiel, irrécupérable)."""
from datetime import date

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.activation import BUDGET_ATTENTION, ErreurActivation, Moteur
from intelligence.detection import scanner
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

TAX = charger_taxonomie()


def test_transaction_valide_tout_ou_rien():
    m = Memoire()
    m.ajouter(Evt(type="A", le=date(2026, 1, 1), statut=Statut.SIMULE))
    avant = m.empreinte()
    with pytest.raises(RuntimeError):
        with m.transaction():
            m.ajouter(Evt(type="B", le=date(2026, 1, 1), statut=Statut.SIMULE))
            assert len(m.evenements()) == 2                          # visible DANS la transaction
            raise RuntimeError("panne au milieu")
    assert m.empreinte() == avant and [e.type for e in m.evenements()] == ["A"]
    with m.transaction():
        with m.transaction():                                         # imbriquée : seule l'externe valide
            m.ajouter(Evt(type="C", le=date(2026, 1, 1), statut=Statut.SIMULE))
    assert [e.type for e in m.evenements()] == ["A", "C"]


def test_lancer_sans_budget_ne_laisse_aucun_etat_partiel():
    r = md.construire()
    opp = next(o for o in scanner(r, TAX)["opportunites"] if o.beneficiaire == md.SOPHIE)
    mo = Moteur(r, TAX)
    t = r.aujourd_hui
    for _ in range(BUDGET_ATTENTION):                                 # Sophie a déjà 2 sollicitations ouvertes
        a = mo.creer(opp, t)
        mo.lancer(a, t)
    aid = mo.creer(opp, t)
    avant = r.memoire.empreinte()
    with pytest.raises(ErreurActivation, match="budget"):
        mo.lancer(aid, t)
    assert r.memoire.empreinte() == avant and mo.etat(aid) == "PLANIFIEE"   # rien n'a été écrit : on peut réessayer


def test_accord_du_beneficiaire_annule_si_un_contributeur_depasse_son_budget():
    r = md.construire()
    opp = next(o for o in scanner(r, TAX)["opportunites"] if o.beneficiaire == md.SOPHIE)
    mo = Moteur(r, TAX)
    t = r.aujourd_hui
    for _ in range(BUDGET_ATTENTION):                                 # Anna est déjà sollicitée deux fois ailleurs
        a = mo.creer(opp, t)
        mo.lancer(a, t)
        mo.repondre(a, t, md.SOPHIE, True)
    aid = mo.creer(opp, t)
    mo.lancer(aid, t)
    avant = r.memoire.empreinte()
    with pytest.raises(ErreurActivation, match="budget"):
        mo.repondre(aid, t, md.SOPHIE, True)
    assert r.memoire.empreinte() == avant                             # ni la réponse, ni une sollicitation partielle
