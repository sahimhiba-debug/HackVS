"""Intersection privée d'ensembles (PSI) par Diffie-Hellman sur ristretto255 (libsodium via ctypes).

Protocole (semi-honnête) entre deux agents A et B, chacun avec un secret aléatoire :
  A envoie {H(x)^a}  →  B renvoie {(H(x)^a)^b} (dans le même ordre) et {H(y)^b}
  A calcule {(H(y)^b)^a} et compare : x est commun ⇔ H(x)^ab = H(y)^ba.
A apprend l'intersection (et la taille de l'ensemble de B) ; B n'apprend rien ; un relais qui transporte les
messages ne voit que des points aléatoires. Coût : 2 multiplications scalaires par élément et par côté.

Repli sans libsodium : groupe MODP 2048 bits (RFC 3526, groupe 14), sous-groupe des résidus quadratiques.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import secrets

_NOM = ctypes.util.find_library("sodium") or "libsodium.so.23"
try:
    _L = ctypes.CDLL(_NOM)
    _L.sodium_init()
    _RISTRETTO = hasattr(_L, "crypto_scalarmult_ristretto255")
except OSError:
    _RISTRETTO = False

_P = int("FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DD"
         "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
         "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
         "83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
         "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
         "15728E5A8AACAA68FFFFFFFFFFFFFFFF", 16)
DOMAINE = b"fil-du-club/intentions-scellees/v1|"
MOTEUR = "ristretto255 (libsodium)" if _RISTRETTO else "MODP-2048 (repli)"


class Cle:
    """Secret éphémère d'un agent pour UNE session (jamais réutilisé, jamais transmis)."""

    def __init__(self) -> None:
        if _RISTRETTO:
            b = ctypes.create_string_buffer(32)
            _L.crypto_core_ristretto255_scalar_random(b)
            self.k: bytes | int = b.raw
        else:
            self.k = secrets.randbelow((_P - 1) // 2 - 2) + 2

    def aveugler_texte(self, jeton: str) -> bytes:
        return self.aveugler_point(hacher(jeton))

    def aveugler_point(self, pt: bytes) -> bytes:
        if _RISTRETTO:
            out = ctypes.create_string_buffer(32)
            if _L.crypto_scalarmult_ristretto255(out, self.k, pt) != 0:
                raise ValueError("point invalide")
            return out.raw
        return pow(int.from_bytes(pt, "big"), int(self.k), _P).to_bytes(256, "big")  # type: ignore[call-overload]


def hacher(jeton: str) -> bytes:
    h = hashlib.sha512(DOMAINE + jeton.encode()).digest()
    if _RISTRETTO:
        out = ctypes.create_string_buffer(32)
        _L.crypto_core_ristretto255_from_hash(out, h)
        return out.raw
    return pow(int.from_bytes(h * 4, "big") % _P, 2, _P).to_bytes(256, "big")


def intersection(mes_jetons: list[str], les_siens: list[str]) -> set[str]:
    """Simulation locale du protocole complet (les deux agents dans le même processus : pour les mesures)."""
    a, b = Cle(), Cle()
    msg1 = [a.aveugler_texte(x) for x in mes_jetons]            # A → B
    retour = [b.aveugler_point(p) for p in msg1]                 # B → A (même ordre)
    msg2 = {a.aveugler_point(b.aveugler_texte(y)) for y in les_siens}  # B → A puis A ré-aveugle
    return {x for x, r in zip(mes_jetons, retour, strict=True) if r in msg2}
