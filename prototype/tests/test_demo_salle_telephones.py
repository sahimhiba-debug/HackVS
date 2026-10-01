"""Revue publique R-01 — la démonstration prévoit de VRAIS téléphones (« téléphones sur son point d'accès », QR juré
scanné par un juré) ; `make demo` n'écoutait que 127.0.0.1 et le QR juré encodait l'adresse vue par l'Établi
(`http://127.0.0.1:8000/app?jure=…`) : un téléphone ne pouvait ni joindre le serveur, ni ouvrir le QR.

Ce qui est vérifié ici : le lancement de démonstration accepte une adresse d'écoute et une URL publique ; l'URL publique
est celle que le QR encode ; la console reste réservée à la machine locale quand le serveur écoute le réseau.
Données FICTIVES."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pulse_api import creer_routeur
from app.taxonomy import charger_taxonomie

RACINE = Path(__file__).resolve().parents[2]
TAX = charger_taxonomie()
CONSOLE = {"X-Pulse-Console": "1"}


def _recette_demo() -> str:
    return RACINE.joinpath("Makefile").read_text(encoding="utf-8").split("\ndemo:", 1)[1].split("\n\n", 1)[0]


def test_make_demo_ecoute_l_adresse_choisie_et_publie_l_url_des_telephones():
    recette = _recette_demo()
    assert "--host $(HOTE)" in recette, recette
    assert 'HACKVS_URL_PUBLIQUE="$(URL_PUBLIQUE)"' in recette, recette
    entete = RACINE.joinpath("Makefile").read_text(encoding="utf-8").split("\ndemo:", 1)[0]
    assert "HOTE ?= 127.0.0.1" in entete                     # par défaut : cette machine seule (rien n'est exposé)


def test_le_qr_jure_encode_l_url_publique_des_telephones(monkeypatch):
    monkeypatch.setenv("HACKVS_URL_PUBLIQUE", "http://192.168.137.1:8000")
    app = FastAPI()
    app.include_router(creer_routeur(TAX))
    c = TestClient(app)
    p = c.post("/api/pulse/console/jure", json={"persona": "s14", "minutes": 15}, headers=CONSOLE).json()
    assert p["url"].startswith("http://192.168.137.1:8000/app?jure="), p["url"]


def test_ecouter_le_reseau_n_ouvre_pas_la_console():
    """Contre-épreuve : un téléphone du point d'accès joint l'application, jamais la console (sans jeton configuré)."""
    app = FastAPI()
    app.include_router(creer_routeur(TAX))
    c = TestClient(app, client=("192.168.137.42", 50000))
    assert c.get("/api/pulse/console/personas", headers=CONSOLE).status_code == 403
