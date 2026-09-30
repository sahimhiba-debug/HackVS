"""NON-RÉGRESSION DU COMPOSITEUR : la recherche complète (retour arrière, `ff6d0ec`) doit donner EXACTEMENT la même
équipe que l'ancien choix glouton partout où celui-ci en trouvait une — mêmes entrées, mêmes équipes. Seuls les échecs
à tort de l'ancien compositeur peuvent devenir des solutions. La référence ci-dessous est l'algorithme d'avant, recopié
tel quel (commit `c3c4678`, `Banc._composer`). Contextes : essais réels de la démonstration (porteur, gestes gardés,
refus) et mondes du registre (hors essai, offres gardées = consenties). Données FICTIVES."""
from datetime import timedelta

import pytest

from app.taxonomy import charger_taxonomie
from intelligence.demo import Demo
from intelligence.essai import PAS_MIN, Creneau, heure, minutes
from tests.test_capacites_oracle import TROUVEES, J, monde

TAX = charger_taxonomie()


def glouton(b, eid, p, c, garder):
    """L'ANCIEN `Banc._composer`, recopié tel quel (seule différence : `b.` au lieu de `self.`)."""
    etapes = [e.model_copy(update={"duree_min": min(e.duree_min, c.duree_min)}) for e in p.etapes]
    par_id = {e.id: e for e in etapes}
    gardees = {k: o for k, o in garder.items()
               if o is not None and b.offre_couvre(o, par_id[k], p.echeance, sauf=eid, creneau=c) is None}
    choix: dict = {}
    auteurs: set = set()
    remplaces = []
    for e in etapes:
        if e.invitation and e.contributeur and garder.get(e.id) is None:
            choix[e.id] = None
            continue
        o = gardees.get(e.id)
        if o is None or o.auteur in auteurs:
            autres = auteurs | {x.auteur for k, x in gardees.items() if k != e.id}
            cands = b.candidats(eid, e, p.echeance, c, autres=autres)
            if not cands:
                return None
            o = cands[0]
            if e.contributeur:
                remplaces.append(e.id)
        choix[e.id] = o.id
        auteurs.add(o.auteur)
    return {"creneau": c, "choix": choix, "remplaces": remplaces}


def _creneaux(fen, duree):
    for m in range(minutes(fen.debut), minutes(fen.fin) - duree + 1, PAS_MIN):
        yield Creneau(jour=fen.jour, debut=heure(m), duree_min=duree)


def _comparer(b, eid, p, garder) -> tuple[int, int]:
    """(créneaux où le glouton trouvait une équipe, créneaux où seule la recherche complète en trouve une)."""
    duree = p.creneau.duree_min if p.creneau else max(e.duree_min for e in p.etapes)
    memes = gagnes = 0
    for c in _creneaux(p.fenetre, duree):
        avant, apres = glouton(b, eid, p, c, garder), b._composer(eid, p, c, garder)
        if avant is not None:
            assert apres == avant, (eid, c, avant, apres)
            memes += 1
        elif apres is not None:
            gagnes += 1
    return memes, gagnes


@pytest.mark.parametrize("etape", range(0, 10))
def test_essais_de_la_demonstration_memes_equipes(etape):
    d = Demo(TAX)
    for _ in range(etape):
        d.suivant()
    b = d.club.banc
    n = 0
    for eid in b.essais():
        p = b.protocole(eid)
        if p.fenetre is None or not p.etapes:
            continue
        partis = b.refus(eid) | {x.acteurs[0] for x in b._evs(eid, "RETRAIT")}
        garder = {e.id: b.offre_de(eid, e) if e.contributeur and e.contributeur not in partis else None for e in p.etapes}
        n += sum(_comparer(b, eid, p, garder))
        n += sum(_comparer(b, eid, p, {e.id: None for e in p.etapes}))       # sans rien garder (proposition initiale)
    assert not 1 <= etape <= 8 or n > 0                             # des créneaux réellement comparés (avant +30 jours)


def test_registre_memes_equipes_sur_les_mondes_de_l_oracle():
    memes = gagnes = 0
    # 400 graines + celles où l'équipe DIFFÉRAIT de l'ancien glouton (trouvées sur 4 000 : une personne gardée sur un
    # autre emplacement était explorée en premier) + celles où seule la recherche complète trouve une équipe
    for graine in [*range(400), 542, 2621, 3409, 3524, *TROUVEES]:
        b, p = monde(graine)
        garder = {e.id: None for e in p.emplacements}
        for ev in b.consentements_finalite(p.id):
            if b.raison_consentement(ev, p.portee(ev.donnees["emplacement"])) is None and garder.get(ev.donnees["emplacement"]) is None:
                garder[ev.donnees["emplacement"]] = b.offre(ev.donnees["offre"])
        m, g = _comparer(b, None, p.protocole(), garder)
        memes, gagnes = memes + m, gagnes + g
    assert memes > 30 and gagnes > 0, (memes, gagnes)             # non vacueux : des équipes identiques, et des gains


def test_le_budget_de_recherche_est_borne_et_le_dit():
    b, p = monde(3)
    avant = b.recherches_tronquees
    b.BUDGET_NOEUDS = 1
    try:
        for c in _creneaux(p.protocole().fenetre, p.duree_min):
            b._composer(None, p.protocole(), c, {e.id: None for e in p.emplacements})
    finally:
        del b.BUDGET_NOEUDS
    assert b.recherches_tronquees > avant
    assert J + timedelta(days=2) == p.fenetre.jour


def test_le_registre_dit_quand_la_recherche_a_ete_bornee():
    from intelligence.capacites import Registre
    b, p = monde(3)
    b.BUDGET_NOEUDS = 1
    inst = Registre(b, [p], lambda: J).instance(p)
    assert any("recherche bornée" in h for h in inst.hypotheses)
