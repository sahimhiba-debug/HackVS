"""LA CORRECTION « HIER » : Émilie (porteuse du challenge) nous a parlé HIER, on y a travaillé jusqu'au soir, et le
pitch est prononcé AUJOURD'HUI, un dimanche. Aucun support du pitch v2 (scripts, prompteur, imprimable, cartes, deck,
Q&R, visite, mode d'emploi) ne garde un repère de temps devenu faux."""
import json
from pathlib import Path

import pytest

P = Path(__file__).resolve().parents[2] / "docs" / "presentation"
SUPPORTS = ["03_SCRIPT_ORAL_v2.md", "03b_SCRIPT_A_DIRE_v2.md", "02_STRUCTURE_v2.md", "06_SLIDE_CONTENT_v2.md",
            "COMMENT_PRESENTER.md", "VISITE_GUIDEE.md", "deck/v2.html", "deck/data/gel.json",
            "prompteur/prompteur.html", "livrables/SCRIPT_v2_IMPRIMABLE.html", "livrables/CARTE_REGIE_V2.html",
            "outils/cartes.py", "qa/qa.json", "qa/TOP20.md", "qa/TOP20.html", "qa/qa-entrainement.html",
            "07_QA_JURY_COMPLET.md"]
FAUX = ["ce matin", "cette nuit", "hier soir", "ce soir", "21 réponses nous sont arrivées"]


def _texte(nom: str) -> str:
    t = (P / nom).read_text(encoding="utf-8")
    return json.dumps(json.loads(t), ensure_ascii=False) if nom.endswith(".json") else t.replace("&#x27;", "'")


@pytest.mark.parametrize("nom", SUPPORTS)
def test_plus_aucun_repere_de_temps_faux(nom):
    t = _texte(nom).lower()
    assert not [f for f in FAUX if f in t], (nom, [f for f in FAUX if f in t])


@pytest.mark.parametrize("nom", ["03_SCRIPT_ORAL_v2.md", "03b_SCRIPT_A_DIRE_v2.md", "prompteur/prompteur.html",
                                 "livrables/SCRIPT_v2_IMPRIMABLE.html"])
def test_les_phrases_corrigees_sont_dites(nom):
    t = _texte(nom)
    for phrase in ("Hier, Émilie nous a dit",
                   "On y a travaillé jusqu'au soir.", "Et on a construit de quoi le savoir.",
                   "Hier, on a reçu 21 vraies demandes avec le QR code de la Foire."):
        assert phrase in t, (nom, phrase)


def test_le_deck_v2_dit_hier():
    t = _texte("deck/v2.html")
    assert "Hier, vous nous avez dit…" in t and "On y a travaillé jusqu'au soir." in t


def test_le_plan_b_dit_enregistree_hier():
    for nom in ("03_SCRIPT_ORAL_v2.md", "COMMENT_PRESENTER.md", "livrables/CARTE_REGIE_V2.html"):
        assert "enregistrée hier" in _texte(nom), nom
