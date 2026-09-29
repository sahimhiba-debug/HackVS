"""Temporalité : une relation HISTORIQUE ne devient pas automatiquement une relation ACTUELLE.

Classe de défauts testée : tout calcul qui s'appuie sur un lien pour AGIR (présentation par un intermédiaire,
opportunité, « déjà en relation ») doit ignorer les liens anciens (> 90 jours), déclinés ou déclarés sans suite.
Données FICTIVES."""
import json
import random
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from adaptateurs.club import cycle as cy
from adaptateurs.club import reseau
from app.models import Profil
from app.taxonomy import DATA_DIR, charger_taxonomie
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

TAX = charger_taxonomie()
P = [Profil(**p) for p in json.loads((DATA_DIR / "profils_demo.json").read_text(encoding="utf-8"))["profils"]]
PAR_ID = {p.id: p for p in P}
J0 = date(2026, 10, 3)
BESOIN = "Nous cherchons un agent commercial pour placer nos jus dans les épiceries fines de Berne cet automne"


def _rencontre(m, a, b, jours, typ="RENCONTRE", **d):
    m.ajouter(Evt(type=typ, le=J0 + timedelta(days=jours), acteurs=sorted([a, b]), statut=Statut.DECLARE, donnees=d))


def _monde(lien_via_z: str):
    """p00 a rencontré Reto (p32) puis a eu un suivi avec lui ; Reto connaît Grégoire (p06), qui peut aider p00.
    lien_via_z : « recent », « ancien » (300 jours avant), « sans_suite » (récent, déclaré sans suite)."""
    m = Memoire()
    cy.publier_besoin(m, "p00", BESOIN, J0 - timedelta(days=1), TAX, Statut.SIMULE)
    _rencontre(m, "p00", "p32", 0)
    _rencontre(m, "p00", "p32", 12, "SUIVI")
    _rencontre(m, "p32", "p06", -300 if lien_via_z == "ancien" else 0)
    if lien_via_z == "sans_suite":
        _rencontre(m, "p32", "p06", 2, "RESULTAT", resultat="pas_pertinent")
    return m


def _opps(m, jour):
    return [(o["a"], o["c"], o["via"]) for o in cy.opportunites(m, P, TAX, J0 + timedelta(days=jour))]


def test_temoin_un_lien_recent_permet_la_presentation():
    assert _opps(_monde("recent"), 12) == [("p00", "p06", "p32")]


@pytest.mark.parametrize("lien", ["ancien", "sans_suite"])
def test_un_lien_ancien_ou_clos_ne_fonde_pas_une_presentation(lien):
    m = _monde(lien)
    assert _opps(m, 12) == []
    rel = cy.relances(m, P, TAX, J0 + timedelta(days=30))
    assert not [r for p in rel["propositions"] for r in p["raisons"] if r["type"] == "PRESENTATION"]


def test_un_intermediaire_perdu_de_vue_n_est_pas_sollicite():
    """x–via : suivi il y a plus de 90 jours → Reto n'est plus « actuel » pour p00 : pas de présentation."""
    m = _monde("recent")
    _rencontre(m, "p32", "p06", 150)                        # Reto–Grégoire reste actuel
    rel = cy.relances(m, P, TAX, J0 + timedelta(days=160))  # p00–Reto : dernier contact il y a 148 jours
    assert not [r for p in rel["propositions"] for r in p["raisons"] if r["type"] == "PRESENTATION"]


def test_la_carte_ne_dit_pas_deja_en_relation_pour_une_relation_ancienne():
    m = Memoire()
    _rencontre(m, "p00", "p06", 0)
    s = {"profil": {"id": "p06"}, "preuves": [], "niveau": "forte"}
    assert reseau.dimensions(m, PAR_ID["p00"], s, PAR_ID, J0 + timedelta(days=30))["reseau"]["type"] == "DIRECT"
    d = reseau.dimensions(m, PAR_ID["p00"], s, PAR_ID, J0 + timedelta(days=200))["reseau"]
    assert d["type"] == "ANCIENNE" and "déjà en relation" not in d["message"]


def test_propriete_graphe_actuel_egal_etat_relation_sur_historiques_aleatoires():
    """Propriété (100 historiques générés) : un lien est ACTUEL ⟺ etat_relation n'est ni ancien, ni décliné, ni sans
    suite. Deux chemins de calcul (une passe globale / une paire) doivent toujours concorder."""
    types = ["RENCONTRE", "SUIVI", "INTRO_DEMANDEE", "INTRO_ACCEPTEE", "INTRO_DECLINEE", "RESULTAT", "RELANCE_REFUSEE"]
    membres = [f"m{i}" for i in range(6)]
    for graine in range(100):
        rnd = random.Random(graine)
        m = Memoire()
        for k in range(rnd.randint(1, 25)):
            a, b = rnd.sample(membres, 2)
            t = rnd.choice(types)
            d = {"resultat": rnd.choice(["utile", "affaire_en_cours", "pas_pertinent"])} if t == "RESULTAT" else {"k": k}
            m.ajouter(Evt(type=t, le=J0 + timedelta(days=rnd.randint(0, 300)), acteurs=sorted([a, b]),
                          statut=Statut.OBSERVE, donnees=d))
        t = J0 + timedelta(days=rnd.randint(0, 400))
        base = reseau.graphe_de_confiance(m, t)
        actuel = reseau.graphe_actuel(m, t)
        assert set(actuel.edges()) <= set(base.edges())
        for a, b in base.edges():
            e = reseau.etat_relation(m, a, b, t)["etat"]
            assert actuel.has_edge(a, b) == (e not in reseau.ETATS_NON_ACTUELS), (graine, a, b, e)


def test_cache_de_la_memoire_exact_face_a_un_autre_ecrivain(tmp_path):
    """Le cache incrémental de la mémoire reste identique à une relecture complète : écritures d'un autre objet sur le
    même fichier, vidage, ré-écritures, doublons idempotents."""
    chemin = str(tmp_path / "m.sqlite")
    m1, m2 = Memoire(chemin), Memoire(chemin)
    rnd = random.Random(3)
    for k in range(200):
        qui = rnd.choice([m1, m2])
        if rnd.random() < 0.03:
            qui.vider()
        else:
            qui.ajouter(Evt(type=rnd.choice(["RENCONTRE", "SUIVI"]), le=J0 + timedelta(days=rnd.randint(0, 9)),
                            acteurs=["a", "b"], statut=Statut.OBSERVE, donnees={"k": rnd.randint(0, 40)}))
        lecteur = rnd.choice([m1, m2])
        frais = Memoire(chemin).evenements()
        assert [(e.id, e.seq) for e in lecteur.evenements()] == [(e.id, e.seq) for e in frais], k


def test_un_evenement_lu_ne_peut_pas_etre_modifie_en_place():
    m = Memoire()
    m.ajouter(Evt(type="RENCONTRE", le=J0, acteurs=["a", "b"], statut=Statut.OBSERVE))
    with pytest.raises(ValidationError):
        m.evenements()[0].type = "SUIVI"


def test_complexite_les_relances_lisent_la_memoire_un_nombre_constant_de_fois(monkeypatch):
    """Régression de performance (déterministe, pas un chronomètre) : lire la mémoire une fois PAR PAIRE rendait les
    relances quadratiques (20,8 s à 500 membres générés). Le nombre de lectures ne doit pas dépendre de la taille."""
    from eval.perf_echelle import generer
    appels = []
    lire = Memoire.evenements
    monkeypatch.setattr(Memoire, "evenements", lambda self, *a, **k: appels.append(1) or lire(self, *a, **k))
    comptes = []
    for n in (40, 160):
        profils, m, t = generer(n)
        appels.clear()
        cy.relances(m, profils, TAX, t)
        comptes.append(len(appels))
    assert comptes[0] == comptes[1], comptes
