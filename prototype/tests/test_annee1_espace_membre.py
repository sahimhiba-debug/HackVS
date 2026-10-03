"""ANNÉE 1 · LOT 3 — L'espace membre : mode pause, préférences (langue, région, canaux), mes demandes envoyées, export
de mes données, purge réelle à l'effacement. Le reste de l'espace (accueil guidé, déclarer ce qu'on offre, reçus,
clôture, solde « reçus / donnés ») existe déjà et garde ses tests. Données FICTIVES."""
import json
from datetime import timedelta

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import espace_membre as em
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.erreurs import Invalide

TAX = charger_taxonomie()


@pytest.fixture
def demo(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(TAX)


def test_mode_pause_on_ne_recoit_plus_rien_jusqu_a_la_date(demo):
    c = demo.club
    pid = md.PAULINE
    assert c._membre_peut(pid, None)
    fin = c.jour + timedelta(days=10)
    em.mettre_en_pause(c, pid, fin)
    assert em.etat_pause(c, pid) == {"en_pause": True, "jusqu_au": fin.isoformat()}
    assert not c._membre_peut(pid, None)                     # plus sollicitable : aucune demande ne lui parvient
    c.avancer(11)
    assert c._membre_peut(pid, None) and not em.etat_pause(c, pid)["en_pause"]   # la pause finit seule


def test_reprendre_avant_la_date(demo):
    c = demo.club
    em.mettre_en_pause(c, md.PAULINE, c.jour + timedelta(days=30))
    em.reprendre(c, md.PAULINE)
    assert c._membre_peut(md.PAULINE, None)


def test_pause_bornee_et_dans_le_futur(demo):
    c = demo.club
    with pytest.raises(Invalide):
        em.mettre_en_pause(c, md.PAULINE, c.jour - timedelta(days=1))
    with pytest.raises(Invalide):
        em.mettre_en_pause(c, md.PAULINE, c.jour + timedelta(days=200))   # au plus six mois


def test_la_pause_survit_a_un_redemarrage(demo, monkeypatch):
    c = demo.club
    em.mettre_en_pause(c, md.PAULINE, c.jour + timedelta(days=5))
    repris = Demo(TAX, reprendre=True).club
    assert em.etat_pause(repris, md.PAULINE)["en_pause"] is True and not repris._membre_peut(md.PAULINE, None)


def test_preferences_langue_region_canaux(demo):
    c = demo.club
    em.regler_preferences(c, md.PAULINE, langue="de", region="Haute-Savoie", canaux=["app", "email"])
    assert em.preferences(c, md.PAULINE) == {"langue": "de", "region": "Haute-Savoie", "canaux": ["app", "email"]}
    with pytest.raises(Invalide):
        em.regler_preferences(c, md.PAULINE, langue="xx", region="", canaux=["app"])
    with pytest.raises(Invalide):
        em.regler_preferences(c, md.PAULINE, langue="fr", region="", canaux=["pigeon"])
    with pytest.raises(Invalide):
        em.regler_preferences(c, md.PAULINE, langue="fr", region="", canaux=[])   # au moins un canal : sinon, la pause


def test_mes_demandes_envoyees(demo):
    c = demo.club
    p = c.demander(md.PAULINE, "Je cherche une salle pour 20 personnes à Martigny, jeudi soir.")
    c.confirmer_demande(md.PAULINE, p["proposition"])
    mes = em.mes_demandes(c, md.PAULINE)
    assert any("salle pour 20 personnes" in d["texte"] for d in mes)
    assert all("salle pour 20 personnes" not in d["texte"] for d in em.mes_demandes(c, md.MARKUS))


def test_export_de_mes_donnees_et_rien_d_autre(demo):
    c = demo.club
    em.regler_preferences(c, md.PAULINE, langue="fr", region="Valais", canaux=["app"])
    x = em.exporter(c, md.PAULINE)
    assert set(x) >= {"format", "membre", "genere_le", "mes_donnees", "preferences", "pause", "demandes", "reciprocite"}
    texte = json.dumps(x, ensure_ascii=False)
    autre = c.coffre.identite(md.MARKUS)
    assert autre is None or autre.nom not in texte                         # rien d'un autre membre


def test_purge_reelle_plus_aucun_texte_du_membre_dans_le_journal(demo):
    c = demo.club
    phrase = "Je cherche un traducteur pour un salon à Bâle, en novembre."
    p = c.demander(md.PAULINE, phrase)
    c.confirmer_demande(md.PAULINE, p["proposition"])
    textes_autres_avant = [e.model_dump_json() for e in c.journal.evenements() if md.PAULINE not in e.acteurs]
    assert any(phrase in e.model_dump_json() for e in c.journal.evenements())
    bilan = em.effacer_definitivement(c, md.PAULINE)
    assert bilan["faits_purges"] >= 1
    assert not any(phrase in e.model_dump_json() for e in c.journal.evenements())
    restants = [e.model_dump_json() for e in c.journal.evenements() if md.PAULINE not in e.acteurs and e.type != "PURGE"]
    assert set(textes_autres_avant) <= set(restants)                      # les autres membres : intacts
    assert c.journal.evenements("PURGE")[-1].donnees == {"faits": bilan["faits_purges"]}   # la purge est un fait, sans contenu


def test_apres_purge_le_club_redemarre_et_le_membre_n_existe_plus(demo):
    c = demo.club
    em.effacer_definitivement(c, md.PAULINE)
    repris = Demo(TAX, reprendre=True).club
    assert repris.coffre.identite(md.PAULINE) is None
    assert not repris.profil(md.PAULINE).offre
