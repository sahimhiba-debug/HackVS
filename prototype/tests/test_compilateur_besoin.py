"""Compilateur d'intention (règles) sur le besoin de la démonstration et ses formulations voisines.

Le comportement vient de la taxonomie et du moteur réutilisable (terme ambigu « distribution » résolu par indices,
marqueurs de non-concurrence), jamais d'une règle propre à la page de démonstration.
"""
import pytest

from app.parser_rules import analyser
from app.taxonomy import charger_taxonomie, norm

TAX = charger_taxonomie()
SCENE = ("Je cherche un partenaire capable de m'aider à développer mon activité en Allemagne, qui connaît la "
         "distribution, qui n'est pas un concurrent direct et qui peut échanger en français.")

VARIANTES = [
    SCENE,
    "Un distributeur en Allemagne, qui ne soit pas un concurrent direct, avec qui je puisse parler français, pour développer mon activité.",  # ordre
    "Partenaire pour l'Allemagne : distribution, pas de concurrent, francophone.",                                                         # court
    "Qui connaît la distribution en Allemagne et parle français ? Pas un concurrent svp.",                                                 # question
    "je cherche qq1 pour developper mes ventes en allemagne, distrib, pas concurent, en francais",                                         # imparfait
]


@pytest.mark.parametrize("texte", VARIANTES)
def test_le_besoin_de_la_scene_et_ses_variantes_sont_compris(texte):
    b = analyser(texte, TAX)
    exp = [c for c in b.criteres if c.type == "expertise"]
    assert exp and exp[0].valeur == "export_allemagne" and exp[0].obligatoire          # besoin principal
    assert all(c.valeur != "logistique" for c in exp)                                   # « distribution » ≠ livraison ici
    assert any(c.type == "langue" and c.valeur == "fr" for c in b.criteres)              # échanger en français
    assert b.exclure_concurrents                                                         # pas un concurrent
    assert not b.ambiguites and not b.avertissements
    for c in b.criteres:                                                                 # chaque critère cite le texte
        assert c.extrait and norm(c.extrait) in norm(texte)


def test_la_phrase_de_la_scene_garde_les_deux_extraits_du_besoin_principal():
    exp = next(c for c in analyser(SCENE, TAX).criteres if c.type == "expertise")
    assert exp.extrait == "activité en Allemagne" and "distribution" in (exp.note or "")


@pytest.mark.parametrize("texte,attendu", [
    ("Je cherche quelqu'un pour la distribution de nos colis en Valais.", "logistique"),             # indice logistique
    ("Je cherche un partenaire pour la distribution en Suisse alémanique.", "export_suisse_alemanique"),
])
def test_distribution_resolue_par_le_contexte(texte, attendu):
    assert analyser(texte, TAX).criteres[0].valeur == attendu


@pytest.mark.parametrize("texte", [
    "Je cherche un partenaire pour la distribution.",                                        # aucun indice
    "Je cherche de l'aide pour la distribution en Allemagne et pour livrer nos palettes.",   # indices contradictoires
])
def test_distribution_sans_indice_ou_contradictoire_reste_une_incertitude_explicite(texte):
    b = analyser(texte, TAX)
    assert [a.terme for a in b.ambiguites] == ["distribution"]
    assert not [c for c in b.criteres if c.type == "expertise"]                   # on ne devine pas


def test_un_concurrent_recherche_n_est_pas_une_exclusion():
    assert not analyser("Je cherche un concurrent pour mutualiser nos achats.", TAX).exclure_concurrents


def test_un_sens_deja_exprime_resout_l_ambiguite():
    """« Distribution dans les épiceries fines zurichoises » est COMMERCIAL : on ne propose plus de transporteurs
    (3 faux positifs trouvés en passant « distribution » de la logistique au terme ambigu)."""
    b = analyser("Distribution dans les épiceries fines zurichoises", TAX)
    assert [c.valeur for c in b.criteres if c.type == "expertise"] == ["export_suisse_alemanique"] and not b.ambiguites
