"""P3 n°1 — APPEL D'OUTILS natif d'Apertus 1.5 (interrupteur APERTUS_APPEL_OUTILS=1, éteint par défaut).

Allumé : le schéma de la tâche part comme UNE fonction imposée (`tools` + `tool_choice`), et la sortie est l'argument
de l'appel d'outil. Le serveur refuse les outils (400/422) → consigne seule, comme pour `response_format`. Le modèle
répond en texte malgré tout → le texte est lu (la validation du code reste seule juge). Éteint : la requête d'hier."""
import json

import pytest

from intelligence.ia import Apertus

SCHEMA = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"], "additionalProperties": False}
ENV = {"APERTUS_API_KEY": "cle-de-test", "APERTUS_MODEL": "swiss-ai/Apertus-v1.5-70B", "APERTUS_BASE_URL": "https://exemple.invalid/v1"}


class Rep:
    def __init__(self, code, corps):
        self.status_code, self._c = code, corps

    def json(self):
        return self._c


class Faux:
    def __init__(self, *reponses):
        self.reponses, self.corps = list(reponses), []

    def post(self, url, headers=None, json=None, timeout=None):
        self.corps.append(json)
        return self.reponses.pop(0)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)


def _appel_outil(args):
    return Rep(200, {"choices": [{"message": {"content": None, "tool_calls": [
        {"type": "function", "function": {"name": "sortie", "arguments": json.dumps(args)}}]}}]})


def test_eteint_par_defaut_la_requete_d_hier(monkeypatch):
    monkeypatch.delenv("APERTUS_APPEL_OUTILS", raising=False)
    h = Faux(Rep(200, {"choices": [{"message": {"content": '{"x": 1}'}}]}))
    assert Apertus(http=h).completer("tâche", "texte", SCHEMA) == '{"x": 1}'
    assert "response_format" in h.corps[0] and "tools" not in h.corps[0]


def test_allume_une_fonction_imposee_et_l_argument_est_la_sortie(monkeypatch):
    monkeypatch.setenv("APERTUS_APPEL_OUTILS", "1")
    h = Faux(_appel_outil({"x": 7}))
    a = Apertus(http=h)
    assert json.loads(a.completer("tâche", "texte", SCHEMA)) == {"x": 7}
    c = h.corps[0]
    assert "response_format" not in c
    assert c["tools"] == [{"type": "function", "function": {"name": "sortie", "description": "Réponse structurée de la tâche.",
                                                            "parameters": SCHEMA}}]
    assert c["tool_choice"] == {"type": "function", "function": {"name": "sortie"}}
    assert a.contrainte == "outil"


def test_serveur_qui_refuse_les_outils_consigne_seule(monkeypatch):
    monkeypatch.setenv("APERTUS_APPEL_OUTILS", "1")
    h = Faux(Rep(400, {"error": "tools not supported"}), Rep(200, {"choices": [{"message": {"content": '{"x": 2}'}}]}))
    a = Apertus(http=h)
    assert a.completer("tâche", "texte", SCHEMA) == '{"x": 2}'
    assert "tools" not in h.corps[1] and "tool_choice" not in h.corps[1] and a.contrainte == "consigne"


def test_reponse_en_texte_malgre_l_outil_est_lue(monkeypatch):
    monkeypatch.setenv("APERTUS_APPEL_OUTILS", "1")
    h = Faux(Rep(200, {"choices": [{"message": {"content": '{"x": 3}', "tool_calls": []}}]}))
    assert Apertus(http=h).completer("tâche", "texte", SCHEMA) == '{"x": 3}'


def test_sans_schema_pas_d_outil(monkeypatch):
    monkeypatch.setenv("APERTUS_APPEL_OUTILS", "1")
    h = Faux(Rep(200, {"choices": [{"message": {"content": "bonjour"}}]}))
    assert Apertus(http=h).completer("tâche", "texte", None) == "bonjour"
    assert "tools" not in h.corps[0]
