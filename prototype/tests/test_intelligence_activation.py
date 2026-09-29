"""ACTIVER : machine à états réelle, consentement d'abord, refus → replanification, résultat jamais fabriqué,
mémoire vérifiée réutilisée. Monde de démonstration FICTIF ; gestes humains simulés par les tests."""
import json
from datetime import timedelta

import pytest

from app.parser_rules import analyser
from app.taxonomy import charger_taxonomie
from intelligence import apprentissage
from intelligence import monde_demo as md
from intelligence.activation import DELAI_REPONSE_JOURS, DELAI_RESULTAT_JOURS, ErreurActivation, Moteur
from intelligence.detection import scanner
from intelligence.modele import BesoinActif

TAX = charger_taxonomie()
S, A, M, L = md.SOPHIE, md.ANNA, md.MARKUS, md.LEA


def _depart(**kw):
    r = md.construire()
    opp = next(o for o in scanner(r, TAX)["opportunites"] if o.beneficiaire == S)
    mo = Moteur(r, TAX)
    return r, mo, mo.creer(opp, r.aujourd_hui, **kw), r.aujourd_hui


def _etats(mo, aid):
    return [j["etat"] for j in mo.journal(aid)]


def _jusqu_au_resultat(mo, aid, t, refus_anna=True):
    mo.lancer(aid, t)
    mo.repondre(aid, t, S, True)
    if refus_anna:
        mo.repondre(aid, t + timedelta(days=1), A, False)
    mo.repondre(aid, t + timedelta(days=1), M, True)
    traductrice = L if refus_anna else A
    mo.repondre(aid, t + timedelta(days=2), traductrice, True)
    mo.contribuer(aid, t + timedelta(days=3), traductrice, "ressource", "Fiche : étiqueter pour l'Allemagne", "Mentions…", True)
    mo.contribuer(aid, t + timedelta(days=3), M, "rencontre", "Rendez-vous au salon", "20 minutes, mardi matin")
    return traductrice


def test_parcours_complet_avec_refus_et_replanification():
    r, mo, aid, t = _depart()
    assert _etats(mo, aid) == ["DETECTEE", "EVALUEE", "PLANIFIEE"]
    _jusqu_au_resultat(mo, aid, t)
    res = mo.confirmer(aid, t + timedelta(days=14), S, "debloque", True, "rendez-vous tenu au salon")
    assert _etats(mo, aid) == ["DETECTEE", "EVALUEE", "PLANIFIEE", "EN_ATTENTE_ACCORD", "BLOQUEE", "REPLANIFICATION",
                               "ALTERNATIVE_PROPOSEE", "EN_ATTENTE_ACCORD", "ACTIVEE", "TERMINEE", "RESULTAT_CONFIRME"]
    assert res["statut"] == "DEMANDE DÉBLOQUÉE" and res["etape_suivante"] == "débloquée"
    alt = next(j for j in mo.journal(aid) if j["etat"] == "ALTERNATIVE_PROPOSEE")["details"]
    assert alt["alternative"] == L and alt["a_verifier"] and "disponibilité" in alt["prochaine_action"]
    assert all(j["agent"] and j["raison"] for j in mo.journal(aid))       # chaque transition : un agent, une raison
    motif = apprentissage.motifs(r.memoire, t + timedelta(days=14))[-1]
    assert set(motif["concepts"]) == {"traduction", "export_allemagne"} and motif["confirmations"] == 1


def test_personne_n_est_sollicite_avant_l_accord_du_beneficiaire():
    r, mo, aid, t = _depart()
    mo.lancer(aid, t)
    assert [e.acteurs for e in r.memoire.evenements("SOLLICITATION_PRIVEE")] == [[S]]
    with pytest.raises(ErreurActivation):
        mo.vue_membre(aid, A)                                             # Anna ne sait même pas que l'activation existe
    mo.repondre(aid, t, S, False)                                          # Sophie ne souhaite pas donner suite
    assert mo.etat(aid) == "ABANDONNEE"
    assert [e.acteurs for e in r.memoire.evenements("SOLLICITATION_PRIVEE")] == [[S]]


def test_vues_privees_avant_et_apres_consentement():
    r, mo, aid, t = _depart()
    mo.lancer(aid, t)
    mo.repondre(aid, t, S, True)
    v = json.dumps(mo.vue_membre(aid, A), ensure_ascii=False)
    for fuite in ("Sophie", "Carron", "Tisanes", "Markus", "Heinzmann", "conformité", "Rencontre", "Orsières", "mar-matin"):
        assert fuite not in v, fuite                                       # identité, autres personnes, autres étapes, agenda
    mo.repondre(aid, t, A, True)
    apres = mo.vue_membre(aid, A)
    assert apres["qui_demande"] == "Sophie Carron"                         # nommée après SON accord (demande non anonyme)
    assert "Markus" not in json.dumps(apres, ensure_ascii=False)
    assert all(set(c) == {"date", "moment", "libelle"} for c in apres["creneaux_communs"])   # intersection seulement


def test_demande_anonyme_reste_anonyme_apres_accord():
    r, mo, aid, t = _depart(anonyme=True)
    mo.lancer(aid, t)
    mo.repondre(aid, t, S, True)
    mo.repondre(aid, t, A, True)
    v = mo.vue_membre(aid, A)
    assert "Sophie" not in json.dumps(v, ensure_ascii=False) and v["creneaux_communs"] == []


def test_un_refus_n_est_jamais_attribue_au_beneficiaire():
    r, mo, aid, t = _depart()
    mo.lancer(aid, t)
    mo.repondre(aid, t, S, True)
    mo.repondre(aid, t, A, False)
    v = json.dumps(mo.vue_beneficiaire(aid, S), ensure_ascii=False)
    assert "Anna" not in v and "Zufferey" not in v and "Léa" not in v and "déclin" not in v and "refus" not in v
    assert "une autre personne est sollicitée" in v
    with pytest.raises(ErreurActivation):
        mo.vue_beneficiaire(aid, M)                                       # personne d'autre ne voit le suivi


def test_transitions_et_gestes_invalides_refuses():
    r, mo, aid, t = _depart()
    with pytest.raises(ErreurActivation):
        mo.repondre(aid, t, S, True)                                       # rien n'a été envoyé
    mo.lancer(aid, t)
    with pytest.raises(ErreurActivation):
        mo.lancer(aid, t)
    for qui in (A, M, "c00001"):                                           # pas (encore) sollicités
        with pytest.raises(ErreurActivation):
            mo.repondre(aid, t, qui, True)
    with pytest.raises(ErreurActivation):
        mo.contribuer(aid, t, A, "ressource", "x", "y")                    # pas d'accord : pas de contribution
    mo.repondre(aid, t, S, True)
    with pytest.raises(ErreurActivation):
        mo.repondre(aid, t, S, True)                                       # une seule réponse
    with pytest.raises(ErreurActivation):
        mo.confirmer(aid, t, S, "debloque", True)                          # rien n'est terminé
    _ = r


def test_seul_le_beneficiaire_confirme_et_jamais_de_succes_presume():
    r, mo, aid, t = _depart()
    _jusqu_au_resultat(mo, aid, t)
    with pytest.raises(ErreurActivation):
        mo.confirmer(aid, t, M, "debloque", True)
    with pytest.raises(ErreurActivation):
        mo.confirmer(aid, t, S, "génial", True)
    fin = t + timedelta(days=3)
    assert mo.echeances(fin + timedelta(days=DELAI_RESULTAT_JOURS - 1)) == []
    mo.echeances(fin + timedelta(days=DELAI_RESULTAT_JOURS))
    assert mo.etat(aid) == "RESULTAT_INCONNU" and mo.resultat(aid)["statut"] == "RÉSULTAT INCONNU"
    assert apprentissage.motifs(r.memoire, fin + timedelta(days=30))[-1]["activation"] != aid   # rien appris d'un inconnu
    mo.confirmer(aid, fin + timedelta(days=30), S, "non", False)             # une confirmation tardive reste possible
    assert mo.etat(aid) == "RESULTAT_NEGATIF"
    assert all(x["activation"] != aid for x in apprentissage.motifs(r.memoire, fin + timedelta(days=31)))


def test_silence_vaut_sans_reponse_puis_alternative():
    r, mo, aid, t = _depart()
    mo.lancer(aid, t)
    mo.repondre(aid, t, S, True)
    mo.repondre(aid, t, M, True)
    assert mo.echeances(t + timedelta(days=DELAI_REPONSE_JOURS - 1)) == []
    mo.echeances(t + timedelta(days=DELAI_REPONSE_JOURS))
    assert mo.etat(aid) == "EN_ATTENTE_ACCORD"
    assert next(e for e in mo.plan(aid)["etapes"] if e["id"] == "e1")["membre"] == L
    assert any("sans réponse" in j["raison"] for j in mo.journal(aid))


def test_toutes_les_alternatives_declinent_arret_propre_explique():
    r, mo, aid, t = _depart()
    mo.lancer(aid, t)
    mo.repondre(aid, t, S, True)
    for _ in range(10):
        if mo.etat(aid) != "EN_ATTENTE_ACCORD":
            break
        e1 = next(e for e in mo.plan(aid)["etapes"] if e["id"] == "e1")
        mo.repondre(aid, t, e1["membre"], False)
    assert mo.etat(aid) == "ABANDONNEE"
    fin = mo.journal(aid)[-1]
    assert "aucune alternative" in fin["raison"] and fin["details"]["levee"]["texte"]
    assert sum(1 for j in mo.journal(aid) if j["etat"] == "ALTERNATIVE_PROPOSEE") <= 3   # pas de boucle infinie


def test_perturbation_membre_retire_pendant_l_activation():
    r, mo, aid, t = _depart()
    mo.lancer(aid, t)
    mo.repondre(aid, t, S, True)
    assert mo.retirer_membre(A, t) == [aid]
    assert next(e for e in mo.plan(aid)["etapes"] if e["id"] == "e1")["membre"] == L
    assert "BLOQUEE" in _etats(mo, aid) and mo.etat(aid) == "EN_ATTENTE_ACCORD"


def test_contrainte_jury_recalcule_le_plan_avant_lancement():
    r, mo, aid, t = _depart()
    mo.changer_contraintes(aid, t, langue="it")                            # personne ne parle italien
    assert any(e.get("incompatible") for e in mo.plan(aid)["etapes"])
    with pytest.raises(ErreurActivation):
        mo.lancer(aid, t)                                                  # un plan qui viole une contrainte ne part pas
    mo.changer_contraintes(aid, t, langue="de")
    assert not any(e.get("incompatible") for e in mo.plan(aid)["etapes"]) and mo.plan(aid)["version"] == 3
    mo.lancer(aid, t)


def test_budget_d_attention_protege_les_membres_serviables():
    r = md.construire()
    opp = next(o for o in scanner(r, TAX)["opportunites"] if o.beneficiaire == S)
    mo = Moteur(r, TAX)
    t = r.aujourd_hui
    for _ in range(2):
        aid = mo.creer(opp, t)
        mo.lancer(aid, t)
        mo.repondre(aid, t, S, True)
    assert mo.ouvertes()[A] == 2
    aid = mo.creer(opp, t)
    mo.lancer(aid, t)
    with pytest.raises(ErreurActivation, match="budget"):
        mo.repondre(aid, t, S, True)


def test_une_lacune_ne_s_active_pas():
    from intelligence.club_synthetique import generer
    r, _ = generer(150, 2026)
    lac = next(o for o in scanner(r, TAX)["opportunites"] if o.type == "LACUNE")
    with pytest.raises(ErreurActivation):
        Moteur(r, TAX).creer(lac, r.aujourd_hui)


def test_la_memoire_rend_la_situation_suivante_plus_simple():
    r, mo, aid, t = _depart()
    _jusqu_au_resultat(mo, aid, t)
    t2 = t + timedelta(days=14)
    mo.confirmer(aid, t2, S, "debloque", True)
    texte = "Je dois faire traduire mes étiquettes de vin en allemand pour un salon à Stuttgart."
    r.besoins.append(BesoinActif(id="b_pauline", auteur=md.PAULINE, texte=texte, le=t2, besoin=analyser(texte, TAX)))
    r.aujourd_hui = t2
    o = next(o for o in scanner(r, TAX)["opportunites"] if o.beneficiaire == md.PAULINE)
    assert o.type == "MEMOIRE" and o.personnes_a_solliciter == 0 and o.motif
    assert any("à vérifier" in c.libelle for c in o.contraintes)          # secteur différent : dit, pas masqué
    assert "Sophie" not in json.dumps(o.model_dump(), ensure_ascii=False)  # le bénéficiaire d'origine n'est jamais nommé
    a2 = mo.creer(o, t2)
    mo.lancer(a2, t2)
    mo.repondre(a2, t2, md.PAULINE, True)
    mo.reutiliser(a2, t2)
    mo.confirmer(a2, t2, md.PAULINE, "partiel", True)
    assert len(r.memoire.evenements("SOLLICITATION_PRIVEE")) == len([e for e in r.memoire.evenements("SOLLICITATION_PRIVEE")
                                                                    if e.donnees["aid"] == aid]) + 1   # seule Pauline
    m = next(x for x in apprentissage.motifs(r.memoire, t2) if x["motif_id"] == o.motif)
    assert m["confirmations"] == 2
