"""F26 — une offre CONSENTIE qui ne couvre plus sa pièce (horaire déplacé hors de la fenêtre) : la capacité est
DÉGRADÉE, la cause est énoncée (sans personne) et journalisée (sans identifiant), le reçu dit l'état réel.

Scénario exact de l'audit (expérience E1) : Pauline répond à la demande « minibus » (14 places, 13:30–15:00), la
capacité devient ACTIVE ; elle déplace son horaire à 06:00–07:00. Avant le correctif : « il manque une pièce »
(ONE_AWAY), aucune perte enregistrée, reçu « valable, révocable ». Données FICTIVES."""
import json

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo

TAX = charger_taxonomie()
A = "delegation_acheteurs"
HORS_FENETRE = [{"jour": "2026-10-09", "debut": "06:00", "fin": "07:00"}]
CAUSE = "l'offre ne couvre plus la pièce : horaire déclaré hors de la fenêtre (09.10 13:00–18:00)"


def _pauline_active(c):
    ask = next(a for _, a in c.asks_pour(md.PAULINE) if a.startswith(A))
    inst = c.repondre_ask(md.PAULINE, ask, True, {"places": 14})
    assert inst.statut == "ACTIVE"
    return inst.liaisons["minibus"]


def _instance(c):
    return next(i for i in c.capacites.projeter() if i.finalite == A)


def test_horaire_deplace_hors_fenetre_degrade_la_capacite_avec_sa_cause(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    c = Demo(TAX).club
    oid = _pauline_active(c)
    c.modifier_offre(md.PAULINE, oid, {"plages": HORS_FENETRE})

    i = _instance(c)
    assert i.statut == "DEGRADED", (i.statut, i.perdus)
    assert i.perdus == [f"minibus : {CAUSE}"]
    assert i.recomposition and i.recomposition["type"] == "demander"            # ce que le moteur propose, jamais appliqué
    vue = c.vues_capacites.instance(i)
    assert vue["perdus"] == ["transport : ce composant n'est plus disponible — la pièce déclarée ne couvre plus la fenêtre"]

    recu = next(r for r in c.capacites.recus(md.PAULINE) if r["finalite"] == A)
    assert (recu["etat"], recu["revocable"]) == (CAUSE, False)                   # plus « valable »

    faits = [e for e in c.journal.evenements("CONSENTEMENT_ETAT")]
    assert [(e.acteurs, e.donnees["finalite"], e.donnees["emplacement"], e.donnees["vaut"], e.donnees["raison"]) for e in faits] \
        == [([], A, "minibus", False, CAUSE)]
    assert md.PAULINE not in json.dumps(faits[0].donnees) and oid not in json.dumps(faits[0].donnees)   # anonyme

    relu = Demo(TAX, reprendre=True).club                                        # le rejeu dit la même chose
    assert (_instance(relu).statut, _instance(relu).perdus) == ("DEGRADED", [f"minibus : {CAUSE}"])


def test_horaire_retabli_le_consentement_revaut_et_c_est_journalise(tmp_path, monkeypatch):
    """Comme une indisponibilité de profil levée : le consentement n'a pas été retiré, il revaut dès que la pièce
    couvre de nouveau — et ce retour est journalisé aussi."""
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    c = Demo(TAX).club
    oid = _pauline_active(c)
    c.modifier_offre(md.PAULINE, oid, {"plages": HORS_FENETRE})
    c.modifier_offre(md.PAULINE, oid, {"plages": [{"jour": "2026-10-09", "debut": "13:30", "fin": "15:00"}]})
    assert _instance(c).statut == "ACTIVE"
    assert [e.donnees["vaut"] for e in c.journal.evenements("CONSENTEMENT_ETAT")] == [False, True]


def test_un_horaire_change_qui_couvre_encore_ne_touche_a_rien(tmp_path, monkeypatch):
    """Contre-épreuve : déplacer l'horaire DANS la fenêtre ne dégrade rien et n'écrit aucun fait de consentement."""
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    c = Demo(TAX).club
    oid = _pauline_active(c)
    c.modifier_offre(md.PAULINE, oid, {"plages": [{"jour": "2026-10-09", "debut": "13:00", "fin": "16:00"}]})
    assert _instance(c).statut == "ACTIVE" and not c.journal.evenements("CONSENTEMENT_ETAT")
