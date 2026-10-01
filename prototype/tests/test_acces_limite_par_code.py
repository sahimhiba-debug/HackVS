"""F09 — `/acces` est limité PAR CODE tenté, plus un plafond GLOBAL doux ; JAMAIS par adresse IP (même règle que le QR
juré) : dans la salle, tout le public sort par la même adresse. Avant : 10 activations par minute et par IP — le
onzième téléphone de la salle recevait 429. Données FICTIVES."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pulse_api import creer_routeur
from app.taxonomy import charger_taxonomie

TAX = charger_taxonomie()
CONSOLE = {"X-Pulse-Console": "1"}


def _client():
    app = FastAPI()
    app.include_router(creer_routeur(TAX))
    c = TestClient(app)
    c.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    return c, [p["code"] for p in c.get("/api/pulse/console/personas", headers=CONSOLE).json()]


def test_une_salle_derriere_une_meme_adresse_active_tous_ses_telephones():
    c, codes = _client()
    statuts = [c.post("/api/pulse/acces", json={"code": code}).status_code for code in codes * 2]   # 14 activations, 1 IP
    assert len(statuts) > 10 and set(statuts) == {200}, statuts


def test_un_meme_code_devine_a_repetition_est_freine():
    c, _ = _client()
    statuts = [c.post("/api/pulse/acces", json={"code": "ZZZZZZ"}).status_code for _ in range(6)]
    assert statuts == [401] * 5 + [429], statuts


def test_un_plafond_global_freine_qui_essaie_beaucoup_de_codes():
    c, _ = _client()
    statuts = [c.post("/api/pulse/acces", json={"code": f"Z{i:05X}"}).status_code for i in range(310)]
    assert statuts[:300].count(401) == 300 and statuts[300:] == [429] * 10, statuts[295:]
