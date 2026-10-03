"""FOIRE 2026 · G — BILAN DE PÉRIODE : mêmes chiffres que Suivi, étiqueté « monde de démonstration », aucun nom ; le
récit d'un modèle n'est accepté que si CHAQUE nombre qu'il écrit est dans les statistiques calculées. Données FICTIVES."""
import subprocess
import sys
from pathlib import Path

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import bilan, suivi
from intelligence import monde_demo as md
from intelligence.demo import Demo

PROTO = Path(__file__).resolve().parents[1]


@pytest.fixture
def c(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    sys.path.insert(0, str(PROTO / "scripts"))
    import bilan as script                                   # la scène du script : un seul endroit
    club = Demo(charger_taxonomie()).club
    script.scene(club)
    return club


class Faux:
    modele = "faux-modele"

    def __init__(self, texte=None, erreur=None):
        self.texte, self.erreur = texte, erreur

    def completer(self, systeme, message, schema):
        assert "Pauline" not in message and md.PAULINE not in message      # le modèle ne reçoit que des agrégats
        if self.erreur:
            raise self.erreur
        return self.texte


def test_les_chiffres_du_bilan_sont_ceux_de_suivi(c):
    s = suivi.calculer(c, "trimestre")
    t = bilan.rediger(c, "trimestre")
    assert "monde de démonstration" in t
    assert f"| Demandes envoyées | {s['demandes']['adressees']} |" in t
    assert f"| Réponses oui | {s['reponses']['oui']} |" in t
    assert "| Résultat déclaré — contact établi | < 3 |" in t
    for nom in ("Pauline", "Markus", "Annecy", "Exposant", md.PAULINE, "Premier contact"):
        assert nom not in t


def test_verifier_recit_rejette_tout_nombre_invente():
    s = {"demandes": {"adressees": 12, "sans_reponse": 3}, "reponses": {"oui": "< 3"}, "du": "2026-10-06", "regles": "sous 3"}
    assert bilan.verifier_recit("Le Club a adressé 12 demandes ; 3 restent ouvertes ; moins de 3 oui.", s) == []
    assert bilan.verifier_recit("Le Club a adressé 12 demandes, soit 25 % de plus.", s) == ["25"]
    assert bilan.verifier_recit("Depuis le 10 octobre, 12 demandes.", s) == ["10"]      # une date n'autorise pas un chiffre


def test_recit_du_modele_accepte_rejete_ou_en_panne(c):
    s = suivi.calculer(c, "trimestre")
    n = s["demandes"]["adressees"]
    c.ia.f, c.ia.actif = Faux(f"Ce trimestre, le Club a adressé {n} demandes."), True
    t = bilan.rediger(c, "trimestre", ia=True)
    assert f"le Club a adressé {n} demandes" in t and "vérifié par le code" in t
    c.ia.f = Faux(f"Ce trimestre, le Club a adressé {n} demandes, 40 % de plus qu'avant.")
    t = bilan.rediger(c, "trimestre", ia=True)
    assert "40 %" not in t and "REJETÉ par le code" in t and "40" in t
    c.ia.f = Faux(erreur=TimeoutError())
    assert "modèle indisponible (TimeoutError)" in bilan.rediger(c, "trimestre", ia=True)
    c.ia.actif = False
    assert "forme déterministe" in bilan.rediger(c, "trimestre", ia=True)


def test_make_bilan_ecrit_le_fichier(tmp_path):
    sortie = tmp_path / "bilan.md"
    r = subprocess.run([sys.executable, "scripts/bilan.py", "7j", "--scene", "--sortie", str(sortie)], cwd=PROTO,
                       capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "HACKVS_FOIRE": "1"})
    assert r.returncode == 0, r.stderr
    t = sortie.read_text(encoding="utf-8")
    assert t.startswith("# Bilan — 7 derniers jours") and "scène Foire 2026 jouée par le script" in t
