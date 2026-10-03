"""ANNÉE 1 — la vitrine dans etat.yaml : ce qui est construit sur la branche annee-1 a son propre statut, « Construit —
branche annee-1, pas dans la démo », jamais compté avec ce que montre la démo (les chiffres de la slide restent ceux de
la démo). Il exige des tests, comme « construit »."""
from collections import Counter

import pytest

from intelligence import feuille_de_route as fdr


def test_le_statut_annee1_se_dit_tel_quel():
    assert fdr.STATUTS["annee1"][1] == "Construit — branche annee-1, pas dans la démo"
    assert fdr.STATUTS["annee1"][3] == "Built — annee-1 branch, not in the demo"


def test_annee1_exige_des_tests_qui_existent(tmp_path):
    f = tmp_path / "etat.yaml"
    f.write_text("- id: x\n  statut: annee1\n  fr: a\n  de: b\n  en: c\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tests"):
        fdr.charger(f)
    f.write_text("- id: x\n  statut: annee1\n  fr: a\n  de: b\n  en: c\n  tests: test_inexistant.py\n", encoding="utf-8")
    with pytest.raises(ValueError, match="introuvables"):
        fdr.charger(f)


def test_les_chiffres_de_la_demo_ne_comptent_pas_annee1():
    n = Counter(e["statut"] for e in fdr.charger())
    assert n["annee1"] >= 1
    assert set(fdr.chiffres_demo()) == {"construit", "valide", "prevu"}
    assert fdr.chiffres_demo()["construit"] == n["construit"]


def test_la_page_ne_donne_aucun_lien_vers_annee1():
    """annee-1 n'est jamais exposé par le tunnel : pas de lien « visite » vers ces chantiers."""
    assert all(e["lien"] is None for e in fdr.pour_la_page("https://visite.exemple") if e["statut"] == "annee1")
