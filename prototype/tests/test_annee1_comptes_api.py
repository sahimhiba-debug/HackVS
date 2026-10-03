"""ANNÉE 1 · LOT 2 — Authentification et rôles (HTTP) : interrupteur HACKVS_COMPTES, CSRF, balayage d'autorisation.

La session passe par l'en-tête X-Pulse-Compte (jamais un cookie) : un autre site ne peut pas la faire envoyer par le
navigateur, et un en-tête personnalisé impose un pré-vol CORS que le serveur n'accorde pas. En plus : toute requête qui
annonce une ORIGINE étrangère est refusée (403). Données FICTIVES."""
import hashlib
import hmac
import struct
import re

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.comptes_api import creer_routeur_comptes
from intelligence import comptes as cp
from plateforme.memoire import Memoire

SECRET = b"t" * 48


def totp(secret_b32: str, t: float) -> str:
    import base64
    cle = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    h = hmac.new(cle, struct.pack(">Q", int(t // 30)), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return f"{(struct.unpack('>I', h[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000:06d}"


@pytest.fixture
def api():
    t = [1_800_000_000.0]
    c = cp.Comptes(Memoire(), SECRET, horloge=lambda: t[0])
    admin = c.amorcer_administration("Administration")
    prep = c.preparer_totp(admin)                          # audit I1 : administrer exige le second facteur
    c.confirmer_totp(admin, totp(prep["secret"], t[0]))
    t[0] += 30
    c.elever(admin, totp(prep["secret"], t[0]))
    app = FastAPI()
    routeur = creer_routeur_comptes(lambda: c)
    app.include_router(routeur)
    app.state.routeur = routeur                    # le balayage lit les routes du ROUTEUR (FastAPI les regroupe une fois incluses)
    return TestClient(app), c, admin, t


def h(session: str) -> dict:
    return {"X-Pulse-Compte": session}


def test_parcours_complet_invitation_session_appareils_deconnexion(api):
    cl, c, admin, t = api
    r = cl.post("/api/pulse/comptes/admin/invitations", headers=h(admin), json={"role": "membre", "etiquette": "membre fictif", "duree_s": 3600})
    assert r.status_code == 200
    jeton = r.json()["jeton"]
    s = cl.post("/api/pulse/comptes/invitations/accepter", json={"jeton": jeton, "appareil": "Téléphone"}).json()["session"]
    assert cl.get("/api/pulse/comptes/moi", headers=h(s)).json()["role"] == "membre"
    assert cl.post("/api/pulse/comptes/invitations/accepter", json={"jeton": jeton, "appareil": "x"}).status_code == 401
    apps = cl.get("/api/pulse/comptes/moi/appareils", headers=h(s)).json()
    assert len(apps) == 1 and apps[0]["celui_ci"] is True
    assert cl.post("/api/pulse/comptes/moi/deconnexion", headers=h(s)).status_code == 200
    assert cl.get("/api/pulse/comptes/moi", headers=h(s)).status_code == 401


def test_console_par_compte_nominatif_et_totp(api):
    cl, c, admin, t = api
    jeton = cl.post("/api/pulse/comptes/admin/invitations", headers=h(admin),
                    json={"role": "secretariat", "etiquette": "Secrétariat 1", "duree_s": 600}).json()["jeton"]
    s = cl.post("/api/pulse/comptes/invitations/accepter", json={"jeton": jeton, "appareil": "Mac"}).json()["session"]
    assert cl.get("/api/pulse/comptes/console/moi", headers=h(s)).status_code == 403
    prep = cl.post("/api/pulse/comptes/moi/totp/preparer", headers=h(s)).json()
    assert cl.post("/api/pulse/comptes/moi/totp/confirmer", headers=h(s), json={"code": totp(prep["secret"], t[0])}).status_code == 200
    t[0] += 30
    assert cl.post("/api/pulse/comptes/moi/elever", headers=h(s), json={"code": totp(prep["secret"], t[0])}).status_code == 200
    assert cl.get("/api/pulse/comptes/console/moi", headers=h(s)).json()["role"] == "secretariat"


def test_une_origine_etrangere_est_refusee(api):
    """CSRF : un formulaire d'un autre site qui tenterait une action reçoit 403, même avec une session valide."""
    cl, c, admin, t = api
    r = cl.post("/api/pulse/comptes/admin/invitations", headers={**h(admin), "Origin": "https://pirate.exemple"},
                json={"role": "membre", "etiquette": "x", "duree_s": 60})
    assert r.status_code == 403
    r = cl.post("/api/pulse/comptes/admin/invitations", headers={**h(admin), "Origin": "http://testserver"},
                json={"role": "membre", "etiquette": "x", "duree_s": 60})
    assert r.status_code == 200                                          # même origine : accepté


def test_balayage_chaque_route_exige_une_session_sauf_accepter(api):
    cl, c, admin, t = api
    routes = cl.app.state.routeur.routes
    assert len(routes) >= 13                                              # le balayage voit bien toutes les routes
    publiques = set()
    for r in routes:
        if not isinstance(r, APIRoute):
            continue
        for m in r.methods:
            chemin = re.sub(r"\{\w+\}", "x1", r.path)
            code = cl.request(m, chemin, json={} if m != "GET" else None).status_code
            if code not in (401, 403):
                publiques.add((m, r.path))
            mauvaise = cl.request(m, chemin, headers=h("faux.1.signature"), json={} if m != "GET" else None).status_code
            if (m, r.path) not in publiques:
                assert mauvaise in (401, 403), (m, r.path)
    assert publiques == {("POST", "/api/pulse/comptes/invitations/accepter")}


def test_un_membre_n_atteint_aucune_route_d_administration(api):
    cl, c, admin, t = api
    jeton = cl.post("/api/pulse/comptes/admin/invitations", headers=h(admin), json={"role": "membre", "etiquette": "m", "duree_s": 60}).json()["jeton"]
    s = cl.post("/api/pulse/comptes/invitations/accepter", json={"jeton": jeton, "appareil": "A"}).json()["session"]
    for m, chemin, corps in (("POST", "/api/pulse/comptes/admin/invitations", {"role": "membre", "etiquette": "x", "duree_s": 60}),
                             ("GET", "/api/pulse/comptes/admin/journal", None),
                             ("POST", "/api/pulse/comptes/admin/comptes/c_x/role", {"role": "secretariat"}),
                             ("POST", "/api/pulse/comptes/admin/comptes/c_x/revoquer", {})):
        assert cl.request(m, chemin, headers=h(s), json=corps).status_code == 403, chemin


def test_interrupteur_eteint_par_defaut_dans_le_serveur(monkeypatch):
    monkeypatch.delenv("HACKVS_COMPTES", raising=False)
    from app.main import app
    assert TestClient(app).get("/api/pulse/comptes/moi").status_code == 404


def test_de_bout_en_bout_dans_le_vrai_serveur(tmp_path):
    """Serveur réel (sous-processus) avec HACKVS_COMPTES=1 ; amorçage par l'outil ; invitation, acceptation, appareils."""
    import json
    import subprocess
    import sys
    import urllib.request
    from pathlib import Path

    from tests.test_e2e_scene import serveur
    journal, secret = str(tmp_path / "j.db"), "s" * 40
    with serveur(HACKVS_COMPTES="1", HACKVS_ESSAIS_DB=journal, HACKVS_SECRET=secret, HACKVS_FOIRE="1") as base:
        out = subprocess.run([sys.executable, "scripts/comptes.py", "amorcer", "Administration fictive"], capture_output=True, text=True,
                             cwd=Path(__file__).resolve().parents[1], env={**__import__("os").environ, "HACKVS_ESSAIS_DB": journal,
                                                                          "HACKVS_SECRET": secret}).stdout
        admin = out.strip().splitlines()[-1]
        from tests.aide_comptes import elever_http
        elever_http(base, admin)

        def appel(chemin, corps=None, session=None):
            req = urllib.request.Request(base + chemin, data=None if corps is None else json.dumps(corps).encode(),
                                         headers={"Content-Type": "application/json", **({"X-Pulse-Compte": session} if session else {})})
            return json.load(urllib.request.urlopen(req, timeout=10))
        jeton = appel("/api/pulse/comptes/admin/invitations", {"role": "membre", "etiquette": "membre fictif", "duree_s": 600}, admin)["jeton"]
        s = appel("/api/pulse/comptes/invitations/accepter", {"jeton": jeton, "appareil": "Téléphone"})["session"]
        assert appel("/api/pulse/comptes/moi", session=s)["role"] == "membre"
        assert [x["action"] for x in appel("/api/pulse/comptes/admin/journal", session=admin)] == ["inviter"]


def test_la_page_compte_suit_l_interrupteur(monkeypatch):
    from app.main import app
    cl = TestClient(app)
    monkeypatch.delenv("HACKVS_COMPTES", raising=False)
    assert cl.get("/compte").status_code == 404
    monkeypatch.setenv("HACKVS_COMPTES", "1")
    r = cl.get("/compte")
    assert r.status_code == 200 and "Double authentification" in r.text and "content-security-policy" in r.headers


def test_la_page_compte_dans_un_vrai_navigateur(tmp_path):
    """Invitation → page /compte → session ouverte → appareils → TOTP préparé et confirmé ; aucune erreur JS (la CSP
    stricte autorise bien le script de la page)."""
    import json
    import subprocess
    import sys
    import time
    import urllib.request
    from pathlib import Path

    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    journal, secret = str(tmp_path / "j.db"), "u" * 40
    with serveur(HACKVS_COMPTES="1", HACKVS_ESSAIS_DB=journal, HACKVS_SECRET=secret) as base:
        admin = subprocess.run([sys.executable, "scripts/comptes.py", "amorcer", "Administration fictive"], capture_output=True, text=True,
                               cwd=Path(__file__).resolve().parents[1], env={**__import__("os").environ, "HACKVS_ESSAIS_DB": journal,
                                                                            "HACKVS_SECRET": secret}).stdout.strip().splitlines()[-1]
        from tests.aide_comptes import elever_http
        elever_http(base, admin)
        req = urllib.request.Request(base + "/api/pulse/comptes/admin/invitations", headers={"Content-Type": "application/json", "X-Pulse-Compte": admin},
                                     data=json.dumps({"role": "secretariat", "etiquette": "Secrétariat 1 (fictif)", "duree_s": 600}).encode())
        jeton = json.load(urllib.request.urlopen(req))["jeton"]
        erreurs: list[str] = []
        with sync_playwright() as p:
            b = _chromium(p)
            pg = b.new_page(viewport={"width": 390, "height": 844})
            pg.on("pageerror", lambda e: erreurs.append(str(e)))
            pg.on("console", lambda m: m.type == "error" and erreurs.append(m.text))
            pg.goto(f"{base}/compte#invitation={jeton}")
            pg.fill("#appareil", "Mac du secrétariat")
            pg.click("#accepter")
            pg.locator("#qui:has-text('Secrétariat 1')").wait_for()
            pg.locator("#liste li:has-text('Mac du secrétariat')").wait_for()
            assert "invitation" not in pg.url                                  # le jeton quitte l'adresse
            pg.click("#preparer")
            pg.locator("#cle").wait_for(state="visible")
            pg.fill("#code", totp(pg.inner_text("#cle"), time.time()))
            pg.click("#confirmer")
            pg.locator("#etat:has-text('activée')").wait_for()
            b.close()
        assert erreurs == [], erreurs
