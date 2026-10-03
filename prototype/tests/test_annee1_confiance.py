"""ANNÉE 1 · LOT 6 — Confiance : journal des accès (qui, dans la console du secrétariat, a consulté quoi, et quand ;
lisible par l'administration seulement) et en-tête HSTS derrière HTTPS. Données FICTIVES."""
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from intelligence.comptes import code_totp


def _eleve(cp, s):
    p = cp.preparer_totp(s)
    cp.confirmer_totp(s, code_totp(p["secret"], time.time()))
    cp.elever(s, code_totp(p["secret"], time.time() + 30))


@pytest.fixture
def api(monkeypatch, tmp_path):
    for k, v in {"HACKVS_ESSAIS_DB": str(tmp_path / "j.db"), "HACKVS_SECRET": "r" * 40, "HACKVS_FOIRE": "1",
                 "HACKVS_COMPTES": "1", "HACKVS_SECRETARIAT": "1"}.items():
        monkeypatch.setenv(k, v)
    from app.pulse_api import creer_routeur
    from app.taxonomy import charger_taxonomie
    routeur = creer_routeur(charger_taxonomie())
    app = FastAPI()
    app.include_router(routeur)
    cp = routeur.comptes()
    admin = cp.amorcer_administration("Administration (fictive)")
    _eleve(cp, admin)
    sec = cp.accepter(cp.inviter(admin, role="secretariat", etiquette="Secrétariat 1 (fictif)", duree_s=600)["jeton"], appareil="x")
    _eleve(cp, sec)
    return TestClient(app), {"X-Pulse-Compte": admin}, {"X-Pulse-Compte": sec}


def test_chaque_consultation_de_la_console_est_journalisee(api):
    cl, admin, sec = api
    cl.get("/api/pulse/secretariat/comptes", headers=sec)
    cl.get("/api/pulse/secretariat/bilan.csv", headers=sec)
    acces = cl.get("/api/pulse/secretariat/acces", headers=admin).json()
    vus = [(x["qui"], x["route"]) for x in acces]
    assert ("Secrétariat 1 (fictif)", "GET /api/pulse/secretariat/comptes") in vus
    assert ("Secrétariat 1 (fictif)", "GET /api/pulse/secretariat/bilan.{fmt}") in vus
    assert all({"le", "qui", "route"} <= set(x) for x in acces)


def test_le_journal_des_acces_est_reserve_a_l_administration(api):
    cl, admin, sec = api
    assert cl.get("/api/pulse/secretariat/acces", headers=sec).status_code == 403


def test_hsts_seulement_quand_on_le_demande(monkeypatch):
    from app.main import app
    cl = TestClient(app)
    monkeypatch.delenv("HACKVS_HSTS", raising=False)
    assert "strict-transport-security" not in cl.get("/sante").headers         # la démo : inchangée
    monkeypatch.setenv("HACKVS_HSTS", "1")
    h = cl.get("/sante").headers["strict-transport-security"]
    assert "max-age=" in h and int(h.split("max-age=")[1].split(";")[0]) >= 31536000


def test_les_textes_juridiques_disent_qu_ils_sont_a_valider():
    from pathlib import Path
    d = Path(__file__).resolve().parents[2] / "docs" / "annee-1" / "conformite"
    for f in ("REGISTRE_TRAITEMENTS", "AIPD_MODELE", "POLITIQUE_CONFIDENTIALITE_FR", "CONDITIONS_UTILISATION_FR",
              "CONTRAT_SOUS_TRAITANCE_MODELE"):
        assert "À VALIDER PAR UN JURISTE" in (d / f"{f}.md").read_text(encoding="utf-8")[:300], f
    for f in ("POLITIQUE_CONFIDENTIALITE_DE", "CONDITIONS_UTILISATION_DE"):
        assert "ZU PRÜFEN" in (d / f"{f}.md").read_text(encoding="utf-8")[:300], f


def test_la_checklist_asvs_couvre_chaque_exigence_de_niveau_2_et_est_a_jour(tmp_path, monkeypatch):
    """Une ligne par exigence de niveau 2 du fichier officiel ; « conforme » jamais sans preuve ; le fichier publié est
    celui que produit le script (aucune retouche à la main)."""
    import csv
    import importlib.util
    from pathlib import Path
    racine = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("asvs_l2", racine / "prototype" / "scripts" / "asvs_l2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "SORTIE", tmp_path / "ASVS_L2.md")
    assert mod.main() == 0
    assert (tmp_path / "ASVS_L2.md").read_text(encoding="utf-8") == (racine / "docs/annee-1/conformite/ASVS_L2.md").read_text(encoding="utf-8")
    l2 = [x["req_id"] for x in csv.DictReader(mod.CSV.open(encoding="utf-8")) if x["level2"].strip()]
    assert len(l2) == 259
    for rid, (statut, preuve) in mod.EVAL.items():
        assert statut in mod.STATUTS and (statut == "non évaluée" or preuve), rid
