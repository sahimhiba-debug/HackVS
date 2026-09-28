"""Explication = décision : ce que la carte affiche est recalculé ici INDÉPENDAMMENT et comparé.
+ nouveau membre (démarrage à froid, invisible par défaut), réciprocité prouvée dans les deux cas (oui / non)."""
import json

from fastapi.testclient import TestClient

from app.main import TAX, app, profils_effectifs

client = TestClient(app)
PROFIL_NADIA = {"nom": "Nadia Berclaz", "fonction": "Fondatrice", "entreprise": "Pixel Rhône (fictive)", "commune": "Sion",
                "offre": [{"concept": "marketing", "texte": "Nous faisons le référencement et les campagnes en ligne pour les PME"}],
                "recherche": [{"concept": "developpement_web", "texte": "Nous cherchons un développeur web pour nos boutiques en ligne"}],
                "langues": ["fr"], "zones_service": ["Valais"]}


def _correspondances(texte: str, qui: dict) -> dict:
    b = client.post("/api/analyser", json={"texte": texte}).json()["besoin"]
    bb = client.post("/api/besoins", json={"besoin": b, "publier": True, "anonyme": False}, headers=qui).json()
    return client.get(f"/api/besoins/{bb['id']}/correspondances", headers=qui).json()


def _textes(p) -> list[str]:
    return [o.texte for o in p.offre] + [o.texte for o in p.recherche] + [p.presentation] + p.zones_service + p.langues + [p.commune]


def _verifier_coherence(x_id: str, corr: dict):
    eff = {p.id: p for p in profils_effectifs()}
    x = eff[x_id]
    for s in corr["suggestions"]:
        c, d = eff[s["profil"]["id"]], s["dimensions"]
        assert c.accepte_introductions, "un membre qui refuse les introductions ne doit jamais être proposé"
        r = d["reciprocite"]
        if r["etablie"]:  # la preuve affichée existe mot pour mot, des deux côtés
            assert any(r["votre_offre"] in t for t in _textes(x)), (x_id, c.id, r)
            besoin = r["son_besoin"].split(" : ", 1)[1]
            assert besoin in [o.texte for o in c.recherche] + [b["besoin"]["texte"] for b in client.get("/api/besoins", headers={"X-Membre": c.id}).json()]
        else:             # « non établie » : vérification indépendante par la taxonomie, sur les offres DÉCLARÉES
            assert not any(o.concept and rc.concept and TAX.couvre(o.concept, rc.concept) for o in x.offre for rc in c.recherche), (x_id, c.id)
        assert (d["contexte"]["etat_relation"] == "AUCUNE") == ("aucune interaction enregistrée entre vous" in d["inconnu"])
        for ligne in d["comment_nous_savons"]["connu"]:
            extrait = ligne.split("« ", 1)[1].split(" »", 1)[0]
            assert any(extrait in t for t in _textes(c)), (c.id, extrait)
        assert d["reseau"].get("via") is None                   # jamais un tiers nommé


def test_nouveau_membre_invisible_par_defaut_puis_visible_s_il_le_choisit():
    client.post("/api/demo/reinitialiser")
    n = client.post("/api/demo/rejoindre", json=PROFIL_NADIA).json()
    nid = n["membre"]["id"]
    assert n["visible_pour_les_autres"] is False
    ines = {"X-Membre": "p26"}                                   # Inès cherche du référencement : Nadia en propose
    trouve = lambda: any(s["profil"]["id"] == nid for s in _correspondances("Nous cherchons un partenaire en référencement", ines)["suggestions"])  # noqa: E731
    assert not trouve()
    client.post("/api/moi/consentement", json={"accepte": True}, headers={"X-Membre": nid})
    assert trouve()


def test_nouveau_membre_reciprocite_prouvee_et_non_prouvee():
    client.post("/api/demo/reinitialiser")
    nid = client.post("/api/demo/rejoindre", json=PROFIL_NADIA).json()["membre"]["id"]
    N = {"X-Membre": nid}
    web = _correspondances("Nous cherchons un développeur pour créer une boutique en ligne", N)
    ines = next(s for s in web["suggestions"] if s["profil"]["id"] == "p26")["dimensions"]
    assert ines["reciprocite"]["etablie"] and "référencement" in ines["reciprocite"]["votre_offre"]
    assert ines["reseau"]["type"] == "AUCUNE"                    # démarrage à froid : aucun lien encore
    fin = _correspondances("Nous cherchons un financement pour notre croissance", N)
    assert fin["suggestions"] and not any(s["dimensions"]["reciprocite"]["etablie"] for s in fin["suggestions"])
    _verifier_coherence(nid, web)
    _verifier_coherence(nid, fin)


def test_coherence_decision_explication_sur_tous_les_membres():
    """Pour chaque membre qui cherche quelque chose : les cartes ne disent que ce que les données prouvent."""
    client.post("/api/demo/reinitialiser")
    verifies = 0
    for p in profils_effectifs():
        for r in p.recherche[:1]:
            corr = _correspondances(r.texte, {"X-Membre": p.id})
            _verifier_coherence(p.id, corr)
            verifies += len(corr["suggestions"])
    assert verifies >= 20


def test_adhesion_valide_ses_entrees():
    client.post("/api/demo/reinitialiser")
    assert client.post("/api/demo/rejoindre", json=PROFIL_NADIA | {"offre": []}).status_code == 422
    assert client.post("/api/demo/rejoindre", json=PROFIL_NADIA | {"secteurs": ["inexistant"]}).status_code == 422
    assert client.post("/api/demo/rejoindre", json=PROFIL_NADIA | {"offre": [{"concept": "x_inconnu", "texte": "a"}]}).status_code == 422
    rep = client.post("/api/demo/rejoindre", json=PROFIL_NADIA).json()
    assert "@" not in json.dumps(rep) and rep["secteurs_deduits_des_offres"] is True
    client.post("/api/demo/reinitialiser")
    assert not any(p.id.startswith("n") for p in profils_effectifs())   # la réinitialisation retire les adhésions


def test_suivi_par_l_autre_sens_de_la_reciprocite_puis_simulation():
    """Nadia rencontre Inès pour SON besoin (web) ; 10 jours plus tard, l'autre sens (Inès cherche du référencement,
    Nadia en propose) devient une raison documentée de reprendre contact — proposée à Inès, pas à Nadia."""
    from datetime import date

    from adaptateurs.club import reseau
    from app.main import MEMOIRE, aujourdhui_reseau
    client.post("/api/demo/reinitialiser")
    nid = client.post("/api/demo/rejoindre", json=PROFIL_NADIA).json()["membre"]["id"]
    N, INES = {"X-Membre": nid}, {"X-Membre": "p26"}
    b = client.post("/api/analyser", json={"texte": "Nous cherchons un développeur pour créer une boutique en ligne"}).json()["besoin"]
    bb = client.post("/api/besoins", json={"besoin": b, "publier": True, "anonyme": False}, headers=N).json()
    t0 = aujourdhui_reseau()
    g0 = reseau.graphe_de_confiance(MEMOIRE, t0)
    sim = reseau.simuler(g0, [(nid, "p26")], t0, focus=[nid])
    assert sim["nature"] == "SIMULATION" and sim["apres"]["liens"] == sim["avant"]["liens"] + 1
    assert sim["portee_a_2_sauts"][nid] == {"avant": 0, "apres": 1}
    assert reseau.graphe_de_confiance(MEMOIRE, t0).number_of_edges() == g0.number_of_edges()   # rien n'est écrit
    r = client.post("/api/relations", json={"besoin_id": bb["id"], "cible_id": "p26", "message": "Bonjour"}, headers=N).json()
    for action, qui, corps in (("accepter", INES, {}), ("planifier", INES, {"date_rencontre": "2026-10-15"}), ("confirmer_rencontre", N, {})):
        assert client.post(f"/api/relations/{r['id']}/{action}", json=corps, headers=qui).status_code == 200
    assert client.get("/api/reseau/boite", headers=INES).json()["suivis_proposes"] == []      # trop tôt
    client.post("/api/cycle/avancer", json={"jours": 10})
    boite_ines = client.get("/api/reseau/boite", headers=INES).json()["suivis_proposes"]
    assert [x["type"] for x in boite_ines] == ["RECIPROCITE_OUVERTE"]
    assert client.get("/api/reseau/boite", headers=N).json()["suivis_proposes"] == []        # le sens déjà servi : rien
    assert date.fromisoformat(MEMOIRE.maintenant(t0).isoformat()) > t0
