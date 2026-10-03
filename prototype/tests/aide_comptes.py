"""Aide aux tests ANNÉE 1 : un compte d'administration ou du secrétariat avec son second facteur activé et sa session
élevée (exigé pour toute action d'administration depuis l'audit des lots 2-3). Données FICTIVES."""
import json
import time
import urllib.request

from intelligence.comptes import code_totp


def elever_http(base: str, session: str) -> str:
    """Par HTTP, contre un vrai serveur : préparer, confirmer, élever (codes RFC 6238 à l'heure réelle)."""
    def post(chemin: str, corps: dict) -> dict:
        req = urllib.request.Request(base + chemin, data=json.dumps(corps).encode(),
                                     headers={"Content-Type": "application/json", "X-Pulse-Compte": session})
        return json.load(urllib.request.urlopen(req, timeout=10))
    secret = post("/api/pulse/comptes/moi/totp/preparer", {})["secret"]
    post("/api/pulse/comptes/moi/totp/confirmer", {"code": code_totp(secret, time.time())})
    post("/api/pulse/comptes/moi/elever", {"code": code_totp(secret, time.time() + 30)})
    return secret
