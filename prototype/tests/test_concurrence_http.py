"""Durcissement H5 — gestes SIMULTANÉS par HTTP (vrais fils, même instant), pas seulement en séquence.

- Les quatre destinataires d'une même demande répondent « oui » au même instant : UNE seule réponse est retenue, les
  autres apprennent que la demande n'est plus d'actualité (404) ; le journal ne contient qu'une réponse « oui ».
- Le même téléphone envoie deux fois « oui » (double toucher) en parallèle : une seule réponse écrite.
- Un retrait et une réponse arrivent ensemble : quel que soit l'ordre, l'état final est un des deux états cohérents,
  jamais un mélange (pas de réponse orpheline sur une capacité retirée, aucune erreur 500).
Données FICTIVES."""
import threading

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pulse_api import creer_routeur
from app.taxonomy import charger_taxonomie

TAX = charger_taxonomie()
CONSOLE = {"X-Pulse-Console": "1"}
OUI = {"oui": True, "attributs": {"places": 14}}


def _monde(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    app = FastAPI()
    app.include_router(creer_routeur(TAX))
    c = TestClient(app)
    ps = c.get("/api/pulse/console/personas", headers=CONSOLE).json()
    s = {p["id"]: {"X-Pulse-Session": c.post("/api/pulse/acces", json={"code": p["code"]}).json()["session"]} for p in ps}
    return c, s


def _ensemble(*appels):
    """Lance les appels au MÊME instant (barrière) et rend leurs statuts dans l'ordre."""
    barriere, res = threading.Barrier(len(appels)), [None] * len(appels)

    def f(i, appel):
        barriere.wait()
        res[i] = appel()
    fils = [threading.Thread(target=f, args=(i, a)) for i, a in enumerate(appels)]
    for t in fils:
        t.start()
    for t in fils:
        t.join(60)
    return res


def test_quatre_destinataires_au_meme_instant_une_seule_reponse(tmp_path, monkeypatch):
    c, s = _monde(tmp_path, monkeypatch)
    dest = [k for k in s if c.get("/api/pulse/moi/asks", headers=s[k]).json()]
    assert len(dest) >= 3, dest
    ask = c.get("/api/pulse/moi/asks", headers=s[dest[0]]).json()[0]["id"]
    statuts = _ensemble(*[lambda k=k: c.post(f"/api/pulse/moi/asks/{ask}/reponse", headers=s[k], json=OUI).status_code
                          for k in dest])
    assert sorted(statuts) == [200] + [404] * (len(dest) - 1), statuts


def test_double_toucher_du_meme_telephone_une_seule_reponse(tmp_path, monkeypatch):
    c, s = _monde(tmp_path, monkeypatch)
    p = s["s01"]
    ask = c.get("/api/pulse/moi/asks", headers=p).json()[0]["id"]
    statuts = _ensemble(*[lambda: c.post(f"/api/pulse/moi/asks/{ask}/reponse", headers=p, json=OUI).status_code] * 2)
    assert sorted(statuts) == [200, 404], statuts


def test_retrait_et_reponse_simultanes_restent_coherents(tmp_path, monkeypatch):
    c, s = _monde(tmp_path, monkeypatch)
    ask = c.get("/api/pulse/moi/asks", headers=s["s01"]).json()[0]["id"]
    finalite = ask.split(":", 1)[0]
    porteur = next(k for k in s if c.post(f"/api/pulse/moi/capacites/{finalite}/consentement", headers=s[k]).status_code == 200
                   and k != "s01")
    statuts = _ensemble(lambda: c.post(f"/api/pulse/moi/asks/{ask}/reponse", headers=s["s01"], json=OUI).status_code,
                        lambda: c.post(f"/api/pulse/moi/capacites/{finalite}/retrait", headers=s[porteur]).status_code)
    assert 500 not in statuts and statuts[1] == 200, statuts
    vue = next(x for x in c.get("/api/pulse/console/capacites", headers=CONSOLE).json()["capacites"] if x["finalite"] == finalite)
    assert vue["statut"] != "ACTIVE", vue["statut"]                   # le retrait a eu lieu : la capacité ne tient plus
    mes = [r for r in c.get("/api/pulse/moi/consentements", headers=s[porteur]).json() if r["finalite"] == finalite]
    assert all(r["etat"] != "valable" for r in mes), mes                # le reçu du porteur dit le retrait
