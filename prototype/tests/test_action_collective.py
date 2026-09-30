"""L'ACTION COLLECTIVE de bout en bout par l'API, avec des SESSIONS DISTINCTES : Sophie (porteuse) et Léa (voix
allemande) agissent chacune depuis son espace ; Pauline, Markus et Nicolas sont JOUÉS par l'équipe depuis la console,
et c'est enregistré comme tel. Perturbation : Léa change SA disponibilité. Projection : des rôles, jamais des noms.
Monde FICTIF ; aucune action n'est décidée à la place d'une personne."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence import monde_demo as md
from intelligence.demo import BESOIN_SOPHIE, FICHE_DE

client = TestClient(app)
CONSOLE = {"X-Pulse-Console": "1"}
S, L, P, M, N = md.SOPHIE, md.LEA, md.PAULINE, md.MARKUS, md.NICOLAS
_n = [0]
NOMS = ("Sophie", "Carron", "Léa", "Imhof", "Pauline", "Darbellay", "Markus", "Heinzmann", "Nicolas", "Roduit")


def _sessions() -> dict[str, dict]:
    assert client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE).status_code == 200
    per = {p["id"]: p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    _n[0] += 1                                        # une adresse par appel : la limite d'essais de code reste active
    entree = TestClient(app, client=(f"10.8.{_n[0] % 250}.1", 50000))
    s = entree.post("/api/pulse/acces", json={"code": per[S]["code"]}).json()["session"]       # Sophie active SON compte
    return {S: {"X-Pulse-Session": s}} | {pid: {"X-Pulse-Session": per[pid]["session"]} for pid in (L, P, M, N)}


def _essai(h, qui, eid):
    return client.get(f"/api/pulse/moi/essais/{eid}", headers=h[qui]).json()


def _jouer(eid, qui, accepte=True):
    v = client.get(f"/api/pulse/console/essais/{eid}", headers=CONSOLE).json()["version"]
    return client.post(f"/api/pulse/console/essais/{eid}/geste", headers=CONSOLE, json={"membre": qui, "version": v, "accepte": accepte})


def _action(h) -> str:
    prop = client.post("/api/pulse/moi/actions/preparer", headers=h[S], json={"texte": BESOIN_SOPHIE}).json()
    assert {x["role"] for x in prop["exigences"]} == {"voix", "lieu", "public"} and prop["fenetre"]["jour"] == "2026-10-08"
    assert prop["ia"]["fournisseur"] in ("deterministe", "apertus")                      # l'origine de la compréhension est dite
    v = client.post("/api/pulse/moi/actions/nouvelle", headers=h[S], json={
        "question": "Présenter nos tisanes à des acheteurs germanophones", "objet": prop["objet"], "critere": prop["critere_suggere"],
        "exigences": prop["exigences"], "fenetre": prop["fenetre"], "duree_min_acceptable": 30}).json()
    assert v["etat"] == "BROUILLON" and v["assemblage"]["creneau"]["texte"] == "08.10 16:00–16:45"
    assert client.post(f"/api/pulse/moi/essais/{v['id']}/projection", headers=h[S], json={"oui": True}).status_code == 200  # SON choix
    return v["id"]


def test_parcours_complet_decisions_depuis_des_sessions_distinctes():
    h = _sessions()
    eid = _action(h)
    assert client.get(f"/api/pulse/moi/essais/{eid}", headers=h[L]).status_code == 404            # brouillon : Léa ne voit rien
    v = client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[S], json={"version": 0}).json()
    assert v["etat"] == "PROPOSE" and v["creneau"]["texte"] == "08.10 16:00–16:45"
    lea = _essai(h, L, eid)
    assert lea["role"] == "contributeur" and lea["votre_part"]["gestes"][0]["livrable"] == "Fiche produit en allemand"
    assert client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": lea["version"], "accepte": True}).status_code == 200
    assert _essai(h, S, eid)["etat"] == "PROPOSE"                                   # rien n'est supposé pour les autres
    for qui in (P, M):
        assert _jouer(eid, qui).json()["joue"] is True
    assert _essai(h, S, eid)["etat"] == "AUTORISE"

    # ---- perturbation : Léa, sur SON espace, n'est disponible qu'à partir de 17 h
    oid = _essai(h, L, eid)["votre_part"]["gestes"][0]["offre_id"]
    r = client.patch(f"/api/pulse/moi/offres/{oid}", headers=h[L], json={"plages": [{"jour": "2026-10-08", "debut": "17:00", "fin": "19:00"}]})
    assert r.status_code == 200 and eid in r.json()["essais_a_adapter"]
    proj = client.get("/api/pulse/console/projection", headers=CONSOLE).json()
    assert proj["etat"] == "A_ADAPTER" and proj["adaptation"]["tombe"] == ["Voix en allemand"]
    assert set(proj["adaptation"]["tient"]) == {"Lieu", "Public allemand"}
    s = _essai(h, S, eid)
    assert client.post(f"/api/pulse/moi/essais/{eid}/lancer", headers=h[S], json={"version": s["version"]}).status_code == 409
    alt = next(a for a in s["adaptation"]["alternatives"] if "17:00–17:45" in a["texte"])
    r = client.post(f"/api/pulse/moi/essais/{eid}/adapter", headers=h[S], json={"version": s["version"], "alternative": alt["id"]})
    assert r.status_code == 200 and r.json()["etat"] == "PROPOSE" and r.json()["creneau"]["debut"] == "17:00"
    lea = _essai(h, L, eid)
    assert lea["votre_part"]["gestes"][0]["statut"].startswith("votre part a changé")          # le moment a changé : à redonner
    client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": lea["version"], "accepte": True})
    assert _essai(h, S, eid)["etat"] == "PROPOSE"
    for qui in (M, N):
        _jouer(eid, qui)
    assert _essai(h, S, eid)["etat"] == "AUTORISE"
    assert client.get(f"/api/pulse/moi/essais/{eid}", headers=h[P]).json()["role"] == "ancien"   # Pauline : plus concernée

    # ---- engagée, puis la fiche : transmise ≠ reçue
    s = _essai(h, S, eid)
    assert client.post(f"/api/pulse/moi/essais/{eid}/lancer", headers=h[S], json={"version": s["version"]}).json()["etat"] == "EN_COURS"
    assert client.post(f"/api/pulse/moi/essais/{eid}/livrer/e1", headers=h[L], json={"contenu": FICHE_DE}).status_code == 200
    s = _essai(h, S, eid)
    g = next(x for x in s["etapes"] if x["id"] == "e1")
    assert g["palier"] == "transmis" and g["livraison"]["contenu"] == FICHE_DE and "confirmer_reception" in s["actions"]
    assert client.post(f"/api/pulse/moi/essais/{eid}/contributions/e1", headers=h[S]).status_code == 409   # la présentation n'a pas eu lieu
    assert client.post(f"/api/pulse/moi/essais/{eid}/receptions/e1", headers=h[S]).status_code == 200
    s = _essai(h, S, eid)
    g = next(x for x in s["etapes"] if x["id"] == "e1")
    assert g["palier"] == "livrable reçu" and g["livraison"]["recue"] and not g["constatable"] and "constater" not in s["actions"]
    assert next(x for x in client.get("/api/pulse/console/projection", headers=CONSOLE).json()["exigences"] if x["id"] == "e1")["palier"] == "livrable reçu"
    assert client.post(f"/api/pulse/moi/essais/{eid}/livrer/e1", headers=h[L], json={"contenu": "autre version"}).status_code == 409


def test_personne_ne_decide_a_la_place_d_un_autre():
    h = _sessions()
    eid = _action(h)
    client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[S], json={"version": 0})
    v = _essai(h, S, eid)["version"]
    assert client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[S], json={"version": v, "accepte": True}).status_code == 403
    assert client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[L], json={"version": v}).status_code in (403, 409)
    assert _jouer(eid, L).status_code == 403                                   # Léa a son téléphone : la console ne la joue pas
    assert client.post(f"/api/pulse/moi/essais/{eid}/livrer/e1", headers=h[L], json={"contenu": "trop tôt"}).status_code == 409
    assert client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": v - 1, "accepte": True}).status_code == 409


def test_sans_solution_bloque_et_le_dit_puis_rouvre_sur_un_fait_nouveau():
    h = _sessions()
    eid = _action(h)
    client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[S], json={"version": 0})
    lea = _essai(h, L, eid)
    client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": lea["version"], "accepte": True})
    oid = _essai(h, L, eid)["votre_part"]["gestes"][0]["offre_id"]
    client.patch(f"/api/pulse/moi/offres/{oid}", headers=h[L], json={"plages": [{"jour": "2026-10-08", "debut": "18:45", "fin": "20:00"}]})
    proj = client.get("/api/pulse/console/projection", headers=CONSOLE).json()
    assert proj["etat"] == "IMPOSSIBLE" and proj["adaptation"]["bloque"] and proj["adaptation"]["alternatives"] == []
    client.patch(f"/api/pulse/moi/offres/{oid}", headers=h[L], json={"plages": [{"jour": "2026-10-08", "debut": "16:30", "fin": "19:00"}]})
    assert _essai(h, S, eid)["etat"] == "A_ADAPTER"                              # rouvert ; rien n'est relancé tout seul


@pytest.mark.parametrize("etape", [2, 5, 7, 9])
def test_la_projection_ne_montre_ni_nom_ni_secret(etape):
    client.post(f"/api/pulse/demo/aller/{etape}", headers=CONSOLE)
    per = client.get("/api/pulse/console/personas", headers=CONSOLE).json()
    brut = json.dumps(client.get("/api/pulse/console/projection", headers=CONSOLE).json(), ensure_ascii=False)
    for x in NOMS + ("MEMBRE-", "@", FICHE_DE[:20]):
        assert x not in brut, (etape, x)
    for p in per:
        assert p["code"] not in brut and (not p["session"] or p["session"] not in brut)


def test_perturbation_jouee_par_l_equipe_est_affichee_comme_telle_et_refusee_pour_un_telephone_reel():
    client.post("/api/pulse/demo/aller/4", headers=CONSOLE)                  # coopération prête, créneau 16:00–16:45
    offres = client.get("/api/pulse/console/essais", headers=CONSOLE).json()["offres"]
    lieu = next(o["id"] for o in offres if o["quoi"].startswith("Présentoir éclairé sur mon stand (halle 2)"))
    voix = next(o["id"] for o in offres if o["quoi"].startswith("Présenter un produit en allemand"))
    plage = [{"jour": "2026-10-08", "debut": "14:00", "fin": "16:30"}]
    assert client.post("/api/pulse/console/jouer/disponibilite", headers=CONSOLE, json={"membre": L, "offre": voix, "plages": plage}).status_code == 403
    r = client.post("/api/pulse/console/jouer/disponibilite", headers=CONSOLE, json={"membre": P, "offre": lieu, "plages": plage})
    assert r.status_code == 200 and r.json()["joue"] and r.json()["essais_a_adapter"]
    proj = client.get("/api/pulse/console/projection", headers=CONSOLE).json()
    assert proj["adaptation"]["tombe"] == ["Lieu"] and any(j["qui"] == "lieu" and "joue_par" in j for j in proj["joues"])
    assert any("16:30" in a["texte"] for a in proj["adaptation"]["alternatives"])           # l'autre lieu ouvre à 16:30


def test_le_creneau_propose_n_est_dit_seul_que_s_il_l_est():
    """Défaut trouvé à la relecture de l'écran commun : « le seul moment où les disponibilités se recouvrent » alors
    qu'elles se recouvraient de 16:00 à 17:30. L'écran reçoit le recouvrement réel et ne dit « seul » que s'il l'est."""
    h = _sessions()
    eid = _action(h)
    r = _essai(h, S, eid)["assemblage"]["creneau"]["recouvrement"]
    assert r == {"debut": "16:00", "fin": "17:30", "unique": False}
    assert client.get("/api/pulse/console/projection", headers=CONSOLE).json()["creneau"]["recouvrement"] == r
    lieu = next(o["id"] for o in client.get("/api/pulse/console/essais", headers=CONSOLE).json()["offres"]
                if o["quoi"].startswith("Présentoir éclairé sur mon stand (halle 2)"))
    plage = [{"jour": "2026-10-08", "debut": "14:00", "fin": "16:45"}]
    assert client.post("/api/pulse/console/jouer/disponibilite", headers=CONSOLE, json={"membre": P, "offre": lieu, "plages": plage}).status_code == 200
    assert _essai(h, S, eid)["assemblage"]["creneau"]["recouvrement"] == {"debut": "16:00", "fin": "16:45", "unique": True}


def test_trente_jours_plus_tard_rien_n_est_reconduit_et_le_resultat_reste_inconnu():
    """Continuité (horloge de démonstration, SIMULÉE) : la fiche reçue le reste ; sans déclaration de la porteuse, le
    silence ne devient pas un succès ; les disponibilités étaient datées : aucune proposition ne renaît."""
    h = _sessions()
    eid = _action(h)
    client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[S], json={"version": 0})
    client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": _essai(h, L, eid)["version"], "accepte": True})
    for qui in (P, M):
        _jouer(eid, qui)
    assert client.post(f"/api/pulse/moi/essais/{eid}/lancer", headers=h[S], json={"version": _essai(h, S, eid)["version"]}).status_code == 200
    client.post(f"/api/pulse/moi/essais/{eid}/livrer/e1", headers=h[L], json={"contenu": FICHE_DE})
    client.post(f"/api/pulse/moi/essais/{eid}/receptions/e1", headers=h[S])
    assert client.post("/api/pulse/console/temps", headers=CONSOLE, json={"jours": 30}).status_code == 200
    proj = client.get("/api/pulse/console/projection", headers=CONSOLE).json()
    assert proj["etat"] == "RESULTAT_INCONNU"
    assert next(x for x in proj["exigences"] if x["id"] == "e1")["palier"] == "livrable reçu"      # un fait reçu ne s'efface pas
    assert {x["palier"] for x in proj["exigences"] if x["id"] != "e1"} == {"accepté"}             # accepté ≠ réalisé : rien de plus
    lea = _essai(h, L, eid)                             # défaut vu à l'enregistrement : « retirer » proposé 30 jours après
    assert "retirer" not in lea["actions"] and lea["apres_action"]
    assert client.post(f"/api/pulse/moi/essais/{eid}/retirer", headers=h[L]).status_code == 409
    prop = client.post("/api/pulse/moi/actions/preparer", headers=h[S], json={"texte": BESOIN_SOPHIE}).json()   # le même besoin, un mois après
    r = client.post("/api/pulse/moi/actions/nouvelle", headers=h[S], json={
        "question": "Recommencer le mois suivant", "objet": prop["objet"], "critere": prop["critere_suggere"],
        "exigences": prop["exigences"], "fenetre": prop["fenetre"], "duree_min_acceptable": 30})
    assert r.status_code == 200 and prop["fenetre"]["jour"] > "2026-10-08"
    assert r.json()["assemblage"]["creneau"] is None and r.json()["assemblage"]["blocage"]         # rien n'est reconduit ni supposé


def test_une_fiche_recue_ne_vaut_pas_la_presentation_et_un_retrait_ensuite_garde_son_effet():
    """Défaut trouvé par la revue « jury » : la réception de la fiche marquait tout le geste « voix » comme reçu —
    présentation comprise, trois jours avant qu'elle ait lieu ; un retrait ensuite était ignoré. Désormais : la fiche
    reçue reste un fait ; la présentation se constate au créneau ; un retrait rouvre l'adaptation."""
    h = _sessions()
    eid = _action(h)
    client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[S], json={"version": 0})
    client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": _essai(h, L, eid)["version"], "accepte": True})
    for qui in (P, M):
        _jouer(eid, qui)
    client.post(f"/api/pulse/moi/essais/{eid}/lancer", headers=h[S], json={"version": _essai(h, S, eid)["version"]})
    client.post(f"/api/pulse/moi/essais/{eid}/livrer/e1", headers=h[L], json={"contenu": FICHE_DE})
    assert client.post(f"/api/pulse/moi/essais/{eid}/receptions/e1", headers=h[S]).status_code == 200
    assert client.post(f"/api/pulse/moi/essais/{eid}/receptions/e1", headers=h[S]).status_code == 409        # double clic
    assert client.post(f"/api/pulse/moi/essais/{eid}/retirer", headers=h[L]).status_code == 200
    proj = client.get("/api/pulse/console/projection", headers=CONSOLE).json()
    assert proj["etat"] in ("A_ADAPTER", "IMPOSSIBLE")
    assert next(x for x in proj["exigences"] if x["id"] == "e1")["palier"] == "ne couvre plus"
    lea = _essai(h, S, eid)
    assert next(x for x in lea["etapes"] if x["id"] == "e1")["livraison"]["recue"]                         # la fiche, elle, reste reçue


def test_rien_n_est_projete_sans_l_accord_de_la_porteuse_et_jamais_le_texte_d_une_offre():
    """Revue « jury » (représentant du Club) : l'écran commun montrait le BROUILLON d'un membre et le texte d'une offre
    (« coin dégustation du stand de la distillerie, halle 3 ») qui désigne quelqu'un sur un salon."""
    h = _sessions()
    prop = client.post("/api/pulse/moi/actions/preparer", headers=h[S], json={"texte": BESOIN_SOPHIE}).json()
    eid = client.post("/api/pulse/moi/actions/nouvelle", headers=h[S], json={
        "question": "Présenter nos tisanes à des acheteurs germanophones", "objet": prop["objet"], "critere": prop["critere_suggere"],
        "exigences": prop["exigences"], "fenetre": prop["fenetre"], "duree_min_acceptable": 30}).json()["id"]
    assert client.get("/api/pulse/console/projection", headers=CONSOLE).json()["vide"] is True          # pas montrée
    assert client.post(f"/api/pulse/moi/essais/{eid}/projection", headers=h[L], json={"oui": True}).status_code in (403, 404)
    assert client.post(f"/api/pulse/moi/essais/{eid}/projection", headers=h[S], json={"oui": True}).status_code == 200
    assert client.get("/api/pulse/console/projection", headers=CONSOLE).json()["id"] == eid
    client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[S], json={"version": 0})
    client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": _essai(h, L, eid)["version"], "accepte": True})
    oid = _essai(h, L, eid)["votre_part"]["gestes"][0]["offre_id"]
    client.patch(f"/api/pulse/moi/offres/{oid}", headers=h[L], json={"plages": [{"jour": "2026-10-08", "debut": "17:00", "fin": "19:00"}]})
    brut = json.dumps(client.get("/api/pulse/console/projection", headers=CONSOLE).json(), ensure_ascii=False)
    offres = client.get("/api/pulse/console/essais", headers=CONSOLE).json()["offres"]
    for o in offres:                                                          # aucun texte d'offre, ni ses conditions
        assert o["quoi"] not in brut, o["quoi"]
    assert "halle" not in brut and "stand C4" not in brut
    assert client.post(f"/api/pulse/moi/essais/{eid}/projection", headers=h[S], json={"oui": False}).status_code == 200
    assert client.get("/api/pulse/console/projection", headers=CONSOLE).json()["vide"] is True          # retirée : plus montrée


@pytest.mark.parametrize("debut,fin,etat,n_min", [
    ("15:00", "18:00", "AUTORISE", 0),                 # le créneau reste couvert : rien ne change, rien n'est redemandé
    ("16:15", "18:00", "A_ADAPTER", 1), ("17:00", "19:00", "A_ADAPTER", 1), ("17:30", "19:00", "A_ADAPTER", 1),
    ("18:00", "19:00", "IMPOSSIBLE", 0),               # hors de la fenêtre de la porteuse (jusqu'à 18:00) : bloqué, dit tel quel
    ("09:00", "11:00", "IMPOSSIBLE", 0)])
def test_la_valeur_choisie_par_le_jury_n_est_pas_fixee_d_avance(debut, fin, etat, n_min):
    """Le jury choisit l'heure ; la réponse est CALCULÉE, pour chaque valeur : adaptation(s), rien à faire, ou blocage."""
    h = _sessions()
    eid = _action(h)
    client.post(f"/api/pulse/moi/essais/{eid}/publier-proposition", headers=h[S], json={"version": 0})
    client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h[L], json={"version": _essai(h, L, eid)["version"], "accepte": True})
    for qui in (P, M):
        _jouer(eid, qui)
    oid = _essai(h, L, eid)["votre_part"]["gestes"][0]["offre_id"]
    client.patch(f"/api/pulse/moi/offres/{oid}", headers=h[L], json={"plages": [{"jour": "2026-10-08", "debut": debut, "fin": fin}]})
    proj = client.get("/api/pulse/console/projection", headers=CONSOLE).json()
    assert proj["etat"] == etat
    alts = (proj["adaptation"] or {}).get("alternatives", [])
    assert len(alts) >= n_min and (etat != "IMPOSSIBLE" or alts == [])
    for a in alts:                                      # chaque adaptation proposée tient dans la NOUVELLE disponibilité
        d = a["texte"].split("Déplacer à 08.10 ")[1][:5]
        assert debut <= d and a["texte"].split("–")[1][:5] <= fin
