"""Observabilité et protections HTTP : identifiant de requête, journaux structurés SANS contenu privé, en-têtes de
sécurité, CSP par empreintes, taille des corps, panne non prévue → 500 JSON portant l'identifiant."""
import json
import logging
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import WEB_PULSE, app
from app.observabilite import FormatJSON, MiddlewareRequete, niveau_depuis_env
from app.protections import CORPS_MAX, Protections, empreintes, politique_contenu
from intelligence import monde_demo as md
from intelligence.demo import Demo

client = TestClient(app)
CONSOLE = {"X-Pulse-Console": "1"}


def _lignes(caplog) -> list[dict]:
    f = FormatJSON()
    return [json.loads(f.format(r)) for r in caplog.records if r.name.startswith(("hackvs", "intelligence"))]


def test_identifiant_de_requete_renvoye_et_assaini():
    r = client.get("/api/pulse/etat", headers={"X-Request-ID": "abc-123-def-456"} | CONSOLE)
    assert r.headers["x-request-id"] == "abc-123-def-456"                  # corrélation avec l'appelant
    r = client.get("/api/pulse/etat", headers={"X-Request-ID": "<script>\nfaux"} | CONSOLE)
    assert re.fullmatch(r"[0-9a-f]{16}", r.headers["x-request-id"])        # valeur hostile : remplacée, jamais recopiée


def test_en_tetes_de_securite_et_csp_par_empreintes():
    for chemin in ("/app", "/console"):
        h = client.get(chemin).headers
        csp = h["content-security-policy"]
        script_src = next(d for d in csp.split(";") if d.strip().startswith("script-src"))
        assert "unsafe-inline" not in script_src and "sha256-" in script_src
        assert "frame-ancestors 'self'" in csp and "object-src 'none'" in csp
        assert h["x-content-type-options"] == "nosniff" and h["referrer-policy"] == "no-referrer"
    assert client.get("/api/pulse/etat", headers=CONSOLE).headers["cache-control"] == "no-store"   # données personnelles : pas de cache
    assert "content-security-policy" not in client.get("/api/pulse/etat", headers=CONSOLE).headers


def test_chaque_script_en_ligne_a_son_empreinte():
    """Une page modifiée sans que la CSP suive serait bloquée par le navigateur : l'empreinte est recalculée au démarrage
    à partir du fichier servi, et le test de bout en bout échoue sur toute violation (erreurs de console)."""
    pages = [WEB_PULSE / "app.html", WEB_PULSE / "console.html", WEB_PULSE / "projection.html", WEB_PULSE / "regie.html"]
    assert len(empreintes(pages)) == 4
    assert all(e.encode() in politique_contenu(pages) for e in empreintes(pages))


def test_corps_trop_volumineux_refuse_annonce_ou_non():
    r = client.post("/api/pulse/acces", content=b"x" * (CORPS_MAX + 1), headers={"Content-Type": "application/json"})
    assert r.status_code == 413 and "x-request-id" in r.headers

    def morceaux():
        for _ in range(CORPS_MAX // 1024 + 2):
            yield b"x" * 1024
    r = client.post("/api/pulse/acces", content=morceaux(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413                                            # sans Content-Length : compté au fil de l'eau


def test_panne_non_prevue_500_json_sans_le_message(caplog):
    appli = FastAPI()

    @appli.get("/boom")
    def boom():
        valeur = "sophie" + "@exemple.ch"                                   # une DONNÉE, pas un littéral du code
        raise RuntimeError(f"donnée sensible : {valeur}")
    appli.add_middleware(Protections, csp=b"default-src 'self'")
    appli.add_middleware(MiddlewareRequete)
    with caplog.at_level(logging.INFO):
        r = TestClient(appli, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500 and r.json()["requete"] == r.headers["x-request-id"]
    assert "sophie" not in r.text
    lignes = _lignes(caplog)
    panne = next(x for x in lignes if x["msg"] == "panne non prévue")
    assert panne["exception"] == "RuntimeError" and panne["requete"] == r.headers["x-request-id"]
    assert "sophie@exemple.ch" not in json.dumps(lignes)                   # le message d'exception n'est pas journalisé


def test_les_journaux_ne_contiennent_ni_secret_ni_note_ni_nom(caplog, monkeypatch):
    """Démonstration complète par l'API (découverte, essai, perturbation, adaptation, observation, mémoire), plus une note
    privée et une demande, au niveau le plus bavard : aucune ligne ne contient un jeton de session, une note, un nom, un
    courriel, un code d'invitation ni le texte d'une observation."""
    with caplog.at_level(logging.DEBUG):
        assert client.post(f"/api/pulse/demo/aller/{len(Demo.ETAPES)}", headers=CONSOLE).status_code == 200
        personas = client.get("/api/pulse/console/personas", headers=CONSOLE).json()
        s = next(p for p in personas if p["id"] == md.SOPHIE)
        client.get("/api/pulse/moi/decouvertes", headers={"X-Pulse-Session": s["session"]})
        client.post("/api/pulse/moi/notes", headers={"X-Pulse-Session": s["session"]}, json={"texte": "Note très privée sur Markus Weber."})
    brut = "\n".join(json.dumps(x, ensure_ascii=False) for x in _lignes(caplog))
    assert "transition" in brut and "appel IA" in brut and '"route": "/api/pulse/moi/decouvertes"' in brut   # le journal existe…
    interdits = [p["session"] for p in personas if p.get("session")] + [p["code"] for p in personas if p.get("code")]
    interdits += [p["nom"] for p in personas] + ["Note très privée", "distributeurs bio", "tisanes", "@"]
    for x in interdits:
        assert x not in brut, x                                            # …et ne dit rien de privé


def test_transition_journalisee_avec_l_identifiant_de_requete(caplog):
    with caplog.at_level(logging.INFO):
        r = client.post("/api/pulse/demo/aller/5", headers=CONSOLE)
    rid = r.headers["x-request-id"]
    transitions = [x for x in _lignes(caplog) if x["msg"] == "transition"]
    assert transitions and all(x["requete"] == rid for x in transitions)
    assert {"essai", "vers", "agent"} <= set(transitions[0]) and "raison" not in transitions[0]


def test_niveau_de_journal_invalide_est_une_erreur_de_configuration_claire():
    assert niveau_depuis_env({}) == "INFO" and niveau_depuis_env({"HACKVS_JOURNAL": "debug"}) == "DEBUG"
    with pytest.raises(ValueError, match="HACKVS_JOURNAL"):
        niveau_depuis_env({"HACKVS_JOURNAL": "BAVARD"})
