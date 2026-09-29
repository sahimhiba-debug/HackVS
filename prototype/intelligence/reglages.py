"""Configuration de Club Pulse : UN seul endroit lit l'environnement.

Aucun secret n'a de valeur par défaut dans le code : sans `HACKVS_SECRET`, un secret ALÉATOIRE est tiré au démarrage
(les sessions et codes d'invitation meurent avec le processus — voulu pour une démonstration). La configuration
d'Apertus est lue par `intelligence.ia.Apertus` (mêmes règles : absente → repli déterministe déclaré).
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass(frozen=True)
class Reglages:
    secret: bytes                      # signe les sessions et dérive les codes d'invitation
    secret_fourni: bool                # False : secret aléatoire du processus (démonstration)
    console_jeton: Optional[str]       # si défini, exigé par la console du Club (en-tête X-Pulse-Console)
    notes_privees_vers_ia: bool        # une note PRIVÉE peut-elle partir vers un fournisseur externe ? (non par défaut)
    duree_session_s: int = 12 * 3600
    essais_db: str = ":memory:"        # journal du banc d'essai (HACKVS_ESSAIS_DB : fichier → survit au redémarrage)

    @classmethod
    def depuis_env(cls, env: Optional[Mapping[str, str]] = None) -> "Reglages":
        e = os.environ if env is None else env
        brut = e.get("HACKVS_SECRET", "")
        if brut and len(brut) < 32:
            raise ValueError("HACKVS_SECRET doit compter au moins 32 caractères")
        return cls(secret=brut.encode() if brut else secrets.token_bytes(32), secret_fourni=bool(brut),
                   console_jeton=e.get("HACKVS_CONSOLE_JETON") or None,
                   notes_privees_vers_ia=e.get("APERTUS_NOTES_PRIVEES", "") == "1",
                   essais_db=e.get("HACKVS_ESSAIS_DB") or ":memory:")
