"""PULSE : ce qui a changé dans ce que le Club peut faire, entre deux positions du journal — chacune calculée par
REJEU (jamais stockée), sans modèle de langage, sans rien écrire. Propriété de fond : l'état rejoué à une position
est EXACTEMENT celui qu'on avait en direct à cette position (même empreinte de l'état complet). Données FICTIVES."""
import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.capacites import pulse_diff
from intelligence.demo import Demo
from intelligence.erreurs import Invalide
from intelligence.ia import Intelligence

TAX = charger_taxonomie()
A = "delegation_acheteurs"


class Espion:
    nom, modele = "espion", "e1"

    def __init__(self):
        self.envois = 0

    def completer(self, s, m, sch):
        self.envois += 1
        return "{}"


@pytest.fixture
def club():
    return Demo(TAX).club


def _seq(c) -> int:
    return c.journal.evenements()[-1].seq


def _titres(p, cle):
    return [x["finalite"] for x in p[cle]]


def test_apparue_eteinte_recomposee_fragile(club):
    s0 = _seq(club)
    club.repondre_ask(md.PAULINE, club.asks_pour(md.PAULINE)[0][1], True, {"places": 14})
    s1 = _seq(club)
    p = club.pulse(s0)
    assert _titres(p, "apparues") == [A] and _titres(p, "fragiles") == [A] and p["eteintes"] == []
    assert p["depuis"]["position"] == s0 and p["calcul"].startswith("par rejeu")
    club.retirer_consentement(md.PAULINE, A)
    s2 = _seq(club)
    assert _titres(club.pulse(s1), "eteintes") == [A]
    club.repondre_ask(md.MARKUS, club.asks_pour(md.MARKUS)[0][1], True, {"places": 16})
    p = club.pulse(s1)
    assert _titres(p, "recomposees") == [A] and p["apparues"] == [] and p["eteintes"] == []    # active → active, autres pièces
    assert _titres(club.pulse(s2), "apparues") == [A]
    texte = str(club.pulse(s0))
    for x in ("Pauline", "Darbellay", "Markus", md.PAULINE, md.MARKUS):
        assert x not in texte


def test_rejouer_une_position_redonne_exactement_l_etat_de_ce_moment(club):
    captures = [(_seq(club), club.empreinte_etat())]
    club.repondre_ask(md.PAULINE, club.asks_pour(md.PAULINE)[0][1], True, {"places": 14})
    captures.append((_seq(club), club.empreinte_etat()))
    club.modifier_profil(md.ANNA, disponible=False)
    captures.append((_seq(club), club.empreinte_etat()))
    club.avancer(2)
    captures.append((_seq(club), club.empreinte_etat()))
    club.retirer_consentement(md.PAULINE, A)
    captures.append((_seq(club), club.empreinte_etat()))
    for seq, empreinte in captures:
        assert club.au(seq).empreinte_etat() == empreinte, seq
    assert len({e for _, e in captures}) == len(captures)                      # non vacueux : chaque étape a changé l'état


def test_le_rejeu_n_appelle_aucun_modele_et_n_ecrit_rien():
    espion = Espion()
    c = Demo(TAX, ia=Intelligence(TAX, espion)).club
    s0 = _seq(c)
    c.repondre_ask(md.PAULINE, c.asks_pour(md.PAULINE)[0][1], True, {"places": 14})
    avant, envois = c.journal.empreinte(), espion.envois
    c.pulse(s0)
    c.au(s0).capacites.projeter()
    assert espion.envois == envois and c.journal.empreinte() == avant


def test_positions_hors_du_journal(club):
    with pytest.raises(Invalide):
        club.pulse(-1)
    with pytest.raises(Invalide):
        club.pulse(0, _seq(club) + 5)


def test_pulse_diff_pur_sur_listes_vides():
    assert pulse_diff([], []) == {"apparues": [], "eteintes": [], "recomposees": [], "fragiles": [], "a_une_piece": []}
