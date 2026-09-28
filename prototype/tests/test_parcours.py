"""Tests du parcours critique et des garde-fous. Peu nombreux, ciblés sur les risques réels."""
from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("HACKVS_DB", ":memory:")

import pytest
from fastapi.testclient import TestClient

from app import parser_llm
from app.intros import ErreurTransition, Registre
from app.main import PAR_ID, PROFILS, TAX, app
from app.matching import rechercher
from app.models import Besoin, Critere
from app.parser_rules import analyser

client = TestClient(app)
MOI = PAR_ID["p00"]
BESOIN_ZURICH = ("On lance nos jus d'abricot en Suisse alémanique. Je cherche un transporteur frigorifique "
                 "qui livre Zurich deux fois par semaine, idéalement germanophone, et pas un concurrent.")


@pytest.fixture(autouse=True)
def _reinit():
    client.post("/api/demo/reinitialiser")


# ---------------------------------------------------------------- analyse du besoin
def test_analyse_ne_retient_que_ce_qui_est_cherche():
    b = analyser(BESOIN_ZURICH, TAX)
    exp = [c.valeur for c in b.criteres if c.type == "expertise"]
    assert exp == ["transport_frigorifique"]  # « jus d'abricot » est ce qu'on vend, pas ce qu'on cherche
    langue = next(c for c in b.criteres if c.type == "langue")
    assert langue.valeur == "de" and not langue.obligatoire  # « idéalement » → souhaité
    assert b.exclure_concurrents
    assert "deux fois par semaine" in b.contexte


def test_terme_ambigu_sans_indice_demande_une_precision():
    b = analyser("Je cherche quelqu'un pour la sécurité.", TAX)
    assert not [c for c in b.criteres if c.type == "expertise"]
    assert b.ambiguites and {o.valeur for o in b.ambiguites[0].options} >= {"cybersecurite", "securite_evenement"}


# ---------------------------------------------------------------- garde-fous de correspondance
def test_consentement_et_communaute_sont_des_invariants():
    """Même un profil parfait qui refuse les introductions, ou un visiteur, n'est jamais proposé."""
    tous = [c for c in TAX.concepts]
    for cid in tous:
        b = Besoin(texte=cid, criteres=[Critere(type="expertise", valeur=cid, libelle=cid)], inclure_exposants=True)
        r = rechercher(b, MOI, PROFILS, TAX)
        ids = {s.profil.id for s in r.suggestions + r.pistes_elargies}
        assert "p04" not in ids and "p31" not in ids, cid


def test_scenario_demo_et_raisons_ecartees_sans_nom():
    r = rechercher(analyser(BESOIN_ZURICH, TAX), MOI, PROFILS, TAX)
    assert [s.profil.id for s in r.suggestions][:1] == ["p01"]
    assert "p03" not in [s.profil.id for s in r.suggestions]  # frigoriste qui « ne livre pas »
    raisons = {e.raison for e in r.ecartes}
    assert "ne souhaite pas recevoir d'introductions" in raisons
    assert "concurrent potentiel (même secteur que vous)" in raisons
    assert all("Imboden" not in e.raison for e in r.ecartes)  # pas de nom dans les raisons d'exclusion


def test_zone_obligatoire_inconnue_n_est_pas_une_zone_valide():
    b = analyser("Je cherche un transport frigorifique dans la région de Sierre.", TAX)
    r = rechercher(b, MOI, PROFILS, TAX)
    assert "p09" not in [s.profil.id for s in r.suggestions]
    assert any(e.raison == "zone desservie non renseignée" for e in r.ecartes)


def test_abstention_quand_rien_de_fiable():
    r = rechercher(analyser("Nous cherchons un accompagnement vers la certification ISO 27001.", TAX), MOI, PROFILS, TAX)
    assert r.abstention and not r.suggestions
    assert [s.profil.id for s in r.pistes_elargies] == ["p10"]


# ---------------------------------------------------------------- garde-fous LLM (client simulé)
class _FauxClient:
    def __init__(self, sortie=None, erreur=None):
        self.messages = SimpleNamespace(parse=self._parse)
        self._sortie, self._erreur = sortie, erreur

    def _parse(self, **kw):
        if self._erreur:
            raise self._erreur
        return SimpleNamespace(parsed_output=self._sortie, stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=100, output_tokens=50))


def test_sortie_llm_hors_vocabulaire_ou_extrait_invente_est_filtree():
    sortie = parser_llm.SortieLLM(
        competences=[parser_llm._Item(valeur="transport_frigorifique", obligatoire=True, extrait="transporteur frigorifique"),
                     parser_llm._Item(valeur="teleportation", obligatoire=False, extrait="téléporteur")],
        langues=[parser_llm._Item(valeur="de", obligatoire=False, extrait="parle couramment le bernois")],
        zones=[parser_llm._Item(valeur="Mars", obligatoire=True, extrait="Zurich")],
        exclure_concurrents=True, contexte=[], termes_non_couverts=[])
    b, tele = parser_llm.analyser(BESOIN_ZURICH, TAX, client=_FauxClient(sortie))
    assert tele["analyseur"] == "claude" and b.analyseur == "claude"
    assert [c.valeur for c in b.criteres if c.type == "expertise"] == ["transport_frigorifique"]
    assert not any(c.type == "zone" for c in b.criteres)
    langue = next(c for c in b.criteres if c.type == "langue")
    assert langue.extrait is None  # extrait absent du texte → retiré
    assert any("teleportation" in a for a in b.avertissements)


def test_panne_llm_repli_visible_sur_les_regles():
    b, tele = parser_llm.analyser(BESOIN_ZURICH, TAX, client=_FauxClient(erreur=TimeoutError()))
    assert tele["analyseur"] == "regles (repli)"
    assert b.avertissements[0].startswith("Claude indisponible")
    assert [c.valeur for c in b.criteres if c.type == "expertise"] == ["transport_frigorifique"]


# ---------------------------------------------------------------- introductions
def test_parcours_api_complet():
    b = client.post("/api/analyser", json={"texte": BESOIN_ZURICH}).json()["besoin"]
    r = client.post("/api/rechercher", json={"besoin": b}).json()
    cible = r["suggestions"][0]["profil"]["id"]
    msg = client.post(f"/api/introductions/brouillon?cible_id={cible}", json={"besoin": b}).json()["message"]
    assert "pas un concurrent" not in msg and "Transport frigorifique".lower() in msg.lower()
    intro = client.post("/api/introductions", json={"cible_id": cible, "besoin": b, "message": msg}).json()
    assert intro["etat"] == "demandee" and not intro["coordonnees_partagees"] and intro["simulation"]
    # Le demandeur ne peut pas accepter à la place de la personne sollicitée.
    assert client.post(f"/api/introductions/{intro['id']}/accepter", json={"acteur": "demandeur"}).status_code == 409
    i = client.post(f"/api/introductions/{intro['id']}/accepter", json={"acteur": "cible"}).json()
    assert i["coordonnees_partagees"]
    assert client.post(f"/api/introductions/{intro['id']}/cloturer", json={"acteur": "demandeur", "resultat": "utile"}).status_code == 409
    client.post(f"/api/introductions/{intro['id']}/planifier", json={"acteur": "demandeur", "date_rencontre": "2026-10-15"})
    client.post(f"/api/introductions/{intro['id']}/confirmer_rencontre", json={"acteur": "demandeur"})
    fin = client.post(f"/api/introductions/{intro['id']}/cloturer", json={"acteur": "demandeur", "resultat": "utile"}).json()
    assert fin["etat"] == "cloturee" and fin["resultat"] == "utile"
    # Doublon actif interdit, relance possible après clôture.
    assert client.post("/api/introductions", json={"cible_id": cible, "besoin": b, "message": msg}).status_code == 200


def test_api_refuse_intro_vers_profil_non_consentant_meme_en_direct():
    b = {"texte": "x", "criteres": []}
    rep = client.post("/api/introductions", json={"cible_id": "p04", "besoin": b, "message": "Bonjour"})
    assert rep.status_code == 409 and "introductions" in rep.json()["detail"]
    rep = client.post("/api/introductions", json={"cible_id": "p31", "besoin": b, "message": "Bonjour"})
    assert rep.status_code == 409


def test_doublon_actif_refuse():
    reg = Registre(":memory:")
    reg.creer("p00", "p01", "t", [], "m", True, True)
    with pytest.raises(ErreurTransition):
        reg.creer("p00", "p01", "t", [], "m", True, True)


# ---------------------------------------------------------------- non-régression de l'évaluation
def test_evaluation_sans_violation_ni_fausse_proposition():
    from eval.run_eval import evaluer
    res = evaluer()
    assert res["moteur"]["violations"].startswith("0/")
    ok, total = res["moteur"]["abstention_correcte"].split("/")
    assert ok == total
    ok, total = res["preuves_verifiees"].split("/")
    assert ok == total
