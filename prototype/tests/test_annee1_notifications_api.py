"""ANNÉE 1 · LOT 5 — Notifications par HTTP : éteintes par défaut ; le secrétariat (compte nominatif élevé) relance les
membres qui ont des demandes en attente ; suivi agrégé ; désinscription publique par lien SIGNÉ (page /desinscription).
Sans SMTP_HOST : tout est SIMULÉ (démonstration). Avec SMTP_HOST : un vrai serveur SMTP local reçoit. Données FICTIVES."""
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from intelligence.comptes import code_totp
from tests.test_annee1_notifications import ServeurSmtp, _texte


@pytest.fixture
def api(monkeypatch, tmp_path):
    for k, v in {"HACKVS_ESSAIS_DB": str(tmp_path / "j.db"), "HACKVS_SECRET": "q" * 40, "HACKVS_FOIRE": "1", "HACKVS_COMPTES": "1",
                 "HACKVS_SECRETARIAT": "1", "HACKVS_NOTIFICATIONS": "1", "HACKVS_ESPACE_MEMBRE": "1"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    from app.pulse_api import creer_routeur
    from app.taxonomy import charger_taxonomie
    routeur = creer_routeur(charger_taxonomie())
    app = FastAPI()
    app.include_router(routeur)
    cl = TestClient(app)
    cp = routeur.comptes()
    admin = cp.amorcer_administration("Administration (fictive)")
    for s in [admin]:
        p = cp.preparer_totp(s)
        cp.confirmer_totp(s, code_totp(p["secret"], time.time()))
        cp.elever(s, code_totp(p["secret"], time.time() + 30))
    sec = cp.accepter(cp.inviter(admin, role="secretariat", etiquette="Secrétariat (fictif)", duree_s=600)["jeton"], appareil="x")
    p = cp.preparer_totp(sec)
    cp.confirmer_totp(sec, code_totp(p["secret"], time.time()))
    cp.elever(sec, code_totp(p["secret"], time.time() + 30))
    return cl, {"X-Pulse-Compte": sec}, monkeypatch


def _membres_email(cl):
    """Tous les membres fictifs choisissent l'e-mail (préférences du lot 3), par leur propre session."""
    for p in cl.get("/api/pulse/console/personas", headers={"X-Pulse-Console": "1"}).json():
        if not p.get("session"):
            continue
        cl.post("/api/pulse/moi/preferences", headers={"X-Pulse-Session": p["session"]},
                json={"langue": "fr", "region": "", "canaux": ["app", "email"]})


def test_eteintes_par_defaut(api):
    cl, sec, mp = api
    mp.delenv("HACKVS_NOTIFICATIONS")
    assert cl.get("/api/pulse/secretariat/notifications", headers=sec).status_code == 404
    assert cl.post("/api/pulse/notifications/desinscrire", json={"jeton": "x.email.y.z"}).status_code == 404


def test_relance_simulee_sans_smtp(api):
    cl, sec, _ = api
    _membres_email(cl)
    r = cl.post("/api/pulse/secretariat/notifications/relance", headers=sec)
    assert r.status_code == 200 and r.json()["simule"] >= 1 and r.json()["envoye"] == 0
    suivi = cl.get("/api/pulse/secretariat/notifications", headers=sec).json()
    assert any(x["statut"] == "simule" for x in suivi["envois"]) and "@" not in str(suivi)


def test_relance_reelle_par_smtp_puis_desinscription(api):
    cl, sec, mp = api
    smtp = ServeurSmtp()
    try:
        mp.setenv("SMTP_HOST", "127.0.0.1")
        mp.setenv("SMTP_PORT", str(smtp.port))
        mp.setenv("SMTP_STARTTLS", "0")
        mp.setenv("SMTP_EXPEDITEUR", "club@exemple.invalid")
        _membres_email(cl)
        r = cl.post("/api/pulse/secretariat/notifications/relance", headers=sec).json()
        assert r["envoye"] >= 1 and len(smtp.recus) == r["envoye"]
        jeton = _texte(smtp.recus[0]).rsplit("desinscription#j=", 1)[1].split()[0]
        assert cl.post("/api/pulse/notifications/desinscrire", json={"jeton": jeton}).json()["desinscrit"] is True
        assert cl.post("/api/pulse/notifications/desinscrire", json={"jeton": jeton[:-2] + "00"}).status_code == 401
        avant = len(smtp.recus)
        r2 = cl.post("/api/pulse/secretariat/notifications/relance", headers=sec).json()
        assert len(smtp.recus) == avant and r2["envoye"] == 0             # même jour : aucun doublon (audit I2), et la
        #                                                                   personne désinscrite ne reçoit plus rien
    finally:
        smtp.fermer()


def test_seul_le_secretariat_eleve_relance(api):
    cl, _, _ = api
    for entetes in ({}, {"X-Pulse-Console": "1"}, {"X-Pulse-Compte": "faux.1.x"}):
        assert cl.post("/api/pulse/secretariat/notifications/relance", headers=entetes).status_code in (401, 403)
