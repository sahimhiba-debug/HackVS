"""Garde-fou de synthèse : un texte (généré ou non) n'est montré que s'il ne cite que des faits fournis."""
import pytest

from adaptateurs.club import cycle as cy
from adaptateurs.club import diagnostic as dg
from adaptateurs.club import synthese as sy
from app.taxonomy import charger_taxonomie
from eval.perf_echelle import generer

TAX = charger_taxonomie()


@pytest.fixture(scope="module")
def diag():
    p, m, t = generer(120, 8)
    return dg.diagnostic(m, p, cy.besoins_publies(m, t), TAX, t), {x.id for x in p}


def test_le_gabarit_est_fidele_et_couvre_les_phenomenes(diag):
    d, ids = diag
    v = sy.verifier(sy.gabarit(d), d, ids)
    assert v["fidele"], v
    assert v["couverture"].split("/")[0] == v["couverture"].split("/")[1] or len(d["diagnostiquer"]["phenomenes"]) > 4


def test_un_nombre_invente_est_detecte_et_le_texte_rejete(diag):
    d, ids = diag
    e = d["comprendre"]["etat"]
    faux = f"Le réseau compte {e['membres']} membres dont 9871 très actifs ; tout va bien."
    v = sy.verifier(faux, d, ids)
    assert not v["fidele"] and "9871" in v["nombres_inventes"]
    r = sy.retenir(faux, d, ids)
    assert r["source"].startswith("gabarit") and r["texte"] == sy.gabarit(d)


def test_un_membre_cite_hors_des_faits_est_detecte(diag):
    d, ids = diag
    absent = next(x for x in sorted(ids) if x not in str(d))
    v = sy.verifier(f"Nous recommandons de contacter {absent}.", d, ids)
    assert not v["fidele"] and v["identifiants_inventes"] == [absent]


def test_un_texte_fidele_reformule_est_accepte(diag):
    d, ids = diag
    e = d["comprendre"]["etat"]
    texte = f"Sur {e['membres']} membres, {e['avec_relation_actuelle']} gardent une relation vivante."
    r = sy.retenir(texte, d, ids)
    assert r["source"].startswith("IA") and r["controle"]["fidele"]


def test_sans_modele_le_gabarit_est_affiche_et_dit_pourquoi(diag):
    d, ids = diag
    assert sy.retenir(None, d, ids)["source"] == "gabarit (aucun modèle configuré)"


@pytest.mark.parametrize("texte,motif", [
    ("Neuf mille membres sont isolés.", "nombres_en_lettres"),
    ("Le réseau est parfaitement sain, aucun membre n'est isolé.", "contradictions"),
    ("Tous les membres sont reliés en un seul groupe.", "contradictions"),
])
def test_red_team_lettres_et_contradictions_sans_nombre(diag, texte, motif):
    """Trous trouvés en attaquant le vérificateur : nombres en lettres, affirmation fausse sans aucun nombre."""
    d, ids = diag
    presents = {p["phenomene"] for p in d["diagnostiquer"]["phenomenes"]}
    assert {"ISOLEMENT", "FRAGMENTATION"} <= presents
    v = sy.verifier(texte, d, ids)
    assert not v["fidele"] and v[motif], v


def test_un_nombre_derive_comme_une_longueur_de_liste_n_est_pas_une_invention(diag):
    """Faux positif trouvé par le benchmark G2 : « 15 plans non dominés » (longueur d'une liste des faits) était rejeté."""
    d, ids = diag
    n = len(d["agir"]["front"])
    assert sy.verifier(f"{n} plans non dominés sont proposés.", d, ids)["fidele"]
