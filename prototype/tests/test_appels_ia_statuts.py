"""STATUTS VÉRIDIQUES des appels IA. Un appel IA journalisé est un fait OBSERVÉ par le système — jamais « SIMULÉ » — et
il dit ce qui a produit la sortie montrée : MODEL_CALLED (le modèle a répondu et sa sortie a été acceptée),
FALLBACK_FORM (la forme déterministe : aucun modèle, modèle en panne, ou sortie rejetée), CACHE_REPLAY (un
enregistrement rejoué sans rappeler le modèle). Données FICTIVES."""
import json

from app.taxonomy import charger_taxonomie
from intelligence.club_pulse import ClubPulse
from intelligence.ia import ErreurFournisseur, Intelligence
from plateforme.affirmations import Statut

TAX = charger_taxonomie()
FAITS = {"capacite_declaree": "traduction", "secteur_demandeur": "agroalimentaire", "demande": "une fiche en allemand",
         "partage": "votre pseudonyme seulement"}


class Toujours:
    nom, modele = "maquette", "maquette-1"

    def __init__(self, sortie):
        self.sortie = sortie

    def completer(self, systeme_txt, message, schema):
        if isinstance(self.sortie, Exception):
            raise self.sortie
        return self.sortie


def _appel(fournisseur):
    c = ClubPulse(TAX, ia=Intelligence(TAX, fournisseur))
    c.ia.rediger_sollicitation(FAITS, [])
    return c.journal.evenements("APPEL_IA")[-1]


def test_un_appel_accepte_est_observe_et_dit_model_called():
    e = _appel(Toujours(json.dumps({"message": "Bonjour, une personne du Club aurait besoin d'une fiche en allemand."})))
    assert e.statut == Statut.OBSERVE and e.statut != Statut.SIMULE
    assert e.donnees["appel"]["issue"] == "MODEL_CALLED"


def test_sans_modele_panne_ou_rejet_la_forme_deterministe_est_dite():
    for f in (None, Toujours(ErreurFournisseur("HTTP 503")), Toujours("pas du JSON")):
        e = _appel(f)
        assert e.statut == Statut.OBSERVE
        assert e.donnees["appel"]["issue"] == "FALLBACK_FORM", f
