"""Matrice de sécurité de l'API (mode démo, identité déclarée par en-tête — limite déclarée : pas d'authentification
réelle). On teste la CLASSE de défauts, pas un cas : chaque action × chaque acteur illégitime, double soumission,
et contenu des erreurs. Données FICTIVES."""
from __future__ import annotations

import os

os.environ.setdefault("HACKVS_DB", ":memory:")
os.environ.setdefault("HACKVS_SEMANTIQUE", "0")

import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import app
from app.store import TRANSITIONS

client = TestClient(app)
SOPHIE, JULIEN, TIERS = {"X-Membre": "p00"}, {"X-Membre": "p01"}, {"X-Membre": "p05"}
BESOIN = ("On lance nos jus d'abricot en Suisse alémanique. Je cherche un transporteur frigorifique "
          "qui livre Zurich deux fois par semaine, idéalement germanophone, et pas un concurrent.")
CORPS = {"planifier": {"date_rencontre": "2026-10-15"}, "cloturer": {"resultat": "utile"}}


@pytest.fixture(autouse=True)
def _reinit():
    client.post("/api/demo/reinitialiser")


def _besoin():
    b = client.post("/api/analyser", json={"texte": BESOIN}).json()["besoin"]
    return client.post("/api/besoins", json={"besoin": b, "publier": True}, headers=SOPHIE).json()


def _relation(etat: str = "proposee"):
    b = _besoin()
    r = client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": "p01", "message": "Bonjour"}, headers=SOPHIE).json()
    chemin = {"acceptee": ["accepter"], "rencontre_planifiee": ["accepter", "planifier"],
              "rencontre_faite": ["accepter", "planifier", "confirmer_rencontre"]}.get(etat, [])
    for a in chemin:
        qui = JULIEN if a == "accepter" else SOPHIE
        assert client.post(f"/api/relations/{r['id']}/{a}", json=CORPS.get(a, {}), headers=qui).status_code == 200
    return b, r


@pytest.mark.parametrize("etat,action", sorted(TRANSITIONS))
def test_un_tiers_ne_peut_faire_aucune_transition_et_n_apprend_pas_l_etat(etat, action):
    _, r = _relation(etat)
    rep = client.post(f"/api/relations/{r['id']}/{action}", json=CORPS.get(action, {}), headers=TIERS)
    assert rep.status_code == 403, rep.json()
    assert etat not in rep.text and "Sophie" not in rep.text and "Julien" not in rep.text   # rien sur l'état ni les noms


@pytest.mark.parametrize("action", ["accepter", "decliner", "retirer"])
def test_double_soumission_une_seule_transition(action):
    _, r = _relation()
    qui = SOPHIE if action == "retirer" else JULIEN
    premiers = [client.post(f"/api/relations/{r['id']}/{action}", json={}, headers=qui).status_code for _ in range(3)]
    assert premiers == [200, 409, 409]
    hist = [h for h in main.MAGASIN.relation(r["id"]).historique if h.action == action]
    assert len(hist) == 1


def test_double_clic_sur_demander_une_introduction():
    b = _besoin()
    codes = [client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": "p01", "message": "Bonjour"},
                         headers=SOPHIE).status_code for _ in range(3)]
    assert codes == [200, 409, 409] and len(client.get("/api/relations", headers=SOPHIE).json()) == 1


def test_un_tiers_ne_touche_ni_ne_lit_le_besoin_d_un_autre():
    b = _besoin()
    nouveau = client.post("/api/analyser", json={"texte": "Je cherche une fiduciaire."}).json()["besoin"]
    assert client.put(f"/api/besoins/{b['id']}", json={"besoin": nouveau}, headers=TIERS).status_code == 403
    for action in ("publier", "depublier", "cloturer"):
        assert client.post(f"/api/besoins/{b['id']}/{action}", json={}, headers=TIERS).status_code == 403, action
    assert client.get(f"/api/besoins/{b['id']}/correspondances", headers=TIERS).status_code == 403
    assert client.get(f"/api/relations/{_relation('acceptee')[1]['id']}/creneaux", headers=TIERS).status_code == 403


def test_identifiants_inexistants_ou_forges():
    for url in ("/api/relations/r_inexistant/accepter", "/api/besoins/b_inexistant/publier"):
        rep = client.post(url, json={}, headers=SOPHIE)
        assert rep.status_code in (404, 409), (url, rep.status_code)
    assert client.post("/api/relations/x/accepter", json={}, headers={"X-Membre": "inconnu"}).status_code in (403, 404)
    assert client.get("/api/reseau/relation/../../etc", headers=SOPHIE).status_code == 404


def test_les_erreurs_ne_divulguent_ni_trace_ni_donnee_privee():
    """Entrées malformées : réponse propre (4xx), jamais une trace Python, un chemin de fichier ou une requête SQL."""
    b = _besoin()
    essais = [client.post("/api/besoins", json={"besoin": {"criteres": "x"}}, headers=SOPHIE),
              client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": "p01", "message": "x" * 100000}, headers=SOPHIE),
              client.post("/api/relations", json={"besoin_id": "'; DROP TABLE relations; --", "cible_id": "p01", "message": "x"}, headers=SOPHIE),
              client.post(f"/api/relations/{b['id']}/planifier", json={"date_rencontre": "pas une date"}, headers=SOPHIE),
              client.post("/api/analyser", json={"texte": ""})]
    for rep in essais:
        assert 400 <= rep.status_code < 500, (rep.status_code, rep.text[:200])
        for motif in ("Traceback", "File \"", "/home/", "sqlite3", "SELECT ", "INSERT "):
            assert motif not in rep.text, (motif, rep.text[:300])
    assert client.get("/api/relations", headers=SOPHIE).status_code == 200    # le service est toujours debout


def test_toutes_les_entrees_sont_bornees():
    """Classe « entrée non bornée » : texte publié dans la Bourse, message d'introduction, profil (5000 offres)…"""
    g = "x " * 50000
    b = client.post("/api/analyser", json={"texte": "Je cherche un transporteur frigorifique pour Zurich."}).json()["besoin"]
    besoin = _besoin()
    offre = {"texte": "Transport frigorifique", "concept": "transport_frigorifique"}
    essais = {
        "besoin texte": client.post("/api/besoins", json={"besoin": {**b, "texte": g}, "publier": True}, headers=SOPHIE),
        "message": client.post("/api/relations", json={"besoin_id": besoin["id"], "cible_id": "p01", "message": g}, headers=SOPHIE),
        "présentation": client.put("/api/moi/profil", headers=JULIEN, json={"offre": [offre], "presentation": g}),
        "5000 offres": client.put("/api/moi/profil", headers=JULIEN, json={"offre": [offre] * 5000}),
        "note": client.post(f"/api/besoins/{besoin['id']}/cloturer", json={"note": g}, headers=SOPHIE),
        "identifiant": client.post("/api/relations", json={"besoin_id": g, "message": "x"}, headers=SOPHIE),
    }
    for nom, rep in essais.items():               # 413 : corps > 64 Kio arrêté avant lecture ; 422 : champ hors de ses bornes
        assert rep.status_code in (413, 422), (nom, rep.status_code)
    assert client.get("/api/bourse", headers=JULIEN).status_code == 200


def test_introspection_aucun_champ_texte_d_entree_sans_borne():
    """Garde-fou de CLASSE : tout nouveau champ texte/liste d'un modèle d'entrée de l'API doit être borné."""
    import typing

    from pydantic import BaseModel

    from app import cycle_api, decisions_api
    from app import main as m
    exemptes = {"EntreeAnalyse.texte", "EntreeTexte.texte"}   # bornés dans le gestionnaire (message dédié), testés
    manquants = []
    for mod in (m, cycle_api, decisions_api):
        for nom, cls in vars(mod).items():
            if not (isinstance(cls, type) and issubclass(cls, BaseModel) and cls.__module__ == mod.__name__):
                continue
            for champ, info in cls.model_fields.items():
                ann = str(info.annotation)
                if ("str" in ann or "list" in ann or "dict" in ann) and "Literal" not in ann and typing.get_origin(info.annotation) is not typing.Literal:
                    if not any(getattr(x, "max_length", None) for x in info.metadata) and f"{nom}.{champ}" not in exemptes:
                        manquants.append(f"{mod.__name__}.{nom}.{champ}")
    assert not manquants, manquants


def test_demande_sans_cible_repond_422_et_non_404():
    """Trouvé par le contrôle de types (mypy) : l'auteur qui oublie la cible recevait « 404 Membre inconnu »."""
    client.post("/api/demo/reinitialiser")
    H = {"X-Membre": "p00"}
    b = client.post("/api/analyser", json={"texte": "Je cherche un transporteur frigorifique pour Zurich"}).json()["besoin"]
    bb = client.post("/api/besoins", json={"besoin": b, "publier": True, "anonyme": False}, headers=H).json()
    r = client.post("/api/relations", json={"besoin_id": bb["id"], "message": "Bonjour"}, headers=H)
    assert r.status_code == 422 and "solliciter" in r.json()["detail"]
