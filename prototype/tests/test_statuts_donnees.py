"""Chaque fait du journal dit d'OÙ il vient : SYNTHETIQUE (données préparées de la démonstration), DECLARE (saisi
par une personne sur son téléphone), JOUE (fait par l'équipe depuis la console pour un membre absent de la scène).
Défauts trouvés à l'audit (2026-09-30) : les offres préparées étaient journalisées « DECLARE », et la marque « joué »
ne vivait que dans une liste en mémoire — perdue au redémarrage. Données FICTIVES."""
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.club_pulse import ClubPulse
from intelligence.demo import Demo
from plateforme.affirmations import Statut

TAX = charger_taxonomie()
client = TestClient(app)
CONSOLE = {"X-Pulse-Console": "1"}


def test_les_offres_preparees_sont_synthetiques():
    d = Demo(TAX)
    offres = d.club.banc.m.evenements("OFFRE")
    assert offres and {e.statut for e in offres} == {Statut.SYNTHETIQUE}


def test_telephone_declare_console_joue_et_c_est_ecrit_dans_le_journal():
    from tests.test_action_collective import L, P, _action, _essai, _jouer, _sessions
    h = _sessions()
    eid = _action(h)
    client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[md.SOPHIE], json={"version": 0})
    client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": _essai(h, L, eid)["version"], "accepte": True})
    assert _jouer(eid, P).status_code == 200
    origines = client.get(f"/api/pulse/console/essais/{eid}", headers=CONSOLE).json()["origines"]
    par_role = {(o["role"], o["origine"]) for o in origines}
    assert ("voix", "DECLARE") in par_role                        # Léa, sur SON téléphone
    assert ("lieu", "JOUE") in par_role and ("porteur", "DECLARE") in par_role
    assert ("lieu", "DECLARE") not in par_role                   # le geste joué n'est jamais présenté comme déclaré
    proj = client.get("/api/pulse/console/projection", headers=CONSOLE).json()
    assert [j["geste"] for j in proj["joues"]] == ["accepte sa part"]


def test_la_marque_joue_survit_au_redemarrage(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "essais.db"))
    c = ClubPulse(TAX)
    c.jouer(md.PAULINE, "accepte sa part", "lieu")
    relu = ClubPulse(TAX)                                        # même journal, nouvelle instance
    assert [(j["geste"], j["role"]) for j in relu.joues] == [("accepte sa part", "lieu")]
    assert [e.statut for e in relu.banc.m.evenements("GESTE_JOUE")] == [Statut.JOUE]
