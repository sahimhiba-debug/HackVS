"""« Attend une décision » est une FILE, pas une étagère : une capacité dont la recherche a été coupée par le budget de
nœuds offre deux actions à l'animation — RELANCER la recherche avec un budget élevé, ou ACQUITTER l'état incertain.
Les deux sont des faits journalisés (rejouables), jamais un état caché ; l'acquittement tombe dès que le monde change.
Données FICTIVES."""
import dataclasses

import pytest
from fastapi.testclient import TestClient

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.erreurs import Conflit

TAX = charger_taxonomie()
A = "delegation_acheteurs"
TITRE = "Accueillir une délégation d'acheteurs germanophones"


@pytest.fixture
def club():
    c = Demo(TAX).club
    c.banc.BUDGET_NOEUDS = 1                                  # toutes les recherches sont coupées
    return c


def _carte(c, finalite=A):
    return next(x for x in c.vues_capacites.console()["capacites"] if x["finalite"] == finalite)


def _file(c):
    return c.vues_capacites.console()["attention"]


def test_la_file_offre_les_deux_actions(club):
    a = _file(club)
    item = next(x for x in a["actions"] if x["finalite"] == A)
    assert item["titre"] == TITRE and [x["action"] for x in item["actions"]] == ["relancer", "acquitter"]
    assert item["actions"][0]["libelle"] == "Relancer la recherche (budget 1 000 000 nœuds)"


def test_relancer_calcule_avec_un_budget_eleve_et_sort_de_la_file(club):
    inst = club.relancer_recherche(A)
    assert inst.recherche_bornee is False and inst.statut == "ONE_AWAY" and inst.distance == 1
    assert club.banc.BUDGET_NOEUDS == 1                                          # le budget global n'a pas bougé
    carte = _carte(club)
    assert carte["recherche_relancee"] == 1_000_000 and carte["statut_libelle"] == "il manque une pièce"
    assert not any(x["finalite"] == A for x in _file(club)["actions"])
    assert not any(TITRE in d for d in _file(club)["decision"])
    ev = club.journal.evenements("RECHERCHE_RELANCEE")[-1]
    assert ev.donnees["finalite"] == A and ev.donnees["budget"] == 1_000_000
    replique = club.au(ev.seq)                                                    # un fait journalisé : rejoué à l'identique
    replique.banc.BUDGET_NOEUDS = 1
    assert next(i for i in replique.projection_capacites() if i.finalite == A).statut == "ONE_AWAY"


def test_une_relance_insuffisante_le_dit_et_reste_dans_la_file(club):
    club.reglages = dataclasses.replace(club.reglages, budget_relance=2)
    inst = club.relancer_recherche(A)
    assert inst.recherche_bornee is True
    carte = _carte(club)
    assert carte["statut_libelle"] == "état incertain : recherche bornée atteinte, même relancée (budget 2 nœuds)"
    assert any(x["finalite"] == A for x in _file(club)["actions"])


def test_rien_a_relancer_ni_a_acquitter_hors_etat_incertain():
    c = Demo(TAX).club
    for f in (c.relancer_recherche, c.acquitter_recherche):
        with pytest.raises(Conflit, match="la recherche de cette capacité n'a pas été coupée"):
            f(A)


def test_acquitter_sort_de_la_file_reste_affiche_et_tombe_quand_le_monde_change(club):
    club.acquitter_recherche(A)
    carte = _carte(club)
    assert carte["recherche_bornee"] is True and carte["acquittee_le"] == "2026-10-06"
    assert carte["statut_libelle"] == "état incertain : recherche bornée atteinte (acquitté par l'animation le 06.10)"
    assert not any(x["finalite"] == A for x in _file(club)["actions"])
    assert not any(TITRE in d for d in _file(club)["decision"])
    club.modifier_profil(md.ANNA, disponible=False)                              # le monde change…
    assert _carte(club)["acquittee_le"] is None                                  # …l'acquittement tombe
    assert any(x["finalite"] == A for x in _file(club)["actions"])


def test_actions_reservees_a_la_console():
    from app.main import app
    t = TestClient(app)
    t.post("/api/pulse/demo/reinitialiser", headers={"X-Pulse-Console": "1"})
    for action in ("relancer", "acquitter"):
        assert t.post(f"/api/pulse/console/capacites/{A}/{action}").status_code == 403          # sans console
    r = t.post(f"/api/pulse/console/capacites/{A}/relancer", headers={"X-Pulse-Console": "1"})
    assert r.status_code == 409 and "n'a pas été coupée" in r.json()["detail"]                # budget normal : rien à relancer
