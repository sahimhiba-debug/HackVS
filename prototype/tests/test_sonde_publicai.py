"""La SONDE Public AI dit ce qu'elle a mesuré, rien de plus : sans clé ou sans réseau, UNKNOWN ; un paramètre accepté mais
non appliqué est IGNORED, pas SUPPORTED ; la clé n'est jamais écrite. Transport simulé : aucun appel réseau ici."""
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sonde_publicai import Sonde  # noqa: E402

CLE = "cle-de-test-ne-doit-jamais-apparaitre-0123456789"
ENV = {"APERTUS_API_KEY": CLE, "APERTUS_BASE_URL": "https://api.exemple.test/v1"}
MODELES = {"data": [{"id": "swiss-ai/Apertus-70B-Instruct-2509"}, {"id": "swiss-ai/Apertus-70B-Thinking"}, {"id": "autre/modele"}]}


def _rep(contenu=None, tool_calls=None, **message):
    return {"choices": [{"message": {"role": "assistant", "content": contenu, **({"tool_calls": tool_calls} if tool_calls else {}), **message}}]}


def _transport(chat):
    vus = []

    def gerer(req: httpx.Request) -> httpx.Response:
        assert req.headers["authorization"] == f"Bearer {CLE}"
        if req.url.path.endswith("/models"):
            return httpx.Response(200, json=MODELES)
        corps = json.loads(req.content)
        vus.append(corps)
        return chat(corps)
    return httpx.Client(transport=httpx.MockTransport(gerer)), vus


def _verdicts(s):
    return {e.nom.split(" ")[0]: e.verdict for e in s.essais}


def test_sans_cle_tout_est_unknown_et_rien_n_est_appele():
    appels = []
    s = Sonde(env={}, http=httpx.Client(transport=httpx.MockTransport(lambda r: appels.append(r) or httpx.Response(500)))).lancer()
    assert appels == [] and set(_verdicts(s).values()) == {"UNKNOWN"}
    r = s.rapport()
    assert "UNKNOWN — aucune clé" in r and "Clé fournie : NON" in r


def test_hote_injoignable_est_unknown_et_le_dit():
    def couper(req):
        raise httpx.ConnectError("CONNECT tunnel failed, response 403")
    s = Sonde(env=ENV, http=httpx.Client(transport=httpx.MockTransport(couper))).lancer()
    assert set(_verdicts(s).values()) == {"UNKNOWN"}
    assert "injoignable : ConnectError" in s.rapport()


def test_tout_supporte_modele_instruct_sans_raisonnement_choisi():
    def chat(c):
        if "tools" in c:
            return httpx.Response(200, json=_rep(None, [{"type": "function", "function": {"name": "enregistrer_offre",
                                                                                          "arguments": '{"nature": "objet", "places": 14}'}}]))
        if "response_format" in c:
            return httpx.Response(200, json=_rep('{"canton": "VS", "code_postal_min": 1950}'))
        return httpx.Response(200, json=_rep('```json\n{"ville": "Sion", "langues": ["fr", "de"]}\n```'))
    http, vus = _transport(chat)
    s = Sonde(env=ENV, http=http).lancer()
    assert s.modele == "swiss-ai/Apertus-70B-Instruct-2509"                 # jamais le modèle « Thinking »
    assert all(c["model"] == s.modele for c in vus)
    assert _verdicts(s) == {"modèles": "SUPPORTED", "JSON": "SUPPORTED", "response_format": "SUPPORTED", "tools": "SUPPORTED",
                            "non-thinking": "SUPPORTED"}
    schema = next(c for c in vus if "response_format" in c)
    assert "canton" in json.dumps(schema["response_format"]) and "code_postal" not in json.dumps(schema["messages"])   # le prompt ne décrit pas le schéma


def test_accepte_mais_non_applique_est_ignored_et_rejete_est_rejected():
    def chat(c):
        if "tools" in c:
            return httpx.Response(200, json=_rep("Je note votre minibus."))                   # outil ignoré
        if "response_format" in c:
            return httpx.Response(200, json=_rep("Sion est dans le canton du Valais."))       # schéma ignoré
        return httpx.Response(200, json=_rep("<think>…</think> Sion", reasoning_content="je réfléchis"))
    s = Sonde(env=ENV, http=_transport(chat)[0]).lancer()
    v = _verdicts(s)
    assert v["JSON"] == v["response_format"] == v["tools"] == v["non-thinking"] == "IGNORED"
    assert "reasoning_content" in s.rapport() and "balise <think>" in s.rapport()

    s = Sonde(env=ENV, http=_transport(lambda c: httpx.Response(400, json={"error": "response_format not supported"})
                                        if "response_format" in c else httpx.Response(200, json=_rep('{"ville": "Sion", "langues": []}')))[0]).lancer()
    assert _verdicts(s)["response_format"] == "REJECTED"
    assert "response_format not supported" in s.rapport()                        # la réponse brute est consignée


def test_cle_invalide_est_une_erreur_pas_un_rejet_de_fonction():
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401, json={"error": "invalid key"})))
    s = Sonde(env=ENV, http=http).lancer()
    assert s.essais[0].verdict == "ERROR" and all(e.verdict == "UNKNOWN" for e in s.essais[1:])


def test_la_cle_n_est_jamais_ecrite(tmp_path):
    def chat(c):
        return httpx.Response(200, json=_rep(f"écho {CLE}"))                    # même si le serveur la renvoyait
    s = Sonde(env=ENV, http=_transport(chat)[0]).lancer()
    with pytest.raises(RuntimeError, match="écriture refusée"):
        s.rapport()
    s = Sonde(env=ENV, http=_transport(lambda c: httpx.Response(200, json=_rep("{}")))[0]).lancer()
    assert CLE not in s.rapport() and "Bearer" not in s.rapport()
