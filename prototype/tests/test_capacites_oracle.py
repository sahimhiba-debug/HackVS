"""ORACLE EN FORCE BRUTE du registre des capacités (B4) : sur des mondes aléatoires PETITS (graines fixes, donc
rejouables), une réimplémentation naïve et indépendante — tous les créneaux au quart d'heure × toutes les affectations
injectives offres → emplacements — dit si la capacité existe (distance 0), s'il manque une pièce (distance 1), et si
une composition ENTIÈREMENT consentie existe (ACTIVE). Le registre doit dire exactement la même chose, et chaque
liaison qu'il propose doit satisfaire l'oracle. L'oracle n'appelle aucune fonction du banc : il relit les règles.
Données FICTIVES, générées."""
import itertools
import random
from datetime import date, timedelta

import pytest

from intelligence.capacites import Emplacement, Fenetre, Patron, Registre
from intelligence.essai import Banc, Plage, minutes
from plateforme.memoire import Memoire

J = date(2026, 10, 6)
JOUR = J + timedelta(days=2)
AUTEURS = ["m1", "m2", "m3", "m4"]
NATURES = ["lieu", "objet", "competence"]
CONCEPTS = [None, "traduction", "logistique"]


def _heure(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def monde(graine: int):
    rnd = random.Random(graine)
    b = Banc(Memoire(), lambda: J, lambda pid: f"org-{pid}")
    debut = rnd.choice(range(8 * 60, 14 * 60 + 1, 15))
    fenetre = (debut, debut + rnd.choice([90, 120, 180, 240]))
    duree = rnd.choice([30, 45, 60])
    emps = []
    for i in range(rnd.choice([2, 2, 3, 3, 4])):
        nat = rnd.choice(NATURES)
        emps.append(Emplacement(id="e" + "abcd"[i], role=f"r{i}", nature=nat, concept=rnd.choice(CONCEPTS) if nat == "competence" else None,  # type: ignore[arg-type]
                                libelle=f"pièce {i}", geste=f"geste {i}", minimums={"places": rnd.choice([5, 10])} if rnd.random() < 0.3 else {}))
    p = Patron(id="p_test", version=1, titre="Capacité de test", auteur="Commission du Club", fictif=True,
               fenetre=Fenetre(jour=JOUR, debut=_heure(fenetre[0]), fin=_heure(fenetre[1])), duree_min=duree, emplacements=emps)
    for k in range(rnd.randint(2, 8)):
        e = rnd.choice(emps)
        nat = e.nature if rnd.random() < 0.8 else rnd.choice(NATURES)
        concept = (e.concept if rnd.random() < 0.8 else rnd.choice(CONCEPTS)) if nat == "competence" else None
        d = rnd.choice(range(fenetre[0] - 60, fenetre[1], 15))
        plages = [Plage(jour=JOUR if rnd.random() < 0.9 else JOUR + timedelta(days=1), debut=_heure(max(0, d)),
                        fin=_heure(min(23 * 60 + 45, d + rnd.choice([30, 60, 90, 180]))))] if rnd.random() < 0.9 else []
        oid = b.publier_offre(rnd.choice(AUTEURS), nat, f"offre {k}", 1, J, JOUR + timedelta(days=rnd.choice([-1, 0, 3])),
                              duree_max_min=rnd.choice([None, None, 30, 60]), concept=concept, plages=plages,
                              attributs={"places": rnd.choice([4, 8, 12])} if rnd.random() < 0.5 else None)
        if rnd.random() < 0.5:                                  # un consentement de finalité, pour un emplacement au hasard
            emp = rnd.choice(emps).id
            if b.etat_offre(oid) == "active":
                b.consentir_finalite(b.offre(oid).auteur, p.id, emp, oid, p.portee(emp), JOUR)
    return b, p


# ---------------------------------------------------------------------- l'oracle : les règles relues, naïvement
def couvre(o, e, jour: date, debut: int, duree: int) -> bool:
    return (o.du <= J <= o.au and JOUR <= o.au and o.nature == e.nature and (e.concept is None or o.concept == e.concept)
            and all(o.attributs.get(k, 0) >= v for k, v in e.minimums.items())
            and (o.duree_max_min is None or o.duree_max_min >= duree)
            and any(pl.jour == jour and minutes(pl.debut) <= debut and debut + duree <= minutes(pl.fin) for pl in o.plages))


def compositions(b, p, emps, permis=None):
    """Toutes les compositions (créneau, affectation) des emplacements `emps` — `permis[e]` restreint les offres."""
    f = p.fenetre
    for debut in range(minutes(f.debut), minutes(f.fin) - p.duree_min + 1, 15):
        for choix in itertools.permutations(b.offres(), len(emps)):
            if len({o.auteur for o in choix}) < len(emps):
                continue
            if all(couvre(o, e, f.jour, debut, p.duree_min) and (permis is None or o.id in permis.get(e.id, set()))
                   for o, e in zip(choix, emps, strict=True)):
                yield debut, {e.id: o.id for o, e in zip(choix, emps, strict=True)}


def oracle(b, p):
    emps = p.emplacements
    consentis: dict[str, set[str]] = {}
    for ev in b.consentements_finalite(p.id):
        if b.raison_consentement(ev, p.portee(ev.donnees["emplacement"])) is None:
            consentis.setdefault(ev.donnees["emplacement"], set()).add(ev.donnees["offre"])
    if next(compositions(b, p, emps), None):
        return 0, next(compositions(b, p, emps, consentis), None) is not None
    un = any(next(compositions(b, p, [e for e in emps if e.id != x.id]), None) for x in emps)
    return (1 if un else None), False


# 300 graines consécutives + celles qui, sur 3 000, ont trouvé un défaut de l'ancien code (compositeur GLOUTON : une
# composition complète manquée → « il manque une pièce » à tort ; registre : un créneau entièrement consenti ignoré
# au profit du premier créneau composable → « ACTIVE » manqué). Rejouées ici pour toujours.
TROUVEES = [377, 759, 1270, 1483, 1794, 1909, 2503, 2655, 2659, 2672, 2903, 2981]
GRAINES = list(range(300)) + TROUVEES


@pytest.mark.parametrize("graine", GRAINES)
def test_le_registre_dit_ce_que_dit_l_oracle(graine):
    b, p = monde(graine)
    inst = Registre(b, [p], lambda: J).instance(p)
    distance, active = oracle(b, p)
    assert inst.distance == distance, (graine, inst.distance, distance)
    assert (inst.statut == "ACTIVE") == active, (graine, inst.statut, active)
    if inst.distance is not None:                               # chaque liaison proposée respecte les règles relues
        c = inst.creneau
        lies = {k: v for k, v in inst.liaisons.items() if v}
        assert len({b.offre(v).auteur for v in lies.values()}) == len(lies)
        for e in p.emplacements:
            if e.id in lies:
                assert couvre(b.offre(lies[e.id]), e, c.jour, minutes(c.debut), p.duree_min), (graine, e.id)
    if inst.distance == 1:
        assert inst.ask is not None and inst.manquant == inst.ask.emplacement and inst.liaisons[inst.manquant] is None


def test_les_mondes_exercent_tous_les_cas():
    """Garde contre un oracle vacueux : les graines produisent des capacités à distance 0, 1 et au-delà, et des ACTIVE."""
    vus = {oracle(*monde(g)) for g in GRAINES}
    assert {(0, True), (0, False), (1, False), (None, False)} <= vus, vus
