"""Durcissement H2 — un membre (ou un juré, 90 requêtes/min) qui publie des offres parasites ne doit pas figer la
démonstration.

Mesuré avant le correctif (monde de démonstration, une projection des capacités, sous le verrou du monde) : 0,45 s sans
offre parasite ; 8 s avec 100 ; 27 à 31 s avec 200. Chaque recherche d'offre RELISAIT tout le journal (requête SQLite +
filtrage de chaque fait) : 160 000 lectures du journal pour une seule projection avec 60 offres.

Ce test est déterministe (pas de chronomètre en CI) : il compte les lectures du journal pendant UNE projection, et
exige qu'elles ne croissent pas avec le nombre d'offres. Les durées mesurées sont dans `docs/audit/FINAL_AUDIT.md`.
Données FICTIVES."""
import datetime

from app.taxonomy import charger_taxonomie
from intelligence.demo import Demo
from plateforme.memoire import Memoire

TAX = charger_taxonomie()
AU = datetime.date(2026, 10, 10)


def _lectures(c, monkeypatch) -> tuple[int, int, list]:
    compte = {"sql": 0, "lectures": 0}
    sync, lire = Memoire._synchroniser, Memoire.evenements

    def _sync(self):
        compte["sql"] += 1
        return sync(self)

    def _lire(self, *a, **k):
        compte["lectures"] += 1
        return lire(self, *a, **k)
    monkeypatch.setattr(Memoire, "_synchroniser", _sync)
    monkeypatch.setattr(Memoire, "evenements", _lire)
    res = c.capacites.projeter()
    monkeypatch.setattr(Memoire, "_synchroniser", sync)
    monkeypatch.setattr(Memoire, "evenements", lire)
    return compte["sql"], compte["lectures"], res


def test_les_lectures_du_journal_ne_croissent_pas_avec_les_offres_parasites(monkeypatch):
    c = Demo(TAX).club
    sql0, lectures0, avant = _lectures(c, monkeypatch)
    for i in range(60):
        c.banc.publier_offre("s14", "objet", f"Offre parasite fictive {i}", 1, c.jour, AU)
    sql, lectures, apres = _lectures(c, monkeypatch)
    assert sql <= sql0 * 1.1 + 2, (sql0, sql)                    # avant : 160 155 requêtes SQLite pour 60 offres
    assert lectures <= lectures0 * 1.1 + 10, (lectures0, lectures)
    # contre-épreuve de sens : les offres parasites ne changent RIEN à ce que le Club peut faire
    assert [(i.finalite, i.statut, i.liaisons) for i in apres] == [(i.finalite, i.statut, i.liaisons) for i in avant]


def test_une_ecriture_pendant_une_lecture_figee_est_vue(tmp_path):
    """La lecture figée ne doit jamais servir un journal périmé : une écriture pendant le bloc est relue."""
    from plateforme.memoire import Evt, Statut
    m = Memoire(str(tmp_path / "j.db"))
    m.ajouter(Evt(type="A", le=datetime.date(2026, 10, 1), donnees={"x": 1}, statut=Statut.OBSERVE))
    with m.figee():
        assert len(m.evenements()) == 1
        m.ajouter(Evt(type="A", le=datetime.date(2026, 10, 1), donnees={"x": 2}, statut=Statut.OBSERVE))
        assert len(m.evenements()) == 2
    assert len(m.evenements()) == 2


def test_une_offre_annulee_ne_survit_pas_dans_l_index():
    """L'index des offres ne doit jamais servir un fait ANNULÉ — même si SQLite réutilise son numéro de séquence pour
    le fait suivant (cas réel : AUTOINCREMENT est annulé avec la transaction)."""
    import pytest
    from intelligence.erreurs import Introuvable
    c = Demo(TAX).club
    b = c.banc
    nb = len(b.offres())
    with pytest.raises(RuntimeError):
        with b.m.transaction():
            x = b.publier_offre("s14", "objet", "Offre fictive annulée", 1, c.jour, AU)
            assert b.offre(x).quoi == "Offre fictive annulée"          # visible DANS la transaction
            raise RuntimeError("panne au milieu de la commande")
    y = b.publier_offre("s14", "objet", "Offre fictive suivante", 1, c.jour, AU)
    with pytest.raises(Introuvable):
        b.offre(x)
    assert [o.quoi for o in b.offres()].count("Offre fictive annulée") == 0
    assert b.offre(y).quoi == "Offre fictive suivante" and len(b.offres()) == nb + 1
