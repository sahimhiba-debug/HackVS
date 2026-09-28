"""Expérience « intentions scellées » : exactitude de la PSI, k-anonymat, révélation symétrique, ce que voit le Club."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("HACKVS_DB", ":memory:")
os.environ.setdefault("HACKVS_SEMANTIQUE", "0")

from fastapi.testclient import TestClient

from app.main import app
from experiences import psi
from experiences.intentions import Agent, Intention, Relais, compatibilite, generaliser

client = TestClient(app)
B = "/api/experiences/scelle"


def test_psi_exacte_et_aveugle():
    assert psi.intersection(["a", "b", "c"], ["c", "d", "a"]) == {"a", "c"}
    assert psi.intersection(["a"], ["b"]) == set()
    k1, k2 = psi.Cle(), psi.Cle()
    assert k1.aveugler_texte("x") != k2.aveugler_texte("x")  # même intention, points différents : aucun traçage


def test_compatibilite_seulement_si_intentions_inverses():
    r = Relais()
    cedant = Agent("a", [Intention("ceder", ("menuiserie",), "Valais")])
    repreneur = Agent("b", [Intention("reprendre", ("menuiserie", "vins"), "Valais")])
    autre_cedant = Agent("c", [Intention("ceder", ("menuiserie",), "Valais")])
    assert compatibilite(cedant, repreneur, r) and compatibilite(repreneur, cedant, r)
    assert not compatibilite(cedant, autre_cedant, r)                     # deux vendeurs ne se « trouvent » pas
    assert not compatibilite(cedant, Agent("d", []), r)                   # agent de couverture : rien
    assert all(len(charge) == 6 for _, _, charge in r.vus)                # taille fixe : on ne voit pas combien d'intentions
    vus = {j for _, _, charge in r.vus for j in charge}
    assert psi.hacher("cedant|menuiserie|Valais").hex() not in vus        # le relais ne peut pas reconnaître un jeton


def test_k_anonymat_des_categories():
    annuaire, parents = {"logistique": 6, "menuiserie": 1, "energie_solaire": 1, "energie": 3}, {"energie_solaire": "energie"}
    assert generaliser("logistique", annuaire, parents) == "logistique"
    assert generaliser("energie_solaire", annuaire, parents) == "energie"   # parent assez peuplé
    assert generaliser("menuiserie", annuaire, parents) == "*"              # seul de son secteur : jamais nommé


def test_revelation_progressive_et_symetrique():
    client.post(f"{B}/reinitialiser")
    club = client.post(f"{B}/tour").json()
    assert club["intentions_lisibles"] == 0 and club["compatibilites_existantes"] == 2
    m = client.get(f"{B}/agent/p20").json()["compatibilites"][0]
    assert "tout secteur" in m["categorie"] and m["devoile"] is None      # seule menuiserie du Club : non nommée
    assert client.post(f"{B}/devoiler/{m['match']}", json={"membre": "p05"}).status_code == 403   # tiers
    client.post(f"{B}/devoiler/{m['match']}", json={"membre": "p20"})
    assert client.get(f"{B}/agent/p21").json()["compatibilites"][0]["devoile"] is None           # unilatéral : rien
    client.post(f"{B}/devoiler/{m['match']}", json={"membre": "p21"})
    vu = client.get(f"{B}/agent/p21").json()["compatibilites"][0]["devoile"]
    assert "identite" not in vu and vu["intention_de_l_autre"] == "céder mon entreprise"          # secteur avant identité
    for qui in ("p20", "p21"):
        client.post(f"{B}/devoiler/{m['match']}", json={"membre": qui})
    assert "Fabienne Carron" in client.get(f"{B}/agent/p20").json()["compatibilites"][0]["devoile"]["identite"]
    assert client.post(f"{B}/attaque").json()["reussites"] == 0
    # un agent sans intention compatible n'apprend rien
    assert client.get(f"{B}/agent/p00").json()["compatibilites"] == []


def test_experience_absente_en_mode_reel():
    code = ("from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); "
            "print(c.get('/scelle').status_code, c.post('/api/experiences/scelle/tour').status_code)")
    env = {**os.environ, "HACKVS_MODE": "reel", "HACKVS_DB": ":memory:"}
    sortie = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parent.parent).stdout.split()
    assert sortie == ["501", "404"]
