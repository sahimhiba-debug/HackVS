"""Le serveur de démonstration ne sert QUE Club Pulse. L'ancien prototype (« Le Fil du Club ») y choisit l'identité par
un simple en-tête `X-Membre` et se réinitialise sans garde : il n'est servi que si on le demande explicitement
(`HACKVS_ANCIEN_PROTOTYPE=1`), et alors seulement à cette machine — ou avec le jeton de console s'il est défini.
Défaut trouvé à l'inspection du pivot (docs/audit/PIVOT_INSPECTION.md, § 2.2) : tout était servi sur le port principal."""
import pytest
from fastapi.testclient import TestClient

from app import main

LOCAL = TestClient(main.app)
DISTANT = TestClient(main.app, client=("10.1.2.3", 50000))
ANCIENNES = [("get", "/api/membres"), ("get", "/api/moi"), ("post", "/api/demo/reinitialiser"), ("post", "/api/demo/historique"),
             ("get", "/api/relations"), ("get", "/decision"), ("get", "/demo/stage"), ("get", "/api/stage"), ("get", "/openapi.json")]


@pytest.fixture
def ancien_coupe(monkeypatch):
    monkeypatch.setattr(main, "ANCIEN_PROTOTYPE", False, raising=False)


@pytest.mark.parametrize("methode,chemin", ANCIENNES)
def test_par_defaut_l_ancien_prototype_n_est_pas_servi(ancien_coupe, methode, chemin):
    r = getattr(LOCAL, methode)(chemin, headers={"X-Membre": "p00"})
    assert r.status_code == 404, (chemin, r.status_code)


def test_par_defaut_l_identite_par_en_tete_n_existe_plus(ancien_coupe):
    assert LOCAL.get("/api/moi", headers={"X-Membre": "p00"}).status_code == 404
    assert LOCAL.get("/api/moi?membre=p00").status_code == 404


@pytest.mark.parametrize("chemin", ["/app", "/console", "/projection", "/demo/regie", "/static/pulse/pulse.css", "/favicon.ico"])
def test_club_pulse_reste_servi(ancien_coupe, chemin):
    assert LOCAL.get(chemin).status_code == 200


def test_la_racine_mene_a_club_pulse(ancien_coupe):
    r = LOCAL.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/app"


def test_l_api_club_pulse_reste_protegee_par_ses_propres_regles(ancien_coupe):
    assert LOCAL.get("/api/pulse/moi/actions").status_code == 401              # session exigée
    assert LOCAL.post("/api/pulse/demo/reinitialiser").status_code == 403       # console exigée


def test_active_explicitement_l_ancien_prototype_ne_repond_qu_a_cette_machine(monkeypatch):
    monkeypatch.setattr(main, "ANCIEN_PROTOTYPE", True, raising=False)
    monkeypatch.setattr(main, "_CONSOLE_JETON", None, raising=False)
    assert DISTANT.post("/api/demo/reinitialiser").status_code == 403
    assert DISTANT.get("/api/moi", headers={"X-Membre": "p00"}).status_code == 403
    assert LOCAL.get("/api/membres").status_code == 200


def test_avec_un_jeton_de_console_l_ancien_prototype_l_exige(monkeypatch):
    monkeypatch.setattr(main, "ANCIEN_PROTOTYPE", True, raising=False)
    monkeypatch.setattr(main, "_CONSOLE_JETON", "j" * 40, raising=False)
    assert LOCAL.post("/api/demo/reinitialiser").status_code == 403
    assert DISTANT.get("/api/membres", headers={"X-Pulse-Console": "faux"}).status_code == 403
    assert DISTANT.get("/api/membres", headers={"X-Pulse-Console": "j" * 40}).status_code == 200
