"""Tranche P0 « réseau vivant » à travers la VRAIE API (mode démo, membres fictifs) :
besoin → candidats (4 dimensions, connu / déduit / inconnu) → aucune coordonnée → introduction en double accord →
relation (état dérivé, ligne de temps unique) → rencontre → +10 jours : suivi en attente → affaire en cours →
boîte réseau. Plus les attaques : fuite de lien tiers, faits orphelins, historique incohérent."""
import json

from fastapi.testclient import TestClient

from app.main import MAGASIN, MEMOIRE, app

client = TestClient(app)
SOPHIE, JULIEN = {"X-Membre": "p00"}, {"X-Membre": "p01"}
BESOIN = ("On lance nos jus d'abricot en Suisse alémanique. Je cherche un transporteur frigorifique "
          "qui livre Zurich deux fois par semaine, idéalement germanophone.")


def _reinit():
    client.post("/api/demo/reinitialiser")


def _publier():
    b = client.post("/api/analyser", json={"texte": BESOIN}).json()["besoin"]
    return client.post("/api/besoins", json={"besoin": b, "publier": True, "anonyme": False}, headers=SOPHIE).json()


def test_boucle_p0_de_bout_en_bout():
    _reinit()
    b = _publier()
    corr = client.get(f"/api/besoins/{b['id']}/correspondances", headers=SOPHIE).json()
    julien = next(s for s in corr["suggestions"] if s["profil"]["id"] == "p01")
    d = julien["dimensions"]
    assert set(d) >= {"pertinence", "reciprocite", "reseau", "contexte", "pourquoi_cette_personne", "pourquoi_maintenant",
                      "comment_nous_savons", "inconnu", "confidentialite"}
    assert d["contexte"]["etat_relation"] == "AUCUNE" and "aucune interaction enregistrée entre vous" in d["inconnu"]
    assert d["reseau"]["type"] in ("NOUVEAU", "PONT")
    texte = json.dumps(corr, ensure_ascii=False)
    assert "@" not in texte and "telephone" not in texte and "creneaux" not in texte   # aucune coordonnée, aucun créneau

    r = client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": "p01", "message": "Bonjour"}, headers=SOPHIE).json()
    boite_j = client.get("/api/reseau/boite", headers=JULIEN).json()
    assert [x["relation_id"] for x in boite_j["introductions_a_repondre"]] == [r["id"]]
    assert client.get("/api/reseau/boite", headers=SOPHIE).json()["mes_demandes_en_attente"][0]["relation_id"] == r["id"]
    assert client.get("/api/reseau/relation/p01", headers=SOPHIE).json()["etat"] == "INTRO_DEMANDEE"

    client.post(f"/api/relations/{r['id']}/accepter", json={}, headers=JULIEN)
    assert client.get("/api/reseau/relation/p00", headers=JULIEN).json()["etat"] == "INTRO_ACCEPTEE"
    client.post(f"/api/relations/{r['id']}/planifier", json={"date_rencontre": "2026-10-15"}, headers=JULIEN)
    client.post(f"/api/relations/{r['id']}/confirmer_rencontre", json={}, headers=JULIEN)
    mem = client.get("/api/reseau/relation/p01", headers=SOPHIE).json()
    assert mem["etat"] == "RENCONTREE" and mem["ou"] == "introduction" and mem["quand"]

    client.post("/api/cycle/avancer", json={"jours": 9})                               # horloge SIMULÉE
    assert client.get("/api/reseau/relation/p01", headers=SOPHIE).json()["etat"] == "RENCONTREE"   # pas avant 10 jours
    client.post("/api/cycle/avancer", json={"jours": 1})
    assert client.get("/api/reseau/relation/p01", headers=SOPHIE).json()["etat"] == "SUIVI_EN_ATTENTE"
    # ... mais aucune relance sans raison NOUVELLE : pas de « restez en contact »
    assert client.get("/api/reseau/boite", headers=SOPHIE).json()["suivis_proposes"] == []

    client.post(f"/api/relations/{r['id']}/cloturer", json={"resultat": "affaire_en_cours"}, headers=SOPHIE)
    fin = client.get("/api/reseau/relation/p01", headers=SOPHIE).json()
    assert fin["etat"] == "OPPORTUNITE"
    assert fin["ensuite"][:4] == ["INTRO_DEMANDEE", "INTRO_ACCEPTEE", "RENCONTRE", "RESULTAT"]


def test_introduction_declinee_est_terminale():
    _reinit()
    b = _publier()
    r = client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": "p01", "message": "Bonjour"}, headers=SOPHIE).json()
    client.post(f"/api/relations/{r['id']}/decliner", json={}, headers=JULIEN)
    assert client.get("/api/reseau/relation/p01", headers=SOPHIE).json()["etat"] == "DECLINEE"


def test_reinitialisation_ne_laisse_aucun_fait_orphelin():
    _reinit()
    b = _publier()
    client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": "p01", "message": "Bonjour"}, headers=SOPHIE)
    client.get("/api/reseau/boite", headers=SOPHIE)
    assert MEMOIRE.evenements("INTRO_DEMANDEE")
    _reinit()
    assert not MEMOIRE.evenements() and not MAGASIN.relations()
    assert client.get("/api/reseau/relation/p01", headers=SOPHIE).json()["etat"] == "AUCUNE"


def test_historique_fictif_projete_a_ses_vraies_dates():
    _reinit()
    client.post("/api/demo/historique")
    client.get("/api/reseau/boite", headers=SOPHIE)
    for r in MAGASIN.relations():
        horos = [e.horodatage for e in r.historique]
        assert horos == sorted(horos) and horos[0][:10] == r.cree_le[:10]              # historique cohérent avec cree_le
    rencontres = MEMOIRE.evenements("RENCONTRE")
    assert rencontres and all(e.le.isoformat() <= MEMOIRE.maintenant(e.le).isoformat() for e in rencontres)
    _reinit()


def test_chemin_chaud_ne_nomme_jamais_l_intermediaire():
    """Le lien entre l'intermédiaire et le candidat appartient à l'intermédiaire : il n'est pas révélé."""
    from datetime import date

    from adaptateurs.club import reseau
    from app.main import profils_effectifs
    from plateforme.affirmations import Statut
    from plateforme.memoire import Evt, Memoire
    m = Memoire()
    j = date(2026, 10, 3)
    for a, b in (("p00", "p32"), ("p32", "p06")):
        m.ajouter(Evt(type="RENCONTRE", le=j, acteurs=[a, b], statut=Statut.DECLARE))
    par_id = {p.id: p for p in profils_effectifs()}
    ch = reseau.chemin_chaud(reseau.graphe_de_confiance(m, j), "p00", "p06", par_id)
    assert ch["type"] == "PRESENTATION" and ch["via"] is None and "Reto" not in ch["message"]
    s = {"profil": {"id": "p06"}, "preuves": [{"critere": "x", "extrait": "y", "nature": "declare", "champ": "offre"}], "niveau": "forte"}
    dims = reseau.dimensions(m, par_id["p00"], s, par_id, j)
    assert "p32" not in json.dumps(dims) and "Reto" not in json.dumps(dims, ensure_ascii=False)
