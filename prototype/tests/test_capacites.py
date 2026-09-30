"""REGISTRE DES CAPACITÉS — Phase 1. Scénario A de bout en bout, SANS modèle de langage : une capacité à UNE pièce →
une demande minimale (Ask) adressée à une catégorie → une réponse sur le téléphone d'un membre → la capacité devient
ACTIVE (toutes les pièces déclarées, valables à cette date, consenties pour cette finalité). Puis les invariants de la
projection : jamais stockée, recalculée à l'identique ; une claim expirée reste dans l'index ; un consentement ne suit
ni d'autres conditions ni une autre version du patron. Données FICTIVES."""
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.capacites import DOSSIER_PATRONS, Patron, charger_patrons
from intelligence.demo import NICOLAS, Demo
from intelligence.erreurs import Conflit, Introuvable, Invalide

TAX = charger_taxonomie()
CONSOLE = {"X-Pulse-Console": "1"}
client = TestClient(app)
ASK_A = "delegation_acheteurs"


def _capacite(reg: dict, finalite: str) -> dict | None:
    return next((x for x in reg["capacites"] if x["finalite"] == finalite), None)


def _session(pid: str) -> dict:
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    return {"X-Pulse-Session": per[pid]["session"]}


# ---------------------------------------------------------------------- scénario A, par l'API, sans IA
def test_scenario_a_une_piece_manquante_une_ask_une_reponse_une_capacite_active():
    assert client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE).status_code == 200
    avant = client.get("/api/pulse/console/capacites", headers=CONSOLE).json()
    a = _capacite(avant, ASK_A)
    assert a["statut"] == "ONE_AWAY" and a["distance"] == 1
    assert [x["emplacement"] for x in a["pieces"] if x["manquante"]] == ["minibus"]
    assert "Un minibus de 12 places ou plus" in a["ask"]["texte"] and "09.10" in a["ask"]["texte"]
    assert all(x["role"] for x in a["pieces"])
    texte = json.dumps(avant, ensure_ascii=False)
    for nom in ("Nicolas", "Roduit", "Anna", "Zufferey", "distillerie"):           # rôles seulement : ni nom, ni texte d'offre
        assert nom not in texte

    pauline = _session(md.PAULINE)
    asks = client.get("/api/pulse/moi/asks", headers=pauline).json()
    ask = next(x for x in asks if x["id"].startswith(ASK_A))
    assert ask["minimums"] == {"places": 12}
    r = client.post(f"/api/pulse/moi/asks/{ask['id']}/reponse", headers=pauline, json={"oui": True, "attributs": {"places": 14},
                                                                                    "quoi": "Minibus de 14 places"})
    assert r.status_code == 200, r.text
    apres = _capacite(client.get("/api/pulse/console/capacites", headers=CONSOLE).json(), ASK_A)
    assert apres["statut"] == "ACTIVE" and apres["distance"] == 0
    assert all(x["presente"] and x["consentement"] == "donné" for x in apres["pieces"])
    # la même demande ne peut plus être comblée une seconde fois : une seule liaison
    markus = _session(md.MARKUS)
    assert all(not x["id"].startswith(ASK_A) for x in client.get("/api/pulse/moi/asks", headers=markus).json())
    assert client.post(f"/api/pulse/moi/asks/{ask['id']}/reponse", headers=markus,
                       json={"oui": True, "attributs": {"places": 20}}).status_code == 404


def test_scenario_a_n_appelle_aucun_modele_et_ecrit_des_faits_declares():
    d = Demo(TAX)
    c = d.club
    ask = c.capacites.instance(c.capacites.patron(ASK_A)).ask
    avant = len(c.journal.evenements())
    inst = c.repondre_ask(md.PAULINE, ask.id, True, {"places": 14})
    assert inst.statut == "ACTIVE"
    nouveaux = c.journal.evenements()[avant:]
    assert {e.type for e in nouveaux} == {"OFFRE", "ACCORD", "ASK_REPONSE"}
    assert {e.statut.value for e in nouveaux} == {"DECLARE"}                    # tapé par la personne, jamais « synthétique »
    assert c.ia.appels == [] and not c.journal.evenements("APPEL_IA")          # aucune IA dans le scénario A


# ---------------------------------------------------------------------- règles de la réponse
@pytest.fixture
def club():
    return Demo(TAX).club


def _ask(c):
    return c.capacites.instance(c.capacites.patron(ASK_A)).ask


def test_une_reponse_qui_ne_couvre_pas_la_contrainte_n_ecrit_rien(club):
    avant = club.journal.empreinte()
    with pytest.raises(Invalide):
        club.repondre_ask(md.PAULINE, _ask(club).id, True, {"places": 9})
    assert club.journal.empreinte() == avant and club.capacites.instance(club.capacites.patron(ASK_A)).statut == "ONE_AWAY"


def test_non_n_a_d_effet_sur_personne(club):
    inst = club.repondre_ask(md.PAULINE, _ask(club).id, False)
    assert inst.statut == "ONE_AWAY"
    assert [e.donnees["oui"] for e in club.journal.evenements("ASK_REPONSE")] == [False]


def test_une_ask_n_est_jamais_adressee_a_une_piece_deja_liee_ni_a_qui_n_est_pas_sollicitable(club):
    assert all(not a.startswith(ASK_A) for _, a in club.asks_pour(NICOLAS))                 # déjà la salle
    club.modifier_profil(md.PAULINE, accepte=False)
    assert club.asks_pour(md.PAULINE) == []
    with pytest.raises(Introuvable):
        club.repondre_ask(md.PAULINE, _ask(club).id, True, {"places": 14})


def test_une_competence_du_catalogue_n_est_proposee_qu_a_qui_la_declare(club):
    p = club.capacites.patron("presentation_germanophone")
    assert all(e.concept is None or e.concept in TAX.concepts for e in p.emplacements)
    # une Ask sur une compétence n'atteint que les membres qui la déclarent (catégorie, jamais une personne choisie)
    for pid in (md.PAULINE, md.MARKUS, md.LEA):
        declarees = {o.concept for o in club.profil(pid).offre if o.concept}
        for inst, _ in club.asks_pour(pid):
            assert inst.ask.concept is None or inst.ask.concept in declarees


# ---------------------------------------------------------------------- invariants de la projection
def test_active_implique_chaque_piece_valable_et_consentie(club):
    club.repondre_ask(md.PAULINE, _ask(club).id, True, {"places": 14})
    p = club.capacites.patron(ASK_A)
    inst = club.capacites.instance(p)
    assert inst.statut == "ACTIVE"
    proto = p.protocole()
    for e in proto.etapes:
        o = club.banc.offre(inst.liaisons[e.id])
        assert club.banc.offre_couvre(o, e, proto.echeance, creneau=inst.creneau) is None
        dernier = next(x for x in club.banc.consentements_finalite(p.id) if x.donnees["emplacement"] == e.id)
        assert club.banc.raison_consentement(dernier, p.portee(e.id)) is None and dernier.donnees["offre"] == o.id


def test_la_capacite_est_une_projection_jamais_stockee(club):
    club.repondre_ask(md.PAULINE, _ask(club).id, True, {"places": 14})
    types = {e.type for e in club.journal.evenements()}
    assert not any("CAPAC" in t or "INSTANCE" in t for t in types)
    une, deux = club.capacites.projeter(), club.capacites.projeter()
    assert [i.model_dump() for i in une] == [i.model_dump() for i in deux]


def test_un_changement_de_conditions_invalide_le_consentement_et_degrade(club):
    club.repondre_ask(md.PAULINE, _ask(club).id, True, {"places": 14})
    salle = club.capacites.instance(club.capacites.patron(ASK_A)).liaisons["salle"]
    club.banc.modifier_offre(NICOLAS, salle, conditions="seulement si la salle n'est pas louée")
    inst = club.capacites.instance(club.capacites.patron(ASK_A))
    assert inst.statut == "DEGRADED" and inst.consentements["salle"] is not None
    assert inst.perdus == ["salle : les conditions de l'offre ont changé depuis le consentement"]      # l'emplacement, jamais qui


def test_une_nouvelle_version_du_patron_ne_reprend_aucun_consentement(club):
    club.repondre_ask(md.PAULINE, _ask(club).id, True, {"places": 14})
    p = club.capacites.patron(ASK_A)
    club.capacites.patrons[ASK_A] = Patron(**(p.model_dump() | {"version": 2}))
    inst = club.capacites.instance(club.capacites.patrons[ASK_A])
    assert inst.statut != "ACTIVE" and all(r == "la finalité a changé depuis le consentement" for r in
                                           (x.split(" : ", 1)[1] for x in inst.perdus))


def test_apres_la_fenetre_la_capacite_s_eteint_et_ses_claims_restent_dans_l_index(club):
    club.repondre_ask(md.PAULINE, _ask(club).id, True, {"places": 14})
    avant = club.claims()
    club.avancer(5)                                                             # 11.10 : la fenêtre du 09.10 est passée
    assert club.capacites.instance(club.capacites.patron(ASK_A)).statut == "EXTINCT"
    apres = club.claims()
    minibus = [c for c in apres if c.membre == md.PAULINE and c.kind == "RESOURCE" and c.texte.startswith("Un minibus")]
    assert len(minibus) == 1 and len(apres) == len(avant)                      # jamais supprimée…
    assert minibus[0].valable(md.JOUR_SCENE + timedelta(days=1)) and not minibus[0].valable(club.jour)   # …mais expirée


def test_index_bi_temporel_ce_que_le_journal_savait_a_une_position(club):
    seq_avant = club.journal.evenements()[-1].seq
    club.modifier_profil(md.LEA, retirer_capacite="traduction")
    lea = [c for c in club.claims() if c.membre == md.LEA and c.kind == "SKILL" and c.id.startswith("profil:")]
    trad = next(c for c in lea if c.concept == "traduction")
    j = club.jour
    assert trad.recorded_at == 0 and trad.superseded_at is not None
    assert trad.valable(j, vu_au=seq_avant) and not trad.valable(j)


def test_les_patrons_sont_ecrits_par_des_personnes_et_valides():
    patrons = charger_patrons(concepts=set(TAX.concepts))
    assert len(patrons) == 6 and all(p.fictif for p in patrons)
    brut = json.loads((DOSSIER_PATRONS / "delegation_acheteurs.json").read_text(encoding="utf-8"))
    for auteur in ("Généré par IA", "Apertus", "modèle de langage"):
        with pytest.raises(ValueError, match="personne"):
            Patron(**(brut | {"auteur": auteur}))
    Patron(**(brut | {"auteur": "Commission sociale et spécialisée du Club"}))      # « sociale », « spécialisée » : humains
    with pytest.raises(ValueError):
        Patron(**(brut | {"emplacements": brut["emplacements"][:1] * 2}))


def test_consentir_pour_une_capacite_composee(club):
    p = club.capacites.patron("presentation_germanophone")
    inst = club.capacites.instance(p)
    assert inst.statut == "PROPOSED"
    lea = next(k for k, v in inst.liaisons.items() if v and club.banc.offre(v).auteur == md.LEA)
    inst = club.consentir_capacite(md.LEA, p.id)
    assert inst.statut == "CONSENTED" and inst.consentements[lea] is None
    assert club.consentir_capacite(md.LEA, p.id).model_dump() == inst.model_dump()          # idempotent
    with pytest.raises(Introuvable):
        club.consentir_capacite(md.SOPHIE, p.id)                                   # aucune de ses offres ne compose
    with pytest.raises(Conflit):
        club.capacites.repondre(md.PAULINE, "presentation_germanophone:1:voix:x", True)
