"""Sessions : « qui êtes-vous ? » (authentification). « Avez-vous le droit ? » est décidé ailleurs (service, politique).

Jeton = `identifiant.expiration.signature` (HMAC-SHA256, secret de `Reglages`). Pas d'état serveur à nettoyer ; une
expiration ; comparaison à temps constant. L'horloge est injectable (tests d'expiration sans attendre).
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Callable

from .erreurs import NonAuthentifie


class Sessions:
    def __init__(self, secret: bytes, duree_s: int, horloge: Callable[[], float] = time.time):
        self._secret, self.duree_s, self._horloge = secret, duree_s, horloge

    def _signature(self, pid: str, expiration: int) -> str:
        return hmac.new(self._secret, f"session|{pid}|{expiration}".encode(), hashlib.sha256).hexdigest()[:32]

    def emettre(self, pid: str) -> str:
        expiration = int(self._horloge()) + self.duree_s
        return f"{pid}.{expiration}.{self._signature(pid, expiration)}"

    def verifier(self, jeton: str) -> str:
        """Identifiant du membre, ou `NonAuthentifie` (jeton absent, mal formé, falsifié ou expiré)."""
        morceaux = (jeton or "").split(".")
        if len(morceaux) != 3 or not morceaux[1].isdigit():
            raise NonAuthentifie("session invalide")
        pid, exp, sig = morceaux[0], int(morceaux[1]), morceaux[2]
        if not hmac.compare_digest(self._signature(pid, exp), sig):
            raise NonAuthentifie("session invalide")
        if exp < self._horloge():
            raise NonAuthentifie("session expirée : scannez à nouveau votre invitation")
        return pid
