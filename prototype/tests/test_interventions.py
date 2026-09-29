"""Intervention minimale (idée I-01) : invariants. Données FICTIVES / GÉNÉRÉES."""
from datetime import timedelta

import networkx as nx

from adaptateurs.club import cycle as cy
from adaptateurs.club import interventions as iv
from adaptateurs.club import reseau
from app.taxonomy import charger_taxonomie
from eval.perf_echelle import generer
from plateforme.affirmations import Statut
from plateforme.memoire import Evt

TAX = charger_taxonomie()


def _monde(n=60, graine=5):
    profils, m, t = generer(n, graine)
    m.ajouter(Evt(type="INTRO_DECLINEE", le=t - timedelta(days=3), acteurs=[profils[0].id, profils[1].id],
                  statut=Statut.SIMULE, donnees={"t": 1}))
    return profils, m, t


def test_plan_prouve_consenti_plafonne_deterministe_et_sans_ecriture():
    profils, m, t = _monde()
    par_id = {p.id: p for p in profils}
    avant = m.empreinte()
    p1 = iv.plan(m, profils, cy.besoins_publies(m, t), TAX, t, k=8, plafond=1)
    p2 = iv.plan(m, profils, cy.besoins_publies(m, t), TAX, t, k=8, plafond=1)
    assert p1 == p2 and m.empreinte() == avant and p1["nature"] == "SIMULATION"   # déterministe, rien n'est écrit
    g = reseau.graphe_actuel(m, t)
    declinees = {frozenset(x) for x in reseau.paires_declinees(m, t)}
    assert declinees
    for option in p1["options"].values():
        assert option["actions"]
        vus: dict[str, int] = {}
        for a in option["actions"]:
            x, y = a["paire"]
            assert a["preuves"] and all(pr["preuve"] for pr in a["preuves"])                 # chaque action a sa preuve
            assert par_id[x].accepte_introductions and par_id[y].accepte_introductions      # consentement
            assert frozenset((x, y)) not in declinees and not g.has_edge(x, y)              # refus ; déjà actuel
            for z in (x, y):
                vus[z] = vus.get(z, 0) + 1
        assert all(v <= 1 for v in vus.values())                                            # budget d'attention


def test_ne_rien_faire_quand_personne_n_accepte_les_introductions():
    profils, m, t = _monde(30)
    fermes = [p.model_copy(update={"accepte_introductions": False}) for p in profils]
    p = iv.plan(m, fermes, cy.besoins_publies(m, t), TAX, t)
    assert p["decision"] == "NE_RIEN_FAIRE" and all(not o["actions"] for o in p["options"].values())


def test_inclusion_relie_un_isole_au_reseau_vivant_plutot_qu_a_un_autre_isole():
    """Effet de second ordre : deux isolés reliés entre eux forment un îlot que personne ne peut présenter plus loin."""
    g = nx.Graph([("v1", "v2"), ("v2", "v3")])
    g.add_nodes_from(["i1", "i2"])
    cands = [iv.Candidate("INTRODUCTION", "i1", "i2", 2.0, True, [{"preuve": "x"}]),      # plus forte, mais îlot
             iv.Candidate("INTRODUCTION", "i1", "v1", 1.0, False, [{"preuve": "y"}])]
    assert iv.choisir(g, cands, 1, variante="INCLUSION")[0]["paire"] == ["i1", "v1"]
    assert iv.choisir(g, cands, 1, variante="V1")[0]["paire"] == ["i1", "i2"]              # l'ablation tombe dans le piège


def test_cohesion_reunit_les_plus_grands_groupes_d_abord():
    g = nx.Graph([("a1", "a2"), ("a2", "a3"), ("b1", "b2"), ("b2", "b3"), ("c1", "c2")])
    cands = [iv.Candidate("INTRODUCTION", "a1", "c1", 1.0, False, [{"preuve": "x"}]),
             iv.Candidate("INTRODUCTION", "a1", "b1", 0.5, False, [{"preuve": "y"}])]
    a = iv.choisir(g, cands, 1, variante="COHESION")[0]
    assert a["paire"] == ["a1", "b1"] and a["pont"] and a["rejoignent_le_reseau_vivant"] == 3


def test_route_organisation_simulation_sans_coordonnees():
    from fastapi.testclient import TestClient

    from app import main
    c = TestClient(main.app)
    c.post("/api/demo/reinitialiser")
    c.get("/api/reseau/interventions?k=3")          # 1er appel : la projection du magasin peut ajouter des faits
    avant = main.MEMOIRE.empreinte()
    r = c.get("/api/reseau/interventions?k=3")
    assert r.status_code == 200
    p = r.json()
    assert p["nature"] == "SIMULATION" and p["donnees_fictives"] and set(p["options"]) == {"INCLUSION", "COHESION"}
    assert "@" not in r.text and "telephone" not in r.text
    assert c.get("/api/reseau/interventions?k=500").status_code == 422
    assert main.MEMOIRE.empreinte() == avant       # le plan n'écrit rien : même mémoire après un second appel
