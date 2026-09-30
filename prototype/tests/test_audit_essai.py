"""Régressions de l'audit indépendant (constats P1 et P2), reproduites sur le domaine, le journal SQLite réel et l'API.
P1 — une modification MATÉRIELLE des conditions d'une offre (texte libre) laissait l'essai AUTORISE et lançable.
P2 — la couverture ne vérifiait que le premier geste d'une personne : retirer l'offre de son second geste ne bloquait rien.
Ces tests échouent sur le code d'avant la correction (vérifié : voir docs/audit/club-pulse-pivot/PREUVES.md)."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from intelligence.erreurs import Conflit
from intelligence.essai import CONDITIONS_A_RECONFIRMER, Etape, Protocole
from plateforme.memoire import Memoire
from tests.test_essai import J, LEA, MARKUS, PAULINE, SOPHIE, Monde

PRESENCE = Etape(id="e1", nature="lieu", geste="Être présent devant le présentoir du stand", duree_min=15)


def _essai_presence(m: Monde) -> tuple[str, int, str]:
    o = m.b.publier_offre(PAULINE, "lieu", "Un présentoir éclairé sur mon stand", 1, J, J + timedelta(days=30), duree_max_min=20,
                          conditions="sur place, stand B12")
    p = Protocole(question="Le présentoir attire-t-il ?", critere="combien s'arrêtent", echeance=J + timedelta(days=5), etapes=[PRESENCE])
    eid = m.b.brouillon(SOPHIE, p)
    v = m.b.proposer(SOPHIE, eid, 0, {"e1": o})
    m.b.decider(PAULINE, eid, v, True)
    assert m.b.etat(eid) == "AUTORISE"
    return eid, v, o


def test_p1_conditions_changees_l_accord_ne_couvre_plus_et_le_lancement_est_refuse(tmp_path):
    m = Monde(Memoire(str(tmp_path / "journal.db")))                          # le journal SQLite réel, sur disque
    eid, v, o = _essai_presence(m)
    m.b.modifier_offre(PAULINE, o, conditions="Uniquement en visioconférence, présence sur le stand impossible")
    assert m.b.etat(eid) == "A_ADAPTER"
    assert m.b.couverture(eid)[PAULINE].startswith("les conditions de son offre ont changé depuis son accord")
    with pytest.raises(Conflit):
        m.b.lancer(SOPHIE, eid, m.b.version(eid))
    assert m.b.etat(eid) != "EN_COURS"


def test_p1_revision_explicite_puis_nouvelle_confirmation():
    m = Monde()
    eid, v, o = _essai_presence(m)
    m.b.modifier_offre(PAULINE, o, conditions="sur place, mais seulement jusqu'à 16 h")
    alt = next(a for a in m.b.alternatives(eid) if a["type"] == "accepter_conditions")   # le porteur révise, explicitement
    m.b.choisir_alternative(SOPHIE, eid, m.b.version(eid), alt["id"])
    assert m.b.etat(eid) == "PROPOSE" and m.b.couverture(eid)[PAULINE] == CONDITIONS_A_RECONFIRMER
    with pytest.raises(Conflit):
        m.b.lancer(SOPHIE, eid, m.b.version(eid))                             # sans la nouvelle confirmation : non
    m.b.decider(PAULINE, eid, m.b.version(eid), True)
    assert m.b.etat(eid) == "AUTORISE"


def test_p1_un_changement_numerique_encore_couvrant_ne_redemande_rien():
    """Durée, dates et capacité se vérifient par un nombre : tant qu'elles couvrent encore, l'accord tient (prouvé)."""
    m = Monde()
    eid, v, o = _essai_presence(m)
    m.b.modifier_offre(PAULINE, o, duree_max_min=30, au=J + timedelta(days=20))
    assert m.b.etat(eid) == "AUTORISE"


def test_p1_par_l_api_la_modification_des_conditions_bloque_le_lancement():
    from app.main import app
    from intelligence.club_synthetique import AUJOURD_HUI
    c = TestClient(app)                                                      # console : cette machine seulement
    console = {"X-Pulse-Console": "1"}
    assert c.post("/api/pulse/demo/reinitialiser", headers=console).status_code == 200
    per = {p["id"]: p["session"] for p in c.get("/api/pulse/console/personas", headers=console).json()}
    s, p = {"X-Pulse-Session": per[LEA]}, {"X-Pulse-Session": per[PAULINE]}      # Léa porte, Pauline prête son lieu
    e = c.post("/api/pulse/moi/essais", headers=s, json={"question": "Le présentoir attire-t-il ?", "critere": "combien s'arrêtent",
                                                           "echeance": (AUJOURD_HUI + timedelta(days=5)).isoformat(),   # horloge du monde servi
                                                           "etapes": [{"nature": "lieu", "geste": PRESENCE.geste, "duree_min": 10}]}).json()
    v = c.post(f"/api/pulse/moi/essais/{e['id']}/publier", headers=s, json={"version": e["version"]}).json()["version"]
    assert c.post(f"/api/pulse/moi/essais/{e['id']}/decision", headers=p, json={"version": v, "accepte": True}).status_code == 200
    oid = next(o["id"] for o in c.get("/api/pulse/moi/souvenirs", headers=p).json()["offres"] if o["nature"] == "un lieu")
    r = c.patch(f"/api/pulse/moi/offres/{oid}", headers=p, json={"conditions": "Uniquement en visioconférence, présence sur le stand impossible"})
    assert r.status_code == 200 and e["id"] in r.json()["essais_a_adapter"]
    assert c.post(f"/api/pulse/moi/essais/{e['id']}/lancer", headers=s, json={"version": v}).status_code == 409
    assert c.get(f"/api/pulse/moi/essais/{e['id']}", headers=s).json()["etat"] == "A_ADAPTER"


def test_p2_chaque_geste_d_une_meme_personne_est_verifie():
    m = Monde()
    stand = m.b.publier_offre(MARKUS, "lieu", "Mon stand pour 15 minutes", 1, J, J + timedelta(days=30), duree_max_min=20)
    p = Protocole(question="Étiquette comprise ?", critere="combien comprennent", echeance=J + timedelta(days=5),
                  etapes=[Etape(id="e1", nature="temps", geste="Regarder l'étiquette", duree_min=10, contributeur=MARKUS, offre_id=m.markus),
                          Etape(id="e2", nature="lieu", geste="Prêter un stand", duree_min=15, contributeur=MARKUS, offre_id=stand)])
    eid = m.b.brouillon(SOPHIE, p)
    v = m.b.proposer(SOPHIE, eid, 0)
    m.b.decider(MARKUS, eid, v, True)
    assert m.b.etat(eid) == "AUTORISE"
    m.b.retirer_offre(MARKUS, stand)                                          # la SECONDE offre seulement
    assert m.b.etat(eid) != "AUTORISE" and m.b.raisons_gestes(eid) == {"e1": None, "e2": "son offre ne couvre plus ce geste : offre retirée"}
    with pytest.raises(Conflit):
        m.b.lancer(SOPHIE, eid, m.b.version(eid))
    assert all(a["etape"] == "e2" for a in m.b.alternatives(eid))            # seul le geste touché est à adapter
