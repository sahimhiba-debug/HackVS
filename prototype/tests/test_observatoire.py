"""Observatoire, événements temporels, frontière de Pareto : invariants. Données GÉNÉRÉES / FICTIVES."""
from datetime import date, timedelta

import networkx as nx
import pytest

from adaptateurs.club import pareto as pa
from adaptateurs.club import sante, temporel
from adaptateurs.club.interventions import Candidate
from eval import reseaux_pathologiques as rp


def _obs(r):
    return {p["phenomene"] for p in sante.phenomenes(r["g_hist"], r["g_act"], r["membres"], r["secteurs"], r["sollicitations"])["phenomenes"]}


@pytest.mark.parametrize("nom", rp.PATHOLOGIES)
def test_chaque_pathologie_injectee_est_nommee(nom):
    r = rp.pathologique(nom, 0)
    assert r["attendu"] <= _obs(r), (nom, _obs(r))


def test_un_reseau_sain_ne_declenche_aucune_alerte():
    assert all(not _obs(rp.sain(g)) for g in range(5))


def test_abstention_quand_trop_peu_de_relations():
    g = nx.Graph([("a", "b")])
    out = sante.phenomenes(g, g, ["a", "b", "c"])
    assert out["phenomenes"] == [] and "abstention" in out


def test_les_observations_ne_nomment_personne():
    r = rp.pathologique("HUB", 0)
    texte = str(sante.phenomenes(r["g_hist"], r["g_act"], r["membres"], r["secteurs"], r["sollicitations"]))
    assert not any(m in texte for m in r["membres"])          # comptes et tailles, jamais d'identifiants


def test_evenements_temporels_injectes():
    membres = [f"m{i}" for i in range(9)]
    g0 = nx.Graph([("m0", "m1"), ("m1", "m2"), ("m2", "m3"), ("m3", "m4"), ("m4", "m5"), ("m6", "m7")])
    g1 = nx.Graph([("m0", "m1"), ("m1", "m2"), ("m3", "m4"), ("m4", "m5"), ("m6", "m8"), ("m8", "m0")])
    types = {e["type"]: e for e in temporel.changements(g0, g1, membres)}
    assert types["RELATION_ENDORMIE"]["nombre"] == 2                 # m2–m3 et m6–m7
    assert types["PONT_DISPARU"]["taille_avant"] == 6 and types["PONT_DISPARU"]["tailles_apres"] == [5, 3]
    assert "NOUVEAU_GROUPE" not in types
    assert "MEMBRE_ISOLE" in types and "m7" in types["MEMBRE_ISOLE"]["membres"]
    assert temporel.changements(g0, g0, membres) == []               # rien ne change → aucun événement


def test_evenement_depuis_la_memoire_une_relation_s_endort():
    from plateforme.affirmations import Statut
    from plateforme.memoire import Evt, Memoire
    m, t = Memoire(), date(2026, 1, 1)
    for a, b in (("a", "b"), ("b", "c"), ("c", "d")):
        m.ajouter(Evt(type="RENCONTRE", le=t, acteurs=[a, b], statut=Statut.DECLARE))
    m.ajouter(Evt(type="SUIVI", le=t + timedelta(days=80), acteurs=["a", "b"], statut=Statut.DECLARE))
    out = temporel.depuis(m, list("abcd"), t + timedelta(days=30), t + timedelta(days=120))
    types = {e["type"] for e in out["evenements"]}
    assert "RELATION_ENDORMIE" in types and "MEMBRE_ISOLE" in types   # b–c et c–d s'endorment ; c et d isolés


def test_pareto_aucun_plan_du_front_n_est_domine_et_les_noms_ne_sont_pas_fabriques():
    g = nx.Graph([("a1", "a2"), ("a2", "a3"), ("b1", "b2"), ("b2", "b3")])
    membres = ["a1", "a2", "a3", "b1", "b2", "b3", "i1", "i2"]
    cands = [Candidate("INTRODUCTION", "a1", "i1", 1, False), Candidate("INTRODUCTION", "a3", "b1", 1, True),
             Candidate("INTRODUCTION", "i2", "b3", 1, False), Candidate("INTRODUCTION", "a2", "b2", 1, False)]
    cands[2] = Candidate("INTRODUCTION", "b3", "i2", 1, False)
    f = pa.frontiere(g, membres, cands, k=1)
    objs = [p["objectifs"] for p in f["front"]]
    assert all(not pa.domine(u, v) for u in objs for v in objs)
    assert len(f["front"]) >= 2 and not f["un_plan_atteint_l_ideal"]         # conflit réel sur ce cas construit
    tous_noms = [n for p in f["plans_nommes"] for n in p["noms"]]
    assert sorted(tous_noms) == sorted([a.upper() for a in pa.AXES] + ["EQUILIBRE"])  # chaque nom une fois, fusionnés si égaux
    assert len(f["plans_nommes"]) <= len(f["front"])


def test_contre_exemple_une_seule_personne_relie_deux_groupes_sans_aucun_pont():
    """Red team : aucune RELATION n'est un pont (2 relations de chaque côté), mais un seul MEMBRE relie les groupes."""
    g = nx.cycle_graph(["a1", "a2", "a3", "a4", "a5"])
    g.add_edges_from(nx.cycle_graph(["b1", "b2", "b3", "b4", "b5"]).edges())
    g.add_edges_from([("passeur_q7", "a1"), ("passeur_q7", "a2"), ("passeur_q7", "b1"), ("passeur_q7", "b2")])
    assert not list(nx.bridges(g))
    out = sante.phenomenes(g, g, list(g.nodes))
    p = {x["phenomene"]: x for x in out["phenomenes"]}
    assert "PASSAGE_UNIQUE" in p and "passeur_q7" not in str(out)       # signalé, personne non nommée


def _m_ab(jours_derniere_interaction):
    from plateforme.affirmations import Statut
    from plateforme.memoire import Evt, Memoire
    m, t = Memoire(), date(2026, 1, 1)
    for a, b in (("a", "b"), ("b", "c"), ("c", "d")):
        m.ajouter(Evt(type="RENCONTRE", le=t, acteurs=[a, b], statut=Statut.DECLARE))
    return m, t


def test_temporel_seuil_exact_90_91_jours():
    m, t = _m_ab(0)
    assert temporel.depuis(m, list("abcd"), t, t + timedelta(days=90))["evenements"] == []     # 90 j : encore actuelle
    types = {e["type"] for e in temporel.depuis(m, list("abcd"), t, t + timedelta(days=91))["evenements"]}
    assert types == {"RELATION_ENDORMIE", "MEMBRE_ISOLE"}                                        # 91 j : endormie


def test_temporel_un_refus_n_est_pas_une_relation_qui_s_endort():
    from plateforme.affirmations import Statut
    from plateforme.memoire import Evt
    m, t = _m_ab(0)
    m.ajouter(Evt(type="INTRO_DEMANDEE", le=t + timedelta(days=5), acteurs=["a", "b"], statut=Statut.OBSERVE, donnees={"r": 1}))
    m.ajouter(Evt(type="INTRO_DECLINEE", le=t + timedelta(days=6), acteurs=["a", "b"], statut=Statut.OBSERVE, donnees={"r": 1}))
    ev = temporel.depuis(m, list("abcd"), t + timedelta(days=1), t + timedelta(days=10))["evenements"]
    endormies = [p for e in ev if e["type"] == "RELATION_ENDORMIE" for p in e["paires"]]
    assert ["a", "b"] not in endormies           # un refus récent n'est pas un « endormissement » à raviver


def test_temporel_donnees_vides_et_membres_inconnus():
    from plateforme.memoire import Memoire
    assert temporel.depuis(Memoire(), ["x"], date(2026, 1, 1), date(2026, 6, 1))["evenements"] == []
    g0 = nx.Graph([("a", "b"), ("b", "c")])
    assert temporel.changements(g0, nx.Graph(), ["z"]) == []    # des membres hors liste ne produisent aucun événement


def test_pareto_sans_aucune_action_prouvee_ne_rien_faire():
    f = pa.frontiere(nx.Graph([("a", "b")]), ["a", "b", "c"], [], k=3)
    assert f["decision"] == "NE_RIEN_FAIRE" and f["front"] == [] and not f["un_plan_atteint_l_ideal"]


def test_cohesion_robuste_prefere_fermer_un_cycle_a_tirer_un_fil():
    """Deux relations possibles : un fil vers un grand groupe (cohésion simple) ou fermer un cycle (groupe qui survit à la
    perte de n'importe quelle relation). Chaque extrême choisit la sienne."""
    g = nx.Graph([("a1", "a2"), ("a2", "a3"), ("a3", "a4"), ("b1", "b2"), ("b2", "b3"), ("b1", "b3"), ("b3", "b4"), ("b4", "b5")])
    membres = sorted(g.nodes)
    fil = Candidate("INTRODUCTION", "a4", "b1", 1, False)          # relie deux groupes par UNE relation
    cycle = Candidate("INTRODUCTION", "a1", "a4", 1, False)        # ferme a1-a2-a3-a4 : 4 membres robustes
    f = pa.frontiere(g, membres, [fil, cycle], k=1)
    noms = {n: p["paires"] for p in f["plans_nommes"] for n in p["noms"]}
    assert noms["COHESION"] == [["a4", "b1"]] and noms["COHESION_ROBUSTE"] == [["a1", "a4"]]
    assert pa.plus_grand_groupe_robuste(g, membres) == 3                        # b1-b2-b3 avant


def test_gain_robuste_rapide_egal_force_brute():
    import random
    for s in range(60):
        r = random.Random(s)
        n = r.randint(4, 20)
        g = nx.relabel_nodes(nx.gnm_random_graph(n, r.randint(0, 2 * n), seed=s), lambda i: f"n{i}")
        for _ in range(5):
            a, b = r.sample(sorted(g), 2)
            if g.has_edge(a, b):
                continue
            h = g.copy()
            h.add_edge(a, b)
            attendu = max(0, pa.arbre_des_ponts(h)[3] - pa.arbre_des_ponts(g)[3])
            assert pa.gain_robuste(a, b, pa.arbre_des_ponts(g)) == attendu, (s, a, b)


def test_hysteresis_prefere_le_plan_proche_de_la_derniere_decision_parmi_les_quasi_egaux():
    g = nx.Graph([("a1", "a2"), ("b1", "b2")])
    membres = ["a1", "a2", "b1", "b2", "i1", "i2"]
    c1 = Candidate("INTRODUCTION", "a1", "i1", 1, False)
    c2 = Candidate("INTRODUCTION", "b1", "i2", 1, False)               # symétrique de c1 : mêmes objectifs
    sans = pa.frontiere(g, membres, [c1, c2], k=1)
    choix_sans = next(p["paires"] for p in sans["plans_nommes"] if "EQUILIBRE" in p["noms"])
    autre = [["b1", "i2"]] if choix_sans == [["a1", "i1"]] else [["a1", "i1"]]
    avec = pa.frontiere(g, membres, [c1, c2], k=1, precedent=autre)
    assert next(p["paires"] for p in avec["plans_nommes"] if "EQUILIBRE" in p["noms"]) == autre
