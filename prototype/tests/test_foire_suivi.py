"""FOIRE 2026 · A — SUIVI : agrégats seulement, k = 3, canari « aucune donnée personnelle », interrupteur.
FOIRE 2026 · B — CLÔTURE d'un reçu : machine à états explicite à quatre étapes, refus testés."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence import monde_demo as md
from intelligence import partenariats as pa
from intelligence.erreurs import Conflit

CONSOLE = {"X-Pulse-Console": "1"}
A = "delegation_acheteurs"
client = TestClient(app)


def _session(pid):
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    return {"X-Pulse-Session": per[pid]["session"]}


@pytest.fixture(autouse=True)
def _foire(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    assert client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE).status_code == 200
    yield
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)


def _repondre(pid, oui=True, choix=None):
    s = _session(pid)
    ask = client.get("/api/pulse/moi/asks", headers=s).json()[0]
    corps = {"oui": oui, **({"attributs": {"places": 14}} if oui and ask["id"].startswith(A) else {}), **({"choix": choix} if choix else {})}
    r = client.post(f"/api/pulse/moi/asks/{ask['id']}/reponse", headers=s, json=corps)
    assert r.status_code == 200, r.text
    return s, ask


def _suivi(periode="demo"):
    r = client.get(f"/api/pulse/console/suivi?periode={periode}", headers=CONSOLE)
    assert r.status_code == 200, r.text
    return r.json()


def _recus():
    return client.get("/api/pulse/console/recus", headers=CONSOLE).json()


def _ref(s):
    """La référence du reçu de CE membre (celle qu'il voit sur son téléphone)."""
    return client.get("/api/pulse/moi/consentements", headers=s).json()[0]["reference"]


def _recu(ref):
    return next(x for x in _recus() if x["reference"] == ref)


# ------------------------------------------------------------------ A · Suivi
def test_suivi_etiquete_monde_de_demonstration_et_periodes():
    for p in ("demo", "7j", "trimestre"):
        s = _suivi(p)
        assert s["monde"] == "monde de démonstration" and s["fictif"] is True and s["k"] == 3
    assert client.get("/api/pulse/console/suivi?periode=an", headers=CONSOLE).status_code == 422


def test_suivi_exige_la_console():
    assert client.get("/api/pulse/console/suivi").status_code in (401, 403)


def test_un_seul_oui_s_affiche_moins_de_trois():
    avant = _suivi()
    assert avant["membres_actifs"] == "< 3"                          # deux accords semés (monde de démonstration)
    _repondre(md.PAULINE)
    s = _suivi()
    assert s["reponses"]["oui"] == "< 3"
    assert s["membres_actifs"] == 3                                  # à 3, le nombre est dit
    assert s["delai_premier_oui_jours"] is None and "moins de 3" in s["delai_note"]
    assert s["demandes"]["adressees"] >= 1                           # une demande ne désigne personne : dite telle quelle


def test_pas_cette_fois_est_compte_a_part_et_n_ecrit_rien_d_autre():
    _repondre(md.MARKUS, oui=False, choix="pas cette fois")
    _repondre(md.LEA, oui=False, choix="non")
    s = _suivi()
    assert s["reponses"]["pas_cette_fois"] == "< 3" and s["reponses"]["non"] == "< 3"


def test_trois_oui_sont_dits_et_le_delai_median_aussi(monkeypatch):
    monkeypatch.setenv("HACKVS_K_ANONYMAT", "1")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    _repondre(md.PAULINE)
    s = _suivi()
    assert s["reponses"]["oui"] == 1 and s["membres_actifs"] == 3
    assert isinstance(s["delai_premier_oui_jours"], (int, float))


def test_canari_aucune_donnee_personnelle_dans_la_charge_utile():
    """Le canari : ni nom de persona, ni identifiant de membre, ni texte d'offre — même après réponses et clôture."""
    _repondre(md.MARKUS, oui=False, choix="pas cette fois")
    _repondre(md.PAULINE)
    ref = _ref(_session(md.PAULINE))
    client.post(f"/api/pulse/console/recus/{ref}/cloture", headers=CONSOLE, json={"resultat": "signé", "note": "Essai réussi chez Pauline"})
    for p in ("demo", "7j", "trimestre"):
        brut = json.dumps(_suivi(p), ensure_ascii=False)
        for pid in (md.PAULINE, md.MARKUS, md.SOPHIE, md.LEA):
            assert pid not in brut
        for nom in ("Pauline", "Markus", "Sophie", "Léa", "Essai réussi"):
            assert nom not in brut
    brut = json.dumps(_recus(), ensure_ascii=False)
    assert md.PAULINE not in brut and "Pauline" not in brut


def test_ligne_nominative_seulement_sous_double_accord():
    s, _ = _repondre(md.PAULINE)
    ref = _ref(s)
    client.post(f"/api/pulse/console/recus/{ref}/visible", headers=CONSOLE, json={"visible": True})
    assert _suivi()["nominatif"] == []                               # le Club seul : rien
    assert client.post(f"/api/pulse/moi/recus/{ref}/visible", headers=s, json={"visible": True}).status_code == 200
    nom = _suivi()["nominatif"]
    assert len(nom) == 1 and nom[0]["membre"] != "—"
    client.post(f"/api/pulse/moi/recus/{ref}/visible", headers=s, json={"visible": False})
    assert _suivi()["nominatif"] == []                               # retiré par le membre : la ligne disparaît


def test_un_membre_ne_rend_pas_visible_le_recu_d_un_autre():
    s, _ = _repondre(md.PAULINE)
    ref = _ref(s)
    r = client.post(f"/api/pulse/moi/recus/{ref}/visible", headers=_session(md.MARKUS), json={"visible": True})
    assert r.status_code == 404


def test_interrupteur_eteint_toutes_les_routes_404(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    assert client.get("/api/pulse/console/suivi", headers=CONSOLE).status_code == 404
    assert client.get("/api/pulse/console/recus", headers=CONSOLE).status_code == 404
    assert client.post("/api/pulse/console/recus/x/cloture", headers=CONSOLE, json={"resultat": "signé"}).status_code == 404


# ------------------------------------------------------------------ B · clôture
def test_machine_a_etats_explicite():
    assert pa.suivante("demande", "oui") == "accord"
    assert pa.suivante("accord", "capacite_possible") == "essai"
    assert pa.suivante("essai", "cloture") == "resultat"
    assert pa.suivante("accord", "retrait") == "retire"
    for etape, fait in [("demande", "cloture"), ("resultat", "cloture"), ("retire", "cloture"), ("resultat", "retrait"),
                        ("demande", "capacite_possible"), ("essai", "oui")]:
        with pytest.raises(Conflit):
            pa.suivante(etape, fait)


def test_cloture_d_un_recu_valable_puis_agregat():
    s, _ = _repondre(md.PAULINE)
    ref = _ref(s)
    assert _recu(ref)["etape"] in ("accord", "essai") and _recu(ref)["resultat"] is None
    rep = client.post(f"/api/pulse/console/recus/{ref}/cloture", headers=CONSOLE, json={"resultat": "contact établi", "note": "à revoir"})
    assert rep.status_code == 200 and rep.json()["etape"] == "resultat"
    assert _recu(ref)["etape"] == "resultat" and _recu(ref)["resultat"] == "contact établi"
    s = _suivi()
    assert s["resultats"]["contact établi"] == "< 3" and s["partenariats_par_etape"]["resultat"] == "< 3"


def test_cloture_refusee_deux_fois_retire_inconnu_resultat_note():
    s, _ = _repondre(md.PAULINE)
    ref = _ref(s)
    url = f"/api/pulse/console/recus/{ref}/cloture"
    assert client.post(url, headers=CONSOLE, json={"resultat": "gagné"}).status_code == 422
    assert client.post(url, headers=CONSOLE, json={"resultat": "signé", "note": "x" * 141}).status_code == 422
    assert client.post("/api/pulse/console/recus/inconnu-1/cloture", headers=CONSOLE, json={"resultat": "signé"}).status_code == 404
    assert client.post(url, headers=CONSOLE, json={"resultat": "signé"}).status_code == 200
    assert client.post(url, headers=CONSOLE, json={"resultat": "abandonné"}).status_code == 409
    # un reçu retiré ne se clôture pas
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    s, _ = _repondre(md.PAULINE)
    ref = _ref(s)
    assert client.post(f"/api/pulse/moi/capacites/{A}/retrait", headers=s).status_code == 200
    assert _recu(ref)["etape"] == "retire"
    assert client.post(f"/api/pulse/console/recus/{ref}/cloture", headers=CONSOLE, json={"resultat": "signé"}).status_code == 409


def test_page_suivi_servie_avec_csp_et_etiquetee():
    r = client.get("/suivi")
    assert r.status_code == 200 and "monde de démonstration" in r.text
    assert "script-src" in r.headers.get("content-security-policy", "")


def test_etat_de_l_interrupteur_toujours_200(monkeypatch):
    """Les écrans lisent l'état avant d'appeler une route de la Foire : éteint, ni 404 ni bruit dans le navigateur."""
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    membre = {"X-Pulse-Session": per[md.PAULINE]["session"]}
    assert client.get("/api/pulse/console/foire", headers=CONSOLE).json() == {"actif": True}
    assert client.get("/api/pulse/moi/foire", headers=membre).json() == {"actif": True}
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    membre = {"X-Pulse-Session": per[md.PAULINE]["session"]}
    assert client.get("/api/pulse/console/foire", headers=CONSOLE).json() == {"actif": False}
    assert client.get("/api/pulse/moi/foire", headers=membre).json() == {"actif": False}
