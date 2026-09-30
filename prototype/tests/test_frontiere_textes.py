"""FRONTIÈRE DU MOTEUR : un texte libre écrit par un membre et LU PAR LE MOTEUR (son profil, un besoin publié, une offre,
une réponse à une demande) n'entre dans l'état ni dans le journal qu'après retrait des identités du coffre — noms,
organisations, courriels, téléphones — y compris le NOM DU MEMBRE LUI-MÊME écrit dans son propre texte.
Défaut trouvé à la fin de la Phase 1 (docs/audit/PHASE_1.md § 6) : `onboarding` rangeait le texte brut dans le profil
que lit le moteur ; même chose pour les besoins, les offres et les réponses. Le moteur raisonne sur des capacités,
jamais sur des identités ; ces textes sont aussi ceux que la Phase 2 utilise pour les demandes.
Restent hors de cette règle, PAR CONCEPTION : les textes échangés de personne à personne (question et critère d'un
essai, livrable, observation, raisons), qui ne partent vers un modèle que filtrés (`Intelligence.proteger`).
Données FICTIVES."""
import json

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo

TAX = charger_taxonomie()


@pytest.fixture
def club():
    return Demo(TAX).club


def _identites(c, pid):
    per, org = c.coffre.identite(pid), c.coffre.organisation_de(pid)
    return per.nom, org.nom.replace("(fictive)", "").replace("(fictif)", "").strip(), per.courriel


def _journal(c) -> str:
    return json.dumps([e.donnees for e in c.journal.evenements()], ensure_ascii=False)


def _absent(texte: str, *interdits: str) -> None:
    for x in interdits:
        assert x not in texte, (x, texte[:300])


def test_onboarding_son_propre_nom_son_organisation_son_courriel_et_ceux_des_autres(club):
    nom, org, courriel = _identites(club, md.SOPHIE)
    autre = club.coffre.identite(md.LEA).nom
    club.onboarding(md.SOPHIE, aide=[{"texte": f"Tisanes de plantes alpines bio, par {nom} ({org}), {courriel}", "concept": "boissons"}],
                    cherche=[{"texte": f"Un distributeur en Allemagne, comme {autre} m'a conseillé", "concept": "export_allemagne"}],
                    visible=True)
    p = club.profil(md.SOPHIE)
    textes = " | ".join(o.texte for o in [*p.offre, *p.recherche])
    _absent(textes, nom, org, courriel, autre)
    _absent(_journal(club), nom, org, courriel, autre)
    assert "plantes alpines" in textes and "distributeur" in textes          # le sens reste


def test_un_interet_ajoute_au_profil(club):
    nom, org, _ = _identites(club, md.LEA)
    club.modifier_profil(md.LEA, ajouter_recherche=f"Des clients pour {org}, contacter {nom} au +41 79 123 45 67")
    textes = " | ".join(r.texte for r in club.profil(md.LEA).recherche)
    _absent(textes, nom, org, "79 123 45 67")
    _absent(_journal(club), nom, org, "79 123 45 67")


def test_un_besoin_publie(club):
    nom, org, courriel = _identites(club, md.MARKUS)
    club.demander(md.SOPHIE, f"Je cherche quelqu'un comme {nom} de {org} pour traduire nos fiches ; écrire à {courriel}.")
    _absent(club.r.besoins[-1].texte, nom, org, courriel)
    _absent(_journal(club), nom, org, courriel)


def test_une_offre_publiee_puis_modifiee(club):
    nom, org, _ = _identites(club, md.PAULINE)
    oid = club.publier_offre(md.PAULINE, "lieu", f"Le stand de {nom}", 1, club.jour, club.jour, None, f"Demander {nom} de {org}", None)
    club.modifier_offre(md.PAULINE, oid, {"conditions": f"Appeler {nom} avant"})
    o = club.banc.offre(oid)
    _absent(o.quoi + o.conditions, nom, org)
    _absent(_journal(club), nom, org)


def test_une_reponse_a_une_demande(club):
    nom, _, _ = _identites(club, md.PAULINE)
    ask = club.capacites.instance(club.capacites.patron("delegation_acheteurs")).ask
    club.repondre_ask(md.PAULINE, ask.id, True, {"places": 14}, quoi=f"Le minibus de {nom}, 14 places")
    _absent(club.banc.offres()[-1].quoi, nom)
    _absent(_journal(club), nom)
