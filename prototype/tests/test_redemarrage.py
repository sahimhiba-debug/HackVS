"""Redémarrage RÉEL (deux processus distincts sur les mêmes fichiers) : l'état survit, rien n'est dupliqué, et une
décision enregistrée avant l'arrêt se rejoue à l'identique après. Données FICTIVES."""
import json
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

AVANT = r"""
import json
from fastapi.testclient import TestClient
from app import main
c = TestClient(main.app)
c.post("/api/demo/reinitialiser")
S, J = {"X-Membre": "p00"}, {"X-Membre": "p01"}
b = c.post("/api/analyser", json={"texte": "On lance nos jus d'abricot en Suisse alémanique. Je cherche un transporteur frigorifique qui livre Zurich deux fois par semaine."}).json()["besoin"]
b = c.post("/api/besoins", json={"besoin": b, "publier": True}, headers=S).json()
r = c.post("/api/relations", json={"besoin_id": b["id"], "cible_id": "p01", "message": "Bonjour"}, headers=S).json()
c.post(f"/api/relations/{r['id']}/accepter", json={}, headers=J)
d = c.post("/api/decisions", json={"demande": "tout le monde au moins une rencontre utile, 3 tours"}).json()["run"]
main.projeter_reseau()
print(json.dumps({"relation": r["id"], "run": d["run_id"], "resultat": d["resultat_empreinte"],
                  "memoire": main.MEMOIRE.empreinte(), "n_memoire": len(main.MEMOIRE.evenements())}))
"""

APRES = r"""
import json, sys
from fastapi.testclient import TestClient
from app import main
avant = json.loads(sys.argv[1])
c = TestClient(main.app)
rel = [x for x in c.get("/api/relations", headers={"X-Membre": "p00"}).json() if x["id"] == avant["relation"]]
main.projeter_reseau(); main.projeter_reseau()                 # projection répétée : idempotente
rej = c.post(f"/api/decisions/{avant['run']}/rejouer").json()
print(json.dumps({"etat": rel[0]["etat"] if rel else None, "memoire": main.MEMOIRE.empreinte(),
                  "n_memoire": len(main.MEMOIRE.evenements()), "rejeu": rej}))
"""


def _lancer(code: str, env: dict, *args: str) -> dict:
    p = subprocess.run([sys.executable, "-c", code, *args], cwd=RACINE, env=env, capture_output=True, text=True, timeout=300)
    assert p.returncode == 0, p.stderr[-2000:]
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_l_etat_survit_a_un_redemarrage_et_la_decision_se_rejoue_a_l_identique(tmp_path):
    env = os.environ | {"HACKVS_DB": str(tmp_path / "fil.db"), "HACKVS_CYCLE_DB": str(tmp_path / "reseau.db"),
                        "HACKVS_DECISIONS_DB": str(tmp_path / "decisions.db"), "HACKVS_SEMANTIQUE": "0"}
    avant = _lancer(AVANT, env)
    apres = _lancer(APRES, env, json.dumps(avant))
    assert apres["etat"] == "acceptee"
    assert apres["memoire"] == avant["memoire"] and apres["n_memoire"] == avant["n_memoire"]   # rien dupliqué ni perdu
    assert apres["rejeu"].get("identique") is True, apres["rejeu"]
