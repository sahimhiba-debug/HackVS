"""F27 — l'état en mémoire de la façade ne diverge jamais du journal, même quand une transaction échoue APRÈS avoir
écrit. Avant : `_enregistrer` appliquait le profil en mémoire tout de suite ; l'exception annulait le journal mais pas
la mémoire (expérience E3) ; et la projection mise en cache par NOMBRE d'événements pouvait servir, après l'annulation,
un état calculé sur des faits annulés. Données FICTIVES."""
import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo

TAX = charger_taxonomie()


class Panne(RuntimeError):
    pass


def test_echec_injecte_apres_l_ecriture_du_profil_memoire_et_journal_d_accord(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    c = Demo(TAX).club
    avant, n = c.empreinte_etat(), len(c.journal.evenements())

    def panne(*a, **k):
        raise Panne("panne simulée après l'écriture du profil")
    monkeypatch.setattr(c.banc, "revoir_membre", panne)
    with pytest.raises(Panne):
        c.modifier_profil(md.LEA, disponible=False, visibilite={"capacites": "PRIVE"})

    assert len(c.journal.evenements()) == n                                  # le journal est annulé…
    assert c.profil(md.LEA).disponible is True and c.preferences.get(md.LEA) is None   # …la mémoire aussi
    assert c.empreinte_etat() == avant
    assert Demo(TAX, reprendre=True).club.empreinte_etat() == avant          # et le rejeu dit la même chose


def test_une_projection_calculee_dans_une_transaction_annulee_n_est_jamais_resservie(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    c = Demo(TAX).club
    accord = next(e for e in c.banc.consentements_finalite("delegation_acheteurs") if e.type == "ACCORD")
    with pytest.raises(Panne):
        with c.journal.transaction():
            c.banc._ecrire("RETRAIT", [accord.acteurs[0]], finalite="delegation_acheteurs",
                           emplacement=accord.donnees["emplacement"], offre=accord.donnees["offre"])
            c.projection_capacites()                                         # mise en cache, sur un fait qui sera annulé
            raise Panne("échec après la lecture")
    c.basculer_ia(False)                                                     # UN autre fait : même nombre d'événements
    assert [i.model_dump() for i in c.projection_capacites()] == [i.model_dump() for i in c.capacites.projeter()]
