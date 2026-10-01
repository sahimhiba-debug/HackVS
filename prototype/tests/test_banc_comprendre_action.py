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


# ------------------------------------------------------------------ banc multi-fournisseurs (dry-run, aucun réseau)
def test_dry_run_chaque_factice_donne_les_mesures_attendues():
    from eval.fournisseurs_factices import FACTICES
    t = {nom: b.executer(f, fournisseur=nom)["totaux"] for nom, f in FACTICES.items()}
    n = 26
    # un modèle « parfait » plafonne à 20/26 ici (c13–c17 et c19 attendent une abstention, impossible sous le schéma)
    assert t["valide"]["modele_justes"] == 20 and t["valide"]["acceptees_fausses"] == 0 and t["valide"]["json_valides"] == n
    assert t["json-invalide"]["json_valides"] == 0 and t["json-invalide"]["acceptees"] == 0 and t["json-invalide"]["replis"] == n
    assert t["hors-schema"]["json_valides"] == n and t["hors-schema"]["schema_valides"] == 0 and t["hors-schema"]["acceptees"] == 0
    assert t["incoherent"]["schema_valides"] == n and t["incoherent"]["acceptees"] == 0                 # schéma OK, métier refusé
    for panne in ("delai", "reseau"):
        assert t[panne]["indisponibles"] == n and t[panne]["replis"] == n and t[panne]["latence_ms"] is None
    for v in t.values():                                                                        # le repli garde le produit juste
        assert v["produit_justes"] >= v["regles_justes"] - 0


def test_chaque_cas_garde_les_mesures_demandees():
    from eval.fournisseurs_factices import FACTICES
    x = b.executer(FACTICES["hors-schema"], fournisseur="hors-schema")["cas"][0]
    for k in ("fournisseur", "modele", "id", "sortie_brute", "json_valide", "schema_valide", "erreur_schema", "validation_metier",
              "cause_rejet", "latence_ms", "repli", "contrainte", "attendu"):
        assert k in x, k
    assert x["json_valide"] is True and x["schema_valide"] is False and "role" in x["erreur_schema"] and x["repli"] is True


def test_les_26_cas_de_reference_sont_inchanges():
    """Le banc de référence est figé : toute modification des cas change l'empreinte et doit devenir une NOUVELLE version."""
    cas, _, sha = b.charger()
    assert len(cas) == 26 and sha.startswith("34bfcc37bf2f8e2f")


def test_comparaison_des_comptes_sans_classement(tmp_path):
    from eval import comparer_bancs as cmp
    from eval.fournisseurs_factices import FACTICES
    for nom in ("valide", "incoherent", "delai"):
        r = b.executer(FACTICES[nom], fournisseur=nom)
        (tmp_path / f"{nom}.json").write_text(json.dumps(r, ensure_ascii=False))
    texte = cmp.comparer(cmp.charger(tmp_path))
    assert "| Fournisseur | Modèle |" in texte and "| p50 | p95 |" in texte and texte.count("| c") >= 26
    assert "factice-valide" in texte and "rejeté : geste ou durée hors bornes" in texte and "indisponible" in texte
    for mot in ("gagnant", "meilleur", "score global", "classement :"):
        assert mot not in texte.lower()


def test_la_comparaison_refuse_des_cas_differents(tmp_path):
    import pytest as _p

    from eval import comparer_bancs as cmp
    from eval.fournisseurs_factices import FauxValide
    r1 = b.executer(FauxValide, fournisseur="a")
    r2 = json.loads(json.dumps(r1))
    r2["contexte"]["cas_sha256"] = "0" * 64
    (tmp_path / "a.json").write_text(json.dumps(r1))
    (tmp_path / "b.json").write_text(json.dumps(r2))
    with _p.raises(SystemExit, match="REFUS"):
        cmp.comparer(cmp.charger(tmp_path))


def test_aucune_cle_dans_un_rapport(monkeypatch, tmp_path):
    from eval.fournisseurs_factices import FauxValide
    for k in b.SECRETS:
        monkeypatch.setenv(k, f"cle-test-{k.lower()}-" + "s" * 20)
    b._ecrire(b.executer(FauxValide, fournisseur="valide"), tmp_path / "valide.md")
    contenu = (tmp_path / "valide.md").read_text() + (tmp_path / "valide.json").read_text()
    assert not [k for k in b.SECRETS if __import__("os").environ[k] in contenu]
