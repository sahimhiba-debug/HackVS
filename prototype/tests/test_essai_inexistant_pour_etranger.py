"""F36 — pour un membre ÉTRANGER à un essai, l'essai n'existe pas : TOUTES ses commandes répondent 404, comme sa lecture.
Avant (balayage E6 de l'audit) : la lecture disait 404, mais 12 commandes répondaient 403 « réservé au porteur » /
« réservé aux participants » — de quoi confirmer qu'un identifiant d'essai existe. Un participant non porteur garde son
403 (il connaît l'essai). Données FICTIVES."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pulse_api import creer_routeur
from app.taxonomy import charger_taxonomie

TAX = charger_taxonomie()
CONSOLE = {"X-Pulse-Console": "1"}
COMMANDES = ["adapter", "annuler", "avis", "contributions/voix", "lancer", "livrer/voix", "modifier", "observation", "projection",
             "publier", "publier-proposition", "receptions/voix", "reutilisation", "decision", "retirer"]
CORPS = {"version": 1, "accepte": True, "oui": True, "contenu": "abc", "texte": "abc", "qualification": "positif", "limites": "abc",
         "revision": 1, "avis": "confirme", "niveau": "club", "mention": "nom", "alternative": "xyz", "raison": "abc", "choix": {}}


def _monde():
    app = FastAPI()
    app.include_router(creer_routeur(TAX))
    c = TestClient(app)
    c.post("/api/pulse/demo/aller/4", headers=CONSOLE)
    personas = {p["id"]: p for p in c.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    eid = c.get("/api/pulse/console/essais", headers=CONSOLE).json()["essais"][0]["id"]
    return c, personas, eid


def test_toutes_les_commandes_d_un_essai_repondent_404_a_un_etranger():
    c, personas, eid = _monde()
    h = lambda pid: {"X-Pulse-Session": personas[pid]["session"]}  # noqa: E731
    etrangers = [p for p in personas if c.get(f"/api/pulse/moi/essais/{eid}", headers=h(p)).status_code == 404]
    assert etrangers, "aucun étranger dans le monde de démonstration"
    for pid in etrangers:
        for cmd in COMMANDES:
            r = c.post(f"/api/pulse/moi/essais/{eid}/{cmd}", headers=h(pid), json=CORPS)
            assert (r.status_code, r.json()["detail"]) == (404, "essai inconnu"), (pid, cmd, r.status_code, r.text[:120])


def test_un_participant_non_porteur_garde_son_refus_explicite():
    """Contre-épreuve : quelqu'un que l'essai concerne apprend POURQUOI il ne peut pas (403), pas un faux « inconnu »."""
    c, personas, eid = _monde()
    h = lambda pid: {"X-Pulse-Session": personas[pid]["session"]}  # noqa: E731
    concernes = [p for p in personas if c.get(f"/api/pulse/moi/essais/{eid}", headers=h(p)).json().get("role") == "contributeur"]
    assert concernes
    r = c.post(f"/api/pulse/moi/essais/{eid}/lancer", headers=h(concernes[0]), json={"version": 1})
    assert r.status_code == 403
