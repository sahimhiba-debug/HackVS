"""ANNÉE 1 · LOT 11 — cause du budget de lecture dépassé (charge à 500 / 1 000 membres) : « Mes données » reconstruisait
l'index bi-temporel des claims de TOUT le Club à chaque lecture. L'index est désormais gardé tant que le journal n'a
pas changé (même version : même index, l'index étant une fonction pure du journal) ; toute écriture, annulation ou
purge le fait recalculer. Données FICTIVES."""
from intelligence import club_pulse as cp
from intelligence import monde_demo as md
from intelligence.demo import Demo
from app.taxonomy import charger_taxonomie


def _club(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(charger_taxonomie()).club


def test_l_index_n_est_pas_recalcule_sans_ecriture(monkeypatch, tmp_path):
    c = _club(monkeypatch, tmp_path)
    appels = []
    vrai = cp.index_claims
    monkeypatch.setattr(cp, "index_claims", lambda *a: appels.append(1) or vrai(*a))
    for _ in range(5):
        c.vues_capacites.mes_donnees(md.PAULINE)
    assert len(appels) == 1


def test_une_ecriture_fait_recalculer_et_se_voit(monkeypatch, tmp_path):
    c = _club(monkeypatch, tmp_path)
    avant = c.vues_capacites.mes_donnees(md.PAULINE)
    c.banc.publier_offre(md.PAULINE, "objet", "Un minibus de 14 places", 1, c.jour, c.jour, attributs={"places": 14})
    apres = c.vues_capacites.mes_donnees(md.PAULINE)
    assert len(apres["declarations"]) == len(avant["declarations"]) + 1
    assert [x.id for x in c.claims()] == [x.id for x in cp.index_claims(c.journal, c._profils_depart)]   # identique au calcul direct


def test_apres_une_purge_l_index_garde_ne_contient_plus_rien_du_membre(monkeypatch, tmp_path):
    from intelligence import espace_membre as em
    c = _club(monkeypatch, tmp_path)
    c.banc.publier_offre(md.PAULINE, "objet", "Un minibus turquoise de 14 places", 1, c.jour, c.jour, attributs={"places": 14})
    assert any("turquoise" in x.texte for x in c.claims())               # l'index est en cache, avec le texte
    em.effacer_definitivement(c, md.PAULINE)
    assert not any("turquoise" in x.texte for x in c.claims())
    assert not any("turquoise" in x["texte"] for x in c.vues_capacites.mes_donnees(md.MARKUS)["declarations"])


def test_une_reecriture_sans_fait_nouveau_change_la_version(monkeypatch, tmp_path):
    c = _club(monkeypatch, tmp_path)
    v = c.journal.version()
    c.journal.reecrire(lambda e: e)                         # aucune modification, aucun fait ajouté
    assert c.journal.version() != v                                      # une réécriture invalide tout index dérivé
