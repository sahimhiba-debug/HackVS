"""Protections HTTP transverses : en-têtes de sécurité, politique de contenu (CSP) des pages Club Pulse, taille des corps.

- CSP stricte pour /app et /console : aucun script sauf nos propres fichiers et les scripts EN LIGNE de ces pages,
  autorisés par leur empreinte SHA-256 calculée au démarrage (pas de 'unsafe-inline' pour les scripts). Le DOM y est
  construit par `createTextNode`, jamais par `innerHTML` : la CSP est une seconde ligne, pas la seule.
  Les styles en ligne restent permis ('unsafe-inline' pour style-src seulement : risque faible, documenté).
- Anciennes pages (prototype antérieur) : en-têtes de base, sans CSP (leurs scripts en ligne ne sont pas recensés).
- CORS : aucun intergiciel CORS ⇒ le navigateur n'autorise que la même origine. La console exige en plus un en-tête
  personnalisé (pas de requête intersite « simple » possible).
- Corps de requête : 64 Kio au plus (les champs sont bornés par les schémas, mais un corps énorme serait lu avant).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
from pathlib import Path
from typing import Callable, Iterable, Optional

from .observabilite import ASGIApp, Message, Receive, Scope, Send

CORPS_MAX = 64 * 1024
LOCALES = {"127.0.0.1", "::1", "localhost", "testclient"}      # « testclient » : client de test en processus
# ce que le serveur de démonstration sert : Club Pulse, et rien d'autre (l'ancien prototype est derrière un drapeau)
CLUB_PULSE_EXACTS = {"/app", "/app/", "/app/manifest.webmanifest", "/app/sw.js", "/console", "/projection", "/demo/regie", "/etabli",
                     "/suivi", "/decouverte", "/reponse", "/salle", "/salle/ecran", "/salle/regie",
                     "/favicon.ico", "/sante"}   # Foire 2026 : Suivi, passe découverte, réponse e-mail
CLUB_PULSE_PREFIXES = ("/api/pulse/", "/static/pulse/")
TROP_GROS = '{"detail": "Corps de requête trop volumineux (64 Kio au plus)."}'.encode()
_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S | re.I)

BASE = {b"x-content-type-options": b"nosniff", b"referrer-policy": b"no-referrer", b"x-frame-options": b"SAMEORIGIN",
        b"permissions-policy": b"camera=(), geolocation=(), microphone=(), payment=()",
        b"cross-origin-opener-policy": b"same-origin"}


def empreintes(pages: Iterable[Path]) -> list[str]:
    """Empreinte de chaque script en ligne, telle que le navigateur la calcule (octets exacts entre les balises)."""
    res = []
    for p in pages:
        for s in _SCRIPT.findall(p.read_text(encoding="utf-8")):
            res.append("'sha256-" + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode() + "'")
    return sorted(set(res))


def politique_contenu(pages: Iterable[Path]) -> bytes:
    return ("default-src 'self'; script-src 'self' " + " ".join(empreintes(pages)) + "; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; worker-src 'self'; manifest-src 'self'; frame-ancestors 'self'; "
            "base-uri 'none'; form-action 'self'; object-src 'none'").encode()


class Protections:
    def __init__(self, app: ASGIApp, csp: bytes, chemins_csp: tuple[str, ...] = ("/app", "/console")):
        self.app, self.csp, self.chemins_csp = app, csp, chemins_csp

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        chemin: str = scope.get("path", "")
        entetes = dict(scope.get("headers") or [])
        longueur = entetes.get(b"content-length", b"")
        if longueur and (not longueur.isdigit() or int(longueur) > CORPS_MAX):
            await _refuser(send, 413, TROP_GROS)
            return
        etat = {"n": 0, "refuse": False}

        async def recevoir() -> Message:
            # corps sans longueur annoncée (chunked) : compté au fil de l'eau ; au-delà, on répond 413 nous-mêmes et on
            # signale une déconnexion à l'application (elle abandonne ; ses propres réponses sont alors ignorées)
            m = await receive()
            if m["type"] == "http.request":
                etat["n"] += len(m.get("body", b""))
                if etat["n"] > CORPS_MAX:
                    if not etat["refuse"]:
                        etat["refuse"] = True
                        await _refuser(send, 413, TROP_GROS)
                    return {"type": "http.disconnect"}
            return m

        async def envoyer(m: Message) -> None:
            if etat["refuse"]:
                return
            if m["type"] == "http.response.start":
                h = [(k, v) for k, v in m.get("headers", []) if k.lower() not in BASE]
                h += list(BASE.items())
                if chemin in self.chemins_csp or chemin.rstrip("/") in self.chemins_csp:
                    h.append((b"content-security-policy", self.csp))
                if chemin.startswith("/api/pulse/"):
                    h.append((b"cache-control", b"no-store"))    # données personnelles : jamais en cache intermédiaire
                m["headers"] = h
            await send(m)
        await self.app(scope, recevoir, envoyer)


async def _refuser(send: Send, statut: int, corps: bytes) -> None:
    await send({"type": "http.response.start", "status": statut,
                "headers": [(b"content-type", b"application/json"), *BASE.items()]})
    await send({"type": "http.response.body", "body": corps})


def club_pulse(chemin: str) -> bool:
    return chemin in CLUB_PULSE_EXACTS or chemin.startswith(CLUB_PULSE_PREFIXES)


class Perimetre:
    """Le serveur ne sert que Club Pulse. L'ANCIEN prototype (identité par en-tête `X-Membre`, réinitialisation sans
    garde) n'existe que si `ancien_actif()` — et alors seulement pour cette machine, ou avec le jeton de console s'il
    est défini. Hors de ce périmètre : 404 (rien n'en révèle l'existence) ; la racine mène à l'application du membre."""

    def __init__(self, app: ASGIApp, ancien_actif: Callable[[], bool], jeton: Callable[[], Optional[str]]):
        self.app, self._ancien, self._jeton = app, ancien_actif, jeton

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or club_pulse(scope.get("path", "")):
            await self.app(scope, receive, send)
            return
        chemin = scope.get("path", "")
        if not self._ancien():
            if chemin == "/":
                await send({"type": "http.response.start", "status": 307, "headers": [(b"location", b"/app"), *BASE.items()]})
                await send({"type": "http.response.body", "body": b""})
                return
            await _refuser(send, 404, b'{"detail": "Not Found"}')
            return
        jeton = self._jeton()
        if jeton:
            fourni = dict(scope.get("headers") or []).get(b"x-pulse-console", b"").decode("latin-1")
            permis = hmac.compare_digest(fourni, jeton)
        else:
            client = scope.get("client") or ("", 0)
            permis = client[0] in LOCALES
        if not permis:
            await _refuser(send, 403, b'{"detail": "Ancien prototype : accessible seulement depuis cette machine ou avec le jeton de console."}')
            return
        await self.app(scope, receive, send)
