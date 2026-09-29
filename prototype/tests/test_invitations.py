"""Invitation ciblée : optimalité EXACTE (contre force brute), budget, capacité, preuve, abstention."""
import itertools
import random

from adaptateurs.club import invitations as inv


def _force_brute(invitables, presents, aides, budget, capacite):
    meilleur = 0
    for k in range(min(budget, len(invitables)) + 1):
        for choix in itertools.combinations(invitables, k):
            meilleur = max(meilleur, inv.servis(list(choix), presents, aides, capacite))
    return meilleur


def test_optimal_contre_force_brute_sur_instances_aleatoires():
    for s in range(60):
        r = random.Random(s)
        invit = [f"i{j}" for j in range(r.randint(1, 7))]
        pres = [f"p{j}" for j in range(r.randint(1, 4))]
        aides = {frozenset((x, y)) for x in invit for y in pres if r.random() < 0.35}
        b, c = r.randint(1, 5), r.randint(1, 2)
        out = inv.choisir(invit, pres, aides, b, c)
        assert out["servis"] == _force_brute(invit, pres, aides, b, c), s
        assert len(out["invites"]) <= b
        charge = {}
        for x, y in out["affectation"].items():
            assert frozenset((x, y)) in aides                      # chaque invité a une aide PROUVÉE avec son hôte
            charge[y] = charge.get(y, 0) + 1
        assert all(v <= c for v in charge.values())                # capacité d'accueil respectée


def test_le_flot_evite_la_contention_que_le_classement_simple_subit():
    # i1 et i2 n'ont qu'un hôte possible (p1) ; i3 peut aller chez p1 ou p2. Classement « le plus d'aides » : i3 d'abord
    aides = {frozenset(("i1", "p1")), frozenset(("i2", "p2")), frozenset(("i3", "p1")), frozenset(("i3", "p2"))}
    assert inv.choisir(["i1", "i2", "i3"], ["p1", "p2"], aides, budget=2)["servis"] == 2
    assert inv.servis(["i3", "i1"], ["p1", "p2"], aides) == 2
    assert inv.choisir(["i1", "i2", "i3"], ["p1", "p2"], aides, budget=3)["servis"] == 2   # 2 hôtes de capacité 1


def test_ne_rien_faire_sans_aide_prouvee():
    out = inv.choisir(["i1", "i2"], ["p1"], set(), budget=5)
    assert out["decision"] == "NE_RIEN_FAIRE" and out["invites"] == []
