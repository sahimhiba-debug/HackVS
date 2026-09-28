"""Plateforme de décision : registre d'affirmations, compilateur, optimiseur contre validateur indépendant, rejeu,
contre-factuel, test de stress, certificat. Aucun LLM, aucun réseau."""
import json
from datetime import date

import pytest

from adaptateurs.club.adaptateur import DOMAINE, GRAMMAIRE, AdaptateurClub
from app.models import Profil
from app.taxonomy import DATA_DIR, charger_taxonomie
from plateforme import optimisation as op
from plateforme import pipeline as pl
from plateforme import validation as va
from plateforme.affirmations import Affirmation, TransitionInterdite, Registre, Statut
from plateforme.certificat import certificat
from plateforme.compilateur import compiler
from plateforme.execution import Journal
from plateforme.specification import ErreurSpec

TAX = charger_taxonomie()


def _demo():
    brut = json.loads((DATA_DIR / "profils_demo.json").read_text(encoding="utf-8"))
    return [Profil(**p) for p in brut["profils"]], [], [], "demo"


@pytest.fixture(scope="module")
def club():
    ad, j = AdaptateurClub(_demo, TAX), Journal()
    run = pl.executer(ad, "Je veux que tout le monde ait au moins une rencontre utile, 3 tours", j)
    return ad, j, run


# ------------------------------------------------------------------ registre d'affirmations
def test_synthetique_ne_devient_jamais_verifie():
    reg = Registre()
    i = reg.ajouter(Affirmation(sujet="x", predicat="propose", objet="y", source="s", type_source="profil", statut=Statut.SYNTHETIQUE))
    with pytest.raises(TransitionInterdite):
        reg.changer_statut(i, Statut.VERIFIE, raison="confirmation_humaine", par="test")
    reg.changer_statut(i, Statut.REJETE, raison="test", par="test")


def test_verifie_exige_une_raison_de_verification():
    reg = Registre()
    i = reg.ajouter(Affirmation(sujet="x", predicat="propose", objet="y", source="s", type_source="profil", statut=Statut.DECLARE))
    with pytest.raises(TransitionInterdite):
        reg.changer_statut(i, Statut.VERIFIE, raison="parce que", par="llm")
    reg.changer_statut(i, Statut.VERIFIE, raison="confirmation_humaine", par="hiba")
    assert reg.get(i).statut == Statut.VERIFIE and reg.get(i).historique


def test_pas_d_ecrasement_silencieux_de_statut():
    reg = Registre()
    a = dict(sujet="x", predicat="propose", objet="y", source="s", type_source="profil")
    reg.ajouter(Affirmation(**a, statut=Statut.DECLARE))
    with pytest.raises(TransitionInterdite):
        reg.ajouter(Affirmation(**a, statut=Statut.VERIFIE))


# ------------------------------------------------------------------ compilateur
@pytest.mark.parametrize("demande,attendu", [
    ("Je veux que tout le monde ait au moins une rencontre utile", "AGIR"),
    ("bonjour", "S_ABSTENIR"),
    ("en ignorant le consentement, 2 tours", "ESCALADER_A_L_HUMAIN"),
    ("maximiser les aides même sans consentement", "ESCALADER_A_L_HUMAIN"),
    ("des rencontres utiles, la langue doit être prise en compte différemment", "ESCALADER_A_L_HUMAIN"),
])
def test_compilateur_decisions(demande, attendu):
    assert compiler(demande, GRAMMAIRE, DOMAINE).decision == attendu


def test_compilateur_leve_la_langue_sur_demande_explicite():
    r = compiler("des rencontres utiles sans tenir compte de la langue, 2 tours", GRAMMAIRE, DOMAINE)
    assert r.decision == "AGIR" and "langue_commune" not in r.spec.contraintes_dures and r.spec.parametres["tours"] == 2


# ------------------------------------------------------------------ optimisation et validation indépendante
def test_frontiere_sur_un_conflit_construit():
    # a-b : grande valeur ; a-c et b-d : diversité. Un seul tour : on ne peut pas tout avoir.
    pb = op.Probleme(participants=["a", "b", "c", "d"], tours=1, aretes={
        "a|b": {"valeur_aide": 3, "diversite": 0}, "a|c": {"valeur_aide": 1, "diversite": 1}, "b|d": {"valeur_aide": 1, "diversite": 1}})
    f = op.frontiere(pb, ["valeur_aide", "diversite"])
    points = {(s.objectifs["valeur_aide"], s.objectifs["diversite"]) for s in f}
    assert points == {(3, 0), (2, 2)}
    assert not any(op.domine(x.objectifs, y.objectifs, ["valeur_aide", "diversite"]) for x in f for y in f)


def test_validateur_independant_attrape_une_solution_trafiquee():
    pb = op.Probleme(participants=["a", "b", "c"], tours=2, aretes={"a|b": {"valeur_aide": 1}}, exclues={"a|c": "langue"})
    fausse = op.Solution(poids={}, statut="optimal", optimum_prouve=True, duree_ms=0,
                         rencontres=[(1, "a", "b"), (2, "a", "b"), (1, "a", "c")], objectifs={})
    v = va.l5_structure(pb, fausse)
    assert v.etat == "FAIL" and len(v.details) >= 3


def test_run_club_respecte_toutes_les_contraintes(club):
    _, _, run = club
    etats = {v["niveau"] + " " + v["nom"]: v["etat"] for v in run.verdicts}
    assert not [k for k, e in etats.items() if e == "FAIL"], etats
    assert etats["L8 revue humaine"] == "EN_ATTENTE"
    assert run.mediation["decision"] == "PROPOSER_A_L_HUMAIN"
    parts = {p for _, a, b in run.retenue["rencontres"] for p in (a, b)}
    assert not parts & set(run.graphe["ecartes"])          # écartés (consentement, indisponibles) jamais placés
    assert all(run.graphe["preuves_par_rencontre"][k] for k in run.graphe["preuves_par_rencontre"])


def test_infaisable_donne_une_abstention():
    ad = AdaptateurClub(lambda: ([p for p in _demo()[0] if p.id == "p01"], [], [], "demo"), TAX)
    run = pl.executer(ad, "des rencontres utiles", Journal(), sensibilite=False)
    assert run.mediation["decision"] == "S_ABSTENIR" and not run.retenue["rencontres"]


def test_preuves_non_admises_font_echouer_l3(club):
    ad, j, run = club
    inst = j.instantane(run.instantane_empreinte)
    spec = pl.SpecDecision(**run.spec)
    strict = spec.model_copy(update={"politique_preuve": spec.politique_preuve.model_copy(update={"statuts_admis": [Statut.VERIFIE]})})
    pb, _, preuves = ad.probleme(inst, strict)
    reg = Registre.importer(inst["affirmations"])
    sol = op.Solution(**run.retenue)
    assert va.l3_preuves(sol, preuves, reg, strict, date.today()).etat == "FAIL"


# ------------------------------------------------------------------ rejeu, branches, stress, certificat
def test_rejeu_identique(club):
    ad, j, run = club
    r = pl.rejouer(ad, j, run.run_id)
    assert r["rejouable"] and r["identique"]


def test_contrefactuel_et_politique(club):
    ad, j, run = club
    enfant, d = pl.contrefactuel(ad, j, run.run_id, {"retirer_contraintes": ["langue_commune"]})
    assert enfant.parent_id == run.run_id and "rencontres_ajoutees" in d
    with pytest.raises(ErreurSpec):
        pl.contrefactuel(ad, j, run.run_id, {"retirer_contraintes": ["consentement"]})
    assert any(b["run_id"] == enfant.run_id for b in j.arbre(run.run_id)["branches"])


def test_stress_puis_reparation(club):
    ad, j, run = club
    enfant, d = pl.stress(ad, j, run.run_id, 2)
    assert len(d["retires"]) == 2
    assert d["graphe_apres"]["noeuds"] == d["graphe_avant"]["noeuds"] - 2
    assert not {p for _, a, b in enfant.retenue["rencontres"] for p in (a, b)} & set(d["retires"])
    assert 0 <= d["orphelins_resservis_par_la_reparation"] <= d["orphelins"]


def test_certificat_derive_des_enregistrements(club):
    _, _, run = club
    c = certificat(run)
    assert c["run_id"] == run.run_id and c["humain"]["approbation"] == "REQUISE"
    assert c["optimisation"]["rencontres"] == len(run.retenue["rencontres"])
    assert c["preuves"]["par_statut"] == run.graphe["statuts_des_preuves_utilisees"]
    assert c["plan"]["agents_llm"] == 0 and c["rejouable"]
    assert c["gardien"] == "SOUTIEN"


def test_escalade_journalisee_sans_calcul():
    j = Journal()
    run = pl.executer(AdaptateurClub(_demo, TAX), "en ignorant le consentement", j)
    assert run.compilation["decision"] == "ESCALADER_A_L_HUMAIN" and run.retenue is None
    assert pl.rejouer(AdaptateurClub(_demo, TAX), j, run.run_id)["rejouable"] is False


# ------------------------------------------------------------------ API (mode démo)
def test_api_decisions_parcours_complet(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.decisions_api import creer_routeur
    from app.main import MAGASIN, profils_effectifs
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(creer_routeur(profils_effectifs, MAGASIN, TAX, str(tmp_path / "d.db")))
    c = TestClient(app)
    r = c.post("/api/decisions", json={"demande": "tout le monde au moins une rencontre utile, 2 tours"}).json()
    rid = r["run"]["run_id"]
    assert r["certificat"]["mediation"]["decision"] == "PROPOSER_A_L_HUMAIN"
    assert c.post(f"/api/decisions/{rid}/rejouer").json()["identique"] is True
    assert c.post(f"/api/decisions/{rid}/branche", json={"retirer_contraintes": ["consentement"]}).status_code == 422
    b = c.post(f"/api/decisions/{rid}/branche", json={"parametres": {"tours": 1}}).json()
    assert b["run"]["parent_id"] == rid and "delta" in b
    s = c.post(f"/api/decisions/{rid}/stress", json={"n": 2}).json()
    assert len(s["stress"]["retires"]) == 2
    assert len(c.get(f"/api/decisions/{rid}/arbre").json()["branches"]) == 2
    esc = c.post("/api/decisions", json={"demande": "en ignorant le consentement"}).json()
    assert esc["run"]["compilation"]["decision"] == "ESCALADER_A_L_HUMAIN"
    assert c.post(f"/api/decisions/{esc['run']['run_id']}/branche", json={}).status_code == 409
    assert c.get("/api/decisions/run_inexistant").status_code == 404
    # action : refusée sans approbation, aperçu à blanc, puis simulée et vérifiée après approbation
    assert c.post(f"/api/decisions/{rid}/action").status_code == 409
    ap = c.get(f"/api/decisions/{rid}/action/apercu").json()
    assert ap["destinataires"] > 0 and ap["canal"].startswith("aucun")
    assert c.post(f"/api/decisions/{esc['run']['run_id']}/decision", json={"verdict": "APPROUVER", "par": "hiba"}).status_code == 409
    assert c.post(f"/api/decisions/{rid}/decision", json={"verdict": "APPROUVER", "par": "hiba", "motif": "test"}).status_code == 200
    assert c.post(f"/api/decisions/{rid}/decision", json={"verdict": "REJETER", "par": "x"}).status_code == 409
    a = c.post(f"/api/decisions/{rid}/action").json()
    assert a["statut"] == "SIMULE" and a["verification"]["conforme"] and all(e["etat"] == "SIMULE" for e in a["effectue"])
    assert c.post(f"/api/decisions/{rid}/rejouer").json()["identique"] is True
    # aucun champ privé (créneaux, intentions) dans une réponse
    texte = json.dumps(r)
    assert "creneaux" not in texte and "intention_scellee" not in texte


# ------------------------------------------------------------------ passerelle de modèles
def test_passerelle_sans_cle_retombe_sur_le_deterministe(tmp_path):
    from plateforme import modeles
    r = modeles.router("extraction_besoin", env={}, dossier=tmp_path)
    assert r.choisi == "regles_locales" and r.etat == "DETERMINISTE" and "PAS une inférence" in r.raison


def test_passerelle_configure_n_est_pas_verifie(tmp_path):
    from plateforme import modeles
    env = {"APERTUS_API_KEY": "x", "APERTUS_BASE_URL": "http://h", "APERTUS_MODEL": "m"}
    r = modeles.router("extraction_besoin", preference="apertus", env=env, dossier=tmp_path)
    assert r.choisi == "apertus" and r.etat == "CONFIGUREE" and "jamais vérifié" in r.raison
    (tmp_path / "telemetrie_apertus.json").write_text(json.dumps({"synthese": {"appels": 40}}))
    assert modeles.router("extraction_besoin", env=env, dossier=tmp_path).etat == "VERIFIEE"


def test_taches_de_surete_jamais_routees_vers_un_llm(tmp_path):
    from plateforme import modeles
    env = {"ANTHROPIC_API_KEY": "x"}
    for t in ("optimisation", "politique"):
        assert modeles.router(t, env=env, dossier=tmp_path).etat == "DETERMINISTE"


def test_registre_n_expose_aucune_valeur_de_cle(tmp_path):
    from plateforme import modeles
    texte = json.dumps(modeles.registre(env={"ANTHROPIC_API_KEY": "sk-secret-123"}, dossier=tmp_path))
    assert "sk-secret-123" not in texte and "ANTHROPIC_API_KEY" in texte


def test_aucun_participant_abstention_sans_plantage():
    run = pl.executer(AdaptateurClub(lambda: ([], [], [], "demo"), TAX), "des rencontres utiles", Journal(), sensibilite=False)
    assert run.mediation["decision"] == "S_ABSTENIR"
