"""Atomicité : une commande qui écrit plusieurs faits les écrit TOUS ou AUCUN (transaction SQLite du journal).
Le banc d'essai s'appuie sur cette garantie : voir `test_essai.py` (panne au milieu d'une publication) et
`test_essai_securite.py` (concurrence)."""
from datetime import date

import pytest

from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire


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
