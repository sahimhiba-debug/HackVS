"""DÉMO SUR LE MAC DU PITCH, DERRIÈRE UN TUNNEL (Tailscale Funnel ; Cloudflare en secours).

Derrière un tunnel, TOUTES les requêtes arrivent de 127.0.0.1 (le démon du tunnel tourne sur la machine). Deux
conséquences, testées ici :
1. « local » ne veut plus dire « cette machine » : une requête qui porte un en-tête de relais (X-Forwarded-For,
   Forwarded, CF-Connecting-IP, Tailscale-Funnel-Request, X-Real-IP) n'est JAMAIS traitée comme locale — sinon la
   salle entière aurait la console ;
2. aucune limite par adresse IP : 80 téléphones derrière une seule IP ne sont pas bloqués (les limites sont par passe,
   par session ou globales, avec le plafond de 80).
Et le QR de la salle est servi EN DIRECT (/qr/salle.svg) depuis PUBLIC_BASE_URL : il suit l'adresse du tunnel."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

CONSOLE = {"X-Pulse-Console": "1"}
RELAIS = [{"X-Forwarded-For": "203.0.113.7"}, {"Forwarded": "for=203.0.113.7"}, {"CF-Connecting-IP": "203.0.113.7"},
          {"Tailscale-Funnel-Request": "?1"}, {"X-Real-IP": "203.0.113.7"}]


@pytest.fixture
def c(monkeypatch):
    monkeypatch.delenv("HACKVS_CONSOLE_JETON", raising=False)
    return TestClient(app)


@pytest.mark.parametrize("relais", RELAIS)
def test_requete_relayee_par_un_tunnel_n_est_pas_locale(c, relais):
    assert c.get("/api/pulse/console/salle/etat", headers=CONSOLE).status_code == 200          # vraiment local : oui
    r = c.get("/api/pulse/console/salle/etat", headers=CONSOLE | relais)
    assert r.status_code == 403 and "HACKVS_CONSOLE_JETON" in r.json()["detail"]


def test_avec_jeton_la_console_marche_a_travers_le_tunnel():
    from fastapi import FastAPI

    from app.pulse_api import creer_routeur
    from app.taxonomy import charger_taxonomie
    a = FastAPI()
    a.include_router(creer_routeur(charger_taxonomie(), console_jeton="jeton-de-test-assez-long"))
    c = TestClient(a)
    assert c.get("/api/pulse/console/salle/etat", headers={"X-Pulse-Console": "1", **RELAIS[0]}).status_code == 403
    assert c.get("/api/pulse/console/salle/etat", headers={"X-Pulse-Console": "jeton-de-test-assez-long", **RELAIS[0]}).status_code == 200


def test_quatre_vingts_telephones_derriere_une_seule_ip_ne_sont_pas_bloques(c):
    """Tous viennent de la même adresse (« testclient », et le même X-Forwarded-For) : aucun 429."""
    ip = {"X-Forwarded-For": "198.51.100.1"}
    c.post("/api/pulse/console/salle/purger", headers=CONSOLE)
    jeton = c.post("/api/pulse/console/salle/ouvrir", headers=CONSOLE).json()["url"].split("#s=", 1)[1]
    passes = []
    for i in range(80):
        r = c.post("/api/pulse/salle/entrer", headers=ip, json={"jeton": jeton})
        assert r.status_code == 200, (i, r.text)
        passes.append({"X-Pulse-Salle": r.json()["passe"], **ip})
    for i, p in enumerate(passes):
        r = c.post("/api/pulse/salle/declarer", headers=p, json={"capacite": ("voiture", "salle", "allemand", "traiteur")[i % 4], "consentement": True})
        assert r.status_code == 200, (i, r.text)
    c.post("/api/pulse/console/salle/lancer", headers=CONSOLE)
    for _ in range(5):                                   # cinq relectures (une toutes les 2 s pendant 10 s)
        for p in passes:
            assert c.get("/api/pulse/salle/moi", headers=p).status_code == 200
    for p in passes:
        assert c.post("/api/pulse/salle/repondre", headers=p, json={"choix": "oui"}).status_code in (200, 409)
    c.post("/api/pulse/console/salle/purger", headers=CONSOLE)


def test_qr_salle_servi_en_direct_depuis_public_base_url(c, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://mac-du-pitch.exemple.ts.net")
    c.post("/api/pulse/console/salle/purger", headers=CONSOLE)
    ferme = c.get("/qr/salle.svg")
    assert ferme.status_code == 200 and ferme.headers["content-type"].startswith("image/svg+xml")
    assert "salle fermée" in ferme.text
    c.post("/api/pulse/console/salle/ouvrir", headers=CONSOLE)
    ouvert = c.get("/qr/salle.svg")
    assert ouvert.status_code == 200 and ouvert.headers["content-type"].startswith("image/svg+xml")
    assert ouvert.headers.get("cache-control") == "no-store" and "<svg" in ouvert.text and "salle fermée" not in ouvert.text
    url = c.get("/qr/salle.txt").text
    assert url.startswith("https://mac-du-pitch.exemple.ts.net/salle#s=s1.")
    c.post("/api/pulse/console/salle/purger", headers=CONSOLE)


def test_qr_feuille_de_route_suit_l_adresse_publique(c, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://mac-du-pitch.exemple.ts.net")
    r = c.get("/qr/feuille-de-route.svg")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml") and "<svg" in r.text
