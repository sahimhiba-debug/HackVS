"""FEUILLE DE ROUTE VIVANTE (§7) : etat.yaml source unique ; trois statuts vérifiés par le code (« construit » exige des
tests qui existent ; « validé sur le terrain » exige une preuve réelle) ; README régénéré et à jour ; page publique
FR / DE / EN ; QR depuis PUBLIC_BASE_URL ; liens vers le monde « visite » seulement s'il existe."""
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence import feuille_de_route as fr

client = TestClient(app)


def test_statuts_verifies_par_le_code(tmp_path):
    e = fr.charger()
    assert {x["statut"] for x in e} <= set(fr.STATUTS) and all(x["fr"] and x["de"] and x["en"] for x in e)
    valides = [x for x in e if x["statut"] == "valide"]
    assert [x["id"] for x in valides] == ["tally"]                    # la SEULE preuve réelle d'aujourd'hui
    for faux, msg in [("- id: x\n  statut: valide\n  fr: a\n  de: b\n  en: c\n", "preuve réelle"),
                      ("- id: x\n  statut: construit\n  fr: a\n  de: b\n  en: c\n  ecran: /app\n  tests: test_inexistant.py\n", "introuvables"),
                      ("- id: x\n  statut: fini\n  fr: a\n  de: b\n  en: c\n", "statut")]:
        f = tmp_path / "e.yaml"
        f.write_text(faux, encoding="utf-8")
        with pytest.raises(ValueError, match=msg):
            fr.charger(f)


def test_readme_est_a_jour_avec_etat_yaml():
    texte = fr.README.read_text(encoding="utf-8")
    jour = re.search(r"État au (\d\d)\.(\d\d)\.(\d{4})", texte)
    assert jour, "le tableau du README doit être daté"
    attendu = fr.tableau(fr.charger(), date(int(jour[3]), int(jour[2]), int(jour[1])))
    assert attendu in texte, "README de la feuille de route périmé : make feuille-de-route"


def test_page_publique_et_api_qr_depuis_public_base_url(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://pulse.exemple.ch")
    monkeypatch.delenv("PUBLIC_VISITE_URL", raising=False)
    assert client.get("/feuille-de-route").status_code == 200
    d = client.get("/api/pulse/feuille-de-route").json()
    assert d["url"] == "https://pulse.exemple.ch/feuille-de-route" and d["qr"].startswith("data:image/svg")
    assert d["visite_disponible"] is False and all(c["lien"] is None for c in d["chantiers"])
    monkeypatch.setenv("PUBLIC_VISITE_URL", "https://visite.exemple.ch")
    d = client.get("/api/pulse/feuille-de-route").json()
    liens = {c["id"]: c["lien"] for c in d["chantiers"]}
    assert liens["suivi"] == "https://visite.exemple.ch/suivi" and liens["pilote"] is None and liens["tally"] is None


def test_monde_visite_console_ouverte_salle_eteinte(monkeypatch):
    from app.pulse_api import creer_routeur
    from app.taxonomy import charger_taxonomie
    from fastapi import FastAPI
    monkeypatch.setenv("HACKVS_VISITE", "1")
    a = FastAPI()
    a.include_router(creer_routeur(charger_taxonomie()))
    distant = TestClient(a, client=("10.0.0.9", 4000))
    assert distant.get("/api/pulse/monde").json()["visite"] is True
    assert distant.get("/api/pulse/console/capacites", headers={"X-Pulse-Console": "1"}).status_code == 200   # bac à sable
    assert distant.post("/api/pulse/console/salle/ouvrir", headers={"X-Pulse-Console": "1"}).status_code == 404  # jamais de salle
    monkeypatch.delenv("HACKVS_VISITE")
    b = FastAPI()
    b.include_router(creer_routeur(charger_taxonomie()))
    assert TestClient(b, client=("10.0.0.9", 4000)).get("/api/pulse/console/capacites", headers={"X-Pulse-Console": "1"}).status_code == 403
