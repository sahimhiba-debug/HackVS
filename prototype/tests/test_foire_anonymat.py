"""FOIRE 2026 · C — ANONYMAT À PETITE ÉCHELLE (interrupteur HACKVS_FOIRE).

Le Club compte une cinquantaine de membres : dire « transport : ce composant n'est plus disponible » quand une seule
personne du Club porte ce rôle, c'est la désigner. Règle : quand un rôle est porté par MOINS DE 3 membres (k = 3),
l'avis de retrait ne dit pas le rôle — « un composant n'est plus disponible ». Le message du téléphone devient
« Consentement retiré. Personne ne sera prévenu que c'est vous. » (on ne promet pas l'impossible : dans un petit club
on peut parfois deviner). Interrupteur éteint : le comportement d'hier, à l'identique."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence import monde_demo as md

CONSOLE = {"X-Pulse-Console": "1"}
A = "delegation_acheteurs"
client = TestClient(app)


def _session(pid):
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    return {"X-Pulse-Session": per[pid]["session"]}


def _registre():
    return next(x for x in client.get("/api/pulse/console/capacites", headers=CONSOLE).json()["capacites"] if x["finalite"] == A)


def _repondre_puis_retirer():
    assert client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE).status_code == 200
    pauline = _session(md.PAULINE)
    ask = next(x for x in client.get("/api/pulse/moi/asks", headers=pauline).json() if x["id"].startswith(A))
    assert client.post(f"/api/pulse/moi/asks/{ask['id']}/reponse", headers=pauline,
                       json={"oui": True, "attributs": {"places": 14}}).status_code == 200
    assert client.post(f"/api/pulse/moi/capacites/{A}/retrait", headers=pauline).status_code == 200
    return _registre()


def test_role_porte_par_moins_de_trois_membres_n_est_pas_dit(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    reg = _repondre_puis_retirer()
    assert reg["statut"] == "DEGRADED"
    assert reg["perdus"] == ["un composant n'est plus disponible"]
    assert "transport" not in str(reg["perdus"])
    assert reg["anonymat"] == {"k": 3, "roles_masques": 1}          # dit qu'on a masqué, jamais lequel


def test_interrupteur_eteint_comportement_d_hier(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    reg = _repondre_puis_retirer()
    assert reg["perdus"] == ["transport : ce composant n'est plus disponible"]
    assert "anonymat" not in reg


def test_role_porte_par_trois_membres_ou_plus_reste_dit(monkeypatch):
    """k = 1 : aucun rôle n'est « rare » — le rôle est dit (la règle masque SEULEMENT sous le seuil)."""
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    monkeypatch.setenv("HACKVS_K_ANONYMAT", "1")
    reg = _repondre_puis_retirer()
    assert reg["perdus"] == ["transport : ce composant n'est plus disponible"]


def test_message_de_retrait_ne_promet_pas_l_impossible():
    html = (Path(__file__).resolve().parent.parent / "web" / "pulse" / "app.html").read_text(encoding="utf-8")
    assert "Personne ne sera prévenu que c'est vous." in html
    assert "Personne ne saura que c'est vous." not in html


@pytest.fixture(autouse=True)
def _remettre_le_monde():
    yield
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
