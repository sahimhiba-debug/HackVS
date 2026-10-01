"""Le banc métier de comprendre_action (eval/banc_comprendre_action.py) : assez de cas, toutes les catégories demandées,
une notation qui ne gonfle jamais le score (une sortie rejetée, en panne ou inventive n'est jamais « modèle juste »),
et la sortie brute conservée. Fournisseurs FICTIFS : aucun réseau."""
import json

from eval import banc_comprendre_action as b


class Fixe:
    """Répond toujours la même chose (ou lève)."""
    nom, modele = "apertus", "swiss-ai/Apertus-fictif"

    def __init__(self, contenu=None, panne=False):
        self.contenu, self.panne = contenu, panne

    def completer(self, systeme_txt, message, schema):
        if self.panne:
            from intelligence.ia import ErreurFournisseur
            raise ErreurFournisseur("HTTP 503", reessayable=True)
        return self.contenu


def test_le_banc_couvre_les_categories_demandees():
    cas, jour, sha = b.charger()
    assert 20 <= len(cas) <= 30 and len({c["id"] for c in cas}) == len(cas) and len(sha) == 64
    cats = {c["categorie"] for c in cas}
    for attendue in ("simple", "ambigu", "plusieurs contraintes", "hors périmètre", "information absente", "ne pas inventer",
                     "structure précise", "injection"):
        assert attendue in cats, attendue


def test_notation_stricte():
    cas = {"roles": [["voix"]], "jour": "2026-10-08", "heures": ["14:00", "16:00"]}
    ok = {"exigences": [{"role": "voix"}], "fenetre": {"jour": "2026-10-08", "debut": "14:00", "fin": "16:00"}, "manquant": []}
    assert b.conforme(ok, cas)[0]
    assert not b.conforme(ok | {"exigences": [{"role": "voix"}, {"role": "lieu"}]}, cas)[0]          # exigence inventée
    assert not b.conforme(ok | {"fenetre": {"jour": "2026-10-08", "debut": "14:00", "fin": "18:00"}}, cas)[0]
    absent = {"roles": [["voix"]], "jour": None, "heures": None}
    assert not b.conforme(ok, absent)[0]                                                             # date inventée
    abst = {"roles": [[]], "jour": None, "heures": None}
    assert b.conforme({"exigences": [], "fenetre": {}, "manquant": ["Quoi ?"]}, abst)[0]
    assert not b.conforme({"exigences": [], "fenetre": {}, "manquant": []}, abst)[0]                 # ni exigence ni question


def test_une_panne_ou_une_sortie_rejetee_n_est_jamais_un_succes_du_modele():
    r = b.executer(lambda: Fixe(panne=True))
    assert r["totaux"]["modele_justes"] == 0 and r["totaux"]["indisponibles"] == r["totaux"]["cas"]
    assert r["totaux"]["produit_justes"] == r["totaux"]["regles_justes"]                             # le repli seul
    r = b.executer(lambda: Fixe("pas du JSON"))
    assert r["totaux"]["modele_justes"] == 0 and r["totaux"]["rejetees"] == r["totaux"]["cas"]
    assert r["cas"][0]["sortie_brute"] == "pas du JSON"


def test_un_modele_qui_repond_toujours_pareil_n_obtient_pas_un_bon_score():
    sortie = {"objet": "x", "langue_public": "de", "manquant": [], "fenetre": {"jour": "2026-10-08", "debut": "14:00", "fin": "16:00"},
              "exigences": [{"role": "voix", "nature": "competence", "concept": None, "geste": "Parler allemand", "duree_min": 60, "livrable": None}]}
    r = b.executer(lambda: Fixe(json.dumps(sortie)))
    t = r["totaux"]
    assert t["acceptees"] == t["cas"] and t["modele_justes"] <= 3                                  # c01, c18 seulement environ
    texte = b.rapport(r)
    assert f"{t['modele_justes']}/{t['cas']}" in texte and "Cas par cas" in texte
