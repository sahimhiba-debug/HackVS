"""L'URL PUBLIQUE du serveur, en UN endroit : tout lien et tout QR produit par le serveur (passe juré, passe
découverte, QR « salle », QR « visite », liens d'e-mail) en part. Ordre : PUBLIC_BASE_URL (déploiement, Foire 2026),
puis HACKVS_URL_PUBLIQUE (compatibilité : point d'accès du portable en salle), puis l'adresse de la requête."""
from __future__ import annotations

import os

from fastapi import Request


def base_publique(request: Request) -> str:
    return (os.environ.get("PUBLIC_BASE_URL") or os.environ.get("HACKVS_URL_PUBLIQUE") or str(request.base_url)).rstrip("/")
