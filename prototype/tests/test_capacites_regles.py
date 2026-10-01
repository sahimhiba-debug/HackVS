"""Règles fines du registre des capacités, écrites pour tuer les mutants SURVIVANTS de la première campagne de
mutation (mutmut, limitée à intelligence/capacites.py) : chaque test ci-dessous correspond à un comportement que la
suite ne distinguait pas encore d'une variante fausse. Données FICTIVES."""
from datetime import date, timedelta

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.capacites import DOSSIER_PATRONS, Claim, Emplacement, Fenetre, Patron, Registre, charger_patrons, index_claims
from intelligence.demo import NICOLAS, Demo
from intelligence.erreurs import Conflit, Introuvable, Invalide
from intelligence.essai import Banc, Plage
from plateforme.memoire import Memoire

TAX = charger_taxonomie()
A = "delegation_acheteurs"
J = date(2026, 10, 6)
JOUR = J + timedelta(days=2)


@pytest.fixture
def club():
    return Demo(TAX).club


def _ask(c, finalite=A):
    return c.capacites.instance(c.capacites.patron(finalite)).ask


# ---------------------------------------------------------------------- répondre à une Ask
def test_un_minimum_exactement_atteint_suffit(club):
    inst = club.repondre_ask(md.PAULINE, _ask(club).id, True, {"places": 12})
    assert inst.statut == "ACTIVE" and inst.hypotheses == ["disponibilités et attributs DÉCLARÉS par les membres, non vérifiés par le système"]


def test_la_reponse_ecrit_une_offre_a_usage_unique_datee_et_un_fait_de_reponse_complet(club):
    ask = _ask(club)
    club.repondre_ask(md.PAULINE, ask.id, True, {"places": 14, "roues": 4})
    o = club.banc.offres()[-1]
    assert (o.auteur, o.nature, o.capacite, o.concept, o.du, o.au) == (md.PAULINE, "objet", 1, None, club.jour, date(2026, 10, 9))
    assert o.attributs == {"places": 14}                               # seuls les attributs demandés sont gardés
    assert [(p.debut, p.fin) for p in o.plages] == [(ask.creneau.debut, ask.creneau.fin)]
    assert o.quoi == "Un minibus de 12 places ou plus" and "Accueillir une délégation" in o.conditions
    rep = club.journal.evenements("ASK_REPONSE")[-1]
    assert rep.acteurs == [md.PAULINE] and rep.donnees["ask"] == ask.id and rep.donnees["oui"] is True and rep.donnees["offre"] == o.id
    assert club.journal.evenements("ACCORD")[-1].donnees["jusqu_au"] == "2026-10-09"


def test_non_journalise_la_demande(club):
    ask = _ask(club)
    club.repondre_ask(md.PAULINE, ask.id, False)
    rep = club.journal.evenements("ASK_REPONSE")[-1]
    assert rep.donnees["ask"] == ask.id and rep.donnees["oui"] is False and "offre" not in rep.donnees


def _registre_competence():
    """Un patron dont la pièce manquante est une COMPÉTENCE du catalogue : seule qui la déclare peut la combler."""
    b = Banc(Memoire(), lambda: J, lambda pid: f"org-{pid}")
    p = Patron(id="p_competence", version=1, titre="Capacité à compétence", auteur="Commission du Club", fictif=True,
               fenetre=Fenetre(jour=JOUR, debut="10:00", fin="12:00"), duree_min=60,
               emplacements=[Emplacement(id="lieu", role="lieu", nature="lieu", libelle="Un lieu", geste="Prêter un lieu"),
                             Emplacement(id="voix", role="voix", nature="competence", concept="traduction", libelle="Une voix",
                                         geste="Traduire")])
    b.publier_offre("m1", "lieu", "Salle", 1, J, JOUR, plages=[Plage(jour=JOUR, debut="09:00", fin="12:00")])
    return b, p, Registre(b, [p], lambda: J)


def test_une_competence_non_declaree_ne_peut_pas_combler_la_piece():
    b, p, r = _registre_competence()
    ask = r.instance(p).ask
    assert ask.concept == "traduction" and ask.emplacement == "voix"
    with pytest.raises(Invalide, match="non déclarée"):
        r.repondre("m2", ask.id, True, competences={"vins"})
    with pytest.raises(Invalide, match="non déclarée"):
        r.repondre("m2", ask.id, True)
    inst = r.repondre("m2", ask.id, True, competences={"traduction"})
    assert inst.distance == 0 and inst.consentements == {"lieu": "consentement à demander", "voix": None}   # la salle n'a pas consenti
    assert inst.statut == "CONSENTED" and b.offre(inst.liaisons["voix"]).concept == "traduction"


def test_messages_de_refus(club):
    with pytest.raises(Invalide, match="ne couvre pas la demande : places ≥ 12"):
        club.repondre_ask(md.PAULINE, _ask(club).id, True, {"places": 3})
    with pytest.raises(Conflit, match="plus d'actualité"):
        club.capacites.repondre(md.PAULINE, f"{A}:1:minibus:faux", True)
    with pytest.raises(Introuvable, match="capacité inconnue"):
        club.capacites.patron("inexistante")
    with pytest.raises(Introuvable, match="aucune de vos offres"):
        club.consentir_capacite(md.PAULINE, A)


# ---------------------------------------------------------------------- consentements
def test_changer_un_emplacement_du_patron_n_invalide_que_son_propre_consentement(club):
    club.repondre_ask(md.PAULINE, _ask(club).id, True, {"places": 14})
    p = club.capacites.patron(A)
    autre = [e.model_copy(update={"minimums": {"places": 16}}) if e.id == "salle" else e for e in p.emplacements]
    club.capacites.patrons[A] = Patron(**(p.model_dump() | {"emplacements": [e.model_dump() for e in autre]}))
    inst = club.capacites.instance(club.capacites.patrons[A])
    assert inst.perdus == ["salle : la finalité a changé depuis le consentement"]
    assert inst.consentements["minibus"] is None and inst.consentements["interp"] is None


def test_un_consentement_pour_un_emplacement_disparu_n_empeche_pas_de_lire_les_autres(club):
    club.repondre_ask(md.PAULINE, _ask(club).id, True, {"places": 14})
    p = club.capacites.patron(A)
    sans = [e for e in p.emplacements if e.id != "salle"]
    club.capacites.patrons[A] = Patron(**(p.model_dump() | {"emplacements": [e.model_dump() for e in sans]}))
    inst = club.capacites.instance(club.capacites.patrons[A])
    assert set(inst.liaisons) == {"minibus", "interp"} and inst.statut == "ACTIVE"      # les consentements suivants sont lus


def test_un_consentement_perdu_a_une_piece_pres_est_degrade_et_dit_ce_qui_manque(club):
    salle = club.capacites.instance(club.capacites.patron(A)).liaisons["salle"]
    club.banc.retirer_offre(NICOLAS, salle)
    inst = club.capacites.instance(club.capacites.patron(A))
    assert inst.statut == "DEGRADED" and inst.distance is None and inst.perdus == ["salle : offre retirée"]


def test_a_une_piece_pres_les_consentements_sont_distingues_de_la_piece_manquante(club):
    inst = club.capacites.instance(club.capacites.patron(A))
    assert inst.statut == "ONE_AWAY"
    assert inst.consentements == {"salle": None, "interp": None, "minibus": "pièce manquante"}
    assert inst.hypotheses == ["disponibilités et attributs DÉCLARÉS par les membres, non vérifiés par le système"]


def _deux_salles():
    """Deux salles couvrent ; seule la SECONDE (dans l'ordre du moteur) a un consentement : c'est elle qui doit être liée."""
    b = Banc(Memoire(), lambda: J, lambda pid: f"org-{pid}")
    p = Patron(id="p_deux", version=1, titre="Capacité à deux salles", auteur="Commission du Club", fictif=True,
               fenetre=Fenetre(jour=JOUR, debut="10:00", fin="12:00"), duree_min=60,
               emplacements=[Emplacement(id="lieu", role="lieu", nature="lieu", libelle="Un lieu", geste="Prêter un lieu"),
                             Emplacement(id="objet", role="objet", nature="objet", libelle="Un objet", geste="Prêter un objet")])
    pl = [Plage(jour=JOUR, debut="09:00", fin="12:00")]
    b.publier_offre("m1", "lieu", "Salle A", 1, J, JOUR + timedelta(days=5), plages=pl)
    b2 = b.publier_offre("m2", "lieu", "Salle B", 1, J, JOUR, plages=pl)
    b.publier_offre("m3", "objet", "Objet", 1, J, JOUR, plages=pl)
    b.consentir_finalite("m2", p.id, "lieu", b2, p.portee("lieu"), JOUR)
    return b, p, b2


def test_la_composition_retenue_garde_le_plus_de_consentements():
    b, p, b2 = _deux_salles()
    inst = Registre(b, [p], lambda: J).instance(p)
    assert inst.statut == "CONSENTED" and inst.liaisons["lieu"] == b2 and inst.consentements["lieu"] is None


def test_a_une_piece_pres_la_piece_consentie_est_gardee():
    b, p, b2 = _deux_salles()
    b.retirer_offre("m3", b.offres()[-1].id)
    inst = Registre(b, [p], lambda: J).instance(p)
    assert inst.statut == "ONE_AWAY" and inst.liaisons["lieu"] == b2 and inst.consentements["lieu"] is None


def test_apres_la_fenetre_l_extinction_est_expliquee(club):
    club.avancer(5)
    inst = club.capacites.instance(club.capacites.patron(A))
    assert inst.statut == "EXTINCT" and inst.hypotheses == ["la fenêtre de cette capacité est passée"]


# ---------------------------------------------------------------------- index bi-temporel
def test_bornes_de_validite_et_d_enregistrement_incluses():
    c = Claim(id="x", kind="RESOURCE", membre="m", texte="t", valid_from=J, valid_until=JOUR, recorded_at=5, statut="DECLARE")
    assert c.valable(J, vu_au=5) and c.valable(JOUR) and not c.valable(J - timedelta(days=1)) and not c.valable(JOUR + timedelta(days=1))
    assert not c.valable(J, vu_au=4)
    remplace = c.model_copy(update={"superseded_at": 9})
    assert remplace.valable(J, vu_au=8) and not remplace.valable(J, vu_au=9) and not remplace.valable(J)


def test_index_offres_retrait_et_nature(club):
    avant = {c.id for c in club.claims()}
    oid = club.banc.publier_offre(md.PAULINE, "lieu", "Une cave voûtée", 1, club.jour, club.jour + timedelta(days=2),
                                  plages=[Plage(jour=club.jour, debut="10:00", fin="11:00")])
    club.banc.publier_offre(md.PAULINE, "competence", "Traduire", 1, club.jour, club.jour + timedelta(days=2), concept="traduction")
    nouvelles = [c for c in club.claims() if c.id not in avant]
    cave, trad = nouvelles
    assert (cave.kind, cave.valid_from, cave.valid_until, cave.statut, len(cave.plages)) == ("RESOURCE", club.jour,
                                                                                          club.jour + timedelta(days=2), "DECLARE", 1)
    assert (trad.kind, trad.concept) == ("SKILL", "traduction")
    seq = club.journal.evenements()[-1].seq
    club.banc.retirer_offre(md.PAULINE, oid)
    cave = next(c for c in club.claims() if c.id == cave.id)
    assert cave.superseded_at == seq + 1 and cave.valable(club.jour, vu_au=seq) and not cave.valable(club.jour)


def test_index_profil_besoins_textes_et_statut(club):
    c0 = {c.id: c for c in club.claims()}
    need = [c for c in c0.values() if c.membre == md.NICOLAS and c.kind == "NEED"]
    assert need and all(c.recorded_at == 0 and c.statut == "SYNTHETIQUE" for c in need)
    lea = next(c for c in c0.values() if c.membre == md.LEA and c.kind == "SKILL" and c.concept == "traduction")
    p = club.profil(md.LEA)
    with club.joue():
        club._remplacer_profil(p.model_copy(update={"offre": [o.model_copy(update={"texte": "Traduction FR–DE, nouvelle formulation"})
                                                              for o in p.offre]}))
    apres = [c for c in club.claims() if c.membre == md.LEA and c.id.startswith("profil:") and c.concept == "traduction"]
    assert len(apres) == 2 and apres[0].superseded_at == apres[1].recorded_at and apres[1].statut == "JOUE"
    assert apres[1].texte == "Traduction FR–DE, nouvelle formulation" and apres[0].id == lea.id == "profil:d01:SKILL:traduction@0"
    club.modifier_profil(md.NICOLAS, ajouter_recherche="Trouver un transporteur frigorifique")
    assert len([c for c in club.claims() if c.membre == md.NICOLAS and c.kind == "NEED"]) == len(need) + 1


def test_index_pur_meme_journal_meme_index(club):
    depart = club._profils_depart
    assert [c.model_dump() for c in index_claims(club.journal, depart)] == [c.model_dump() for c in index_claims(club.journal, depart)]


# ---------------------------------------------------------------------- patrons
def test_un_patron_hors_catalogue_ou_en_double_est_refuse(tmp_path):
    brut = (DOSSIER_PATRONS / "delegation_acheteurs.json").read_text(encoding="utf-8")
    (tmp_path / "a.json").write_text(brut, encoding="utf-8")
    assert [p.id for p in charger_patrons(tmp_path, set(TAX.concepts))] == [A]
    assert [p.id for p in charger_patrons(tmp_path)] == [A]                   # sans catalogue fourni : pas de contrôle croisé
    with pytest.raises(ValueError, match="hors catalogue"):
        charger_patrons(tmp_path, {"vins"})
    (tmp_path / "b.json").write_text(brut, encoding="utf-8")
    with pytest.raises(ValueError, match="même identifiant"):
        charger_patrons(tmp_path, set(TAX.concepts))


def test_le_jour_meme_de_la_fenetre_la_capacite_existe_encore(club):
    club.avancer(3)                                                     # vendredi 09.10 : le jour de la fenêtre
    assert club.capacites.instance(club.capacites.patron(A)).statut == "ONE_AWAY"


def test_un_attribut_absent_vaut_zero(club):
    with pytest.raises(Invalide, match="places ≥ 12"):
        club.repondre_ask(md.PAULINE, _ask(club).id, True)


def test_le_texte_de_l_ask_dit_jusqu_a_quand(club):
    assert _ask(club).texte.endswith("Usage jusqu'au 09.10.")


def test_au_dela_d_une_piece_rien_n_est_expose_et_c_est_dit(club):
    inst = club.capacites.instance(club.capacites.patron("atelier_cyber"))
    assert (inst.statut, inst.distance, inst.ask, inst.perdus) == (None, None, None, [])
    assert inst.hypotheses == ["disponibilités et attributs DÉCLARÉS par les membres, non vérifiés par le système"]


def test_une_piece_consentie_perdue_a_une_piece_pres_est_degradee(club):
    club.repondre_ask(md.PAULINE, _ask(club).id, True, {"places": 14})
    interp = club.capacites.instance(club.capacites.patron(A)).liaisons["interp"]
    club.banc.retirer_offre(md.ANNA, interp)                             # personne d'autre n'interprète le 09.10
    inst = club.capacites.instance(club.capacites.patron(A))
    assert (inst.statut, inst.distance, inst.manquant) == ("DEGRADED", 1, "interp")
    assert inst.perdus == ["interp : offre retirée"] and inst.ask is not None and inst.ask.emplacement == "interp"


def test_la_composition_libre_prefere_le_creneau_qui_garde_un_consentement():
    """Salle A (non consentie) dès 10:00 ; salle B (consentie) seulement à partir de 11:00 : la composition retenue est
    celle de 11:00, qui garde le consentement — pas la première dans l'ordre du temps."""
    b = Banc(Memoire(), lambda: J, lambda pid: f"org-{pid}")
    p = Patron(id="p_ordre", version=1, titre="Capacité ordonnée", auteur="Commission du Club", fictif=True,
               fenetre=Fenetre(jour=JOUR, debut="10:00", fin="12:00"), duree_min=60,
               emplacements=[Emplacement(id="lieu", role="lieu", nature="lieu", libelle="Un lieu", geste="Prêter un lieu"),
                             Emplacement(id="objet", role="objet", nature="objet", libelle="Un objet", geste="Prêter un objet")])
    b.publier_offre("m1", "lieu", "Salle A", 1, J, JOUR, plages=[Plage(jour=JOUR, debut="10:00", fin="12:00")])
    sb = b.publier_offre("m2", "lieu", "Salle B", 1, J, JOUR, plages=[Plage(jour=JOUR, debut="11:00", fin="12:00")])
    b.publier_offre("m3", "objet", "Objet", 1, J, JOUR, plages=[Plage(jour=JOUR, debut="10:00", fin="12:00")])
    b.consentir_finalite("m2", p.id, "lieu", sb, p.portee("lieu"), JOUR)
    inst = Registre(b, [p], lambda: J).instance(p)
    assert inst.statut == "CONSENTED" and inst.liaisons["lieu"] == sb and inst.creneau.debut == "11:00"


def test_une_competence_retiree_puis_redeclaree_garde_sa_date_de_retrait(club):
    seq = club.journal.evenements()[-1].seq
    club.modifier_profil(md.LEA, retirer_capacite="traduction")
    p = club.profil(md.LEA)
    club._remplacer_profil(p.model_copy(update={"offre": [*p.offre, club._profils_depart[md.LEA].offre[0]]}))
    trad = [c for c in club.claims() if c.membre == md.LEA and c.id.startswith("profil:") and c.concept == "traduction"]
    assert [c.superseded_at for c in trad] == [seq + 1, None] and trad[1].recorded_at == seq + 2


# ---------------------------------------------------------------------- campagne après F26 / F31 (2026-10-01)
def test_active_par_la_seconde_piece_consentie_quand_la_premiere_ne_tient_pas_le_creneau():
    """Le chemin ACTIVE cherche une composition dont CHAQUE pièce est consentie, à n'importe quel créneau. Deux salles
    consenties : la première (A) ne tient pas le seul créneau où l'objet est libre, la seconde (B) oui ; une troisième
    salle, NON consentie, ressemble davantage au geste. Sans ce chemin, la composition libre prend la troisième et la
    capacité reste « consentements en cours » (mutants _composer 27, 28, 40 de la campagne du 2026-10-01)."""
    b = Banc(Memoire(), lambda: J, lambda pid: f"org-{pid}")
    p = Patron(id="p_creneau", version=1, titre="Capacité à un créneau commun", auteur="Commission du Club", fictif=True,
               fenetre=Fenetre(jour=JOUR, debut="10:00", fin="14:00"), duree_min=60,
               emplacements=[Emplacement(id="lieu", role="lieu", nature="lieu", libelle="Un lieu", geste="Prêter un lieu"),
                             Emplacement(id="objet", role="objet", nature="objet", libelle="Un objet", geste="Prêter un objet")])
    a = b.publier_offre("m1", "lieu", "Salle A", 1, J, JOUR, plages=[Plage(jour=JOUR, debut="10:00", fin="11:00")])
    bb = b.publier_offre("m2", "lieu", "Salle B", 1, J, JOUR, plages=[Plage(jour=JOUR, debut="13:00", fin="14:00")])
    b.publier_offre("m4", "lieu", "Lieu à prêter", 1, J, JOUR, plages=[Plage(jour=JOUR, debut="10:00", fin="14:00")])
    o = b.publier_offre("m3", "objet", "Objet", 1, J, JOUR, plages=[Plage(jour=JOUR, debut="13:00", fin="14:00")])
    for membre, emp, oid in (("m1", "lieu", a), ("m2", "lieu", bb), ("m3", "objet", o)):
        b.consentir_finalite(membre, p.id, emp, oid, p.portee(emp), JOUR)
    inst = Registre(b, [p], lambda: J).instance(p)
    assert (inst.statut, inst.liaisons) == ("ACTIVE", {"lieu": bb, "objet": o})


def test_une_reponse_journalisee_avant_la_provenance_reste_declaree_par_le_membre():
    """Un journal écrit AVANT F31 (ASK_REPONSE sans clé « provenance ») : la pièce reste SELF_DECLARED, jamais une
    provenance inventée (mutants x_index_claims 99, 100)."""
    m = Memoire()
    b = Banc(m, lambda: J, lambda pid: f"org-{pid}")
    oid = b.publier_offre("m1", "objet", "Un minibus", 1, J, JOUR, attributs={"places": 14})
    b._ecrire("ASK_REPONSE", ["m1"], ask="p:1:minibus", oui=True, offre=oid)
    assert [x.provenance for x in index_claims(m, {}) if x.id.startswith(oid)] == ["SELF_DECLARED"]
