"""Invariants du moteur d'activation, vérifiés par MARCHES ALÉATOIRES (graines fixes, donc rejouables) : des gestes
humains et des perturbations au hasard — accepter, décliner, se taire, contribuer, confirmer, annuler, mettre en pause,
retirer une capacité ou un accord — puis, après CHAQUE pas, les propriétés qui ne doivent jamais être violées.
Un refus métier (ErreurMetier) est un comportement normal ; toute autre exception fait échouer le test."""
import random

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import apprentissage
from intelligence import monde_demo as md
from intelligence.activation import BUDGET_ATTENTION, FINAUX, TRANSITIONS, Moteur
from intelligence.detection import scanner
from intelligence.erreurs import ErreurMetier
from intelligence.politique import Contexte, Spectateur, peut_voir
from plateforme.memoire import Memoire

TAX = charger_taxonomie()
ACCORDS = ("accord_beneficiaire", "contribution", "animation", "accord_participant")


def _verifier(mo: Moteur) -> None:
    m = mo.m
    for aid in mo.activations():
        journal = [e.donnees for e in m.evenements("ACTIVATION") if e.donnees["aid"] == aid]
        for t in journal:                                                   # I1 : rejeu = transitions permises seulement
            assert t["etat"] in TRANSITIONS.get(t["de"], set()), (aid, t["de"], t["etat"])
        etat = journal[-1]["etat"]
        plan = mo.plan(aid)
        rep = mo._reponses(aid)
        if etat == "ACTIVEE":                                               # I2 : pas d'action sans TOUS les accords
            for e in plan["etapes"]:
                if e["type"] in ACCORDS:
                    r = rep.get((e["id"], e["membre"]))
                    assert r is not None and r.donnees["accepte"], (aid, e["id"])
        if etat in ("RESULTAT_CONFIRME", "RESULTAT_PARTIEL"):              # I3 : un résultat a une déclaration et une action
            dec = [e for e in m.evenements("RESULTAT_DECLARE") if e.donnees["aid"] == aid]
            assert dec and dec[-1].acteurs == [mo.opportunite(aid).beneficiaire]
            assert mo.opportunite(aid).type == "MEMOIRE" or [e for e in m.evenements("CONTRIBUTION_RECUE") if e.donnees["aid"] == aid]
        finals = [e for e in m.evenements("ACTIVATION") if e.donnees["aid"] == aid and e.donnees["etat"] in FINAUX]
        if finals:                                                          # I4 : rien ne continue après un état final
            apres = [e for e in m.evenements("SOLLICITATION_PRIVEE", "CONTRIBUTION_RECUE")
                     if e.donnees["aid"] == aid and e.seq > finals[0].seq]
            assert not apres, (aid, [e.type for e in apres])
        for (etape, membre), r in rep.items():                              # I5 : un refus n'est jamais relancé
            if not r.donnees["accepte"]:
                relances = [e for e in m.evenements("SOLLICITATION_PRIVEE")
                            if e.donnees["aid"] == aid and e.donnees["etape"] == etape and e.acteurs[0] == membre and e.seq > r.seq]
                assert not relances, (aid, etape, membre)
    assert all(n <= BUDGET_ATTENTION for n in mo.ouvertes().values())      # I6 : budget d'attention respecté
    etats = {aid: mo.etat(aid) for aid in mo.activations()}
    for x in apprentissage.motifs(m, mo.r.aujourd_hui):                     # I7 : une mémoire a une preuve confirmée
        assert x["activation"].startswith("historique") or etats.get(x["activation"]) in ("RESULTAT_CONFIRME", "RESULTAT_PARTIEL")


GESTES = {"repondre": 8, "contribuer": 4, "confirmer": 4, "echeances": 1, "avancer": 1, "annuler": 0.5, "pause": 0.5,
          "reprendre": 1, "retirer_accord": 0.5, "retirer_capacite": 0.5, "nouvelle": 1}   # réaliste d'abord, perturbations aussi


def _geste(nom: str, mo: Moteur, rnd: random.Random, opps: list) -> None:
    r, t = mo.r, mo.r.aujourd_hui
    acts = mo.activations()
    a = rnd.choice(acts)
    contrib = [e for e in mo.plan(a)["etapes"] if e["type"] == "contribution"]
    if nom == "repondre":
        ouvertes = [(e.donnees["aid"], e.acteurs[0]) for e in r.memoire.evenements("SOLLICITATION_PRIVEE")
                    if (e.donnees["etape"], e.acteurs[0]) not in mo._reponses(e.donnees["aid"])]
        if ouvertes:
            aid, membre = rnd.choice(ouvertes)
            mo.repondre(aid, t, membre, rnd.random() < 0.8)
    elif nom == "contribuer":
        for e in contrib:
            mo.contribuer(a, t, e["membre"], "conseil", "aide", "texte", rnd.random() < 0.5)
    elif nom == "confirmer":
        mo.confirmer(a, t, mo.opportunite(a).beneficiaire or "", rnd.choice(["debloque", "partiel", "non"]), True)
    elif nom == "echeances":
        mo.echeances(t)
    elif nom == "avancer":
        r.aujourd_hui = t.fromordinal(t.toordinal() + rnd.choice([1, 4, 21]))
    elif nom == "annuler":
        mo.annuler(a, t)
    elif nom == "pause":
        mo.mettre_en_pause(a, t)
    elif nom == "reprendre":
        mo.reprendre(a, t)
    elif nom == "retirer_accord" and contrib:
        mo.retirer_consentement(a, t, contrib[0]["membre"])
    elif nom == "retirer_capacite" and contrib and contrib[0].get("concept"):
        mo.retirer_capacite(contrib[0]["membre"], contrib[0]["concept"], t)
    elif nom == "nouvelle":
        mo.lancer(mo.creer(rnd.choice(opps), t), t)


def _marche(graine: int, pas: int = 40) -> str:
    rnd = random.Random(graine)
    r = md.construire()
    mo = Moteur(r, TAX)
    opps = [o for o in scanner(r, TAX)["opportunites"] if o.type != "LACUNE"][:4]
    for o in opps[:2]:
        mo.lancer(mo.creer(o, r.aujourd_hui), r.aujourd_hui)
    for _ in range(pas):
        try:
            _geste(rnd.choices(list(GESTES), weights=list(GESTES.values()))[0], mo, rnd, opps)
        except ErreurMetier:
            pass                                                            # refus attendu : l'état doit rester sain
        _verifier(mo)
    return r.memoire.empreinte()


@pytest.mark.parametrize("graine", range(25))
def test_marche_aleatoire_ne_viole_aucun_invariant(graine):
    _marche(graine)


def test_meme_graine_meme_journal():
    assert _marche(7, 25) == _marche(7, 25)


def test_un_evenement_rejoue_ne_change_pas_l_etat():
    m = Memoire()
    r = md.construire()
    for e in r.memoire.evenements()[:50]:
        m.ajouter(e)
    avant = m.empreinte()
    for e in m.evenements():
        m.ajouter(e)                                                        # doublon exact : ignoré (idempotence)
    assert m.empreinte() == avant


@pytest.mark.parametrize("graine", range(10))
def test_politique_aucun_nom_sans_raison(graine):
    """Propriété : un membre ne voit le nom d'un autre que s'il s'agit de lui-même, d'un choix PUBLIC du sujet, d'une
    relation existante, ou d'un accord donné dans une activation — quelle que soit la combinaison tirée au hasard."""
    rnd = random.Random(graine)
    ids = [f"m{i}" for i in range(8)]
    ctx = Contexte(relations={frozenset(rnd.sample(ids, 2)) for _ in range(5)},
                   consentis={tuple(rnd.sample(ids, 2)) for _ in range(5)},  # type: ignore[misc]
                   preferences={x: {"nom": rnd.choice(["PUBLIC", "SUR_CONSENTEMENT"])} for x in rnd.sample(ids, 3)})
    for v in ids:
        for s in ids:
            if peut_voir(Spectateur("membre", v), s, "nom", ctx):
                assert v == s or ctx.preferences.get(s, {}).get("nom") == "PUBLIC" or frozenset((v, s)) in ctx.relations \
                    or (v, s) in ctx.consentis
            assert not peut_voir(Spectateur("membre", v), s, "notes", ctx) or v == s
