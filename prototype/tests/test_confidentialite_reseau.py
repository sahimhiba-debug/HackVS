"""Attaques de confidentialité sur le réseau : brouillons, besoins clos, nouveaux membres, liens de tiers."""
import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SOPHIE = {"X-Membre": "p00"}
SECRET = "Nous envisageons discrètement de céder l'entreprise et cherchons un transporteur frigorifique pour Zurich"


def _besoin(texte, publier, qui=SOPHIE):
    b = client.post("/api/analyser", json={"texte": texte}).json()["besoin"]
    return client.post("/api/besoins", json={"besoin": b, "publier": publier, "anonyme": False}, headers=qui).json()


def test_brouillon_jamais_utilise_comme_raison_de_rencontre():
    client.post("/api/demo/reinitialiser")
    _besoin(SECRET, publier=False)
    plan = client.get("/api/soiree/plan").json()
    assert "céder" not in json.dumps(plan, ensure_ascii=False)
    d = client.post("/api/decisions", json={"demande": "des rencontres utiles"}).json()
    assert "céder" not in json.dumps(d, ensure_ascii=False)


def test_besoin_clos_ne_sert_plus_de_raison():
    client.post("/api/demo/reinitialiser")
    b = _besoin(SECRET, publier=True)
    client.post(f"/api/besoins/{b['id']}/cloturer", json={"note": "fini"}, headers=SOPHIE)
    assert "céder" not in json.dumps(client.get("/api/soiree/plan").json(), ensure_ascii=False)


def test_sonde_par_identifiants_ne_revele_pas_le_consentement():
    """IDOR / inférence de refus : solliciter un membre qui refuse et un membre qui ne correspond pas doit produire la
    MÊME réponse ; sinon on énumère le consentement de chacun."""
    client.post("/api/demo/reinitialiser")
    b = _besoin("Je cherche un transporteur frigorifique pour Zurich", publier=True)
    from app.main import profils_effectifs
    refuse = next(p.id for p in profils_effectifs() if not p.accepte_introductions and p.type == "membre_club")
    hors_sujet = "p15"
    r1 = client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": refuse, "message": "x"}, headers=SOPHIE)
    r2 = client.post("/api/relations", json={"besoin_id": b["id"], "cible_id": hors_sujet, "message": "x"}, headers=SOPHIE)
    assert (r1.status_code, r1.json()) == (r2.status_code, r2.json())


def test_exclusions_ne_comptent_pas_les_refus_en_petit_nombre():
    """k-anonymat : « 1 × ne souhaite pas recevoir d'introductions » permet d'identifier la personne dans un petit club."""
    from app.main import TAX, profils_effectifs
    from app.matching import rechercher
    from app.parser_rules import analyser
    eff = profils_effectifs()
    for texte in ("Je cherche un transporteur frigorifique pour Zurich", "Nous cherchons une fiduciaire", "Je cherche un traducteur"):
        res = rechercher(analyser(texte, TAX), eff[0], eff, TAX)
        for e in res.ecartes:
            assert "introductions" not in e.raison and "indisponible" not in e.raison or e.nombre >= 3, (texte, e)


def test_une_carte_ne_revele_rien_du_graphe_des_autres():
    """Inférence de graphe : un membre ne doit apprendre que des faits sur SES relations. Ni « un de vos contacts la
    connaît » (avec un seul contact, on sait lequel), ni la taille des groupes, ni une distance, ni le degré du candidat."""
    from datetime import date

    from adaptateurs.club import reseau
    from app.main import profils_effectifs
    from plateforme.affirmations import Statut
    from plateforme.memoire import Evt, Memoire
    m, j = Memoire(), date(2026, 10, 3)
    for a, b in (("p00", "p32"), ("p32", "p06"), ("p06", "p07"), ("p10", "p11")):
        m.ajouter(Evt(type="RENCONTRE", le=j, acteurs=[a, b], statut=Statut.DECLARE))
    ids = {p.id: p for p in profils_effectifs()}
    for cand in ("p06", "p07", "p11", "p20", "p32"):
        s = {"profil": {"id": cand}, "preuves": [{"critere": "x", "extrait": "y", "nature": "declare", "champ": "offre"}], "niveau": "forte"}
        d = reseau.dimensions(m, ids["p00"], s, ids, j)
        assert d["reseau"]["type"] in ("DIRECT", "AUCUNE"), (cand, d["reseau"])
        texte = json.dumps(d, ensure_ascii=False)
        assert "contact" not in texte.lower() and "groupe" not in texte and "poignées" not in texte, (cand, texte)
