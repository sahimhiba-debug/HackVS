"""ANNÉE 1 · LOT 4 — La console du secrétariat par HTTP : éteinte par défaut (404) ; chaque route exige un compte
NOMINATIF du secrétariat ou de l'administration, double authentification active ET session élevée (lot 2) ; un membre,
une session non élevée, un jeton de console « démo » : refusés. Données FICTIVES."""
import time

import pytest
from fastapi.testclient import TestClient

from intelligence.comptes import code_totp

CONSOLE = {"X-Pulse-Console": "1"}
LECTURES = ["/api/pulse/secretariat/metiers", "/api/pulse/secretariat/pilote", "/api/pulse/secretariat/campagnes",
            "/api/pulse/secretariat/comptes", "/api/pulse/secretariat/bilan.md", "/api/pulse/secretariat/bilan.csv"]


@pytest.fixture
def api(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_SECRET", "z" * 40)
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    monkeypatch.setenv("HACKVS_COMPTES", "1")
    monkeypatch.setenv("HACKVS_SECRETARIAT", "1")
    csv = tmp_path / "e.csv"
    csv.write_text("nom;metier\nQuirinFidu;Fiduciaire\nYvoJardins;Paysagiste\n", encoding="utf-8")
    monkeypatch.setenv("HACKVS_ENTREPRISES_CSV", str(csv))
    monkeypatch.setenv("HACKVS_CRITERES_PILOTE", str(tmp_path / "criteres.json"))
    import json
    from intelligence import secretariat
    (tmp_path / "criteres.json").write_text(json.dumps(secretariat.criteres_par_defaut()), encoding="utf-8")
    from fastapi import FastAPI
    from app.comptes_api import creer_routeur_comptes
    from app.pulse_api import creer_routeur
    from app.taxonomy import charger_taxonomie
    routeur = creer_routeur(charger_taxonomie())
    app = FastAPI()
    app.include_router(routeur)
    app.include_router(creer_routeur_comptes(routeur.comptes))
    cl = TestClient(app)
    comptes = routeur.comptes()
    admin = comptes.amorcer_administration("Administration (fictive)")
    prep = comptes.preparer_totp(admin)                    # audit I1 : administrer exige le second facteur
    comptes.confirmer_totp(admin, code_totp(prep["secret"], time.time()))
    comptes.elever(admin, code_totp(prep["secret"], time.time() + 30))

    def compte(role: str, totp: bool = True, elever: bool = True) -> str:
        jeton = comptes.inviter(admin, role=role, etiquette=f"{role} fictif", duree_s=600)["jeton"]
        s = comptes.accepter(jeton, appareil="test")
        if totp:
            prep = comptes.preparer_totp(s)
            comptes.confirmer_totp(s, code_totp(prep["secret"], time.time()))
            if elever:
                comptes.elever(s, code_totp(prep["secret"], time.time() + 30))
        return s
    compte.admin = comptes.verifier(admin)["compte"]  # type: ignore[attr-defined]
    return cl, compte


def h(s):
    return {"X-Pulse-Compte": s}


def test_eteinte_par_defaut(api, monkeypatch):
    cl, compte = api
    s = compte("secretariat")
    monkeypatch.delenv("HACKVS_SECRETARIAT")
    for chemin in LECTURES:
        assert cl.get(chemin, headers=h(s)).status_code == 404, chemin


def test_seul_un_compte_nominatif_eleve_ouvre_la_console(api):
    cl, compte = api
    refuses = {"aucune session": {}, "jeton console démo": CONSOLE, "membre": h(compte("membre")),
               "secrétariat sans TOTP": h(compte("secretariat", totp=False)),
               "secrétariat non élevé": h(compte("secretariat", elever=False))}
    for nom, entetes in refuses.items():
        for chemin in LECTURES:
            assert cl.get(chemin, headers=entetes).status_code in (401, 403), (nom, chemin)
    s = h(compte("secretariat"))
    for chemin in LECTURES:
        assert cl.get(chemin, headers=s).status_code == 200, chemin


def test_metier_confirme_campagne_et_pilote(api):
    cl, compte = api
    s = h(compte("secretariat"))
    m = cl.get("/api/pulse/secretariat/metiers", headers=s).json()
    assert m["a_verifier"] == [] and m["rares"] == 2                      # une entreprise chacun : jamais montrés (audit I5)
    assert cl.post("/api/pulse/secretariat/metiers", headers=s, json={"valeur": "Fiduciaire", "metier": "comptabilite"}).status_code == 200
    assert cl.get("/api/pulse/secretariat/metiers", headers=s).json()["rares"] == 1
    metier = cl.get("/api/pulse/secretariat/campagnes", headers=s).json()["metiers_cherches"][0]["metier"]
    r = cl.post("/api/pulse/secretariat/campagnes", headers=s, json={"metier": metier, "nombre": 2})
    assert r.status_code == 200 and len(r.json()["invitations"]) == 2
    assert cl.post("/api/pulse/secretariat/pilote/geler", headers=s).status_code == 200
    assert cl.post("/api/pulse/secretariat/pilote/geler", headers=s).status_code == 422          # le premier gel fait foi
    assert cl.get("/api/pulse/secretariat/pilote", headers=s).json()["gel"] is not None


def test_bilan_exportable(api):
    cl, compte = api
    s = h(compte("secretariat"))
    md = cl.get("/api/pulse/secretariat/bilan.md", headers=s)
    assert md.status_code == 200 and "attachment" in md.headers["content-disposition"] and md.text.startswith("# Bilan")
    csv = cl.get("/api/pulse/secretariat/bilan.csv", headers=s)
    assert csv.headers["content-type"].startswith("text/csv") and csv.text.startswith("mesure;valeur")
    pdf = cl.get("/api/pulse/secretariat/bilan.pdf", headers=s)
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-" and pdf.headers["content-type"] == "application/pdf"


def test_gestion_des_comptes_depuis_la_console(api):
    cl, compte = api
    s = h(compte("secretariat"))
    m = compte("membre")
    liste = cl.get("/api/pulse/secretariat/comptes", headers=s).json()
    assert any(x["role"] == "membre" for x in liste) and all("totp" not in x and "secret" not in str(x) for x in liste)
    cible = next(x["compte"] for x in liste if x["role"] == "membre")
    assert cl.post(f"/api/pulse/secretariat/comptes/{cible}/revoquer", headers=s).status_code == 200
    assert cl.get("/api/pulse/comptes/moi", headers=h(m)).status_code == 401
    assert all(x["role"] in ("membre", "invite") for x in liste)            # le secrétariat ne voit que membres et invités
    assert cl.post(f"/api/pulse/secretariat/comptes/{compte.admin}/revoquer", headers=s).status_code == 403   # ni ne révoque l'administration
    inv = cl.post("/api/pulse/secretariat/invitations", headers=s, json={"role": "membre", "etiquette": "nouveau membre fictif"})
    assert inv.status_code == 200 and inv.json()["jeton"]
    assert cl.post("/api/pulse/secretariat/invitations", headers=s,
                   json={"role": "administration", "etiquette": "x"}).status_code == 403


def test_la_console_dans_un_vrai_navigateur(tmp_path):
    """Serveur réel : administration amorcée par l'outil, invitation du secrétariat, /compte (session, TOTP, élévation),
    puis /secretariat : le tableau du pilote s'affiche ; aucune erreur JS (CSP stricte)."""
    import json
    import os
    import subprocess
    import sys
    import urllib.request
    from pathlib import Path

    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    journal, secret = str(tmp_path / "j.db"), "w" * 40
    env = {"HACKVS_COMPTES": "1", "HACKVS_SECRETARIAT": "1", "HACKVS_ESSAIS_DB": journal, "HACKVS_SECRET": secret,
           "HACKVS_FOIRE": "1"}
    with serveur(**env) as base:
        admin = subprocess.run([sys.executable, "scripts/comptes.py", "amorcer", "Administration fictive"], capture_output=True,
                               text=True, cwd=Path(__file__).resolve().parents[1],
                               env={**os.environ, **env}).stdout.strip().splitlines()[-1]
        from tests.aide_comptes import elever_http
        elever_http(base, admin)
        req = urllib.request.Request(base + "/api/pulse/comptes/admin/invitations", headers={"Content-Type": "application/json",
                                     "X-Pulse-Compte": admin}, data=json.dumps({"role": "secretariat", "etiquette": "Secrétariat 1 (fictif)",
                                                                                 "duree_s": 600}).encode())
        jeton = json.load(urllib.request.urlopen(req))["jeton"]
        erreurs: list[str] = []
        with sync_playwright() as p:
            b = _chromium(p)
            pg = b.new_page(viewport={"width": 1100, "height": 900})
            pg.on("pageerror", lambda e: erreurs.append(str(e)))
            pg.goto(f"{base}/compte#invitation={jeton}")
            pg.click("#accepter")
            pg.locator("#liste li").first.wait_for()
            pg.click("#preparer")
            pg.locator("#cle").wait_for(state="visible")
            cle = pg.inner_text("#cle")
            pg.fill("#code", code_totp(cle, time.time()))
            pg.click("#confirmer")
            pg.locator("#etat:has-text('activée')").wait_for()
            pg.fill("#code", code_totp(cle, time.time() + 30))
            pg.click("#elever")
            pg.locator("#qui:has-text('console ouverte')").wait_for()
            pg.goto(f"{base}/secretariat")
            pg.locator("#pilote tr").first.wait_for()
            assert pg.locator("#pilote tr").count() == 5
            pg.fill("#inv-etiquette", "Entreprise fictive")
            pg.click("#inv-ok")
            pg.locator("#inv-lien:has-text('/compte#invitation=')").wait_for()
            b.close()
        assert not erreurs, erreurs
