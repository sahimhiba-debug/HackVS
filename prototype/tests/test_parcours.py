"""Tests du parcours critique et des garde-fous. Ciblés sur les risques réels, pas sur le volume."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("HACKVS_DB", ":memory:")
os.environ.setdefault("HACKVS_SEMANTIQUE", "0")  # tests déterministes et rapides ; la couche sémantique a son test dédié

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
    rel = lambda: next(x for x in client.get("/api/relations", headers=SOPHIE).json() if x["id"] == r["id"])
    assert rel()["besoin_modifie_depuis"]
    assert client.put(f"/api/besoins/{b['id']}", json={"besoin": nouveau}, headers=JULIEN).status_code == 403
    client.post(f"/api/besoins/{b['id']}/cloturer", json={"note": "Trouvé ailleurs"}, headers=SOPHIE)
    assert rel()["etat"] == "annulee"  # demande en attente annulée
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
            "c.get('/api/journal').status_code, c.get('/api/club/tableau').status_code, c.get('/api/soiree/plan').status_code)")
    env = {**os.environ, "HACKVS_MODE": "reel", "HACKVS_DB": ":memory:"}
    env.pop("HACKVS_PROFILS", None)
    sortie = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parent.parent).stdout.split()
    assert sortie == ["503", "501", "403", "501", "501", "501"]  # le journal (identités) n'est pas exposé hors démo


# ---------------------------------------------------------------- plan de soirée (programme linéaire)
def _verifier_plan(r):
    vus = set()
    for t in range(1, r["tours"] + 1):
        gens = [x for m in r["rencontres"] if m["tour"] == t for x in (m["a"]["id"], m["b"]["id"])]
        assert len(gens) == len(set(gens)), "une personne à deux tables dans le même tour"
    for m in r["rencontres"]:
        paire = frozenset((m["a"]["id"], m["b"]["id"]))
        assert paire not in vus, "même paire deux fois"
        vus.add(paire)
        assert m["b_aide_a"] or m["a_aide_b"], "rencontre sans aide prouvée"
        assert m["langues"], "rencontre sans langue commune"
    for x in r["sans_rencontre"]:
        assert x["raison"], "absence non expliquée"


@pytest.mark.parametrize("donnees", ["club", "synthetique"])
def test_plan_soiree_optimal_et_contraintes(donnees):
    r = client.get(f"/api/soiree/plan?donnees={donnees}&tours=3").json()
    assert r["donnees_fictives"] and r["solveur"]["optimal_prouve"]
    _verifier_plan(r)
    c = r["comparaison"]
    objectif = lambda s: s["valeur_totale"] + 0.5 * s["participants_avec_rencontre_utile"]
    assert objectif(c["optimal"]) >= objectif(c["glouton"]) - 1e-6
    assert objectif(c["optimal"]) >= objectif(c["aleatoire_moyenne_30"]) - 1e-6
    if donnees == "synthetique":
        assert r["membres"] == 150 and c["optimal"]["participants_avec_rencontre_utile"] > c["glouton"]["participants_avec_rencontre_utile"]


def test_plan_soiree_langue_commune_et_agenda_ics():
    from app import soiree
    from app.models import Profil
    base = PAR_ID["p00"].model_dump()
    fr = Profil(**base | {"id": "x1", "nom": "Ana X.", "entreprise": "A", "langues": ["fr"]})
    de = Profil(**PAR_ID[OBERWALLIS].model_dump() | {"id": "x2", "nom": "Urs Y.", "entreprise": "B", "langues": ["de"]})
    ecartees = {}
    soiree.valeurs([fr, de], [], TAX, ecartees)
    assert not soiree.langues_communes(fr, de)
    r = client.get("/api/soiree/plan?donnees=synthetique&tours=3").json()
    assert r["paires_ecartees_sans_langue_commune"] > 0
    qui = r["rencontres"][0]["a"]["id"]
    ics = client.get(f"/api/soiree/programme.ics?membre={qui}&donnees=synthetique&tours=3")
    assert ics.status_code == 200 and ics.headers["content-type"].startswith("text/calendar")
    lignes = ics.text.split("\r\n")
    assert lignes[0] == "BEGIN:VCALENDAR" and ics.text.count("BEGIN:VEVENT") == sum(
        qui in (m["a"]["id"], m["b"]["id"]) for m in r["rencontres"])
    assert all(len(l.encode()) <= 75 for l in lignes) and "Données fictives" in ics.text.replace("\r\n ", "")
    assert client.get("/api/soiree/programme.ics?membre=inconnu").status_code == 404


def test_plan_soiree_preuves_verbatim_et_besoin_anonyme_jamais_expose():
    publier(anonyme=True)  # le besoin anonyme de Sophie ne doit pas créer de rencontre nominative
    r = client.get("/api/soiree/plan?tours=3").json()
    for m in r["rencontres"]:
        for aidant, aide in ((m["b"], m["b_aide_a"]), (m["a"], m["a_aide_b"])):
            if aide:
                textes = [o.texte for o in PAR_ID[aidant["id"]].offre] + [PAR_ID[aidant["id"]].presentation]
                assert any(aide["preuve"] in t for t in textes), aide
                assert BESOIN_ZURICH not in aide["besoin"]


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


# ---------------------------------------------------------------- couche sémantique locale (si le modèle est présent)
def test_ia_locale_suggere_sans_jamais_decider_seule(monkeypatch):
    from app import analyse, semantique
    monkeypatch.setenv("HACKVS_SEMANTIQUE", "1")
    if not semantique.disponible():
        pytest.skip("modèle sémantique absent (python scripts/telecharger_modele.py)")
    b, info = analyse.analyser_hybride("Nos produits laitiers doivent arriver au frais chez nos clients de Berne.", TAX)
    assert info["semantique"] == "consultée"
    assert not [c for c in b.criteres if c.type == "expertise"]  # pas de décision automatique par défaut
    options = {o.valeur for a in b.ambiguites for o in a.options}
    assert "transport_frigorifique" in options  # la bonne compétence est proposée, à confirmer
    b, _ = analyse.analyser_hybride("Je cherche un transporteur frigorifique.", TAX)
    assert [c.valeur for c in b.criteres if c.type == "expertise"] == ["transport_frigorifique"] and not b.ambiguites


# ---------------------------------------------------------------- Apertus (LLM suisse, API compatible OpenAI) simulé
def _serveur_apertus(json_sortie: str, refuse_schema=False, statut=200, balises=False):
    import httpx
    appels = []

    def repondre(requete: httpx.Request) -> httpx.Response:
        corps = json.loads(requete.content)
        appels.append({"corps": corps, "auth": requete.headers.get("authorization")})
        if statut != 200:
            return httpx.Response(statut, json={"error": "panne"})
        if refuse_schema and "response_format" in corps:
            return httpx.Response(400, json={"error": "response_format non pris en charge"})
        texte = f"```json\n{json_sortie}\n```" if balises else json_sortie
        morceaux = [texte[i:i + 23] for i in range(0, len(texte), 23)]
        lignes = [f"data: {json.dumps({'choices': [{'delta': {'content': m}}]})}" for m in morceaux]
        lignes += [f"data: {json.dumps({'choices': [], 'usage': {'prompt_tokens': 1200, 'completion_tokens': 140}})}", "data: [DONE]"]
        return httpx.Response(200, text="\n\n".join(lignes) + "\n\n", headers={"content-type": "text/event-stream"})
    return httpx.Client(transport=httpx.MockTransport(repondre)), appels


@pytest.fixture
def env_apertus(monkeypatch):
    monkeypatch.setenv("HACKVS_LLM", "apertus")
    monkeypatch.setenv("APERTUS_API_KEY", "cle-de-test")
    monkeypatch.setenv("APERTUS_BASE_URL", "https://apertus.example/v1")
    monkeypatch.setenv("APERTUS_MODEL", "swiss-ai/apertus-test")


def test_apertus_flux_valide_par_le_code(env_apertus):
    assert parser_llm.llm_configure()
    http, appels = _serveur_apertus(SORTIE)
    evs = list(parser_llm.analyser_flux(BESOIN_ZURICH, TAX, http=http))
    assert any(e["type"] == "provisoire" for e in evs)
    fin = evs[-1]
    b = Besoin(**fin["besoin"])
    assert fin["telemetrie"]["analyseur"] == "apertus" and b.analyseur == "apertus"
    assert [c.valeur for c in crit(b, "expertise")] == ["transport_frigorifique"]  # « teleportation » filtré
    assert fin["telemetrie"]["tokens_entree"] == 1200 and fin["telemetrie"]["sortie_contrainte"] is True
    assert appels[0]["auth"] == "Bearer cle-de-test" and appels[0]["corps"]["response_format"]["type"] == "json_schema"


def test_apertus_sans_sortie_contrainte_et_balises(env_apertus):
    http, appels = _serveur_apertus(SORTIE, refuse_schema=True, balises=True)
    b, tele = parser_llm.analyser(BESOIN_ZURICH, TAX, http=http)
    assert tele["analyseur"] == "apertus" and tele["sortie_contrainte"] is False and len(appels) == 2
    assert "response_format" not in appels[1]["corps"]
    assert [c.valeur for c in crit(b, "expertise")] == ["transport_frigorifique"]


def test_apertus_en_panne_repli_visible(env_apertus):
    http, _ = _serveur_apertus(SORTIE, statut=503)
    b, tele = parser_llm.analyser(BESOIN_ZURICH, TAX, http=http)
    assert tele["analyseur"] == "regles (repli)" and b.avertissements[0].startswith("Apertus indisponible")


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


def test_energie_categorie_parente_couvre_solaire_et_efficacite():
    b = analyser("Je cherche un expert en énergie, idéalement dans les renouvelables.", TAX)
    assert [c.valeur for c in crit(b, "expertise")][:1] == ["energie"]
    concepts = {o.concept for s in rechercher(b, PAR_ID["p00"], PROFILS, TAX, limite=10).suggestions
                for o in PAR_ID[s.profil.id].offre}
    assert {"energie_solaire", "efficacite_energetique"} <= concepts
    # le plus spécifique gagne toujours
    assert crit(analyser("Je cherche un installateur photovoltaïque.", TAX), "expertise")[0].valeur == "energie_solaire"
