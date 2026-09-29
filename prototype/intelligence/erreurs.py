"""Erreurs MÉTIER typées : un refus attendu n'est jamais une panne.

Chaque classe porte son code HTTP, traduit à UN seul endroit (`app/pulse_api.py`). Les messages sont écrits pour
l'utilisateur : ils ne contiennent ni identité, ni donnée privée, ni détail d'implémentation. Une erreur qui n'est
PAS une `ErreurMetier` (bogue, panne) remonte telle quelle et devient un 500 journalisé — jamais maquillée en refus.
"""
from __future__ import annotations


class ErreurMetier(Exception):
    statut_http = 422


class Invalide(ErreurMetier):
    """Entrée mal formée ou hors limites."""
    statut_http = 422


class NonAuthentifie(ErreurMetier):
    """Qui êtes-vous ? — session absente, expirée ou falsifiée ; code d'invitation inconnu."""
    statut_http = 401


class Interdit(ErreurMetier):
    """Avez-vous le droit ? — authentifié, mais ce geste ne vous revient pas."""
    statut_http = 403


class Introuvable(ErreurMetier):
    """Inconnu — ou invisible pour vous (on ne révèle pas l'existence de ce qu'on ne peut pas voir)."""
    statut_http = 404


class Conflit(ErreurMetier):
    """L'état a changé ou ne permet pas ce geste (transition interdite, déjà fait, budget atteint)."""
    statut_http = 409


class Limite(ErreurMetier):
    """Trop de demandes en peu de temps."""
    statut_http = 429
