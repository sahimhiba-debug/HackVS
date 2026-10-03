"""FOIRE 2026 · F — MEMBRE À DISTANCE : zone et langue déclarées ; Suivi « hors Valais » (k = 3) ; réponse depuis
l'e-mail par trois liens signés, à usage unique, expirants ; boîte de sortie locale « simulé en démonstration »
(aucun envoi). Données FICTIVES."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence import monde_demo as md

CONSOLE = {"X-Pulse-Console": "1"}
client = TestClient(app)


@pytest.fixture(autouse=True)
def _foire(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    yield
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)


def _session(pid):
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    return {"X-Pulse-Session": per[pid]["session"]}


def _boite():
    r = client.get("/api/pulse/console/boite", headers=CONSOLE)
    assert r.status_code == 200, r.text
    return r.json()


def _lien(courriel, libelle):
    return next(x["url"] for x in courriel["liens"] if x["libelle"] == libelle).split("#lien=", 1)[1]


def test_zone_et_langue_declarees_puis_suivi_hors_valais():
    assert client.get("/api/pulse/console/suivi", headers=CONSOLE).json()["hors_valais"] == "zone non renseignée"
    s = _session(md.PAULINE)
    assert client.post("/api/pulse/moi/distance", headers=s, json={"zone": "Lune", "langue": "fr"}).status_code == 422
    assert client.post("/api/pulse/moi/distance", headers=s, json={"zone": "Haute-Savoie", "langue": "it"}).status_code == 422
    assert client.post("/api/pulse/moi/distance", headers=s, json={"zone": "Haute-Savoie", "langue": "fr"}).status_code == 200
    assert client.get("/api/pulse/moi/distance", headers=s).json()["profil"]["zone"] == "Haute-Savoie"
    hv = client.get("/api/pulse/console/suivi", headers=CONSOLE).json()["hors_valais"]
    assert hv == {"membres": "< 3", "zones_renseignees": "< 3"}


def test_boite_de_sortie_simulee_trois_liens_dans_la_langue_du_membre():
    assert _boite()["courriels"] == []                              # personne n'a déclaré de zone : rien ne partirait
    client.post("/api/pulse/moi/distance", headers=_session(md.MARKUS), json={"zone": "Haut-Valais", "langue": "de"})
    b = _boite()
    assert b["simule"] == "simulé en démonstration" and "Aucun e-mail n'est envoyé" in b["note"]
    m = b["courriels"][0]
    assert m["langue"] == "de" and m["objet"].startswith("Der Club fragt Sie") and [x["libelle"] for x in m["liens"]] == ["Ja", "Nein", "Diesmal nicht"]
    assert all("/reponse#lien=m1." in x["url"] for x in m["liens"])


def test_lien_non_depuis_l_e_mail_repond_une_seule_fois():
    s = _session(md.PAULINE)
    client.post("/api/pulse/moi/distance", headers=s, json={"zone": "Vaud", "langue": "fr"})
    jeton = _lien(_boite()["courriels"][0], "Pas cette fois")
    lu = client.post("/api/pulse/courriel/lire", json={"jeton": jeton}).json()
    assert lu["choix"] == "pas cette fois" and lu["minimums"] == {} and lu["monde"] == "monde de démonstration"
    assert client.post("/api/pulse/courriel/repondre", json={"jeton": jeton}).status_code == 200
    assert client.post("/api/pulse/courriel/repondre", json={"jeton": jeton}).status_code == 409   # usage unique
    assert client.get("/api/pulse/console/suivi", headers=CONSOLE).json()["reponses"]["pas_cette_fois"] == "< 3"
    assert client.get("/api/pulse/moi/asks", headers=s).json() == []      # même effet que « non » (plafond)


def test_lien_oui_exige_les_minimums_et_rend_la_capacite_possible():
    s = _session(md.PAULINE)
    client.post("/api/pulse/moi/distance", headers=s, json={"zone": "Vaud", "langue": "fr"})
    jeton = _lien(_boite()["courriels"][0], "Oui")
    assert client.post("/api/pulse/courriel/lire", json={"jeton": jeton}).json()["minimums"] == {"places": 12}
    assert client.post("/api/pulse/courriel/repondre", json={"jeton": jeton, "attributs": {"places": 3}}).status_code in (409, 422)
    r = client.post("/api/pulse/courriel/repondre", json={"jeton": jeton, "attributs": {"places": 14}})
    assert r.status_code == 200, r.text
    assert client.get("/api/pulse/moi/consentements", headers=s).json()        # le reçu est là
    assert client.post("/api/pulse/courriel/repondre", json={"jeton": jeton, "attributs": {"places": 14}}).status_code == 409


def test_lien_falsifie_ou_detourne_refuse():
    s = _session(md.PAULINE)
    client.post("/api/pulse/moi/distance", headers=s, json={"zone": "Vaud", "langue": "fr"})
    jeton = _lien(_boite()["courriels"][0], "Non")
    m1, pid, ask, ch, exp, sig = jeton.split(".")
    for faux in ("", "m1.x", f"{m1}.{pid}.{ask}.o.{exp}.{sig}",            # changer le choix casse la signature
                 f"{m1}.{md.MARKUS}.{ask}.{ch}.{exp}.{sig}",                # le lien d'un autre membre
                 f"{m1}.{pid}.{ask}.{ch}.2099-01-01.{sig}",                 # repousser l'échéance
                 f"{m1}.{pid}.{ask}.{ch}.{exp}.{'0' * 32}"):
        assert client.post("/api/pulse/courriel/repondre", json={"jeton": faux}).status_code == 401, faux


def test_lien_expire_avec_la_demande(monkeypatch, tmp_path):
    from app.taxonomy import charger_taxonomie
    from intelligence import distance
    from intelligence.demo import Demo
    from intelligence.erreurs import NonAuthentifie
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    c = Demo(charger_taxonomie()).club
    distance.declarer(c, md.PAULINE, "Vaud", "fr")
    m = distance.boite(c, "http://x")["courriels"][0]
    jeton = m["liens"][1]["url"].split("#lien=", 1)[1]
    assert distance.lire_lien(c, jeton)["choix"] == "non"
    c.avancer(4)                                                    # 10.10 : la demande du 09.10 est échue
    with pytest.raises(NonAuthentifie):
        distance.repondre_lien(c, jeton)


def test_la_boite_et_les_liens_n_ecrivent_rien_en_lisant():
    s = _session(md.PAULINE)
    client.post("/api/pulse/moi/distance", headers=s, json={"zone": "Vaud", "langue": "fr"})
    avant = json.dumps(client.get("/api/pulse/console/suivi", headers=CONSOLE).json())
    jeton = _lien(_boite()["courriels"][0], "Non")
    _boite(); client.post("/api/pulse/courriel/lire", json={"jeton": jeton})
    assert json.dumps(client.get("/api/pulse/console/suivi", headers=CONSOLE).json()) == avant
    assert client.post("/api/pulse/courriel/repondre", json={"jeton": jeton}).status_code == 200   # le lien vaut encore


def test_page_reponse_servie_et_interrupteur_eteint(monkeypatch):
    assert client.get("/reponse").status_code == 200 and "monde de démonstration" in client.get("/reponse").text
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    assert client.get("/api/pulse/console/boite", headers=CONSOLE).status_code == 404
    assert client.post("/api/pulse/courriel/repondre", json={"jeton": "m1.a.b.o.2026-10-09.c"}).status_code == 404
