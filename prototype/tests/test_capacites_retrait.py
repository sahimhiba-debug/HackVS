"""CRITÈRE DE SORTIE DE LA PHASE 2 : retrait → dégradation → recomposition vérifiable, retrait ANONYME.

Par l'API, sessions réelles : Pauline comble la capacité (ACTIVE) puis retire son consentement en un geste ; à la
projection suivante la capacité est DEGRADED, la recomposition est calculée (une nouvelle demande), elle n'est jamais
adressée à Pauline, et AUCUN écran ne dit qui s'est retiré ni pourquoi. Une autre personne répond : ACTIVE de nouveau,
avec une autre pièce. Puis : recomposition par une pièce qui existe déjà (son auteur consent), et « aucune solution
sûre » dite honnêtement. Reçu de consentement et « Mes données ». Données FICTIVES."""
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import NICOLAS, Demo
from intelligence.erreurs import Conflit, Introuvable
from intelligence.essai import Plage

TAX = charger_taxonomie()
CONSOLE = {"X-Pulse-Console": "1"}
client = TestClient(app)
A = "delegation_acheteurs"
NOMS_PAULINE = ("Pauline", "Darbellay")


def _session(pid):
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    return {"X-Pulse-Session": per[pid]["session"]}


def _registre():
    return next(x for x in client.get("/api/pulse/console/capacites", headers=CONSOLE).json()["capacites"] if x["finalite"] == A)


def _ask(h):
    return next((x for x in client.get("/api/pulse/moi/asks", headers=h).json() if x["id"].startswith(A)), None)


def test_retrait_degradation_recomposition_anonyme_de_bout_en_bout():
    assert client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE).status_code == 200
    pauline, markus = _session(md.PAULINE), _session(md.MARKUS)
    ask = _ask(pauline)
    assert client.post(f"/api/pulse/moi/asks/{ask['id']}/reponse", headers=pauline, json={"oui": True, "attributs": {"places": 14}}).status_code == 200
    assert _registre()["statut"] == "ACTIVE"

    recus = client.get("/api/pulse/moi/consentements", headers=pauline).json()
    assert [(r["finalite"], r["piece"], r["jusqu_au"], r["etat"], r["revocable"]) for r in recus] == [
        (A, "Un minibus de 12 places ou plus", "2026-10-09", "valable", True)]

    # ---- le retrait, en un geste
    r = client.post(f"/api/pulse/moi/capacites/{A}/retrait", headers=pauline)
    assert r.status_code == 200
    reg = _registre()
    assert reg["statut"] == "DEGRADED"
    assert reg["perdus"] == ["transport : ce composant n'est plus disponible"]
    assert reg["recomposition"]["texte"] == ("Il manque de nouveau : Un minibus de 12 places ou plus. Une demande est adressée "
                                             "aux membres qui peuvent la fournir.")
    assert reg["date"] and reg["jour"] == "2026-10-09"                      # l'écran dit sa date et le jour de la scène
    # ---- anonyme : aucun écran commun, aucun autre membre ne lit qui, ni « retiré »
    public = json.dumps([client.get("/api/pulse/console/capacites", headers=CONSOLE).json(),
                         client.get("/api/pulse/moi/asks", headers=markus).json()], ensure_ascii=False)
    for x in (*NOMS_PAULINE, md.PAULINE, "retir", "Minibus de 14"):
        assert x not in public, x
    # ---- la recomposition ne revient jamais vers la personne qui s'est retirée
    assert _ask(pauline) is None
    assert client.get("/api/pulse/moi/consentements", headers=pauline).json()[0]["etat"] == "consentement retiré"
    # ---- une autre personne répond : la capacité est de nouveau active, avec une autre pièce
    nouvelle = _ask(markus)
    assert nouvelle is not None
    assert client.post(f"/api/pulse/moi/asks/{nouvelle['id']}/reponse", headers=markus,
                       json={"oui": True, "attributs": {"places": 16}}).status_code == 200
    assert _registre()["statut"] == "ACTIVE"


@pytest.fixture
def club():
    return Demo(TAX).club


def _active(c):
    ask = c.capacites.instance(c.capacites.patron(A)).ask
    c.repondre_ask(md.PAULINE, ask.id, True, {"places": 14})
    assert c.capacites.instance(c.capacites.patron(A)).statut == "ACTIVE"


def test_recomposition_par_une_piece_qui_existe_deja_puis_consentement_de_son_auteur(club):
    _active(club)
    club.banc.publier_offre(md.MARKUS, "objet", "Bus de 20 places", 1, club.jour, club.jour + timedelta(days=3),
                            attributs={"places": 20}, plages=[Plage(jour=md.JOUR_SCENE + timedelta(days=1), debut="13:00", fin="18:00")])
    inst = club.retirer_consentement(md.PAULINE, A)
    assert inst.statut == "DEGRADED" and inst.distance == 0
    assert inst.recomposition["type"] == "consentir" and inst.recomposition["pieces"] == ["minibus"]
    assert club.banc.offre(inst.liaisons["minibus"]).auteur == md.MARKUS            # jamais l'offre de Pauline
    assert club.consentir_capacite(md.MARKUS, A).statut == "ACTIVE"             # la décision humaine


def test_sans_solution_sure_la_cause_ce_qu_on_sait_ce_qu_on_ignore_ce_qui_debloquerait(club):
    _active(club)
    club.retirer_consentement(md.ANNA, A)
    inst = club.retirer_consentement(NICOLAS, A)
    assert inst.statut == "DEGRADED" and inst.distance is None and inst.recomposition is None
    s = inst.sans_solution
    assert s["cause"] == ["lieu : ce composant n'est plus disponible", "voix : ce composant n'est plus disponible"]
    assert s["sait"] == ["Un minibus de 12 places ou plus : au moins une pièce déclarée couvre la fenêtre"]
    assert s["debloquerait"] == ["Une salle de 15 places ou plus le 09.10 entre 13:00 et 18:00",
                                 "Une interprétation français–allemand le 09.10 entre 13:00 et 18:00"]
    assert "personne ne l'a déclaré" in s["ignore"][0]


def test_retrait_idempotence_et_refus(club):
    with pytest.raises(Introuvable):
        club.retirer_consentement(md.PAULINE, A)                                # rien à retirer
    _active(club)
    club.retirer_consentement(md.PAULINE, A)
    with pytest.raises(Introuvable):
        club.retirer_consentement(md.PAULINE, A)                                # déjà retiré : rien de plus
    with pytest.raises(Conflit):
        club.banc.retirer_finalite(md.PAULINE, A, "minibus")
    with pytest.raises(Introuvable):
        club.consentir_capacite(md.PAULINE, A)                                  # sa pièce n'est plus liée à cette finalité


def test_mes_donnees_dit_quoi_pourquoi_jusqu_a_quand(club):
    _active(club)
    d = club.vues_capacites.mes_donnees(md.PAULINE)
    minibus = next(x for x in d["declarations"] if x["texte"].startswith("Un minibus"))
    assert minibus["type"] == "ressource" and minibus["valable_jusqu_au"] == "2026-10-09" and minibus["etat"] == "valable"
    assert all(x["pourquoi"] for x in d["declarations"])
    assert [r["finalite"] for r in d["consentements"]] == [A]
    assert d["reponses_aux_demandes"] == [{"le": club.jour.isoformat(), "reponse": "oui"}]
    assert "coffre" in d["hors_du_journal"]
    texte = json.dumps(d, ensure_ascii=False)
    for x in ("Anna", "Zufferey", "Nicolas", "Roduit", NICOLAS, md.ANNA):         # rien sur les AUTRES membres
        assert x not in texte
