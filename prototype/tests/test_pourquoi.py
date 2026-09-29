"""« Pourquoi cette personne ? » — l'explication structurée d'une opportunité (Network Intelligence).
Chaque élément porte son statut (DÉCLARÉ, OBSERVÉ, CONFIRMÉ, INFÉRÉ, INCONNU) et renvoie à une source vérifiable.
Données FICTIVES : la scène « marché allemand » du monde de démonstration."""
import json

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.detection import scanner
from intelligence.explication import expliquer
from intelligence.identite import AdhesionsSynthetiques, Coffre

TAX = charger_taxonomie()
STATUTS = {"DÉCLARÉ", "OBSERVÉ", "CONFIRMÉ", "INFÉRÉ", "INCONNU"}


@pytest.fixture(scope="module")
def scene():
    r = md.construire(True, md.BESOIN_ALLEMAGNE)
    o = next(o for o in scanner(r, TAX)["opportunites"] if o.beneficiaire == md.SOPHIE)
    return r, o


def _souvenir(qualification="positif", statut="confirmee", concepts=("export_allemagne",)):
    return {"essai": "es-1", "question": "Préparer l'entrée sur le marché allemand", "contributeurs": [md.MARKUS],
            "concepts": list(concepts), "qualification": qualification, "statut": statut, "le": "2026-11-20",
            "limites": "un échange de 20 minutes, une seule gamme"}


def test_la_scene_est_une_suite_sophie_markus_avec_toutes_les_rubriques(scene):
    r, o = scene
    assert o.type == "SUIVI" and {x.membre for x in o.roles} == {md.SOPHIE, md.MARKUS}
    e = expliquer(o, r, TAX, {}, [])
    for rubrique in ("besoin", "capacite", "contexte", "relation", "moment", "consentement", "preuves", "inconnues", "risques"):
        assert e[rubrique], rubrique
    assert e["resume"]["statut"] == "INFÉRÉ" and e["question"] == "Voulez-vous proposer un essai ?"
    elements = [x for k in ("besoin", "capacite", "contexte", "relation", "consentement", "preuves", "inconnues") for x in e[k]]
    assert all(x["statut"] in STATUTS for x in elements + [e["moment"], e["resume"]])


def test_chaque_declaration_est_citee_mot_pour_mot(scene):
    r, o = scene
    e = expliquer(o, r, TAX, {}, [])
    p = r.par_id()
    assert all(x["texte"] in [y.texte for y in p[md.SOPHIE].recherche] for x in e["besoin"])
    assert all(x["texte"] in [y.texte for y in p[x["qui"]].offre] for x in e["capacite"])
    rencontre = next(ev for ev in r.memoire.evenements("RENCONTRE") if sorted(ev.acteurs) == sorted([md.SOPHIE, md.MARKUS]))
    assert e["relation"][0]["le"] == rencontre.le.isoformat() and e["relation"][0]["statut"] == "OBSERVÉ"


def test_disponibilite_inconnue_tant_que_rien_n_est_declare(scene):
    r, o = scene
    sans = expliquer(o, r, TAX, {}, [])
    assert any(x["statut"] == "INCONNU" and "Disponibilité actuelle" in x["texte"] for x in sans["inconnues"])
    avec = expliquer(o, r, TAX, {md.MARKUS: [{"quoi": "Une heure d'échange sur le marché allemand", "duree_max_min": 60, "au": "2026-11-30"}]}, [])
    assert not any("Disponibilité actuelle" in x["texte"] for x in avec["inconnues"])
    assert any(x["source"] == "offre volontaire" and x["statut"] == "DÉCLARÉ" for x in avec["preuves"])


def test_memoire_confirmee_releve_la_confiance_et_devient_une_preuve(scene):
    r, o = scene
    o = o.model_copy(update={"confiance": "moyenne"})
    e = expliquer(o, r, TAX, {}, [_souvenir()])
    assert e["confiance"]["niveau"] == "elevee" and e["confiance"]["detection"] == "moyenne" and e["confiance"]["effet_memoire"]
    assert any(x["statut"] == "CONFIRMÉ" and "pas une garantie" in x["texte"] for x in e["preuves"])


@pytest.mark.parametrize("souvenir,attendu", [(_souvenir("negatif"), "jugé « negatif »"),
                                              (_souvenir(statut="contestee"), "CONTESTÉE")])
def test_memoire_negative_ou_contestee_devient_un_risque_et_abaisse_la_confiance(scene, souvenir, attendu):
    r, o = scene
    e = expliquer(o, r, TAX, {}, [souvenir])
    assert any(attendu in x for x in e["risques"]) and e["confiance"]["niveau"] == "moyenne"   # était élevée
    assert not any(x["statut"] == "CONFIRMÉ" for x in e["preuves"])


def test_sans_memoire_le_risque_est_dit(scene):
    r, o = scene
    e = expliquer(o, r, TAX, {}, [_souvenir(concepts=("traduction",))])        # mémoire hors sujet : ignorée
    assert any("aucune contribution" in x and "confirmée" in x for x in e["risques"])


def test_consentement_lu_dans_le_profil_jamais_suppose(scene):
    r, o = scene
    r2 = md.construire(True, md.BESOIN_ALLEMAGNE)
    r2.profils = [p.model_copy(update={"accepte_introductions": False}) if p.id == md.MARKUS else p for p in r2.profils]
    e = expliquer(o, r2, TAX, {}, [])
    assert any("n'accepte pas les sollicitations" in x["texte"] for x in e["consentement"])
    assert any("ne peut pas être activée" in x for x in e["risques"])


def test_l_explication_ne_contient_que_des_pseudonymes():
    r = md.construire(True, md.BESOIN_ALLEMAGNE)
    coffre = Coffre(AdhesionsSynthetiques(r.profils).importer(), secret=b"secret-de-test-assez-long-pour-hmac")
    r.profils = [coffre.pseudonymiser(p) for p in r.profils]
    o = next(o for o in scanner(r, TAX)["opportunites"] if o.beneficiaire == md.SOPHIE)
    texte = json.dumps(expliquer(o, r, TAX, {}, [_souvenir()]), ensure_ascii=False)
    for pid in (md.SOPHIE, md.MARKUS):
        per = coffre.identite(pid)
        assert per.nom not in texte and per.courriel not in texte
    assert "MEMBRE-" in texte
