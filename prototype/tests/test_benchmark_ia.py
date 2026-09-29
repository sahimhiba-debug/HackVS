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


def _faux_apertus(monkeypatch, reponses, premier_statut=200):
    """Double du serveur Apertus (API compatible OpenAI) : enregistre les requêtes, renvoie des réponses construites."""
    import httpx
    monkeypatch.setenv("HACKVS_LLM", "apertus")
    for k, v in {"APERTUS_API_KEY": "factice", "APERTUS_BASE_URL": "https://apertus.test/v1", "APERTUS_MODEL": "m"}.items():
        monkeypatch.setenv(k, v)
    requetes, file = [], list(reponses)

    def gerer(req):
        requetes.append(json.loads(req.content))
        if premier_statut != 200 and len(requetes) == 1:
            return httpx.Response(premier_statut, json={"error": "response_format non pris en charge"})
        return httpx.Response(200, json={"choices": [{"message": {"content": file.pop(0)}}]})
    return httpx.Client(transport=httpx.MockTransport(gerer)), requetes


def test_ia_seule_via_apertus_et_repli_sans_sortie_contrainte(monkeypatch):
    profils, par_id, moi = charger()
    http, requetes = _faux_apertus(monkeypatch, ['```json\n{"ids": ["p01"], "abstention": false, "justification": "x"}\n```',
                                                 '{"ids": [], "abstention": true, "justification": "personne"}'], 400)
    r = evaluer_bras("IA_SEULE", CAS, profils, par_id, moi, llm=ia_seule_client(profils, moi, apertus_http=http))
    assert r["succes@3"] == 1 and r["abstention_ok"] == 2 and r["appels_llm"] == 2
    assert "response_format" in requetes[0] and "response_format" not in requetes[1]   # repli : consigne seule
    assert requetes[1]["model"] == "m" and requetes[1]["temperature"] == 0


def test_synthese_via_apertus(monkeypatch):
    from eval.benchmark_synthese import _llm
    http, requetes = _faux_apertus(monkeypatch, ["Le réseau compte 120 membres."])
    assert _llm(apertus_http=http)({"membres": 120}) == "Le réseau compte 120 membres."
    assert "response_format" not in requetes[0] and "120" in requetes[0]["messages"][1]["content"]
