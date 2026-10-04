"""ANNÉE 1 — correctifs de l'audit des lots 6 (confiance), 7 (suivi IA) et 8 (plusieurs clubs). Chaque cas reproduit un
constat de l'audit (docs/annee-1/AUDIT_LOT678.md) ; il était ROUGE avant le correctif. Données FICTIVES."""
import time

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import clubs, espace_membre as em, monde_demo as md, suivi_ia
from intelligence.comptes import Comptes, code_totp
from intelligence.demo import Demo
from intelligence.erreurs import Invalide

TAX = charger_taxonomie()


@pytest.fixture
def demo(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(TAX)


# ------------------------------------------------------------------ B1 : la purge d'un membre ne touche pas la sécurité
def test_b1_la_purge_ne_falsifie_pas_le_journal_des_acces(demo):
    c = demo.club
    cp = Comptes(c.journal, b"z" * 48)
    admin = cp.amorcer_administration("Secrétariat 1")
    p = cp.preparer_totp(admin)
    cp.confirmer_totp(admin, code_totp(p["secret"], time.time()))
    cp.elever(admin, code_totp(p["secret"], time.time() + 30))
    cp.tracer_acces(admin, "GET /api/pulse/secretariat/comptes")
    avant = cp.journal_acces(admin)
    for texte in ("GET /api/pulse/secretariat", "Secrétariat 1"):           # exactement la route, exactement l'étiquette
        prop = c.demander(md.PAULINE, texte)
        c.confirmer_demande(md.PAULINE, prop["proposition"])
    em.effacer_definitivement(c, md.PAULINE)
    assert cp.journal_acces(admin)[:len(avant)] == avant                      # ni la route ni le « qui » ne changent


def test_b1_le_nom_d_un_club_exemple_n_est_pas_purge(demo):
    c = demo.club
    clubs.declarer(c, "hs-exemple", "Club partenaire Haute-Savoie — exemple fictif", region="", pays="FR", fictif=True)
    prop = c.demander(md.PAULINE, "Club partenaire Haute-Savoie — exemple fictif")
    c.confirmer_demande(md.PAULINE, prop["proposition"])
    em.effacer_definitivement(c, md.PAULINE)
    assert "exemple fictif" in next(x for x in clubs.liste(c) if x["id"] == "hs-exemple")["nom"]


# ------------------------------------------------------------------ I1 : « < 3 » compté sur ceux qui ont accepté
def test_i1_acceptations_d_une_seule_entreprise_non_dites(demo, monkeypatch):
    monkeypatch.setenv("HACKVS_SUIVI_IA", "1")
    c = demo.club
    membres = [md.PAULINE, md.MARKUS, md.SOPHIE, "s02", "s03"]
    for pid in membres:
        p = c.demander(pid, "Je cherche une salle pour 20 personnes à Martigny.")
        if pid == md.PAULINE:
            c.confirmer_demande(pid, p["proposition"])
    r = suivi_ia.taux(c)["par_source"]["regles"]
    assert r["acceptees"] == "< 3" and r["taux"] is None


# ------------------------------------------------------------------ I6 : un membre effacé ne compte plus ; export complet
def test_i6_apres_effacement_le_membre_ne_compte_plus_et_l_export_dit_ses_clubs(demo):
    c = demo.club
    clubs.declarer(c, "hs-exemple", "Club partenaire — exemple fictif", region="", pays="FR", fictif=True)
    for pid in (md.PAULINE, md.MARKUS, md.SOPHIE):
        clubs.rejoindre(c, pid, "hs-exemple")
        clubs.a_distance(c, pid, True)
    x = em.exporter(c, md.MARKUS)
    assert x["clubs"]["croises"] == ["hs-exemple"] and x["clubs"]["a_distance"] is True
    vue = clubs.vue_console(c)
    assert next(z for z in vue["clubs"] if z["id"] == "hs-exemple")["membres_croises"] == 3
    em.effacer_definitivement(c, md.PAULINE)
    vue = clubs.vue_console(c)
    assert next(z for z in vue["clubs"] if z["id"] == "hs-exemple")["membres_croises"] == "< 3"
    assert vue["membres_a_distance"] == "< 3"


# ------------------------------------------------------------------ M2 : « exemple fictif » exigé, pas un mot quelconque
def test_m2_un_nom_qui_contient_fictif_ne_suffit_pas(demo):
    with pytest.raises(Invalide):
        clubs.declarer(demo.club, "rot", "Rotary — pas fictif, partenaire signé", region="", pays="CH", fictif=True)


# ------------------------------------------------------------------ I4 : l'anglais suit l'interrupteur
def test_i4_l_anglais_suit_l_interrupteur(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app
    cl = TestClient(app)
    monkeypatch.delenv("HACKVS_MULTICLUB", raising=False)
    assert cl.get("/api/pulse/langues").status_code == 404
    monkeypatch.setenv("HACKVS_MULTICLUB", "1")
    assert cl.get("/api/pulse/langues").json()["en"] is True


def test_i4_dans_un_vrai_navigateur_eteint_reste_en_francais(tmp_path):
    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    with serveur(HACKVS_ESSAIS_DB=str(tmp_path / "j.db"), HACKVS_FOIRE="1") as base, sync_playwright() as p:
        b = _chromium(p)
        pg = b.new_page()
        pg.goto(f"{base}/app?lang=en#acces")
        pg.locator("text=Activez votre compte du Club").wait_for()
        pg.wait_for_timeout(800)
        assert pg.evaluate("document.documentElement.lang") != "en" and "Activate" not in pg.inner_text("body")
        b.close()


def test_i2_refus_et_administration_entrent_au_journal_des_acces(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.comptes_api import creer_routeur_comptes
    from app.pulse_api import creer_routeur
    for k, v in {"HACKVS_ESSAIS_DB": str(tmp_path / "j.db"), "HACKVS_SECRET": "y" * 40, "HACKVS_FOIRE": "1",
                 "HACKVS_COMPTES": "1", "HACKVS_SECRETARIAT": "1"}.items():
        monkeypatch.setenv(k, v)
    routeur = creer_routeur(TAX)
    app = FastAPI()
    app.include_router(routeur)
    app.include_router(creer_routeur_comptes(routeur.comptes))
    cl = TestClient(app)
    cp = routeur.comptes()
    admin = cp.amorcer_administration("Admin (fictive)")
    p = cp.preparer_totp(admin)
    cp.confirmer_totp(admin, code_totp(p["secret"], time.time()))
    cp.elever(admin, code_totp(p["secret"], time.time() + 30))
    sec = cp.accepter(cp.inviter(admin, role="secretariat", etiquette="Secrétariat non élevé", duree_s=600)["jeton"], appareil="x")
    assert cl.get("/api/pulse/secretariat/comptes", headers={"X-Pulse-Compte": sec}).status_code == 403
    cl.get("/api/pulse/comptes/admin/journal", headers={"X-Pulse-Compte": admin})
    vus = [(x["qui"], x["route"]) for x in cl.get("/api/pulse/secretariat/acces", headers={"X-Pulse-Compte": admin}).json()]
    assert ("Secrétariat non élevé", "GET /api/pulse/secretariat/comptes (refusé)") in vus
    assert ("Admin (fictive)", "GET /api/pulse/comptes/admin/journal") in vus
