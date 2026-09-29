"""Scène « Le Club répond » : rejouable, honnête sur ce qui est joué, jury en lecture seule, fiches protégées."""
import json
import os

from fastapi.testclient import TestClient

os.environ.setdefault("HACKVS_MODE", "demo")
from app.club_repond import ETAPES, rejouer_jusqu_a  # noqa: E402
from app.main import TAX, app  # noqa: E402

client = TestClient(app)


def test_histoire_complete_deterministe_et_rejouable():
    a, b = rejouer_jusqu_a(TAX, len(ETAPES)), rejouer_jusqu_a(TAX, len(ETAPES))
    assert a.m.empreinte() == b.m.empreinte() and a.traces == b.traces
    titres = [t["titre"] for t in a.traces]
    assert "DEMANDE DÉBLOQUÉE" in titres
    f = {t["etape"]: t["faits"] for t in a.traces}
    assert f[1]["sollicitees"] == 2 and f[1]["couverture"] == "2/2"
    assert f[4]["etat"]["etat"] == "DEBLOQUEE"
    assert f[5]["personnes_derangees"] == 0 and f[5]["depuis_la_memoire"]
    assert all(not x["qui"] for x in f[6]["japon"])


def test_chaque_geste_humain_est_marque_joue():
    w = rejouer_jusqu_a(TAX, len(ETAPES))
    humains = {e.type for e in w.m.evenements("SOLLICITATION_ACCEPTEE", "CONTRIBUTION", "EFFET_CONFIRME")}
    assert humains == {"SOLLICITATION_ACCEPTEE", "CONTRIBUTION", "EFFET_CONFIRME"}
    assert all(e.statut.value == "SIMULE" for e in w.m.evenements())      # rien ne se présente comme observé
    joues = [t for t in w.traces if t["joue"]]
    assert {t["etape"] for t in joues} >= {3, 4}                            # accords, contributions, confirmation


def test_la_vue_d_anna_ne_revele_ni_sophie_ni_l_autre_etape():
    w = rejouer_jusqu_a(TAX, 3)
    vue = json.dumps(w.traces[2]["faits"]["vue_anna"], ensure_ascii=False)
    assert "Sophie" not in vue and "Tisanes" not in vue and "Allemagne" not in vue.replace("en allemand", "")


def test_jury_ne_modifie_rien_et_distingue_les_cas():
    client.post("/api/club-repond/aller/5")
    avant = client.get("/api/club-repond").json()
    cas = {"J'ai besoin d'aide pour la distribution de nos produits.": "QUESTION",
           "Je cherche un distributeur au Japon pour nos tisanes.": "MANQUE",
           "Je cherche un conseil en sécurité": "MANQUE",
           "bonjour tout le monde": "PRECISER",
           "Je cherche une traductrice pour nos étiquettes.": "PLAN"}
    for texte, attendu in cas.items():
        r = client.post("/api/club-repond/essayer", json={"texte": texte})
        assert r.status_code == 200 and r.json()["verdict"] == attendu and r.json()["ecrit"] is False, texte
    assert client.get("/api/club-repond").json() == avant
    assert client.post("/api/club-repond/essayer", json={"texte": "x" * 601}).status_code == 422
    assert client.post("/api/club-repond/essayer", json={"texte": "traduction", "demandeur": "inconnu"}).status_code == 422


def test_seule_une_fiche_confirmee_et_partageable_se_telecharge():
    client.post("/api/club-repond/aller/4")                                 # contributions reçues, pas encore confirmées
    w = client.get("/api/club-repond").json()
    lien = next(c["telecharger"] for c in w["traces"][3]["faits"]["contributions"] if "telecharger" in c)
    assert client.get(lien).status_code == 404                              # pas encore confirmée
    client.post("/api/club-repond/aller/5")
    r = client.get(lien)
    assert r.status_code == 200 and "Provenance" in r.text and "FICTIVES" in r.text and "Sophie" not in r.text
    intro = rejouer_jusqu_a(TAX, 5).ctx["c_intro"]
    assert client.get(f"/api/club-repond/ressource/{intro}").status_code == 404   # l'introduction reste privée


def test_navigation_bornes_et_fin():
    assert client.post("/api/club-repond/aller/99").status_code == 422
    client.post(f"/api/club-repond/aller/{len(ETAPES)}")
    assert client.post("/api/club-repond/suivant").status_code == 409
    assert client.post("/api/club-repond/reinitialiser").json()["etape"] == 0
