"""ANNÉE 1 · LOT 7 — Suivi du taux d'acceptation des propositions : quand un membre écrit une demande, ce que le Club en
a compris (par le modèle Apertus, ou par les règles en repli) lui est PROPOSÉ ; il confirme, ou reformule. Le taux
d'acceptation, par source, se lit dans la console — décomptes seulement, « < 3 » compté en entreprises. Interrupteur
HACKVS_SUIVI_IA (éteint : la démo n'écrit rien de plus). Données FICTIVES, modèle simulé (aucun réseau)."""
import json

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence import suivi_ia
from intelligence.demo import Demo

TAX = charger_taxonomie()


@pytest.fixture
def demo(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(TAX)


def test_eteint_rien_n_est_ecrit(demo, monkeypatch):
    monkeypatch.delenv("HACKVS_SUIVI_IA", raising=False)
    c = demo.club
    avant = len(c.journal.evenements())
    c.demander(md.PAULINE, "Je cherche une salle pour 20 personnes à Martigny jeudi soir.")
    assert [e.type for e in c.journal.evenements()[avant:]] == ["APPEL_IA"]   # la trace de l'appel, qui existait déjà
    assert not c.journal.evenements("PROPOSITION", "PROPOSITION_ACCEPTEE")


def test_taux_d_acceptation_par_source(demo, monkeypatch):
    monkeypatch.setenv("HACKVS_SUIVI_IA", "1")
    c = demo.club
    membres, vues = [], set()                       # 7 membres de 7 entreprises distinctes
    for p in c.r.profils:
        e = c.coffre.cle_entreprise(p.id)
        if e not in vues and c.coffre.identite(p.id):
            vues.add(e)
            membres.append(p.id)
        if len(membres) == 7:
            break
    for i, pid in enumerate(membres):
        p = c.demander(pid, f"Je cherche une salle pour {20 + i} personnes à Martigny jeudi soir.")
        if i < 4:
            c.confirmer_demande(pid, p["proposition"])               # 4 acceptées (4 entreprises), 3 non (3 entreprises)
    t = suivi_ia.taux(c)
    regles = t["par_source"]["regles"]                             # sans clé d'IA : le repli déterministe
    assert regles["proposees"] == 7 and regles["acceptees"] == 4 and regles["taux"] == 57
    assert "modele" in t["par_source"] and t["par_source"]["modele"]["proposees"] == 0
    brut = json.dumps(t, ensure_ascii=False)
    assert "Pauline" not in brut and "salle pour" not in brut      # décomptes seulement


def test_sous_trois_entreprises_le_taux_n_est_pas_dit(demo, monkeypatch):
    monkeypatch.setenv("HACKVS_SUIVI_IA", "1")
    c = demo.club
    p = c.demander(md.PAULINE, "Je cherche une salle pour 20 personnes.")
    c.confirmer_demande(md.PAULINE, p["proposition"])
    r = suivi_ia.taux(c)["par_source"]["regles"]
    assert r["proposees"] == "< 3" and r["taux"] is None


def test_la_console_lit_le_taux(monkeypatch, tmp_path):
    import time

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from intelligence.comptes import code_totp
    for k, v in {"HACKVS_ESSAIS_DB": str(tmp_path / "j.db"), "HACKVS_SECRET": "m" * 40, "HACKVS_FOIRE": "1",
                 "HACKVS_COMPTES": "1", "HACKVS_SECRETARIAT": "1", "HACKVS_SUIVI_IA": "1"}.items():
        monkeypatch.setenv(k, v)
    from app.pulse_api import creer_routeur
    routeur = creer_routeur(TAX)
    app = FastAPI()
    app.include_router(routeur)
    cp = routeur.comptes()
    admin = cp.amorcer_administration("Administration (fictive)")
    p = cp.preparer_totp(admin)
    cp.confirmer_totp(admin, code_totp(p["secret"], time.time()))
    cp.elever(admin, code_totp(p["secret"], time.time() + 30))
    r = TestClient(app).get("/api/pulse/secretariat/ia", headers={"X-Pulse-Compte": admin})
    assert r.status_code == 200 and r.json()["allume"] is True and set(r.json()["par_source"]) == {"modele", "regles"}
