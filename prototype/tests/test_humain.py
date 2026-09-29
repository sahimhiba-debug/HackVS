"""« Mathématiquement valide mais humainement absurde » : garde-fous testés. Données FICTIVES."""
import json

import pytest

from app.matching import meme_organisation, rechercher
from app.models import Profil
from app.parser_rules import analyser
from app.soiree import calculer_aides
from app.taxonomy import DATA_DIR, charger_taxonomie

TAX = charger_taxonomie()
P = [Profil(**p) for p in json.loads((DATA_DIR / "profils_demo.json").read_text(encoding="utf-8"))["profils"]]
SOPHIE = P[0]
RETO = next(p for p in P if p.id == "p32")
BESOIN = analyser("Nous cherchons un agent commercial pour placer nos jus dans les épiceries fines de Berne cet automne", TAX)


@pytest.mark.parametrize("ent", ["Vergers du Rhône Sàrl", "VERGERS DU RHONE SARL", "Vergers du Rhône  Sàrl.", "vergers du rhône"])
def test_un_collegue_n_est_jamais_propose_quelle_que_soit_l_ecriture(ent):
    collegue = RETO.model_copy(update={"id": "c1", "entreprise": ent})
    assert meme_organisation(SOPHIE, collegue)
    r = rechercher(BESOIN, SOPHIE, [SOPHIE, collegue], TAX)
    assert not r.suggestions and not r.ecartes          # ni proposé, ni compté comme écarté (silencieux)
    assert not calculer_aides([SOPHIE, collegue], [], TAX)   # donc jamais apparié en soirée ni en cercle


def test_deux_entreprises_non_renseignees_ne_sont_pas_la_meme_organisation():
    a = SOPHIE.model_copy(update={"entreprise": ""})
    b = RETO.model_copy(update={"id": "c1", "entreprise": " "})
    assert not meme_organisation(a, b)
    assert [s.profil.id for s in rechercher(BESOIN, a, [a, b], TAX).suggestions] == ["c1"]


def test_des_noms_proches_mais_distincts_restent_distincts():
    b = RETO.model_copy(update={"id": "c1", "entreprise": "Vergers du Rhône Transports SA"})
    assert not meme_organisation(SOPHIE, b)


# ------------------------------------------------------------------ un refus d'introduction est définitif pour le moteur
def _run(refus=(), demande="tout le monde au moins une rencontre utile, 3 tours"):
    from adaptateurs.club.adaptateur import AdaptateurClub
    from plateforme import pipeline as pl
    from plateforme.execution import Journal
    ad = AdaptateurClub(lambda: (P, [], [], "demo", None, list(refus)), TAX)
    return pl.executer(ad, demande, Journal(), sensibilite=False)


def test_une_soiree_ne_contourne_jamais_un_refus_d_introduction():
    """B a décliné l'introduction de A : les placer à la même table contournerait son refus."""
    base = _run()
    _, a, b = base.retenue["rencontres"][0]
    for demande in ("tout le monde au moins une rencontre utile, 3 tours",
                    "tout le monde au moins une rencontre utile, même déjà en relation, 3 tours"):  # contrainte levée
        r = _run([(a, b)], demande)
        assert r.retenue is not None, r.compilation
        assert "pas_deja_en_relation" not in r.spec["contraintes_dures"] or "même" not in demande
        assert {frozenset((x, y)) for _, x, y in r.retenue["rencontres"]}.isdisjoint({frozenset((a, b))}), demande


def test_le_refus_est_reverifie_independamment_du_probleme():
    from adaptateurs.club.adaptateur import AdaptateurClub, validateurs
    from plateforme.optimisation import Solution
    from plateforme.specification import SpecDecision
    base = _run()
    t, a, b = base.retenue["rencontres"][0]
    ad = AdaptateurClub(lambda: (P, [], [], "demo", None, [(a, b)]), TAX)
    inst = ad.instantane_courant()
    spec = SpecDecision(**base.spec)
    sol = Solution(rencontres=[(t, a, b)], statut="optimal", poids={}, optimum_prouve=True, duree_ms=0.0, objectifs={})
    verdicts = {v(sol).nom: v(sol).etat for v in validateurs(inst, spec)}
    assert verdicts.get("refus d'introduction respecté (recalculé)") == "FAIL", verdicts


def test_paires_refusees_suit_le_fait_le_plus_recent():
    from types import SimpleNamespace as R

    from app.soiree import paires_refusees
    rels = [R(auteur_id="a", aidant_id="b", etat="declinee", cree_le="2026-01-01"),
            R(auteur_id="a", aidant_id="b", etat="acceptee", cree_le="2026-03-01"),   # refus ancien, relation vivante
            R(auteur_id="c", aidant_id="d", etat="acceptee", cree_le="2026-01-01"),
            R(auteur_id="d", aidant_id="c", etat="declinee", cree_le="2026-02-01")]   # refus récent (sens inverse)
    assert paires_refusees(rels) == frozenset({frozenset(("c", "d"))})


def test_le_plan_de_soiree_de_l_application_respecte_un_refus(monkeypatch):
    """Câblage réel : /api/soiree/plan transmet les refus du magasin au planificateur."""
    from fastapi.testclient import TestClient

    from app import main
    c = TestClient(main.app)
    m0 = c.get("/api/soiree/plan").json()["rencontres"][0]
    a, b = m0["a"]["id"], m0["b"]["id"]
    monkeypatch.setattr(main.soiree, "paires_refusees", lambda _: frozenset({frozenset((a, b))}))
    plan = c.get("/api/soiree/plan").json()
    assert plan["rencontres"] and all({m["a"]["id"], m["b"]["id"]} != {a, b} for m in plan["rencontres"])


def test_paires_declinees_de_la_memoire():
    from datetime import date

    from adaptateurs.club import reseau
    from plateforme.affirmations import Statut
    from plateforme.memoire import Evt, Memoire
    m, j = Memoire(), date(2026, 3, 1)
    for t, typ in enumerate(["INTRO_DEMANDEE", "INTRO_DECLINEE"]):
        m.ajouter(Evt(type=typ, le=date(2026, 1, 1 + t), acteurs=["a", "b"], statut=Statut.OBSERVE, donnees={"relation_id": "r1"}))
    assert reseau.paires_declinees(m, j) == [("a", "b")]
    m.ajouter(Evt(type="INTRO_ACCEPTEE", le=date(2026, 2, 1), acteurs=["a", "b"], statut=Statut.OBSERVE, donnees={"relation_id": "r2"}))
    assert reseau.paires_declinees(m, j) == []


def test_branche_et_stress_sur_une_execution_sans_specification_refuses_proprement():
    from adaptateurs.club.adaptateur import AdaptateurClub
    from plateforme import pipeline as pl
    from plateforme.execution import Journal
    from plateforme.specification import ErreurSpec
    j = Journal()
    ad = AdaptateurClub(lambda: (P, [], [], "demo"), TAX)
    r = pl.executer(ad, "autoriser les paires, et puis quoi", j, sensibilite=False)
    assert r.spec is None
    with pytest.raises(ErreurSpec):
        pl.contrefactuel(ad, j, r.run_id, {"retirer_contraintes": ["langue_commune"]})
    with pytest.raises(ErreurSpec):
        pl.stress(ad, j, r.run_id, 1)


def test_budget_d_attention_un_membre_ne_recoit_pas_huit_relances_le_meme_jour():
    """Membre sur-sollicité (scénario adversarial n° 9) : 8 personnes rencontrées peuvent toutes répondre à son besoin."""
    from datetime import date, timedelta

    from adaptateurs.club import cycle as cy
    from plateforme.affirmations import Statut
    from plateforme.memoire import Evt, Memoire
    clones = [RETO.model_copy(update={"id": f"r{i}", "nom": f"Agent {i}", "entreprise": f"Agence {i} SA"}) for i in range(8)]
    m, j = Memoire(), date(2026, 10, 3)
    for c in clones:
        m.ajouter(Evt(type="RENCONTRE", le=j, acteurs=sorted(["p00", c.id]), statut=Statut.SIMULE, donnees={"evenement": "S"}))
    cy.publier_besoin(m, "p00", BESOIN.texte, j + timedelta(days=5), TAX, Statut.SIMULE)
    vues = []
    for tour in range(4):                                   # la file se vide au rythme des réponses, rien n'est perdu
        rel = cy.relances(m, [SOPHIE] + clones, TAX, j + timedelta(days=11))
        raisons = [r for p in rel["propositions"] for r in p["raisons"]]
        assert len([r for r in raisons if r["pour"] == "p00"]) <= cy.MAX_RELANCES_PAR_MEMBRE
        if tour == 0:
            assert rel["abstentions"]["reportees_budget_attention"] == 8 - cy.MAX_RELANCES_PAR_MEMBRE
        for r in raisons:
            vues.append(r["avec"])
            cy.repondre(m, [SOPHIE] + clones, TAX, j + timedelta(days=11), r["id"], False, "p00")
    assert sorted(vues) == sorted(c.id for c in clones)     # chacune proposée une fois, au fil des réponses


def test_presentation_et_opportunite_exigent_le_consentement_des_trois():
    """Défaut trouvé en red team (antérieur au gel) : un intermédiaire ou un membre fermé aux introductions était sollicité."""
    from datetime import date, timedelta

    from adaptateurs.club import cycle as cy
    from plateforme.affirmations import Statut
    from plateforme.memoire import Evt, Memoire
    j0 = date(2026, 10, 3)
    for ferme in ("p32", "p00", "p06"):
        pm = [p.model_copy(update={"accepte_introductions": False}) if p.id == ferme else p for p in P]
        m = Memoire()
        cy.publier_besoin(m, "p00", BESOIN.texte, j0 - timedelta(days=1), TAX, Statut.SIMULE)
        for a, b, j, typ in (("p00", "p32", 0, "RENCONTRE"), ("p00", "p32", 12, "SUIVI"), ("p32", "p06", 0, "RENCONTRE")):
            m.ajouter(Evt(type=typ, le=j0 + timedelta(days=j), acteurs=sorted([a, b]), statut=Statut.DECLARE))
        t = j0 + timedelta(days=30)
        rel = cy.relances(m, pm, TAX, t)
        assert not [r for p in rel["propositions"] for r in p["raisons"] if r["type"] == "PRESENTATION"], ferme
        assert cy.opportunites(m, pm, TAX, t) == [], ferme
