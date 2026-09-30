"""« ET SI » (I3), LEVIER et COMPOSANTS CRITIQUES (I1). Une pièce hypothétique est typée à part (HypotheticalClaim),
n'écrit rien, ne porte aucun consentement et disparaît après le calcul. Le levier et les composants critiques sont
DÉRIVÉS du compositeur partagé — et vérifiés ici contre l'oracle en force brute, qui ne l'utilise pas. FICTIF."""
import random
from datetime import timedelta

import pytest

from app.taxonomy import charger_taxonomie
from intelligence.capacites import HypotheticalClaim, Patron, Registre
from intelligence.demo import Demo
from intelligence.essai import Plage
from tests.test_capacites_oracle import J, JOUR, compositions, monde, oracle

TAX = charger_taxonomie()
A = "delegation_acheteurs"


@pytest.fixture
def club():
    return Demo(TAX).club


def _minibus(c, places=14):
    return HypotheticalClaim(nature="objet", quoi="Un minibus imaginé", attributs={"places": places},
                             plages=[Plage(jour=JOUR + timedelta(days=1), debut="13:00", fin="18:00")], du=c.jour, au=JOUR + timedelta(days=1))


def test_une_hypothese_n_ecrit_rien_ne_consent_rien_et_disparait(club):
    avant, offres = club.journal.empreinte(), len(club.banc.offres())
    si = {i.finalite: i for i in club.capacites.status_if([_minibus(club)])}
    a = si[A]
    assert a.hypothetique and a.distance == 0
    assert a.statut == "CONSENTED" and a.consentements["minibus"] == "consentement à demander"   # jamais ACTIVE par hypothèse
    assert club.journal.empreinte() == avant and len(club.banc.offres()) == offres
    assert club.capacites.instance(club.capacites.patron(A)).statut == "ONE_AWAY"                 # la réalité n'a pas bougé
    assert not any(o.id.startswith("hyp-") for o in club.banc.offres())


def test_l_hypothese_disparait_meme_sur_erreur(club):
    with pytest.raises(RuntimeError):
        with club.banc.hypothese([_minibus(club).offre(1)]):
            assert club.banc.hypothetique("hyp-1")
            raise RuntimeError("panne au milieu")
    assert not club.banc.hypothetique("hyp-1") and all(o.id != "hyp-1" for o in club.banc.offres())


def test_une_hypothese_insuffisante_ne_debloque_rien(club):
    assert {i.finalite: i.distance for i in club.capacites.status_if([_minibus(club, places=8)])}[A] == 1


def test_le_levier_de_la_demande_de_la_demonstration(club):
    ask = club.capacites.projeter()[2].ask
    assert ask is not None and (ask.levier, ask.debloque) == (1, ["Accueillir une délégation d'acheteurs germanophones"])


def _deux_patrons(graine):
    """Deux patrons sur le MÊME banc (offres de la graine) : une même pièce peut en débloquer deux."""
    b, p1 = monde(graine)
    _, autre = monde(graine + 10_000)
    p2 = Patron(**(autre.model_dump() | {"id": "p_second", "titre": "Seconde capacité"}))
    if random.Random(graine).random() < 0.5:                  # la moitié du temps : même besoin, pour exercer un levier de 2
        p2 = Patron(**(p1.model_dump() | {"id": "p_second", "titre": "Seconde capacité"}))
    return b, [p1, p2]


@pytest.mark.parametrize("graine", range(150))
def test_levier_et_composants_critiques_contre_l_oracle(graine):
    b, patrons = _deux_patrons(graine)
    r = Registre(b, patrons, lambda: J)
    projection = r.projeter()
    avant = {p.id: oracle(b, p)[0] for p in patrons}
    for inst in projection:
        p = next(x for x in patrons if x.id == inst.finalite)
        if inst.ask is not None:                               # levier : combien de patrons l'oracle voit passer à 0
            h = HypotheticalClaim(nature=inst.ask.nature, concept=inst.ask.concept, attributs=dict(inst.ask.minimums),  # type: ignore[arg-type]
                                  plages=[Plage(jour=inst.ask.creneau.jour, debut=inst.ask.creneau.debut, fin=inst.ask.creneau.fin)],
                                  du=J, au=inst.ask.expire)
            with b.hypothese([h.offre(1)]):
                apres = {x.id: oracle(b, x)[0] for x in patrons}
            attendu = sorted(x.titre for x in patrons if apres[x.id] == 0 and avant[x.id] != 0)
            assert inst.ask.levier == len(attendu) and sorted(inst.ask.debloque) == attendu, (graine, inst.ask, attendu)
        if inst.distance == 0:                                 # critique : l'oracle ne trouve plus rien sans cette pièce
            tous = {o.id for o in b.offres()}
            for k, oid in inst.liaisons.items():
                seul = next(compositions(b, p, p.emplacements, {e.id: tous - {oid} for e in p.emplacements}), None)
                assert (k in inst.critiques) == (seul is None), (graine, k)


def test_les_mondes_exercent_levier_et_criticite():
    leviers, critiques, robustes = set(), 0, 0
    for g in range(150):
        b, patrons = _deux_patrons(g)
        for i in Registre(b, patrons, lambda: J).projeter():
            if i.ask:
                leviers.add(i.ask.levier)
            if i.distance == 0:
                critiques += len(i.critiques)
                robustes += len([k for k, v in i.liaisons.items() if v and k not in i.critiques])
    assert {1, 2} <= leviers and critiques > 0, (leviers, critiques, robustes)


def test_une_piece_qui_a_une_alternative_n_est_pas_critique(club):
    """Jeudi 08.10 : deux lieux déclarés couvrent la présentation ; la voix et le public, non."""
    inst = club.capacites.instance(club.capacites.patron("presentation_germanophone"))
    assert inst.distance == 0 and inst.critiques == ["voix", "public"]
