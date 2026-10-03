"""P3 n°4 — SUIVI : « nouveaux liens tissés ». Un lien = deux ENTREPRISES distinctes qui portent chacune un accord sur
la même capacité ; « nouveau » = jamais vu avant le début de la période. Seuil « < 3 » en entreprises. Le routage qui
favoriserait les membres jamais liés reste une HYPOTHÈSE (non branchée : une demande va à une catégorie, jamais à une
personne choisie par le système). Données FICTIVES."""
import pytest

from app.taxonomy import charger_taxonomie
from intelligence import liens, suivi
from intelligence import monde_demo as md
from intelligence.demo import Demo

TAX = charger_taxonomie()
A = "delegation_acheteurs"


@pytest.fixture
def c(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    monkeypatch.setenv("HACKVS_SECRET", "un-secret-de-test-assez-long-pour-32-octets!")
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(TAX).club


def _oui_pauline(c):
    ask = next(a for _, a in c.asks_pour(md.PAULINE) if a.startswith(A))
    c.repondre_ask(md.PAULINE, ask, True, {"places": 14})


def test_deux_accords_semes_un_lien_trois_avec_pauline(c):
    assert liens.paires(c, None) == 1                              # s04 et s10, deux entreprises
    _oui_pauline(c)
    assert liens.paires(c, None) == 3                              # trois entreprises : trois paires


def test_meme_entreprise_ne_fait_pas_de_lien(c):
    autre = "s04"
    c.coffre._personnes["s10"] = c.coffre._personnes["s10"].model_copy(update={"adhesion_id": c.coffre._personnes[autre].adhesion_id})
    assert liens.paires(c, None) == 0


def test_suivi_dit_moins_de_trois_sous_trois_entreprises_puis_le_nombre(c):
    assert suivi.calculer(c)["liens"]["nouveaux"] == "< 3"        # 1 lien, 2 entreprises
    _oui_pauline(c)
    assert suivi.calculer(c)["liens"]["nouveaux"] == 3             # 3 liens, 3 entreprises


def test_un_lien_deja_tisse_avant_la_periode_n_est_pas_nouveau(c):
    from datetime import timedelta
    _oui_pauline(c)
    assert liens.paires(c, c.jour + timedelta(days=1)) == 0       # rien de neuf après aujourd'hui


def test_le_routage_reste_une_hypothese():
    assert "hypothèse" in liens.ROUTAGE.lower() and "non branché" in liens.ROUTAGE
