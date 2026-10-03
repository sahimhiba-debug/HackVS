"""ANNÉE 1 · LOT 9 — Allumage Foire : borne de stand (sans personne derrière), import d'une liste d'exposants en CSV,
passes découverte à grande échelle, mesure des ADHÉSIONS venues du passe (confirmées par le secrétariat : une intention
n'est jamais comptée comme une adhésion). Interrupteur HACKVS_FOIRE_ALLUMAGE. Données FICTIVES."""
import json
import time

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import foire_allumage as fa
from intelligence.demo import Demo
from intelligence.erreurs import Invalide, NonAuthentifie

TAX = charger_taxonomie()
CSV = ("exposant;metier;stand\nTraiteur Alpin Fictif SA;restauration/traiteur;A12\nTransports Rhône Fictifs;transport;B03\n"
       "traiteur alpin fictif sa;traiteur;A12\nAtelier Sans Métier;;C01\n")


@pytest.fixture
def demo(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(TAX)


def test_passes_a_grande_echelle(demo):
    c = demo.club
    t0 = time.monotonic()
    lot = fa.emettre_lot(c, 500, origine="stand")
    assert len(lot) == 500 and len({x["nonce"] for x in lot}) == 500
    assert time.monotonic() - t0 < 20
    with pytest.raises(Invalide):
        fa.emettre_lot(c, 501, origine="stand")                   # au plus 500 par lot


def test_import_des_exposants_dedoublonne_et_ne_garde_aucun_nom(demo):
    c = demo.club
    r = fa.importer_exposants(c, CSV, base="https://club.exemple")
    assert r["importes"] == 3 and r["doublons"] == 1 and r["sans_metier"] == 1
    assert r["csv"].splitlines()[0] == "exposant;metier;stand;lien;reference"
    assert all("https://club.exemple/decouverte#passe=" in l for l in r["csv"].splitlines()[1:])
    brut = "".join(e.model_dump_json() for e in c.journal.evenements())
    assert "Traiteur Alpin" not in brut and "Transports Rhône" not in brut   # le journal : décomptes seulement
    passes = c.decouverte.passes()
    assert sum(1 for p in passes.values() if p["origine"] == "exposant") == 3
    with pytest.raises(Invalide):
        fa.importer_exposants(c, "nom_inconnu;x\nA;b\n", base="https://x")


def test_entonnoir_adhesions_confirmees_jamais_des_intentions(demo):
    c = demo.club
    lot = fa.emettre_lot(c, 4, origine="stand")
    sessions = [c.decouverte.activer(x["jeton"])["invite"] for x in lot]
    for i, s in enumerate(sessions):
        c.decouverte.declarer(s, f"Entreprise Fictive {i}", "conseil", "Valais romand")
        c.decouverte.rejoindre(s)                                   # 4 intentions
    e = fa.entonnoir(c)["par_origine"]["stand"]
    assert e["intentions"] == 4 and e["adhesions"] == 0             # une intention n'est pas une adhésion
    refs = [x["reference"] for x in fa.intentions(c)]
    for ref in refs[:3]:
        fa.confirmer_adhesion(c, ref, par="Secrétariat (fictif)")
    e = fa.entonnoir(c)["par_origine"]["stand"]
    assert e["adhesions"] == 3 and e["emis"] == 4 and e["taux_adhesion"] == 75
    with pytest.raises(Invalide):
        fa.confirmer_adhesion(c, refs[0], par="x")                  # une seule fois
    with pytest.raises(Invalide):
        fa.confirmer_adhesion(c, "inconnue", par="x")
    assert "Entreprise Fictive" not in json.dumps(fa.intentions(c))  # la liste montre une référence, jamais un nom


def test_sous_trois_entreprises_les_adhesions_ne_sont_pas_dites(demo):
    c = demo.club
    s = c.decouverte.activer(fa.emettre_lot(c, 1, origine="stand")[0]["jeton"])["invite"]
    c.decouverte.declarer(s, "Seule Fictive SA", "conseil", "Valais romand")
    c.decouverte.rejoindre(s)
    fa.confirmer_adhesion(c, fa.intentions(c)[0]["reference"], par="x")
    e = fa.entonnoir(c)["par_origine"]["stand"]
    assert e["adhesions"] == "< 3" and e["taux_adhesion"] is None


# ------------------------------------------------------------------ borne
def test_la_borne_exige_son_jeton_et_respecte_son_rythme(demo):
    c = demo.club
    secret = b"b" * 32
    jeton = fa.jeton_borne(secret, "stand-A")
    assert fa.verifier_borne(secret, jeton) == "stand-A"
    with pytest.raises(NonAuthentifie):
        fa.verifier_borne(secret, jeton[:-2] + "00")
    horloge = [1000.0]
    borne = fa.Borne(secret, horloge=lambda: horloge[0])
    assert borne.passe(c, jeton)["jeton"]
    with pytest.raises(fa.TropVite):
        borne.passe(c, jeton)                                       # un visiteur à la fois
    horloge[0] += fa.BORNE_INTERVALLE_S
    assert borne.passe(c, jeton)["origine"] == "borne"


# ------------------------------------------------------------------ par HTTP et dans un vrai navigateur
def test_la_borne_par_http_refuse_sans_jeton_et_eteinte(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.pulse_api import creer_routeur
    for k, v in {"HACKVS_ESSAIS_DB": str(tmp_path / "j.db"), "HACKVS_SECRET": "k" * 40, "HACKVS_FOIRE": "1"}.items():
        monkeypatch.setenv(k, v)
    app = FastAPI()
    app.include_router(creer_routeur(TAX))
    cl = TestClient(app)
    assert cl.post("/api/pulse/borne/passe").status_code == 404                 # éteinte
    monkeypatch.setenv("HACKVS_FOIRE_ALLUMAGE", "1")
    assert cl.post("/api/pulse/borne/passe").status_code == 401
    assert cl.post("/api/pulse/borne/passe", headers={"X-Pulse-Borne": "b1.x.00"}).status_code == 401


def test_la_borne_dans_un_vrai_navigateur(tmp_path):
    import hashlib
    import hmac

    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    secret = "h" * 40
    with serveur(HACKVS_FOIRE_ALLUMAGE="1", HACKVS_ESSAIS_DB=str(tmp_path / "j.db"), HACKVS_SECRET=secret, HACKVS_FOIRE="1") as base, \
            sync_playwright() as p:
        from intelligence.reglages import Reglages
        cle = hmac.new(Reglages.depuis_env({"HACKVS_SECRET": secret}).secret, b"bornes|annee-1", hashlib.sha256).digest()
        jeton = fa.jeton_borne(cle, "stand-test")
        erreurs: list[str] = []
        b = _chromium(p)
        pg = b.new_page()
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(f"{base}/borne#b={jeton}")
        assert "#b=" not in pg.url                                               # le jeton quitte l'adresse
        pg.click("#prendre")
        pg.locator("#ref").wait_for()
        assert pg.inner_text("#ref").startswith("P-") and pg.get_attribute("#qr-img", "src").startswith("data:image/svg")
        b.close()
    assert not erreurs, erreurs
