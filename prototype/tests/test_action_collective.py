"""L'ACTION COLLECTIVE de bout en bout par l'API, avec des SESSIONS DISTINCTES : Sophie (porteuse) et Léa (voix
allemande) agissent chacune depuis son espace ; Pauline, Markus et Nicolas sont JOUÉS par l'équipe depuis la console,
et c'est enregistré comme tel. Perturbation : Léa change SA disponibilité. Projection : des rôles, jamais des noms.
Monde FICTIF ; aucune action n'est décidée à la place d'une personne."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence import monde_demo as md
from intelligence.demo import BESOIN_SOPHIE, FICHE_DE

client = TestClient(app)
CONSOLE = {"X-Pulse-Console": "1"}
S, L, P, M, N = md.SOPHIE, md.LEA, md.PAULINE, md.MARKUS, md.NICOLAS
_n = [0]
NOMS = ("Sophie", "Carron", "Léa", "Imhof", "Pauline", "Darbellay", "Markus", "Heinzmann", "Nicolas", "Roduit")


def _sessions() -> dict[str, dict]:
    assert client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE).status_code == 200
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    _n[0] += 1                                        # une adresse par appel : la limite d'essais de code reste active
    entree = TestClient(app, client=(f"10.8.{_n[0] % 250}.1", 50000))
    s = entree.post("/api/pulse/acces", json={"code": per[S]["code"]}).json()["session"]       # Sophie active SON compte
    return {S: {"X-Pulse-Session": s}} | {pid: {"X-Pulse-Session": per[pid]["session"]} for pid in (L, P, M, N)}


def _essai(h, qui, eid):
    return client.get(f"/api/pulse/moi/essais/{eid}", headers=h[qui]).json()


def _jouer(eid, qui, accepte=True):
    v = client.get(f"/api/pulse/console/essais/{eid}", headers=CONSOLE).json()["version"]
    return client.post(f"/api/pulse/console/essais/{eid}/geste", headers=CONSOLE, json={"membre": qui, "version": v, "accepte": accepte})


def _action(h) -> str:
    prop = client.post("/api/pulse/moi/actions/preparer", headers=h[S], json={"texte": BESOIN_SOPHIE}).json()
    assert {x["role"] for x in prop["exigences"]} == {"voix", "lieu", "public"} and prop["fenetre"]["jour"] == "2026-11-05"
    assert prop["ia"]["fournisseur"] in ("deterministe", "apertus")                      # l'origine de la compréhension est dite
    v = client.post("/api/pulse/moi/actions/nouvelle", headers=h[S], json={
        "question": "Présenter nos tisanes à des acheteurs germanophones", "objet": prop["objet"], "critere": prop["critere_suggere"],
        "exigences": prop["exigences"], "fenetre": prop["fenetre"], "duree_min_acceptable": 30}).json()
    assert v["etat"] == "BROUILLON" and v["assemblage"]["creneau"]["texte"] == "05.11 16:00–16:45"
    return v["id"]


def test_parcours_complet_decisions_depuis_des_sessions_distinctes():
    h = _sessions()
    eid = _action(h)
    assert client.get(f"/api/pulse/moi/essais/{eid}", headers=h[L]).status_code == 404            # brouillon : Léa ne voit rien
    v = client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[S], json={"version": 0}).json()
    assert v["etat"] == "PROPOSE" and v["creneau"]["texte"] == "05.11 16:00–16:45"
    lea = _essai(h, L, eid)
    assert lea["role"] == "contributeur" and lea["votre_part"]["gestes"][0]["livrable"] == "Fiche produit en allemand"
    assert client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": lea["version"], "accepte": True}).status_code == 200
    assert _essai(h, S, eid)["etat"] == "PROPOSE"                                   # rien n'est supposé pour les autres
    for qui in (P, M):
        assert _jouer(eid, qui).json()["joue"] is True
    assert _essai(h, S, eid)["etat"] == "AUTORISE"

    # ---- perturbation : Léa, sur SON espace, n'est disponible qu'à partir de 17 h
    oid = _essai(h, L, eid)["votre_part"]["gestes"][0]["offre_id"]
    r = client.patch(f"/api/pulse/moi/offres/{oid}", headers=h[L], json={"plages": [{"jour": "2026-11-05", "debut": "17:00", "fin": "19:00"}]})
    assert r.status_code == 200 and eid in r.json()["essais_a_adapter"]
    proj = client.get("/api/pulse/console/projection", headers=CONSOLE).json()
    assert proj["etat"] == "A_ADAPTER" and proj["adaptation"]["tombe"] == ["voix"] and set(proj["adaptation"]["tient"]) == {"lieu", "public"}
    s = _essai(h, S, eid)
    assert client.post(f"/api/pulse/moi/essais/{eid}/lancer", headers=h[S], json={"version": s["version"]}).status_code == 409
    alt = next(a for a in s["adaptation"]["alternatives"] if "17:00–17:45" in a["texte"])
    r = client.post(f"/api/pulse/moi/essais/{eid}/adapter", headers=h[S], json={"version": s["version"], "alternative": alt["id"]})
    assert r.status_code == 200 and r.json()["etat"] == "PROPOSE" and r.json()["creneau"]["debut"] == "17:00"
    lea = _essai(h, L, eid)
    assert lea["votre_part"]["gestes"][0]["statut"].startswith("votre part a changé")          # le moment a changé : à redonner
    client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": lea["version"], "accepte": True})
    assert _essai(h, S, eid)["etat"] == "PROPOSE"
    for qui in (M, N):
        _jouer(eid, qui)
    assert _essai(h, S, eid)["etat"] == "AUTORISE"
    assert client.get(f"/api/pulse/moi/essais/{eid}", headers=h[P]).json()["role"] == "ancien"   # Pauline : plus concernée

    # ---- engagée, puis la fiche : transmise ≠ reçue
    s = _essai(h, S, eid)
    assert client.post(f"/api/pulse/moi/essais/{eid}/lancer", headers=h[S], json={"version": s["version"]}).json()["etat"] == "EN_COURS"
    assert client.post(f"/api/pulse/moi/essais/{eid}/livrer/e1", headers=h[L], json={"contenu": FICHE_DE}).status_code == 200
    s = _essai(h, S, eid)
    g = next(x for x in s["etapes"] if x["id"] == "e1")
    assert g["palier"] == "transmis" and g["livraison"]["contenu"] == FICHE_DE and "confirmer_reception" in s["actions"]
    assert client.post(f"/api/pulse/moi/essais/{eid}/contributions/e1", headers=h[S]).status_code == 200
    assert next(x for x in _essai(h, S, eid)["etapes"] if x["id"] == "e1")["palier"] == "reçu"
    assert next(x for x in client.get("/api/pulse/console/projection", headers=CONSOLE).json()["exigences"] if x["id"] == "e1")["palier"] == "reçu"


def test_personne_ne_decide_a_la_place_d_un_autre():
    h = _sessions()
    eid = _action(h)
    client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[S], json={"version": 0})
    v = _essai(h, S, eid)["version"]
    assert client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[S], json={"version": v, "accepte": True}).status_code == 403
    assert client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[L], json={"version": v}).status_code in (403, 409)
    assert _jouer(eid, L).status_code == 403                                   # Léa a son téléphone : la console ne la joue pas
    assert client.post(f"/api/pulse/moi/essais/{eid}/livrer/e1", headers=h[L], json={"contenu": "trop tôt"}).status_code == 409
    assert client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": v - 1, "accepte": True}).status_code == 409


def test_sans_solution_bloque_et_le_dit_puis_rouvre_sur_un_fait_nouveau():
    h = _sessions()
    eid = _action(h)
    client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[S], json={"version": 0})
    lea = _essai(h, L, eid)
    client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": lea["version"], "accepte": True})
    oid = _essai(h, L, eid)["votre_part"]["gestes"][0]["offre_id"]
    client.patch(f"/api/pulse/moi/offres/{oid}", headers=h[L], json={"plages": [{"jour": "2026-11-05", "debut": "18:45", "fin": "20:00"}]})
    proj = client.get("/api/pulse/console/projection", headers=CONSOLE).json()
    assert proj["etat"] == "IMPOSSIBLE" and proj["adaptation"]["bloque"] and proj["adaptation"]["alternatives"] == []
    client.patch(f"/api/pulse/moi/offres/{oid}", headers=h[L], json={"plages": [{"jour": "2026-11-05", "debut": "16:30", "fin": "19:00"}]})
    assert _essai(h, S, eid)["etat"] == "A_ADAPTER"                              # rouvert ; rien n'est relancé tout seul


@pytest.mark.parametrize("etape", [2, 5, 7, 9])
def test_la_projection_ne_montre_ni_nom_ni_secret(etape):
    client.post(f"/api/pulse/demo/aller/{etape}", headers=CONSOLE)
    per = client.get("/api/pulse/console/personas", headers=CONSOLE).json()
    brut = json.dumps(client.get("/api/pulse/console/projection", headers=CONSOLE).json(), ensure_ascii=False)
    for x in NOMS + ("MEMBRE-", "@", FICHE_DE[:20]):
        assert x not in brut, (etape, x)
    for p in per:
        assert p["code"] not in brut and (not p["session"] or p["session"] not in brut)
