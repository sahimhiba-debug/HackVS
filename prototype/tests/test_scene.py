"""Mode scène : déterministe, rejouable, isolé, sûr en direct (double clic, retour arrière, fin, réinitialisation)."""
import json
import re

from fastapi.testclient import TestClient

from app import stage
from app.main import TAX, app

client = TestClient(app)


def _canon(traces: list[dict]) -> str:
    """Ce qui est AFFICHÉ, sans identifiants internes aléatoires (ids de relance ou de relation)."""
    return re.sub(r'"(id|relance_id|relation_id)": "[^"]*"', '"id": "*"', json.dumps(traces, ensure_ascii=False, sort_keys=True))


def test_rejeu_identique_trois_fois():
    n = len(stage.ETAPES)
    runs = [_canon(stage.rejouer_jusqu_a(TAX, n).traces) for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]


def test_histoire_racontee_par_le_moteur():
    t = {x["etape"]: x["faits"] for x in stage.rejouer_jusqu_a(TAX, len(stage.ETAPES)).traces}
    assert t[1]["invisible_par_defaut"] is True and t[1]["coordonnees_enregistrees"] == "aucune"
    assert t[2]["compris"] == ["Développement commercial en Allemagne (obligatoire)"]
    cand = t[3]["candidats"]
    assert cand[0]["nom"] == "Markus Heinzmann" and cand[0]["niveau"] == "forte"
    assert cand[0]["dimensions"]["reciprocite"]["etablie"] is True
    assert t[3]["ecartes_par_leur_choix"] == 0                       # Stefan refuse : ni nommé, ni compté (k < 3)
    assert "Kalbermatten" not in json.dumps(t, ensure_ascii=False)
    assert t[4]["decision"] == "S_ABSTENIR"                           # Japon : le système s'abstient
    assert t[5]["coordonnees_partagees"] is False and t[6]["coordonnees_partagees"] is True
    assert t[7]["etat_relation"] == "RENCONTREE" and t[9]["etat_relation"] == "OPPORTUNITE"
    assert [r["type"] for p in t[8]["relances"] for r in p["raisons"]] == ["RECIPROCITE_OUVERTE"]
    assert t[8]["silences"]["rien_de_nouveau"] >= 10                  # pas de relance sans raison
    cercle = t[10]["micro_cercle"]
    assert cercle["decision"] == "PROPOSER_A_L_HUMAIN" and 3 <= len(cercle["membres"]) <= 5
    assert any("non mis à jour" in u for u in cercle["inconnu"])      # la preuve ancienne est signalée
    fin = t[11]
    assert fin["nature"] == "SIMULATION" and fin["si_le_cercle_a_lieu"]["composantes"] < fin["maintenant"]["composantes"]
    assert "liens_actifs" not in fin["maintenant"]                   # pas de métrique dépendant d'une hypothèse


def test_api_scene_suivant_precedent_fin_reinitialisation():
    v = client.post("/api/stage/reinitialiser").json()
    assert v["etape"] == 0 and "FICTIF" in v["avertissement"]
    for _ in range(3):
        v = client.post("/api/stage/suivant").json()
    assert v["etape"] == 3
    seq = _canon(v["traces"])
    prec = client.post("/api/stage/aller/3").json()                   # rejouer jusqu'à 3 = même chose
    assert _canon(prec["traces"]) == seq
    assert client.post("/api/stage/aller/99").status_code == 422
    client.post(f"/api/stage/aller/{len(stage.ETAPES)}")
    assert client.post("/api/stage/suivant").status_code == 409        # fin : pas d'étape fantôme
    assert client.post("/api/stage/reinitialiser").json()["etape"] == 0
    assert client.get("/api/stage").json()["etape"] == 0               # un rafraîchissement lit l'état serveur


def test_scene_isolee_de_la_demo():
    """La scène n'écrit rien dans la démo principale (et inversement) : deux mondes séparés."""
    client.post("/api/demo/reinitialiser")
    client.post(f"/api/stage/aller/{len(stage.ETAPES)}")
    noms = {m["nom"] for m in client.get("/api/membres").json()}
    assert "Sophie Carron" not in noms and "Markus Heinzmann" not in noms
    assert client.get("/api/relations", headers={"X-Membre": "p00"}).json() == []


def test_scene_ne_montre_aucun_champ_prive():
    v = client.post(f"/api/stage/aller/{len(stage.ETAPES)}").json()
    texte = json.dumps(v, ensure_ascii=False)
    assert "creneaux" not in texte and "mar-matin" not in texte and "@" not in texte


def test_le_graphe_ne_trahit_pas_qui_refuse_les_introductions():
    """La carte dit « ni nommé, ni proposé » : le graphe ne doit pas le laisser deviner (défaut trouvé en red team)."""
    v = client.post(f"/api/stage/aller/{len(stage.ETAPES)}").json()
    assert all(set(n) == {"id", "nom", "x", "y", "present"} for n in v["noeuds"])
    html = (stage.DATA_DIR.parent / "web" / "stage.html").read_text(encoding="utf-8")
    assert ".consent" not in html and ".refus" not in html and '" refus"' not in html
