"""ANNÉE 1 · LOT 1 — Métriques simples, au format texte de Prometheus.

Volontairement pauvres : nombre de requêtes par classe de statut (2xx, 3xx, 4xx, 5xx), somme et nombre des durées,
nombre de faits du journal, temps depuis le démarrage. AUCUNE étiquette par route, par membre ou par adresse : une
métrique ne doit rien dire de qui fait quoi. Servies par /metriques seulement si HACKVS_METRIQUES=1, et seulement à
cette machine (ou avec le jeton de console)."""
from __future__ import annotations

import threading
import time

_v = threading.Lock()
_DEBUT = time.monotonic()
_par_classe: dict[str, int] = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
_duree = {"somme": 0.0, "nombre": 0}


def enregistrer(statut: int, duree_s: float) -> None:
    classe = f"{max(2, min(5, statut // 100))}xx"
    with _v:
        _par_classe[classe] += 1
        _duree["somme"] += duree_s
        _duree["nombre"] += 1


def texte(faits: int) -> str:
    with _v:
        lignes = ["# HELP clubpulse_requetes_total Requêtes servies, par classe de statut HTTP.",
                  "# TYPE clubpulse_requetes_total counter"]
        lignes += [f'clubpulse_requetes_total{{classe="{c}"}} {n}' for c, n in _par_classe.items()]
        lignes += ["# HELP clubpulse_duree_requetes_secondes Durée de traitement des requêtes.",
                   "# TYPE clubpulse_duree_requetes_secondes summary",
                   f"clubpulse_duree_requetes_secondes_somme {_duree['somme']:.6f}",
                   f"clubpulse_duree_requetes_secondes_nombre {_duree['nombre']}"]
    lignes += ["# HELP clubpulse_journal_faits Faits dans le journal du Club.", "# TYPE clubpulse_journal_faits gauge",
               f"clubpulse_journal_faits {faits}",
               "# HELP clubpulse_demarre_depuis_secondes Temps depuis le démarrage du processus.",
               "# TYPE clubpulse_demarre_depuis_secondes gauge",
               f"clubpulse_demarre_depuis_secondes {time.monotonic() - _DEBUT:.0f}"]
    return "\n".join(lignes) + "\n"
