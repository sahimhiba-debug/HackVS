"""Observabilité : un identifiant par requête, une ligne JSON par fait, et JAMAIS de contenu privé.

Journalisé : route, méthode, statut, durée, identifiants techniques (requête, activation, appel IA), classe d'erreur.
Jamais journalisé : corps de requête, en-têtes (sessions, jetons), notes, textes libres, noms, prompts, sorties de
modèle, messages d'exception (ils peuvent citer une donnée) — d'une exception on garde le TYPE et la pile d'appels.

L'identifiant de requête est posé dans un `ContextVar` : les journaux du domaine (`intelligence.*`) le portent sans
que le domaine dépende de la couche HTTP (un filtre l'ajoute à chaque enregistrement).
"""
from __future__ import annotations

import contextvars
import json
import logging
import re
import time
import traceback
import uuid
from typing import Any, Awaitable, Callable, Mapping, MutableMapping

ID_REQUETE: contextvars.ContextVar[str] = contextvars.ContextVar("id_requete", default="-")
_ID_SUR = re.compile(r"^[A-Za-z0-9._-]{8,64}$")          # un identifiant fourni par le client n'est repris que s'il est inoffensif
# champs structurés admis dans une ligne (liste FERMÉE : un champ imprévu n'est pas écrit)
CHAMPS = ("route", "methode", "statut", "duree_ms", "classe", "activation", "de", "vers", "agent", "trace", "tache",
          "fournisseur", "modele", "prompt", "repli", "politique", "erreur_ia")

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class FormatJSON(logging.Formatter):
    def format(self, r: logging.LogRecord) -> str:
        d: dict[str, Any] = {"t": self.formatTime(r, "%Y-%m-%dT%H:%M:%S"), "niveau": r.levelname, "source": r.name,
                             "msg": r.getMessage(), "requete": getattr(r, "requete", ID_REQUETE.get())}
        for k in CHAMPS:
            v = getattr(r, k, None)
            if v is not None:
                d[k] = v
        if r.exc_info and r.exc_info[0] is not None:        # type + pile, SANS le message (qui peut citer une donnée)
            d["exception"] = r.exc_info[0].__name__
            d["pile"] = "".join(traceback.format_tb(r.exc_info[2]))[-2000:]
        return json.dumps(d, ensure_ascii=False)


class _AjouterRequete(logging.Filter):
    def filter(self, r: logging.LogRecord) -> bool:
        r.requete = ID_REQUETE.get()
        return True


NIVEAUX = ("DEBUG", "INFO", "WARNING", "ERROR")


def niveau_depuis_env(env: Mapping[str, str]) -> str:
    """HACKVS_JOURNAL (défaut INFO). Une valeur inconnue est une erreur de configuration EXPLICITE au démarrage."""
    niveau = env.get("HACKVS_JOURNAL", "INFO").upper()
    if niveau not in NIVEAUX:
        raise ValueError(f"HACKVS_JOURNAL={niveau!r} : valeurs admises {', '.join(NIVEAUX)}")
    return niveau


def configurer(niveau: str = "INFO") -> None:
    """Idempotent. Les journaux de l'application (`hackvs`) et du domaine (`intelligence`) sortent en JSON sur stderr."""
    for nom in ("hackvs", "intelligence"):
        lg = logging.getLogger(nom)
        lg.setLevel(niveau)
        if not any(getattr(h, "_hackvs", False) for h in lg.handlers):
            h = logging.StreamHandler()
            h.setFormatter(FormatJSON())
            h.addFilter(_AjouterRequete())
            h._hackvs = True  # type: ignore[attr-defined]
            lg.addHandler(h)


journal = logging.getLogger("hackvs.http")


class MiddlewareRequete:
    """ASGI pur (pas de BaseHTTPMiddleware : le ContextVar se propage aux gestionnaires synchrones et asynchrones).
    Pose l'identifiant, le renvoie dans `X-Request-ID`, journalise UNE ligne par requête, et transforme une panne non
    prévue en 500 JSON portant l'identifiant (l'utilisateur peut le citer ; le détail reste dans le journal)."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        fourni = dict(scope.get("headers") or []).get(b"x-request-id", b"").decode("latin-1")
        rid = fourni if _ID_SUR.match(fourni) else uuid.uuid4().hex[:16]
        jeton = ID_REQUETE.set(rid)
        t0 = time.perf_counter()
        statut = {"code": 500, "envoye": False}

        async def envoyer(m: Message) -> None:
            if m["type"] == "http.response.start":
                statut["code"], statut["envoye"] = m["status"], True
                m["headers"] = list(m.get("headers", [])) + [(b"x-request-id", rid.encode())]
            await send(m)
        try:
            await self.app(scope, receive, envoyer)
        except Exception as e:
            journal.error("panne non prévue", exc_info=True, extra={"route": scope.get("path"), "methode": scope.get("method"),
                                                                    "classe": type(e).__name__})
            if statut["envoye"]:
                raise
            corps = json.dumps({"detail": "Erreur interne du serveur.", "requete": rid}).encode()
            await send({"type": "http.response.start", "status": 500,
                        "headers": [(b"content-type", b"application/json"), (b"x-request-id", rid.encode())]})
            await send({"type": "http.response.body", "body": corps})
        finally:
            code = statut["code"]
            niveau = logging.ERROR if code >= 500 else logging.WARNING if code in (401, 403, 409, 429) else logging.INFO
            journal.log(niveau, "requête", extra={"route": scope.get("path"), "methode": scope.get("method"), "statut": code,
                                                  "duree_ms": round((time.perf_counter() - t0) * 1000, 1)})
            ID_REQUETE.reset(jeton)
