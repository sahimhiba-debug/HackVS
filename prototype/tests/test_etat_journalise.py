"""TOUT l'état métier se reconstruit depuis le journal : profils (ce que le membre déclare), besoins publiés, préférences
de visibilité et horloge de démonstration — pas seulement les essais. Défauts trouvés à l'inspection du pivot
(docs/audit/PIVOT_INSPECTION.md, écarts 1 et 2) : ces faits vivaient en mémoire du processus, un redémarrage les
perdait, et le serveur VIDAIT le journal durable à son démarrage. Exceptions assumées (hors journal métier, par
conception) : le coffre d'identités, les sessions et les notes privées. Données FICTIVES."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pulse_api import creer_routeur
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.club_pulse import ClubPulse

TAX = charger_taxonomie()
CONSOLE = {"X-Pulse-Console": "1"}


def _vivre(c: ClubPulse) -> None:
    c.modifier_profil(md.LEA, retirer_capacite="traduction", disponible=False, visibilite={"capacites": "PRIVE"})
    c.onboarding(md.SOPHIE, aide=[{"texte": "tisanes de plantes alpines bio", "concept": "boissons"}],
                 cherche=[{"texte": "Trouver un distributeur en Allemagne", "concept": "export_allemagne"}], visible=True)
    c.confirmer_demande(md.SOPHIE, c.demander(md.SOPHIE, "Je cherche quelqu'un pour traduire nos fiches produit en allemand.")["proposition"])
    c.avancer(3)


def test_profils_besoins_preferences_et_horloge_survivent_au_redemarrage(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    c = ClubPulse(TAX)
    _vivre(c)
    relu = ClubPulse(TAX)                                        # même journal, nouvelle instance (redémarrage)
    assert relu.jour == c.jour
    for pid in (md.LEA, md.SOPHIE):
        assert relu.profil(pid).model_dump(exclude={"entreprise"}) == c.profil(pid).model_dump(exclude={"entreprise"})
    assert relu.profil(md.LEA).disponible is False and not any(o.concept == "traduction" for o in relu.profil(md.LEA).offre)
    assert relu.preferences == c.preferences == {md.LEA: {"capacites": "PRIVE"}}
    assert [(b.auteur, b.texte) for b in relu.r.besoins] == [(b.auteur, b.texte) for b in c.r.besoins]


def test_le_serveur_redemarre_sans_vider_le_journal(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    avant = FastAPI()
    avant.include_router(creer_routeur(TAX))
    a = TestClient(avant)
    assert a.post("/api/pulse/demo/aller/4", headers=CONSOLE).status_code == 200            # accords réunis
    essais = a.get("/api/pulse/console/essais", headers=CONSOLE).json()["essais"]
    assert [x["etat"] for x in essais] == ["AUTORISE"]
    apres = FastAPI()                                           # redémarrage du serveur sur le même fichier
    apres.include_router(creer_routeur(TAX))
    b = TestClient(apres)
    assert b.get("/api/pulse/console/essais", headers=CONSOLE).json()["essais"] == essais


def test_meme_journal_meme_empreinte_de_l_etat_complet(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    c = ClubPulse(TAX)
    vierge = c.empreinte_etat()
    _vivre(c)
    e = c.empreinte_etat()
    assert e != vierge                                          # non vacueuse : profils, besoins, horloge y entrent
    assert ClubPulse(TAX).empreinte_etat() == e                 # rejeu du même journal → même état, profils et horloge compris
    c.avancer(1)
    assert c.empreinte_etat() != e                              # l'horloge compte


def test_un_journal_d_un_autre_monde_est_refuse(tmp_path, monkeypatch):
    import sqlite3

    import pytest
    chemin = tmp_path / "journal.db"
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(chemin))
    ClubPulse(TAX)
    with sqlite3.connect(chemin) as db:                        # un semis falsifié : ce journal n'est pas celui de ce monde
        db.execute("""UPDATE evenements SET donnees = replace(donnees, '"empreinte":"', '"empreinte":"x') """
                   """WHERE donnees LIKE '%"SEMIS"%'""")
    with pytest.raises(ValueError, match="autre monde"):
        ClubPulse(TAX)
