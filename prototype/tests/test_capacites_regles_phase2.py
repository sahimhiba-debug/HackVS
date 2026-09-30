"""Règles fines de la Phase 2 (retrait, reçus, recomposition, hypothèses, pièces critiques, Pulse), écrites pour tuer
les mutants SURVIVANTS de la campagne de mutation de fin de Phase 2 : chaque test correspond à un comportement que la
suite ne distinguait pas encore d'une variante fausse. Données FICTIVES."""
from datetime import timedelta

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.capacites import HypotheticalClaim, Patron
from intelligence.demo import NICOLAS, Demo
from intelligence.erreurs import Introuvable
from intelligence.essai import Plage

TAX = charger_taxonomie()
A = "delegation_acheteurs"
VENDREDI = md.JOUR_SCENE + timedelta(days=1)


@pytest.fixture
def club():
    return Demo(TAX).club


def _active(c):
    c.repondre_ask(md.PAULINE, c.asks_pour(md.PAULINE)[0][1], True, {"places": 14})


# ---------------------------------------------------------------------- reçus
def test_le_recu_complet_de_chaque_membre_quel_que_soit_son_rang(club):
    _active(club)
    anna = club.capacites.recus(md.ANNA)                    # s10 : après s01 et s04 dans l'ordre des consentements
    assert len(anna) == 1
    r = anna[0]
    assert {k: r[k] for k in ("finalite", "titre", "version", "piece", "offre", "donne_le", "jusqu_au", "etat", "retire_le", "revocable")} == {
        "finalite": A, "titre": "Accueillir une délégation d'acheteurs germanophones", "version": 1,
        "piece": "Une interprétation français–allemand", "offre": "Interprétation français–allemand, une demi-journée",
        "donne_le": "2026-10-06", "jusqu_au": "2026-10-09", "etat": "valable", "retire_le": None, "revocable": True}
    assert len(r["reference"]) == 12 and r["fenetre"] == {"jour": "2026-10-09", "debut": "13:00", "fin": "18:00"}
    assert r["partage"].startswith("Votre offre n'est utilisée que pour cette capacité")


def test_le_recu_dit_la_date_du_retrait(club):
    _active(club)
    club.avancer(1)
    club.retirer_consentement(md.PAULINE, A)
    r = club.capacites.recus(md.PAULINE)[0]
    assert (r["etat"], r["retire_le"], r["revocable"]) == ("consentement retiré", "2026-10-07", False)


def test_le_recu_d_une_piece_disparue_du_patron(club):
    p = club.capacites.patron(A)
    club.capacites.patrons[A] = Patron(**(p.model_dump() | {"emplacements": [e.model_dump() for e in p.emplacements if e.id != "salle"]}))
    r = club.capacites.recus(NICOLAS)[0]
    assert r["piece"] == "Une salle de 15 places ou plus" and r["etat"] == "cette pièce n'existe plus dans la capacité"


def test_deux_pieces_consenties_par_une_meme_personne_deux_recus(club):
    b, p = club.banc, club.capacites.patron(A)
    j = club.jour
    o1 = b.publier_offre(md.MARKUS, "lieu", "Salle A", 1, j, VENDREDI, attributs={"places": 20}, plages=[Plage(jour=VENDREDI, debut="13:00", fin="18:00")])
    o2 = b.publier_offre(md.MARKUS, "objet", "Bus B", 1, j, VENDREDI, attributs={"places": 20}, plages=[Plage(jour=VENDREDI, debut="13:00", fin="18:00")])
    b.consentir_finalite(md.MARKUS, A, "salle", o1, p.portee("salle"), VENDREDI)
    b.consentir_finalite(md.MARKUS, A, "minibus", o2, p.portee("minibus"), VENDREDI)
    assert sorted((r["piece"], r["offre"]) for r in club.capacites.recus(md.MARKUS)) == [
        ("Un minibus de 12 places ou plus", "Bus B"), ("Une salle de 15 places ou plus", "Salle A")]


def test_rien_a_retirer_est_dit(club):
    with pytest.raises(Introuvable, match="aucun consentement en cours pour cette capacité"):
        club.retirer_consentement(md.PAULINE, A)


# ---------------------------------------------------------------------- recomposition : textes et types exacts
def test_recomposition_demander_et_consentir_textes_exacts(club):
    _active(club)
    inst = club.retirer_consentement(md.PAULINE, A)
    assert inst.recomposition == {"type": "demander", "pieces": ["minibus"], "a_decider": ["un membre qui répond à la demande"],
                                  "texte": "Il manque de nouveau : Un minibus de 12 places ou plus. Une demande est adressée aux membres "
                                           "qui peuvent la fournir."}
    club.banc.publier_offre(md.MARKUS, "objet", "Bus", 1, club.jour, VENDREDI, attributs={"places": 20},
                            plages=[Plage(jour=VENDREDI, debut="13:00", fin="18:00")])
    inst = club.capacites.instance(club.capacites.patron(A))
    assert inst.recomposition == {"type": "consentir", "pieces": ["minibus"], "a_decider": ["la personne qui offre cette pièce"],
                                  "texte": "Une autre pièce existe pour : Un minibus de 12 places ou plus. Elle ne comptera qu'avec le "
                                           "consentement de la personne qui l'offre."}


def test_aucune_solution_sure_ce_qu_on_ignore_est_exact(club):
    _active(club)
    club.retirer_consentement(md.ANNA, A)
    inst = club.retirer_consentement(NICOLAS, A)
    assert inst.sans_solution["ignore"] == ["si d'autres membres pourraient fournir Une salle de 15 places ou plus, Une interprétation "
                                            "français–allemand : personne ne l'a déclaré pour cette fenêtre"]


# ---------------------------------------------------------------------- hypothèses et pièces critiques
def _vendredi(nature, concept=None, attributs=None):
    return HypotheticalClaim(nature=nature, concept=concept, attributs=attributs or {}, plages=[Plage(jour=VENDREDI, debut="13:00", fin="18:00")],
                             du=md.JOUR_SCENE - timedelta(days=2), au=VENDREDI)


def test_une_hypothese_porte_son_concept(club):
    _active(club)
    club.retirer_consentement(md.ANNA, A)                   # la voix manque ; seule une compétence « traduction » la comble
    club.banc.retirer_offre(md.ANNA, next(o.id for o in club.banc.offres() if o.auteur == md.ANNA and o.plages and o.plages[0].jour == VENDREDI))
    si = lambda h: {i.finalite: i.distance for i in club.capacites.status_if([h])}[A]  # noqa: E731
    assert si(_vendredi("competence", "traduction")) == 0 and si(_vendredi("competence", None)) == 1


def test_deux_hypotheses_a_la_fois(club):
    _active(club)
    club.retirer_consentement(md.ANNA, A)
    club.retirer_consentement(NICOLAS, A)                  # il manque DEUX pièces : il faut les deux hypothèses
    h1, h2 = _vendredi("lieu", attributs={"places": 30}), _vendredi("competence", "traduction")
    assert {i.finalite: i.distance for i in club.capacites.status_if([h1])}[A] == 1        # une seule ne suffit pas
    assert {i.finalite: i.distance for i in club.capacites.status_if([h1, h2])}[A] == 0


def test_une_alternative_d_un_membre_retire_ne_rend_pas_une_piece_non_critique(club):
    _active(club)
    club.banc.publier_offre(md.MARKUS, "objet", "Bus", 1, club.jour, VENDREDI, attributs={"places": 20},
                            plages=[Plage(jour=VENDREDI, debut="13:00", fin="18:00")])
    assert "minibus" not in club.capacites.instance(club.capacites.patron(A)).critiques      # le bus de Markus remplacerait
    p = club.capacites.patron(A)
    club.banc.consentir_finalite(md.MARKUS, A, "minibus", club.banc.offres()[-1].id, p.portee("minibus"), VENDREDI)
    club.retirer_consentement(md.MARKUS, A)                                                   # Markus s'est retiré de CETTE finalité
    assert "minibus" in club.capacites.instance(club.capacites.patron(A)).critiques          # son bus ne compte plus comme alternative


def test_la_recherche_bornee_est_dite_mot_pour_mot():
    from intelligence.capacites import Registre
    from tests.test_capacites_oracle import J, monde
    b, p = monde(3)
    b.BUDGET_NOEUDS = 1
    assert "recherche bornée atteinte : une composition a pu échapper au calcul (absence non garantie)" in \
        Registre(b, [p], lambda: J).instance(p).hypotheses


# ---------------------------------------------------------------------- Pulse
def test_pulse_a_une_piece_pres_et_lignes_exactes(club):
    p = club.pulse(0)
    assert p["a_une_piece"] == [{"finalite": A, "titre": "Accueillir une délégation d'acheteurs germanophones", "avant": None,
                                 "apres": "ONE_AWAY"}]
    s = club.journal.evenements()[-1].seq
    assert club.pulse(s)["a_une_piece"] == []                                                # déjà à une pièce : rien de nouveau
    _active(club)
    assert club.pulse(s)["apparues"] == [{"finalite": A, "titre": "Accueillir une délégation d'acheteurs germanophones",
                                          "avant": "ONE_AWAY", "apres": "ACTIVE"}]
