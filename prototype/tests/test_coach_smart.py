"""P3 n°3 — COACH « SMART » d'une demande : ce qui manque pour qu'on puisse dire oui (quand ? combien ? où ?).

Règles sur les MOTS DU MEMBRE seulement (FR / DE) : les mêmes questions IA allumée ou éteinte (parité par
construction). Interrupteur HACKVS_COACH_SMART (allumé par défaut). Ni le texte ni les questions ne sont écrits."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence import monde_demo as md
from intelligence.coach_smart import questions

CONSOLE = {"X-Pulse-Console": "1"}
client = TestClient(app)


def ids(texte):
    return [q["id"] for q in questions(texte)]


@pytest.mark.parametrize("texte,attendu", [
    ("J'ai besoin d'aide pour un événement", ["quand", "combien", "ou"]),
    ("Jeudi 8 octobre à 14h, accueillir 8 acheteurs à Martigny", []),
    ("Il me faut un minibus de 12 places vendredi", ["ou"]),
    ("Une salle à Sion pour 20 personnes", ["quand"]),
    ("Am Donnerstag um 14 Uhr, 8 Einkäufer in Brig empfangen", []),
    ("Demain matin, au stand de la Foire", ["combien"]),
])
def test_questions_selon_ce_qui_manque(texte, attendu):
    assert ids(texte) == attendu


def test_chaque_question_a_un_exemple():
    for q in questions("aide"):
        assert q["question"].endswith("?") and q["exemple"]


def _session(pid):
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    return {"X-Pulse-Session": per[pid]["session"]}


def test_route_preparer_donne_les_questions_ia_eteinte(monkeypatch):
    for k in ("APERTUS_API_KEY", "APERTUS_MODEL", "APERTUS_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    r = client.post("/api/pulse/moi/actions/preparer", headers=_session(md.LEA), json={"texte": "J'ai besoin d'aide pour un événement"})
    assert r.status_code == 200, r.text
    assert [q["id"] for q in r.json()["smart"]] == ["quand", "combien", "ou"]


def test_interrupteur_eteint(monkeypatch):
    monkeypatch.setenv("HACKVS_COACH_SMART", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    r = client.post("/api/pulse/moi/actions/preparer", headers=_session(md.LEA), json={"texte": "aide pour un événement"})
    assert "smart" not in r.json()
