"""Mode scène : déterministe, rejouable, isolé, sûr en direct (double clic, retour arrière, fin, réinitialisation)."""
import json
import re

from fastapi.testclient import TestClient

from app import stage
from app.main import TAX, app

client = TestClient(app)


def _canon(traces: list[dict]) -> str:
    """Ce qui est AFFICHÉ, sans identifiants internes aléatoires (ids de relance ou de relation)."""
    return re.sub(r'"(id|relance_id|relation_id)": "[^"]*"', '"id": "*"', json.dumps(traces, ensure_ascii=False, sort_keys=True))


def test_rejeu_identique_trois_fois():
    n = len(stage.ETAPES)
    runs = [_canon(stage.rejouer_jusqu_a(TAX, n).traces) for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]


def test_histoire_racontee_par_le_moteur():
    t = {x["etape"]: x["faits"] for x in stage.rejouer_jusqu_a(TAX, len(stage.ETAPES)).traces}
    assert t[0]["invisible_par_defaut"] is True and t[0]["coordonnees_enregistrees"] == "aucune"
    compris = {c["role"]: c for c in t[1]["compris"]}
    assert compris["besoin principal"]["quoi"] == "Développement commercial en Allemagne"
    assert "distribution" in compris["besoin principal"]["note"]
    assert compris["langue"]["quoi"] == "français" and compris["contrainte"]["quoi"] == "pas un concurrent direct"
    assert t[1]["incertain"] == [] and "aucune IA générative" in t[1]["analyse"]
    cand = t[2]["candidats"]
    assert cand[0]["nom"] == "Markus Heinzmann" and cand[0]["niveau"] == "forte"
    assert cand[0]["dimensions"]["reciprocite"]["etablie"] is True
    assert t[2]["ecartes_par_leur_choix"] == 0                       # Stefan refuse : ni nommé, ni compté (k < 3)
    assert "Kalbermatten" not in json.dumps(t, ensure_ascii=False)
    assert t[3]["coordonnees_avant_accord"] is False and t[3]["coordonnees_apres_accord"] is True
    assert t[4]["etat_relation"] == "RENCONTREE"
    assert [r["type"] for p in t[5]["relances"] for r in p["raisons"]] == ["RECIPROCITE_OUVERTE"]
    assert t[5]["silences"]["rien_de_nouveau"] == 17
    assert t[6]["etat_relation"] == "OPPORTUNITE"
    r = t[7]                                                          # le réseau qui évolue (simulation)
    assert (r["avant"]["groupes"], r["apres"]["groupes"]) == (2, 1)
    assert (r["avant"]["groupe_robuste"], r["apres"]["groupe_robuste"]) == (4, 15)
    assert r["avant"]["isoles"] == r["apres"]["isoles"] == 2          # pas de lien inventé pour faire baisser l'indicateur
    assert r["nature"].startswith("SIMULATION") and r["besoins_couverts"] == 3
    a = t[8]                                                          # « je pourrais… je préfère m'abstenir »
    assert a["decision"] == "S_ABSTENIR" and a["introductions_fondees"] == 0 and a["introductions_possibles"] >= 10
    assert a["par_ressemblance"] and a["japon"]["decision"] == "S_ABSTENIR"
    s_ = t[9]["soirees"]                                              # saturation : 9 → 1 → 0 rencontres utiles
    assert [x["rencontres_utiles_possibles"] for x in s_] == [9, 1, 0] and s_[-1]["decision"] == "S_ABSTENIR"
    assert any("NON MESURÉE" in n["nature"] for n in t[10]["natures"])


def test_l_abstention_suit_les_regles_du_moteur():
    """« Je préfère m'abstenir » n'est pas une phrase de présentation : c'est le résultat de candidates/refus_motives."""
    from adaptateurs.club import interventions as iv
    w = stage.rejouer_jusqu_a(TAX, 8)
    g, bes, etats = stage._contexte_reseau(w)
    x = w.traces[-1]["etape"] and stage._membres(w)
    seul = next(m for m in x if g.degree(m) == 0 and w.par_id()[m].accepte_introductions)
    fondees = {c.b if c.a == seul else c.a for c in iv.candidates(w.profils(), bes, TAX, g, etats) if seul in (c.a, c.b)}
    assert set(iv.relier_sans_preuve(seul, w.profils(), bes, TAX, g, etats)["introductions_fondees"]) == fondees == set()


def test_les_simulations_n_ecrivent_rien():
    w = stage.rejouer_jusqu_a(TAX, 7)
    avant = w.memoire.empreinte()
    for etape in stage.ETAPES[7:10]:                                  # réseau, abstention, soirées
        etape(w)
    assert w.memoire.empreinte() == avant


def test_tour_de_controle_chaque_chiffre_est_explicable():
    w = stage.rejouer_jusqu_a(TAX, len(stage.ETAPES))
    for i in stage.tour(w):
        assert i["definition"] and isinstance(i["valeur"], int)
        if i["cle"] != "suivis":                                      # suivis : une paire peut porter plusieurs raisons
            assert len(i["elements"]) == i["valeur"], i
    ind = {i["cle"]: i["valeur"] for i in stage.tour(w)}
    assert ind["besoins_actifs"] == 1                                 # une seule source de vérité (plus de doublon)
    assert client.get("/api/stage/tour").json()["donnees_fictives"] is True


def test_refus_motives_coherent_avec_les_candidates_sur_toutes_les_paires():
    """Une paire est proposable SI ET SEULEMENT SI aucune raison de refus n'est donnée (mêmes règles, jamais divergentes)."""
    from adaptateurs.club import cycle as cy
    from adaptateurs.club import interventions as iv
    from adaptateurs.club import reseau
    for n in (0, 3, len(stage.ETAPES)):
        w = stage.rejouer_jusqu_a(TAX, n)
        t = w.synchroniser()
        membres = sorted(p.id for p in w.profils() if p.type == "membre_club")
        g = reseau.graphe_actuel(w.memoire, t)
        g.add_nodes_from(membres)
        bes, et = w.magasin.besoins() + cy.besoins_publies(w.memoire, t), reseau.etats_par_paire(w.memoire, t)
        prop = {frozenset((c.a, c.b)) for c in iv.candidates(w.profils(), bes, TAX, g, et)}
        for i, a in enumerate(membres):
            for b in membres[i + 1:]:
                assert (not iv.refus_motives(a, b, w.profils(), bes, TAX, g, et)) == (frozenset((a, b)) in prop), (n, a, b)


def test_contrefactuel_a_la_demande_n_ecrit_rien():
    client.post("/api/stage/aller/8")
    avant = client.get("/api/stage").json()
    r = client.get("/api/stage/sans_relation", params={"a": "s02", "b": "s06"}).json()
    assert r["nature"].startswith("SIMULATION") and r["coupes_noms"] and r["est_un_pont"]
    assert client.get("/api/stage").json() == avant                      # aucun effet de bord
    assert client.get("/api/stage/sans_relation", params={"a": "s02", "b": "s15"}).status_code == 404
    assert client.get("/api/stage/sans_relation", params={"a": "x" * 65, "b": "s06"}).status_code == 422


def test_api_scene_suivant_precedent_fin_reinitialisation():
    v = client.post("/api/stage/reinitialiser").json()
    assert v["etape"] == 0 and "FICTIF" in v["avertissement"]
    for _ in range(3):
        v = client.post("/api/stage/suivant").json()
    assert v["etape"] == 3
    seq = _canon(v["traces"])
    prec = client.post("/api/stage/aller/3").json()                   # rejouer jusqu'à 3 = même chose
    assert _canon(prec["traces"]) == seq
    assert client.post("/api/stage/aller/99").status_code == 422
    client.post(f"/api/stage/aller/{len(stage.ETAPES)}")
    assert client.post("/api/stage/suivant").status_code == 409        # fin : pas d'étape fantôme
    assert client.post("/api/stage/reinitialiser").json()["etape"] == 0
    assert client.get("/api/stage").json()["etape"] == 0               # un rafraîchissement lit l'état serveur


def test_scene_isolee_de_la_demo():
    """La scène n'écrit rien dans la démo principale (et inversement) : deux mondes séparés."""
    client.post("/api/demo/reinitialiser")
    client.post(f"/api/stage/aller/{len(stage.ETAPES)}")
    noms = {m["nom"] for m in client.get("/api/membres").json()}
    assert "Sophie Carron" not in noms and "Markus Heinzmann" not in noms
    assert client.get("/api/relations", headers={"X-Membre": "p00"}).json() == []


def test_scene_ne_montre_aucun_champ_prive():
    v = client.post(f"/api/stage/aller/{len(stage.ETAPES)}").json()
    texte = json.dumps(v, ensure_ascii=False)
    assert "creneaux" not in texte and "mar-matin" not in texte and "@" not in texte


def test_le_graphe_ne_trahit_pas_qui_refuse_les_introductions():
    """La carte dit « ni nommé, ni proposé » : le graphe ne doit pas le laisser deviner (défaut trouvé en red team)."""
    v = client.post(f"/api/stage/aller/{len(stage.ETAPES)}").json()
    assert all(set(n) == {"id", "nom", "x", "y", "present"} for n in v["noeuds"])
    html = (stage.DATA_DIR.parent / "web" / "stage.html").read_text(encoding="utf-8")
    assert ".consent" not in html and ".refus" not in html and '" refus"' not in html


def test_le_graphe_ne_contredit_pas_la_carte_isolee():
    """Défaut trouvé à l'écran : Chantal était dessinée reliée (relations de plus de 90 jours) alors que la carte dit
    « aucune relation ». Le graphe distingue désormais relation actuelle et endormie, avec la même règle que le moteur."""
    v = client.post("/api/stage/aller/9").json()
    seul = v["traces"][8]["faits"]["membre_id"]
    touches = [lien for lien in v["liens"] if seul in (lien["a"], lien["b"])]
    assert touches and not any(lien["actuelle"] for lien in touches)
