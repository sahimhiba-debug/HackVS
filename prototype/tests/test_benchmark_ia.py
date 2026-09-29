"""Mécanique du banc G1 (moteur / IA seule / hybride) vérifiée SANS modèle réel : un double de test renvoie des
réponses construites. Aucun chiffre de ce test n'est un résultat d'IA."""
import json
from types import SimpleNamespace

from eval.benchmark_ia import evaluer_bras, ia_seule_client
from eval.run_eval import charger

CAS = [{"id": "c1", "categorie": "test", "texte": "Je cherche un transporteur frigorifique pour Zurich.",
        "attendus": ["p01"], "interdits": ["p02"], "abstention": False},
       {"id": "c2", "categorie": "test", "texte": "Je cherche un distributeur au Japon.", "attendus": [], "interdits": [],
        "abstention": True}]


class DoubleClient:
    """Imite l'interface `messages.create` du SDK ; réponses construites pour exercer la notation."""
    def __init__(self, reponses):
        self.reponses, self.messages, self.systemes = list(reponses), self, []

    def create(self, **kw):
        self.systemes.append(kw["system"])
        corps = json.dumps(self.reponses.pop(0))
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=corps)])


def test_ia_seule_inventions_violations_et_abstention_sont_comptees():
    profils, par_id, moi = charger()
    ferme = next(p.id for p in profils if not p.accepte_introductions)
    double = DoubleClient([{"ids": ["p01", "p99_invente", ferme], "abstention": False, "justification": "x"},
                           {"ids": [], "abstention": True, "justification": "personne"}])
    r = evaluer_bras("IA_SEULE", CAS, profils, par_id, moi, llm=ia_seule_client(profils, moi, double))
    assert r["inventes"] == 1 and r["violations"] == 1 and r["succes@3"] == 1 and r["abstention_ok"] == 2
    assert r["appels_llm"] == 2
    assert "p01" in double.systemes[0] and moi.id not in json.loads(double.systemes[0].split("JSON) :\n")[1])[0]["id"]


def test_bras_moteur_sans_appel_au_modele():
    profils, par_id, moi = charger()
    r = evaluer_bras("MOTEUR", CAS, profils, par_id, moi)
    assert r["appels_llm"] == 0 and r["inventes"] == 0
