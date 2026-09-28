"""Tests du parcours critique et des garde-fous. Ciblés sur les risques réels, pas sur le volume."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("HACKVS_DB", ":memory:")

import pytest
from fastapi.testclient import TestClient

from app import parser_llm
from app.main import PROFILS, TAX, app
from app.matching import rechercher
from app.models import Besoin, Critere
from app.parser_rules import analyser

client = TestClient(app)
PAR_ID = {p.id: p for p in PROFILS}
SOPHIE, JULIEN, ELODIE, OBERWALLIS = {"X-Membre": "p00"}, {"X-Membre": "p01"}, {"X-Membre": "p05"}, "p04"
BESOIN_ZURICH = ("On lance nos jus d'abricot en Suisse alémanique. Je cherche un transporteur frigorifique "
                 "qui livre Zurich deux fois par semaine, idéalement germanophone, et pas un concurrent.")


@pytest.fixture(autouse=True)
def _reinit():
    client.post("/api/demo/reinitialiser")


def crit(b, type_):
    return [c for c in b.criteres if c.type == type_]


def publier(texte=BESOIN_ZURICH, qui=SOPHIE, anonyme=False):
    b = client.post("/api/analyser", json={"texte": texte}).json()["besoin"]
    return client.post("/api/besoins", json={"besoin": b, "publier": True, "anonyme": anonyme}, headers=qui).json()


# ---------------------------------------------------------------- analyse du besoin
def test_analyse_ne_retient_que_ce_qui_est_cherche():
    b = analyser(BESOIN_ZURICH, TAX)
    assert [c.valeur for c in crit(b, "expertise")] == ["transport_frigorifique"]
    assert crit(b, "zone")[0].valeur == "Suisse alémanique" and crit(b, "zone")[0].obligatoire
    assert not crit(b, "langue")[0].obligatoire  # « idéalement » → souhaité
    assert b.exclure_concurrents and "deux fois par semaine" in b.contexte


def test_preference_negation_implantation():
    b = analyser("Nous sommes basés à Sion et cherchons un transporteur frigorifique, de préférence basé en Valais, pour livrer Genève.", TAX)
    assert {(c.type, c.valeur, c.obligatoire) for c in b.criteres} >= {
        ("zone", "Suisse romande", True), ("implantation", "Valais", False)}
    assert any("Votre localisation" in x for x in b.contexte)  # « basés à Sion » décrit le demandeur
    b = analyser("Pas de cybersécurité : il nous faut un support informatique pour notre wifi.", TAX)
    assert [e.valeur for e in b.exclusions] == ["cybersecurite"]
    r = rechercher(b, PAR_ID["p00"], PROFILS, TAX)
    assert [s.profil.id for s in r.suggestions] == ["p11"]  # Cyberalp exclu, même via sa présentation


def test_terme_ambigu_demande_une_precision_et_hors_catalogue_reste_prudent():
    b = analyser("Je cherche quelqu'un pour la sécurité.", TAX)
    assert not crit(b, "expertise") and b.ambiguites
    b = analyser("Je cherche un expert en droit maritime.", TAX)
    assert crit(b, "texte_libre") and rechercher(b, PAR_ID["p00"], PROFILS, TAX).abstention
    b = analyser("Je cherche un apiculteur pour polliniser mes vergers d'abricotiers.", TAX)
    r = rechercher(b, PAR_ID["p00"], PROFILS, TAX)
    assert [s.profil.id for s in r.suggestions] == ["p35"] and r.suggestions[0].niveau == "partielle"


# ---------------------------------------------------------------- garde-fous de correspondance
def test_consentement_et_communaute_sont_des_invariants():
    for cid in TAX.concepts:
        b = Besoin(texte=cid, criteres=[Critere(type="expertise", valeur=cid, libelle=cid)], inclure_exposants=True)
        r = rechercher(b, PAR_ID["p00"], PROFILS, TAX)
        ids = {s.profil.id for s in r.suggestions + r.pistes_elargies}
        assert OBERWALLIS not in ids and "p31" not in ids, cid


def test_une_phrase_de_client_ou_de_besoin_ne_prouve_pas_une_competence():
    r = rechercher(analyser("Je cherche un transporteur frigorifique pour Zurich.", TAX), PAR_ID["p00"], PROFILS, TAX)
    ids = [s.profil.id for s in r.suggestions]
    assert ids[0] == "p01" and not {"p33", "p34", "p03"} & set(ids)
    assert all("Imboden" not in e.raison for e in r.ecartes)  # exclusions jamais nominatives


def test_zone_obligatoire_inconnue_n_est_pas_une_zone_valide():
    r = rechercher(analyser("Je cherche un transport frigorifique dans la région de Sierre.", TAX), PAR_ID["p00"], PROFILS, TAX)
    assert "p09" not in [s.profil.id for s in r.suggestions]
    assert any(e.raison == "zone d'intervention non renseignée" for e in r.ecartes)


# ---------------------------------------------------------------- Bourse : la boucle complète
def test_boucle_bourse_complete_avec_anonymat():
    b = publier(anonyme=True)
    assert b["statut"] == "publie"
    bourse = client.get("/api/bourse", headers=JULIEN).json()
    assert len(bourse) == 1 and bourse[0]["besoin"]["auteur"]["anonyme"] and bourse[0]["besoin"]["auteur_id"] is None
    assert bourse[0]["correspondance"]["preuves"][0]["champ"] == "offre"
    assert client.get("/api/bourse", headers={"X-Membre": "p15"}).json() == []  # agence de com : pas concernée
    r = client.post("/api/relations", json={"besoin_id": b["id"], "message": "Je peux aider."}, headers=JULIEN).json()
    assert r["initiateur"] == "aidant" and r["etat"] == "proposee"
    vue_julien = client.get("/api/relations", headers=JULIEN).json()[0]
    assert vue_julien["autre"]["anonyme"] and vue_julien["auteur_id"] is None
    # Seule Sophie (destinataire) peut accepter
    assert client.post(f"/api/relations/{r['id']}/accepter", json={}, headers=JULIEN).status_code == 403
    assert client.post(f"/api/relations/{r['id']}/accepter", json={}, headers=SOPHIE).json()["coordonnees_partagees"]
    assert client.get("/api/relations", headers=JULIEN).json()[0]["autre"]["nom"] == "Sophie Moret"  # nom révélé
    assert client.get("/api/besoins", headers=SOPHIE).json()[0]["statut"] == "en_cours"
    for action, corps in [("planifier", {"date_rencontre": "2026-10-15"}), ("confirmer_rencontre", {}), ("cloturer", {"resultat": "utile"})]:
        assert client.post(f"/api/relations/{r['id']}/{action}", json=corps, headers=JULIEN).status_code == 200
    fin = client.post(f"/api/besoins/{b['id']}/cloturer", json={"resolu_par": r["id"]}, headers=SOPHIE).json()
    assert fin["statut"] == "resolu"
    assert client.get("/api/bourse", headers=ELODIE).json() == []  # besoin clos : sort de la Bourse


def test_bourse_et_correspondances_sont_symetriques():
    """Un membre voit un besoin dans sa Bourse SI ET SEULEMENT SI l'auteur le voit dans ses correspondances."""
    for texte in [BESOIN_ZURICH, "Je cherche une fiduciaire, si possible germanophone.",
                  "Je cherche un apiculteur pour polliniser mes vergers.", "Il nous faut de la sécurité pour notre stand."]:
        b = publier(texte)
        corr = {s["profil"]["id"] for s in client.get(f"/api/besoins/{b['id']}/correspondances", headers=SOPHIE).json()["suggestions"]}
        for p in PROFILS:
            if p.type == "visiteur" or p.id == "p00":
                continue
            dans_bourse = any(x["besoin"]["id"] == b["id"] for x in client.get("/api/bourse", headers={"X-Membre": p.id}).json())
            if p.type == "membre_club":
                assert dans_bourse == (p.id in corr), (texte, p.id)


def test_retrait_du_consentement_en_cascade():
    b = publier()
    r = client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": "p01", "message": "Bonjour"}, headers=SOPHIE).json()
    assert r["etat"] == "proposee"
    rep = client.post("/api/moi/consentement", json={"accepte": False}, headers=JULIEN).json()
    assert rep["relations_annulees"] == [r["id"]]
    rel = client.get("/api/relations", headers=SOPHIE).json()[0]
    assert rel["etat"] == "annulee" and "consentement" in rel["motif_fin"]
    corr = client.get(f"/api/besoins/{b['id']}/correspondances", headers=SOPHIE).json()
    assert "p01" not in [s["profil"]["id"] for s in corr["suggestions"]]
    assert client.get("/api/bourse", headers=JULIEN).json() == []
    assert client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": "p01", "message": "Re"}, headers=SOPHIE).status_code == 409
    client.post("/api/moi/consentement", json={"accepte": True}, headers=JULIEN)
    assert client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": "p01", "message": "Re"}, headers=SOPHIE).status_code == 200


def test_modification_versionnee_et_cloture_sans_suite():
    b = publier()
    r = client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": "p05", "message": "Bonjour"}, headers=SOPHIE).json()
    nouveau = client.post("/api/analyser", json={"texte": "Je cherche un transporteur frigorifique pour livrer Genève."}).json()["besoin"]
    m = client.put(f"/api/besoins/{b['id']}", json={"besoin": nouveau}, headers=SOPHIE).json()
    assert m["version"] == 2
    corr = client.get(f"/api/besoins/{b['id']}/correspondances", headers=SOPHIE).json()
    assert corr["besoin_version"] == 2 and "p02" in [s["profil"]["id"] for s in corr["suggestions"]]
    assert client.get("/api/relations", headers=SOPHIE).json()[0]["besoin_modifie_depuis"]
    assert client.put(f"/api/besoins/{b['id']}", json={"besoin": nouveau}, headers=JULIEN).status_code == 403
    client.post(f"/api/besoins/{b['id']}/cloturer", json={"note": "Trouvé ailleurs"}, headers=SOPHIE)
    assert client.get("/api/relations", headers=SOPHIE).json()[0]["etat"] == "annulee"  # demande en attente annulée
    assert client.put(f"/api/besoins/{b['id']}", json={"besoin": nouveau}, headers=SOPHIE).status_code == 409


def test_on_ne_sollicite_que_qui_correspond():
    b = publier()
    for cible, attendu in [("p15", 409), (OBERWALLIS, 409), ("p31", 409), ("p01", 200)]:
        rep = client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": cible, "message": "Bonjour"}, headers=SOPHIE)
        assert rep.status_code == attendu, (cible, rep.json())
    # une offre d'un membre qui ne correspond pas est refusée
    assert client.post("/api/relations", json={"besoin_id": b["id"], "message": "Moi !"}, headers={"X-Membre": "p15"}).status_code == 409


def test_le_serveur_refuse_un_critere_invente():
    b = client.post("/api/analyser", json={"texte": BESOIN_ZURICH}).json()["besoin"]
    b["criteres"][0]["libelle"] = "<img src=x onerror=alert(1)>"
    ok = client.post("/api/besoins", json={"besoin": b, "publier": True}, headers=SOPHIE).json()
    assert ok["besoin"]["criteres"][0]["libelle"] == "Transport frigorifique"  # libellé recalculé
    b["criteres"] = [{"type": "expertise", "valeur": "teleportation", "libelle": "x", "obligatoire": True}]
    assert client.post("/api/besoins", json={"besoin": b, "publier": True}, headers=SOPHIE).status_code == 422


def test_profil_en_30_secondes_met_la_bourse_a_jour():
    b = publier("Je cherche un transporteur frigorifique pour livrer Genève.")
    chloe = {"X-Membre": "p15"}
    assert client.get("/api/bourse", headers=chloe).json() == []
    prop = client.post("/api/profil/analyser", json={"texte": (
        "Nous livrons des produits frais en camion frigorifique en Valais et à Genève. Nous parlons français et allemand. "
        "Nous ne faisons pas de déménagements. Nous cherchons des chauffeurs.")}).json()
    assert [o["concept"] for o in prop["offre"]] == ["transport_frigorifique"]
    assert set(prop["zones_service"]) == {"Valais", "Suisse romande"} and set(prop["langues"]) == {"fr", "de"}
    assert "Nous ne faisons pas de déménagements" in prop["phrases_ignorees"] and prop["recherche"]
    # rien n'est enregistré par l'analyse ; l'enregistrement valide le vocabulaire
    assert client.put("/api/moi/profil", json={"offre": [{"concept": "teleportation", "texte": "x"}]}, headers=chloe).status_code == 422
    r = client.put("/api/moi/profil", json={"offre": prop["offre"], "zones_service": prop["zones_service"], "langues": prop["langues"]}, headers=chloe)
    assert r.status_code == 200
    bourse = client.get("/api/bourse", headers=chloe).json()
    assert [x["besoin"]["id"] for x in bourse] == [b["id"]]
    assert bourse[0]["correspondance"]["preuves"][0]["extrait"] == prop["offre"][0]["texte"]  # la phrase devient la preuve


def test_vue_du_club_calcule_les_competences_a_recruter():
    assert client.post("/api/demo/historique").json()["besoins_charges"] == 14
    t = client.get("/api/club/tableau").json()
    assert t["a_recruter"][0]["competence"] == "Accompagnement certification ISO 27001" and t["a_recruter"][0]["demandes"] == 3
    assert t["besoins"]["total"] == 14 and t["taux_resolution"] == {"resolus": 6, "clos": 12}
    assert "nom" not in str(t["a_recruter"])  # agrégats seulement
    # l'historique fictif ne pollue pas la Bourse de la démo principale
    assert client.get("/api/bourse", headers=JULIEN).json() == []
    # un membre qui ajoute la compétence manquante la retire de la liste « à recruter »
    client.put("/api/moi/profil", json={"offre": [{"concept": "certification_iso27001", "texte": "Nous accompagnons les PME vers ISO 27001"}],
                                        "zones_service": ["Valais"], "langues": ["fr"]}, headers={"X-Membre": "p10"})
    t = client.get("/api/club/tableau").json()
    assert all("ISO 27001" not in m["competence"] for m in t["a_recruter"])


def test_qr_code_local():
    r = client.get("/api/qr.svg?chemin=/")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg")
    assert client.get("/api/qr.svg?chemin=https://ailleurs.example").status_code == 422


def test_mode_reel_ne_simule_rien(tmp_path: Path):
    code = ("from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); "
            "print(c.get('/api/moi').status_code, c.get('/api/membres').status_code, c.post('/api/demo/reinitialiser').status_code, "
            "c.get('/api/journal').status_code, c.get('/api/club/tableau').status_code)")
    env = {**os.environ, "HACKVS_MODE": "reel", "HACKVS_DB": ":memory:"}
    env.pop("HACKVS_PROFILS", None)
    sortie = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parent.parent).stdout.split()
    assert sortie == ["503", "501", "403", "501", "501"]  # le journal (identités) n'est pas exposé hors démo


# ---------------------------------------------------------------- analyse par Claude (client simulé)
class _FluxFaux:
    def __init__(self, morceaux, final):
        self.text_stream, self._final = iter(morceaux), final
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self): return self._final


class _ClientFaux:
    def __init__(self, json_sortie=None, erreur=None, stop="end_turn"):
        self.messages = SimpleNamespace(stream=self._stream)
        self.json, self.erreur, self.stop = json_sortie, erreur, stop
    def _stream(self, **kw):
        if self.erreur:
            raise self.erreur
        assert kw["output_config"]["format"]["type"] == "json_schema"
        coupe = [self.json[i:i + 17] for i in range(0, len(self.json), 17)]
        final = SimpleNamespace(content=[SimpleNamespace(type="text", text=self.json)], stop_reason=self.stop,
                                usage=SimpleNamespace(input_tokens=900, output_tokens=120))
        return _FluxFaux(coupe, final)


SORTIE = parser_llm.SortieLLM(
    competences=[parser_llm._Item(valeur="transport_frigorifique", obligatoire=True, extrait="transporteur frigorifique"),
                 parser_llm._Item(valeur="teleportation", obligatoire=False, extrait="téléporteur")],
    langues=[parser_llm._Item(valeur="de", obligatoire=False, extrait="parle couramment le bernois")],
    zones=[parser_llm._Item(valeur="Mars", obligatoire=True, extrait="Zurich")],
    implantations=[], exclusions=[], exclure_concurrents=True, contexte=[], termes_hors_catalogue=[]).model_dump_json()


def test_flux_claude_provisoire_puis_valide_par_le_code():
    evs = list(parser_llm.analyser_flux(BESOIN_ZURICH, TAX, client=_ClientFaux(SORTIE)))
    provisoires = [e for e in evs if e["type"] == "provisoire"]
    assert provisoires and evs[-1]["type"] == "final"
    assert any(p["critere"]["valeur"] == "teleportation" for p in provisoires)  # le provisoire n'est pas filtré…
    b = Besoin(**evs[-1]["besoin"])                                              # …mais le final l'est
    assert [c.valeur for c in crit(b, "expertise")] == ["transport_frigorifique"] and not crit(b, "zone")
    assert crit(b, "langue")[0].extrait is None and any("teleportation" in a for a in b.avertissements)
    assert evs[-1]["telemetrie"]["tokens_entree"] == 900


@pytest.mark.parametrize("client_faux", [_ClientFaux(erreur=TimeoutError()), _ClientFaux(SORTIE, stop="refusal"),
                                         _ClientFaux('{"competences": [')])
def test_panne_refus_ou_json_invalide_repli_visible(client_faux):
    b, tele = parser_llm.analyser(BESOIN_ZURICH, TAX, client=client_faux)
    assert tele["analyseur"] == "regles (repli)" and b.avertissements[0].startswith("Claude indisponible")
    assert [c.valeur for c in crit(b, "expertise")] == ["transport_frigorifique"]


# ---------------------------------------------------------------- non-régression de l'évaluation
@pytest.mark.parametrize("jeu", ["base", "adversarial"])
def test_evaluation_sans_violation_ni_fausse_proposition(jeu):
    from eval.run_eval import evaluer
    res = evaluer(jeu=jeu)
    assert res["moteur"]["violations"].startswith("0/")
    for k in ("abstention_correcte", "preuves_verifiees"):
        v = res["moteur"][k] if k in res["moteur"] else res[k]
        ok, total = v.split("/")
        assert ok == total, (jeu, k, v)
