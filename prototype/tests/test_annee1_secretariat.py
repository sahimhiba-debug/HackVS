"""ANNÉE 1 · LOT 4 — La console du secrétariat (domaine) : métiers des entreprises à confirmer, critères du pilote FIXÉS
D'AVANCE (gelés par empreinte), bilan trimestriel exportable, « Le Club cherche » relié à une campagne d'invitation.
Les annonces sous chiffre et l'escalade vers les piliers existent déjà et gardent leurs tests. Données FICTIVES."""
import json

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import secretariat as sec
from intelligence.demo import Demo
from intelligence.erreurs import Invalide

TAX = charger_taxonomie()


@pytest.fixture
def demo(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    csv = tmp_path / "entreprises.csv"
    csv.write_text("nom;metier\nZoéTraiteurSA;restauration/traiteur\nQuirinFidu;Fiduciaire\nXavFidu;fiduciaire\n"
                   "YvoJardins;Paysagiste\nWebWolfSarl;Agence Web\n", encoding="utf-8")
    monkeypatch.setenv("HACKVS_ENTREPRISES_CSV", str(csv))
    return Demo(TAX)


# ------------------------------------------------------------------ métiers à confirmer
def test_les_metiers_non_reconnus_sont_a_confirmer_sans_aucun_nom(demo):
    """Audit des lots 4-5 (I5) : les libellés portés par moins de 3 ENTREPRISES ne sont jamais montrés (ils peuvent
    contenir un nom) — seul leur nombre est dit ; aucun nom d'entreprise ne sort."""
    a = sec.metiers_a_verifier(demo.club)
    brut = json.dumps(a, ensure_ascii=False)
    assert not any(nom in brut for nom in ("ZoéTraiteurSA", "QuirinFidu", "XavFidu", "YvoJardins", "WebWolfSarl"))
    assert a["a_verifier"] == [] and a["rares"] == 3                        # fiduciaire (2), paysagiste (1), agence web (1)
    assert "fiduciaire" not in brut and "agence web" not in brut


def test_confirmer_un_metier_le_compte_dans_le_club_cherche(demo):
    c = demo.club
    sec.confirmer_metier(c, "Fiduciaire", "comptabilite")                   # saisi par le secrétariat (libellé rare)
    assert sec.metiers_a_verifier(c)["rares"] == 2
    from intelligence import club_cherche
    assert club_cherche.entreprises_par_metier(confirmes=sec.confirmations(c))["par_metier"]["comptabilite"] == 2
    with pytest.raises(Invalide):
        sec.confirmer_metier(c, "Paysagiste", "jardinage-inconnu")


# ------------------------------------------------------------------ critères du pilote fixés d'avance
def test_les_criteres_du_pilote_sont_geles_et_toute_retouche_se_voit(demo, tmp_path):
    c = demo.club
    f = tmp_path / "criteres.json"
    f.write_text(json.dumps(sec.criteres_par_defaut(), ensure_ascii=False), encoding="utf-8")
    t = sec.tableau_pilote(c, f)
    assert t["gel"] is None and t["alerte"]                                   # pas encore gelés : dit en clair
    sec.geler_criteres(c, f, par="Secrétariat 1 (fictif)")
    t = sec.tableau_pilote(c, f)
    assert t["gel"] and not t["alerte"] and t["fictif"] is True
    for x in t["criteres"]:
        assert {"id", "libelle", "seuil", "valeur", "atteint"} <= set(x)
        assert x["atteint"] in (True, False, None)                            # None : non mesurable (seuil « < 3 »)
    d = json.loads(f.read_text(encoding="utf-8"))
    d[0]["seuil"] = 1                                                         # on retouche un seuil APRÈS le gel
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    assert "modifiés après le gel" in sec.tableau_pilote(c, f)["alerte"]
    with pytest.raises(Invalide):
        sec.geler_criteres(c, f, par="x")                                     # on ne regèle pas : le premier gel fait foi


# ------------------------------------------------------------------ bilan trimestriel
def test_bilan_trimestriel_markdown_csv_et_html_imprimable(demo):
    c = demo.club
    md, csv, html = sec.bilan_trimestriel(c, "md"), sec.bilan_trimestriel(c, "csv"), sec.bilan_trimestriel(c, "html")
    assert md.startswith("# Bilan — trimestre") and "monde de démonstration" in md
    assert csv.splitlines()[0].startswith("mesure;valeur")
    assert "<table>" in html and "<script" not in html and "monde de démonstration" in html
    with pytest.raises(Invalide):
        sec.bilan_trimestriel(c, "docx")


# ------------------------------------------------------------------ campagne d'invitation
def test_une_campagne_relie_le_club_cherche_a_des_passes_decouverte(demo):
    c = demo.club
    from intelligence import club_cherche
    metier = club_cherche.calculer(c)["metiers"][0]["metier"]
    camp = sec.lancer_campagne(c, metier, 3, base="https://club.example")
    assert len(camp["invitations"]) == 3 and all(i["url"].startswith("https://club.example/decouverte#passe=") for i in camp["invitations"])
    assert {"fr", "de"} <= set(camp["invitations"][0]["texte"])
    liste = sec.campagnes(c)
    assert liste[-1]["id"] == camp["id"] and liste[-1]["emis"] == 3 and liste[-1]["actives"] == 0
    c.decouverte.activer(camp["invitations"][0]["jeton"])
    assert sec.campagnes(c)[-1]["actives"] == "< 3"                          # un invité : jamais le nombre exact
    with pytest.raises(Invalide):
        sec.lancer_campagne(c, metier, 0, base="https://club.example")
    with pytest.raises(Invalide):
        sec.lancer_campagne(c, "metier-inconnu", 2, base="https://club.example")
