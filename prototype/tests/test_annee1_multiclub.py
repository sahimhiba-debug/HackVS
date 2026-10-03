"""ANNÉE 1 · LOT 8 — Grandir : la notion de « club » (un club partenaire, EXEMPLE FICTIF marqué comme tel), l'adhésion
croisée demandée par le membre lui-même, les membres à distance ; et l'interface FR / DE / EN (traductions « à relire
par un natif »). Interrupteur HACKVS_MULTICLUB. Données FICTIVES."""
import json
import re
from pathlib import Path

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import clubs
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.erreurs import Interdit, Invalide

TAX = charger_taxonomie()
WEB = Path(__file__).resolve().parents[1] / "web" / "pulse"


@pytest.fixture
def demo(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(TAX)


def test_sans_declaration_un_seul_club_et_tout_le_monde_y_est(demo):
    c = demo.club
    assert [x["id"] for x in clubs.liste(c)] == [clubs.PRINCIPAL]
    assert clubs.clubs_de(c, md.PAULINE) == {"principal": clubs.PRINCIPAL, "croises": [], "a_distance": False}


def test_un_club_partenaire_est_un_exemple_fictif_marque(demo):
    c = demo.club
    p = clubs.declarer(c, "hs-exemple", "Club partenaire — exemple fictif", region="Haute-Savoie", pays="FR", fictif=True)
    assert p["fictif"] is True and "fictif" in p["nom"].lower()
    with pytest.raises(Invalide):
        clubs.declarer(c, "vraiment", "Un vrai club", region="Aoste", pays="IT", fictif=False)   # jamais un partenaire présenté comme acquis
    with pytest.raises(Invalide):
        clubs.declarer(c, "hs-exemple", "doublon", region="", pays="FR", fictif=True)


def test_adhesion_croisee_demandee_par_le_membre_et_retirable(demo):
    c = demo.club
    clubs.declarer(c, "hs-exemple", "Club partenaire — exemple fictif", region="Haute-Savoie", pays="FR", fictif=True)
    clubs.rejoindre(c, md.PAULINE, "hs-exemple")
    assert clubs.clubs_de(c, md.PAULINE)["croises"] == ["hs-exemple"]
    assert clubs.peut_etre_sollicite(c, md.PAULINE, "hs-exemple") and not clubs.peut_etre_sollicite(c, md.MARKUS, "hs-exemple")
    clubs.quitter(c, md.PAULINE, "hs-exemple")
    assert clubs.clubs_de(c, md.PAULINE)["croises"] == [] and not clubs.peut_etre_sollicite(c, md.PAULINE, "hs-exemple")
    with pytest.raises(Invalide):
        clubs.rejoindre(c, md.PAULINE, "inconnu")
    with pytest.raises(Interdit):
        clubs.rejoindre(c, md.PAULINE, clubs.PRINCIPAL)                       # on n'adhère pas « en croisé » à son propre club


def test_membre_a_distance(demo):
    c = demo.club
    clubs.a_distance(c, md.PAULINE, True)
    assert clubs.clubs_de(c, md.PAULINE)["a_distance"] is True
    clubs.a_distance(c, md.PAULINE, False)
    assert clubs.clubs_de(c, md.PAULINE)["a_distance"] is False


def test_la_console_ne_voit_que_des_decomptes(demo):
    c = demo.club
    clubs.declarer(c, "hs-exemple", "Club partenaire — exemple fictif", region="Haute-Savoie", pays="FR", fictif=True)
    clubs.rejoindre(c, md.PAULINE, "hs-exemple")
    vue = clubs.vue_console(c)
    partenaire = next(x for x in vue["clubs"] if x["id"] == "hs-exemple")
    assert partenaire["membres_croises"] == "< 3" and "s01" not in json.dumps(vue)


def test_survit_au_redemarrage(demo):
    c = demo.club
    clubs.declarer(c, "hs-exemple", "Club partenaire — exemple fictif", region="Haute-Savoie", pays="FR", fictif=True)
    clubs.rejoindre(c, md.PAULINE, "hs-exemple")
    repris = Demo(TAX, reprendre=True).club
    assert clubs.clubs_de(repris, md.PAULINE)["croises"] == ["hs-exemple"]


# ------------------------------------------------------------------ interface FR / DE / EN
def _cles(js: str, nom: str) -> set[str]:
    bloc = js.split(f"export const {nom} = {{", 1)[1].split("\n};", 1)[0]
    return set(re.findall(r'"((?:[^"\\]|\\.)*)":', bloc))


def test_l_anglais_couvre_chaque_libelle_de_l_allemand():
    js = (WEB / "traduction-de.js").read_text(encoding="utf-8")
    de, en = _cles(js, "DE"), _cles(js, "EN")
    assert len(de) > 40 and en == de
    assert "native speaker" in js and "à relire" in js


def test_l_interface_en_anglais_dans_un_vrai_navigateur(tmp_path):
    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    erreurs: list[str] = []
    with serveur(HACKVS_ESSAIS_DB=str(tmp_path / "j.db"), HACKVS_FOIRE="1") as base, sync_playwright() as p:
        b = _chromium(p)
        pg = b.new_page()
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(f"{base}/app?lang=en#acces")
        pg.locator("[data-role=traduction]").wait_for()
        assert pg.evaluate("document.documentElement.lang") == "en"
        assert "Activate your Club account" in pg.inner_text("body")
        b.close()
    assert not erreurs, erreurs


def test_par_http_eteint_puis_allume(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app
    cl = TestClient(app)
    console = {"X-Pulse-Console": "1"}
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    cl.post("/api/pulse/demo/reinitialiser", headers=console)
    s = {"X-Pulse-Session": next(p["session"] for p in cl.get("/api/pulse/console/personas", headers=console).json()
                                 if p["id"] == md.PAULINE)}
    monkeypatch.delenv("HACKVS_MULTICLUB", raising=False)
    assert cl.get("/api/pulse/moi/clubs", headers=s).status_code == 404
    monkeypatch.setenv("HACKVS_MULTICLUB", "1")
    assert cl.get("/api/pulse/moi/clubs", headers=s).json()["moi"]["croises"] == []
    assert cl.post("/api/pulse/moi/clubs/inconnu", headers=s).status_code == 422
    assert cl.post("/api/pulse/moi/a-distance", headers=s, json={"oui": True}).json()["a_distance"] is True
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    cl.post("/api/pulse/demo/reinitialiser", headers=console)
