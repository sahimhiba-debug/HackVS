"""« LA CARTE DEVIENT LE PROFIL » : Apertus (vision) PROPOSE, le code valide, le membre confirme ou corrige, un reçu ;
l'image n'est JAMAIS conservée ; parité (formulaire) si l'IA est éteinte, absente, en panne ou invalide ; l'entreprise
reste HORS du journal et part avec « tout effacer ». Données FICTIVES."""
import base64
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import charger_taxonomie
from intelligence import carte
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.erreurs import Invalide

PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"carte-fictive" * 50).decode()
CONSOLE = {"X-Pulse-Console": "1"}


class Faux:
    nom, modele = "apertus", "faux-apertus-vision"

    def __init__(self, sortie=None, erreur=None):
        self.sortie, self.erreur, self.recu = sortie, erreur, None

    def completer(self, systeme, message, schema):
        if self.erreur:
            raise self.erreur
        if isinstance(message, list):                                    # 1er temps : la vision recopie la carte
            self.recu = message
            return "SION · VALAIS / Paul Exemple / Fiduciaire du Rhône Fictive"
        return self.sortie                                               # 2e temps : extraction sous schéma


@pytest.fixture
def c(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    club = Demo(charger_taxonomie()).club
    club._chemin_db = tmp_path / "j.db"
    return club


def test_proposition_validee_par_le_code(c):
    c.ia.f, c.ia.actif = Faux(json.dumps({"entreprise": "Tisanes Alpines Fictives", "metier": "agriculture", "region": "Valais romand",
                                          "langue": "fr"})), True
    r = carte.proposer(c, PNG)
    assert r["source"] == "ia" and r["proposition"] == {"entreprise": "Tisanes Alpines Fictives", "metier": "agriculture",
                                                         "zone": "Valais romand", "langue": "fr"}
    assert c.ia.f.recu[1]["type"] == "image_url"                       # l'image part bien au modèle…
    c.ia.f = Faux(json.dumps({"entreprise": "X", "metier": "astrologie", "region": "Mars", "langue": "it"}))
    assert carte.proposer(c, PNG)["proposition"] == {}                 # …mais ce qui sort hors des listes est écarté


@pytest.mark.parametrize("etat", ["eteinte", "absente", "panne", "illisible", "autre_fournisseur"])
def test_parite_formulaire_manuel(c, etat):
    if etat == "eteinte":
        c.ia.f, c.ia.actif = Faux("{}"), False
    elif etat == "absente":
        c.ia.f = None
    elif etat == "panne":
        c.ia.f, c.ia.actif = Faux(erreur=TimeoutError()), True
    elif etat == "illisible":
        c.ia.f, c.ia.actif = Faux("pas du JSON"), True
    else:
        f = Faux("{}")
        f.nom = "openai"
        c.ia.f, c.ia.actif = f, True                                    # la vision ne part que vers Apertus
    r = carte.proposer(c, PNG)
    assert r["source"] == "formulaire" and r["proposition"] == {} and r["referentiel"]["metiers"]


def test_image_refusee_hors_format_ou_trop_lourde(c):
    for faux in ("", "data:text/plain;base64,aGVsbG8=", "data:image/gif;base64,R0lG",
                 "data:image/png;base64," + base64.b64encode(b"x" * (carte.OCTETS_MAX + 1)).decode()):
        with pytest.raises(Invalide):
            carte.proposer(c, faux)


def test_confirmation_recu_entreprise_hors_journal_et_l_image_jamais_conservee(c, tmp_path):
    c.ia.f, c.ia.actif = Faux(json.dumps({"entreprise": "Tisanes Alpines Fictives", "metier": "agriculture", "region": "Valais romand",
                                          "langue": "fr"})), True
    p = carte.proposer(c, PNG)["proposition"]
    r = carte.confirmer(c, md.PAULINE, "Tisanes Alpines Fictives", "agriculture", "Valais romand", "fr", p)
    assert r["recu"]["revocable"] and "pas conservée" in r["recu"]["finalite"] and r["recu"]["provenance"].startswith("proposé par l'IA")
    assert c.identites_profil[md.PAULINE]["entreprise"] == "Tisanes Alpines Fictives"
    with sqlite3.connect(tmp_path / "j.db") as db:
        brut = " ".join(str(x) for x in db.execute("SELECT * FROM evenements").fetchall())
    assert "Tisanes Alpines" not in brut                               # l'entreprise n'est PAS dans le journal
    assert PNG.split(",")[1][:40] not in brut and "carte-fictive" not in brut   # ni l'image
    assert list(tmp_path.glob("*.png")) == [] and list(tmp_path.glob("*.jp*g")) == []
    corrige = carte.confirmer(c, md.PAULINE, "Autre Nom Fictif", "agriculture", "Valais romand", "fr", p)
    assert corrige["recu"]["provenance"] == "déclaré par vous"         # corrigé par le membre : déclaré


def test_tout_effacer_purge_l_entreprise(c):
    carte.confirmer(c, md.PAULINE, "Tisanes Alpines Fictives", "agriculture", "Valais romand", "fr")
    c.effacer(md.PAULINE)
    assert md.PAULINE not in c.identites_profil


def test_http_plafond_de_corps_propre_a_la_route_et_interrupteur(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    cl = TestClient(app)
    cl.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    per = {p["id"]: p for p in cl.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    s = {"X-Pulse-Session": per[md.PAULINE]["session"]}
    grosse = "data:image/png;base64," + base64.b64encode(b"\x89PNG" + b"y" * 300_000).decode()
    r = cl.post("/api/pulse/moi/carte/proposer", headers=s, json={"image": grosse})
    assert r.status_code == 200 and r.json()["source"] == "formulaire"  # 400 Kio acceptés sur CETTE route (IA éteinte en test)
    assert cl.post("/api/pulse/moi/offres", headers=s, json={"x": "y" * 70_000}).status_code == 413   # ailleurs : 64 Kio
    ok = cl.post("/api/pulse/moi/carte/confirmer", headers=s, json={"entreprise": "Tisanes Alpines Fictives", "metier": "agriculture",
                                                                   "zone": "Valais romand", "langue": "fr"})
    assert ok.status_code == 200
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    cl.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    per = {p["id"]: p for p in cl.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    assert cl.post("/api/pulse/moi/carte/proposer", headers={"X-Pulse-Session": per[md.PAULINE]["session"]},
                   json={"image": PNG}).status_code == 404
