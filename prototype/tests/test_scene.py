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
    # A — sans modèle : les règles comprennent mal la phrase libre et s'abstiennent ; rien n'est simulé à la place de l'IA
    assert t[0]["regles"]["decision"] == "S_ABSTENIR" and t[0]["ia"]["etat"] == "NON_CONFIGUREE"
    assert t[0]["retenu"] == "REFORMULATION"
    assert t[0]["reformulation_comprise"][0]["quoi"] == "Développement commercial en Allemagne (obligatoire)"
    cand = t[1]["candidats"]
    assert cand[0]["nom"] == "Markus Heinzmann" and cand[0]["niveau"] == "forte"
    assert cand[0]["dimensions"]["reciprocite"]["etablie"] is True
    assert t[1]["ecartes_par_leur_choix"] == 0                       # Stefan refuse : ni nommé, ni compté (k < 3)
    assert "Kalbermatten" not in json.dumps(t, ensure_ascii=False)
    assert t[2]["coordonnees_avant_accord"] is False and t[2]["coordonnees_apres_accord"] is True
    assert t[2]["etat_relation"] == "RENCONTREE"
    # B — diagnostic, deux plans en conflit, contrefactuel
    assert {"ISOLEMENT", "PONT_FRAGILE", "FRAGMENTATION"} <= {p["code"] for p in t[3]["phenomenes"]}
    assert all("[[" not in p["observation"] for p in t[3]["phenomenes"])
    plans = t[4]["plans"]
    assert len(plans) == 2 and t[4]["budget"] == 1
    reunir = max(plans, key=lambda p: p["plus_grand_groupe"])
    consolider = max(plans, key=lambda p: p["groupe_robuste"])
    assert reunir is not consolider                                   # aucun plan ne gagne sur tout
    assert reunir["plus_grand_groupe"] > consolider["plus_grand_groupe"] and consolider["groupe_robuste"] > reunir["groupe_robuste"]
    assert t[4]["nature"].startswith("SIMULATION")
    assert t[5]["est_un_pont"] and len(t[5]["coupes_de_leur_groupe"]) >= 3 and t[5]["apres"]["groupes"] > t[5]["avant"]["groupes"]
    # C — silence et refus motivés
    assert [r["type"] for p in t[6]["relances"] for r in p["raisons"]] == ["RECIPROCITE_OUVERTE"]
    assert t[6]["silences"]["rien_de_nouveau"] >= 10
    dec = [x["decision"] for x in t[7]["tentatives"]]
    assert dec == ["S_ABSTENIR", "REFUSER", "REFUSER"] and all(x["raisons"] for x in t[7]["tentatives"])
    assert "consentement" in t[7]["tentatives"][1]["raisons"][0] and "aucune aide" in t[7]["tentatives"][2]["raisons"][0]
    assert any("NON MESURÉE" in n["nature"] for n in t[8]["natures"])


def test_scene_a_avec_une_ia_verifiee_n_utilise_que_des_criteres_valides():
    """Chemin IA exercé avec un DOUBLE (aucun modèle réel) : sortie passée par `parser_llm.valider`, extrait inventé retiré."""
    from app.parser_llm import SortieLLM, valider
    texte = stage.Monde(TAX).donnees["sophie"]["besoin_complexe"]
    sortie = SortieLLM.model_validate({"competences": [{"valeur": "export_allemagne", "obligatoire": True, "extrait": "développe déjà des ventes"},
                                                       {"valeur": "traduction", "obligatoire": False, "extrait": "étiquettes doivent être traduites"}],
                                       "langues": [{"valeur": "de", "obligatoire": True, "extrait": "parle allemand"}],
                                       "zones": [], "implantations": [], "exclusions": [], "exclure_concurrents": True,
                                       "termes_hors_catalogue": [], "contexte": ["avant le salon de mars"]})
    double = valider(texte, sortie, TAX), {"analyseur": "double de test", "modele": "aucun", "latence_ms": 0}
    w = stage.rejouer_jusqu_a(TAX, 2, interpreter=lambda _t: double)
    f = w.traces[0]["faits"]
    assert f["retenu"] == "INTERPRETATION_IA_VERIFIEE" and f["ia"]["etat"] == "UTILISEE" and "reformulation" not in f
    assert w.traces[1]["faits"]["candidats"][0]["nom"] == "Markus Heinzmann"


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
    client.post("/api/stage/aller/6")
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


def test_scene_a_ia_en_echec_ou_sans_resultat_ne_casse_pas_la_scene():
    """Red team : (1) modèle en panne → repli visible ; (2) interprétation IA valide mais AUCUN membre prouvé → la scène
    continue par la reformulation (sinon l'étape d'introduction n'aurait personne à présenter)."""
    from app.models import Besoin, Critere
    from app.parser_rules import analyser
    texte = stage.Monde(TAX).donnees["sophie"]["besoin_complexe"]
    panne = analyser(texte, TAX), {"analyseur": "regles (repli)", "erreur": "APITimeoutError", "latence_ms": 30000}
    introuvable = Besoin(texte=texte, criteres=[Critere(type="expertise", valeur="cybersecurite", libelle="Cybersécurité",
                                                         obligatoire=True, extrait="ventes")]), {"analyseur": "double", "modele": "aucun"}
    for double, etat in ((panne, "REPLI"), (introuvable, "UTILISEE")):
        w = stage.rejouer_jusqu_a(TAX, len(stage.ETAPES), interpreter=lambda _t, d=double: d)
        f = w.traces[0]["faits"]
        assert f["ia"]["etat"] == etat and f["retenu"] == "REFORMULATION", f
        assert w.traces[2]["faits"]["coordonnees_apres_accord"] is True
