"""SÉLECTION DES DEMANDES (Ask) et CONCURRENCE (B3.12). Au plus une demande montrée à la fois, le plus fort levier
d'abord ; aucune nouvelle demande pendant 7 jours après une réponse (oui comme non) ; paramétrable. Deux réponses
concurrentes à la même demande : UNE seule liaison, déterministe — la seconde ne trouve plus la demande. FICTIF."""
import dataclasses
import threading
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.capacites import Ask, Instance, choisir_asks
from intelligence.demo import Demo
from intelligence.essai import Creneau

TAX = charger_taxonomie()
CONSOLE = {"X-Pulse-Console": "1"}
A = "delegation_acheteurs"


def _inst(fin: str, levier: int, expire: date) -> Instance:
    c = Creneau(jour=expire, debut="10:00", duree_min=60)
    return Instance(finalite=fin, version=1, titre=fin, fictif=True, statut="ONE_AWAY", distance=1,
                    ask=Ask(id=f"{fin}:1:x", finalite=fin, titre=fin, emplacement="x", libelle="x", nature="objet", concept=None,
                            minimums={}, creneau=c, expire=expire, texte="x", levier=levier))


def test_le_plus_fort_levier_d_abord_puis_l_expiration_puis_un_ordre_stable():
    a, b, c, d = (_inst("a", 1, date(2026, 10, 9)), _inst("b", 3, date(2026, 10, 11)), _inst("c", 1, date(2026, 10, 7)),
                  _inst("d", 3, date(2026, 10, 11)))
    assert [i.finalite for i in choisir_asks([a, b, c, d], 4)] == ["b", "d", "c", "a"]
    assert [i.finalite for i in choisir_asks([a, b, c, d], 1)] == ["b"]
    assert choisir_asks([Instance(finalite="z", version=1, titre="z", fictif=True, statut="PROPOSED", distance=0)], 1) == []


@pytest.fixture
def club():
    return Demo(TAX).club


def test_apres_une_reponse_plus_de_demande_pendant_sept_jours(club):
    ask_id = club.asks_pour(md.PAULINE)[0][1]
    club.repondre_ask(md.PAULINE, ask_id, False)                  # « pas cette fois » : compte aussi
    assert club.asks_pour(md.PAULINE) == []
    assert club.asks_pour(md.MARKUS) != []                        # les autres membres, non
    club.reglages = dataclasses.replace(club.reglages, plafond_jours=0)
    assert [a for _, a in club.asks_pour(md.PAULINE)] == [ask_id]  # paramétrable


def test_lire_ses_demandes_n_ecrit_rien(club):
    avant = club.journal.empreinte()
    for _ in range(3):
        club.asks_pour(md.PAULINE)
        club.vues_capacites.asks(md.MARKUS)
    assert club.journal.empreinte() == avant


def _sessions(c: TestClient) -> dict:
    per = {p["id"]: p for p in c.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    return {pid: {"X-Pulse-Session": per[pid]["session"]} for pid in (md.PAULINE, md.MARKUS)}


@pytest.mark.parametrize("essai", range(10))
def test_deux_reponses_concurrentes_une_seule_liaison(essai):
    client = TestClient(app)
    assert client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE).status_code == 200
    h = _sessions(client)
    ask_id = client.get("/api/pulse/moi/asks", headers=h[md.PAULINE]).json()[0]["id"]
    depart = threading.Barrier(2)
    statuts: dict[str, int] = {}

    def repondre(pid: str) -> None:
        depart.wait()
        statuts[pid] = client.post(f"/api/pulse/moi/asks/{ask_id}/reponse", headers=h[pid],
                                   json={"oui": True, "attributs": {"places": 14}}).status_code

    fils = [threading.Thread(target=repondre, args=(pid,)) for pid in (md.PAULINE, md.MARKUS)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert sorted(statuts.values()) in ([200, 404], [200, 409]), statuts
    reg = next(x for x in client.get("/api/pulse/console/capacites", headers=CONSOLE).json()["capacites"] if x["finalite"] == A)
    assert reg["statut"] == "ACTIVE"
    etat = client.get("/api/pulse/console/essais", headers=CONSOLE).json()      # rien d'autre n'a bougé
    assert etat["essais"] == []
    gagnant = next(pid for pid, s in statuts.items() if s == 200)
    donnees = {pid: client.get("/api/pulse/moi/donnees", headers=h[pid]).json() for pid in h}
    assert len(donnees[gagnant]["consentements"]) == 1
    assert [p for p in h if p != gagnant and donnees[p]["consentements"]] == []  # UNE seule liaison, un seul consentement
