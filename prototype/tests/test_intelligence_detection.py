"""DÉTECTER : vraies opportunités trouvées, pièges jamais proposés, chaque opportunité prouvée. Données SYNTHÉTIQUES."""
import json

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.club_synthetique import FOND, RESERVES, generer, phrase_besoin
from intelligence.detection import Detecteur, scanner

TAX = charger_taxonomie()


def _membres(o):
    return {r.membre for r in o.roles}


def test_generateur_reproductible_et_phrases_comprises_par_l_analyseur():
    (r1, v1), (r2, v2) = generer(150, 7), generer(150, 7)
    assert [p.model_dump() for p in r1.profils] == [p.model_dump() for p in r2.profils] and v1 == v2
    assert r1.memoire.empreinte() == r2.memoire.empreinte()
    assert len(r1.profils) == 150 and generer(150, 8)[0].profils[0] != r1.profils[0]
    for c in FOND + RESERVES:
        assert phrase_besoin(c)                                  # l'analyseur RÉEL comprend chaque phrase générée


@pytest.mark.parametrize("n,graine", [(150, 2026), (500, 11), (1000, 3)])
def test_vraies_trouvees_et_pieges_jamais_proposes(n, graine):
    r, v = generer(n, graine)
    ops = scanner(r, TAX)["opportunites"]
    for t in v["vraies"]:
        assert any(t["type"] in (o.type, *o.mecanismes) and set(t["membres"]) <= _membres(o) and set(t["concepts"]) <= set(o.capacites)
                   for o in ops), t
    for t in v["pieges"]:
        assert not any(set(t["membres"]) <= _membres(o) for o in ops), t


def test_chaque_opportunite_est_prouvee_consentie_et_unique():
    r, _ = generer(500, 5)
    par_id = r.par_id()
    d = Detecteur(r, TAX)
    ops = d.detecter()["opportunites"]
    assert ops
    vues = set()
    for o in ops:
        cle = (frozenset(_membres(o)), frozenset(o.capacites))
        assert cle not in vues                                   # aucune opportunité en double
        vues.add(cle)
        assert o.signaux and o.raisonnement and o.confiance_raisons and o.action
        for s in o.signaux:                                      # aucune preuve inventée : l'extrait existe mot pour mot
            if s.source == "offre":
                assert any(s.extrait == x.texte for x in par_id[s.membre].offre) or s.extrait in par_id[s.membre].presentation
            if s.source == "recherche":
                assert any(s.extrait == x.texte for x in par_id[s.membre].recherche)
        demandeurs = {r_.membre for r_ in o.roles if r_.role in ("participant", "demandeur bloqué")}
        demandeurs |= {o.beneficiaire} if o.besoin_id else set()   # qui a publié un besoin l'a demandé lui-même
        for m in _membres(o) - demandeurs:
            p = par_id[m]
            assert p.accepte_introductions and p.disponible      # personne qui refuse n'est jamais sollicité
            assert m in o.consentements                          # et tout sollicité doit consentir
        benef = par_id.get(o.beneficiaire or "")
        if benef:
            for r_ in o.roles:
                if r_.membre != benef.id:
                    assert d.e.exclusion(benef, par_id[r_.membre], None) in (None,)  # règles dures re-vérifiées


def test_ecartees_ne_nomment_personne_et_le_scan_n_ecrit_rien():
    r, _ = generer(150, 2026)
    avant = r.memoire.empreinte()
    res = scanner(r, TAX)
    assert r.memoire.empreinte() == avant
    brut = json.dumps(res["ecartees"], ensure_ascii=False)
    assert not any(p.nom in brut or p.id in brut for p in r.profils)
    assert all(isinstance(v, int) for v in res["ecartees"].values())


def test_latente_exige_un_pourquoi_maintenant():
    r = md.construire()
    sophie = lambda res: [o for o in res["opportunites"] if md.SOPHIE in _membres(o)]  # noqa: E731
    assert sophie(scanner(r, TAX))
    r.evenements = [e for e in r.evenements if e.id != md.SALON]  # sans le salon, Sophie–Markus reste réciproque
    reste = sophie(scanner(r, TAX))
    assert all(o.evenement is None for o in reste)


def test_scene_centrale_sophie_marche_allemand():
    r = md.construire()
    res = scanner(r, TAX)
    o = next(o for o in res["opportunites"] if o.beneficiaire == md.SOPHIE)
    assert o.type == "LATENTE" and _membres(o) == {md.SOPHIE, md.ANNA, md.MARKUS}
    assert o.evenement == md.SALON and o.manque and "conformité" in o.manque[0]
    tous = json.dumps([x.model_dump() for x in res["opportunites"]], ensure_ascii=False)
    assert "Stefan" not in tous and "Claudia" not in tous      # refuse les introductions ; profil de 2024
    # perturbation : Anna retirée → l'alternative (Léa) prend sa place, sans rien d'autre à changer
    o2 = next(o for o in scanner(r, TAX, exclus={md.ANNA})["opportunites"] if o.beneficiaire == md.SOPHIE)
    assert md.LEA in _membres(o2) and md.ANNA not in _membres(o2)
