"""LISTE DU CLUB — « Ce que votre Club pourrait assembler » : 9 capacités types × métiers présents. Attendu sur la liste
du 3 octobre : 8 sur 9 ; la délégation germanophone bloque sur « interprète » (absent du Club). Agrégats, aucun nom."""
import json

from fastapi.testclient import TestClient

from app.main import app
from intelligence import assembler, club_cherche

CONSOLE = {"X-Pulse-Console": "1"}


def test_liste_du_club_huit_sur_neuf_la_delegation_bloque_sur_l_interprete():
    r = assembler.calculer(club_cherche.entreprises_par_metier()["par_metier"])
    assert (r["assemblables"], r["total"]) == (8, 9)
    bloquee = [x for x in r["capacites"] if not x["assemblable"]]
    assert [(x["id"], x["manque"]) for x in bloquee] == [("delegation", ["interprète"])]
    assert r["source"] == "d'après la liste du Club, classification à confirmer"
    assert r["phrase"] == "Votre liste dit ce que le Club pourrait faire. Club Pulse dit ce qu'il peut faire cette semaine."


def test_seuil_sur_les_decomptes_d_entreprises():
    r = assembler.calculer({"transport": 1, "hebergement": 5})
    d = next(x for x in r["capacites"] if x["id"] == "delegation")
    assert [p["entreprises"] for p in d["pieces"]] == ["< 3", 5, 0]


def test_absents_et_rares_d_apres_la_liste():
    r = assembler.absents_et_rares(club_cherche.entreprises_par_metier()["par_metier"])
    assert "Interprète, langues" in r["absents"]
    for m in ("Logistique", "Santé, sécurité", "Juridique", "Comptabilité, fiscalité", "Informatique", "Formation"):
        assert m in r["rares"], m


def test_liste_absente_est_dite():
    assert assembler.calculer(None)["disponible"] is False


def test_route_console_agregats_sans_nom(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    c = TestClient(app)
    assert c.post("/api/pulse/demo/reinitialiser", headers=CONSOLE).status_code == 200
    assert c.get("/api/pulse/console/club/assembler").status_code in (401, 403)
    r = c.get("/api/pulse/console/club/assembler", headers=CONSOLE)
    assert r.status_code == 200
    j = r.json()
    assert j["assembler"]["assemblables"] == 8 and j["cherche"]["absents"]
    assert j["chiffres"] == {"entreprises": 145, "representants": 173, "source": "liste fournie par le Club (3 octobre 2026)"}
    texte = json.dumps(j, ensure_ascii=False)
    assert "Sàrl" not in texte and " SA" not in texte
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    c.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
