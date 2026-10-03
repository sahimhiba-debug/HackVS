"""LISTE DU CLUB (3 octobre) — le seuil « < 3 » compte des ENTREPRISES distinctes, pas des personnes.

Le Club compte 145 entreprises et 173 représentants : deux représentants d'une même entreprise ne sont pas deux
sources indépendantes. Si trois personnes ont répondu mais qu'elles viennent de deux entreprises, dire « 3 » laisse
deviner « l'entreprise X a répondu ». Règle : sous k ENTREPRISES distinctes, « < 3 ». Données FICTIVES."""
import pytest

from app.taxonomy import charger_taxonomie
from intelligence import anonymat, suivi
from intelligence import monde_demo as md
from intelligence.demo import Demo

TAX = charger_taxonomie()
A = "delegation_acheteurs"


@pytest.fixture
def c(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    monkeypatch.setenv("HACKVS_SECRET", "un-secret-de-test-assez-long-pour-32-octets!")
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    club = Demo(TAX).club
    ask = next(a for _, a in club.asks_pour(md.PAULINE) if a.startswith(A))
    assert club.repondre_ask(md.PAULINE, ask, True, {"places": 14}).statut == "ACTIVE"
    return club


def _actifs(c):
    return {e.acteurs[0] for e in c.journal.evenements("ASK_REPONSE")} | {e.acteurs[0] for e in c.journal.evenements("ACCORD") if e.acteurs}


def _meme_entreprise(c, a, b):
    """`a` devient représentant de l'entreprise de `b` (deux représentants, une entreprise)."""
    c.coffre._personnes[a] = c.coffre._personnes[a].model_copy(update={"adhesion_id": c.coffre._personnes[b].adhesion_id})


def test_trois_personnes_de_trois_entreprises_sont_dites(c):
    assert len(_actifs(c)) == 3 and anonymat.entreprises(c, _actifs(c)) == 3
    assert suivi.calculer(c)["membres_actifs"] == 3


def test_deux_representants_d_une_meme_entreprise_plus_un_autre_membre_donnent_moins_de_trois(c):
    autre = next(m for m in _actifs(c) if m != md.PAULINE)
    _meme_entreprise(c, md.PAULINE, autre)
    assert len(_actifs(c)) == 3 and anonymat.entreprises(c, _actifs(c)) == 2
    assert suivi.calculer(c)["membres_actifs"] == "< 3"


def test_seuil_entreprises_zero_reste_zero_et_k_un_dit_tout(c):
    assert anonymat.seuil(c, set(), 0) == 0
    assert anonymat.seuil(c, {md.PAULINE}, 1) == "< 3"
    c.reglages = c.reglages.__class__(**{**c.reglages.__dict__, "k_anonymat": 1})
    assert anonymat.seuil(c, {md.PAULINE}, 1) == 1


def test_porteur_d_un_role_compte_en_entreprises(c):
    """Un rôle tenu par trois personnes de deux entreprises est « rare » : l'avis de retrait ne le dit pas."""
    nb = anonymat.porteurs(c, A)
    assert all(isinstance(v, int) for v in nb.values())
    membres = anonymat.porteurs_membres(c, A)
    for role, qui in membres.items():
        assert nb[role] == anonymat.entreprises(c, qui)
