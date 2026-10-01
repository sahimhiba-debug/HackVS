"""QR JURÉ : la console remet à un membre du jury, par un QR code, le téléphone d'un personnage FICTIF pour la scène.

Un passe = « nonce.expiration.personnage.signature » (HMAC du secret du processus) :
- EXPIRATION : courte (15 min par défaut) ; la session obtenue expire avec le passe, pas plus tard ;
- NONCE UNIQUE : tiré au hasard à l'émission, CONSOMMÉ à la première activation — un QR photographié et rescanné ne
  donne rien ; un passe émis par un autre monde ne vaut rien. Émission et activation sont JOURNALISÉES (nonce,
  personnage, expiration — jamais la signature) : après un redémarrage sur le même journal et le même secret, un
  passe encore valable le reste, un passe consommé le reste aussi (F29) ;
- LIMITATION par CODE (activations tentées sur un même nonce) et par SESSION (actions d'une session de juré) — jamais
  par adresse IP : dans une salle, tout le public sort par la même adresse, et le premier bloquerait les autres.
Aucune donnée réelle : le passe ne désigne qu'un personnage du monde fictif."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Callable

from .erreurs import Conflit, NonAuthentifie


class PassesJure:
    def __init__(self, secret: bytes, horloge: Callable[[], float] = time.time):
        self._secret, self._horloge = secret, horloge
        self._en_attente: dict[str, tuple[str, int]] = {}        # nonce → (personnage, expiration)
        self._utilises: set[str] = set()
        self._sessions: set[tuple[str, int]] = set()              # sessions de juré : (personnage, expiration)

    def _signature(self, nonce: str, exp: int, pid: str) -> str:
        return hmac.new(self._secret, f"jure|{nonce}|{exp}|{pid}".encode(), hashlib.sha256).hexdigest()[:32]

    def emettre(self, pid: str, duree_s: int) -> tuple[str, int]:
        nonce, exp = secrets.token_hex(8), int(self._horloge()) + duree_s
        self._en_attente[nonce] = (pid, exp)
        return f"{nonce}.{exp}.{pid}.{self._signature(nonce, exp, pid)}", exp

    @staticmethod
    def nonce(jeton: str) -> str:
        """La clé de limitation d'un essai d'activation : le code lui-même (jamais l'adresse IP du client)."""
        return (jeton or "").split(".", 1)[0][:32] or "?"

    def utiliser(self, jeton: str) -> tuple[str, int]:
        morceaux = (jeton or "").split(".")
        if len(morceaux) != 4 or not morceaux[1].isdigit():
            raise NonAuthentifie("passe de juré invalide")
        nonce, exp, pid, sig = morceaux[0], int(morceaux[1]), morceaux[2], morceaux[3]
        if not hmac.compare_digest(self._signature(nonce, exp, pid), sig):
            raise NonAuthentifie("passe de juré invalide")
        if exp < self._horloge():
            self._en_attente.pop(nonce, None)
            raise NonAuthentifie("passe de juré expiré : demandez-en un nouveau à l'équipe")
        if nonce in self._utilises:
            raise Conflit("ce passe de juré a déjà été utilisé : demandez-en un nouveau à l'équipe")
        if self._en_attente.get(nonce) != (pid, exp):          # signé, mais pas émis par CE processus (redémarrage)
            raise NonAuthentifie("passe de juré inconnu")
        del self._en_attente[nonce]
        self._utilises.add(nonce)
        return pid, exp

    def reprendre(self, emis: list[tuple[str, str, int]], utilises: list[str], sessions: list[tuple[str, int]]) -> None:
        """Redémarrage : l'état des passes RELU du journal (émis, consommés, sessions ouvertes)."""
        self._utilises = set(utilises)
        self._en_attente = {n: (pid, exp) for n, pid, exp in emis if n not in self._utilises}
        self._sessions = set(sessions)

    def noter_session(self, pid: str, exp: int) -> None:
        self._sessions.add((pid, exp))

    def est_session_de_jure(self, session: str) -> bool:
        """Une session de juré expire avec son passe : son jeton porte (personnage, expiration) ; aucun jeton n'est gardé."""
        morceaux = (session or "").split(".")
        if len(morceaux) != 3 or not morceaux[1].isdigit():
            return False
        cle = (morceaux[0], int(morceaux[1]))
        return cle in self._sessions and cle[1] >= self._horloge()
