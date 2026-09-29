"""Rejoue TOUS les benchmarks du sprint d'innovation et régénère leurs fichiers de résultats.

Si `git diff eval/resultats_*.md` est vide après exécution, les chiffres publiés sont reproductibles à l'octet près
(tout est déterministe : graines fixées, aucune horloge réelle, aucun appel externe).

    python scripts/reproduire_sprint.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
BENCHMARKS = [
    ("eval.reseaux_pathologiques", ["--graines", "20", "--sortie", "eval/resultats_observatoire.md"]),
    ("eval.benchmark_pareto", ["--reseaux", "20", "--sortie", "eval/resultats_benchmark_pareto.md"]),
    ("eval.benchmark_extinction", ["--reseaux", "20", "--horizon", "30", "--sortie", "eval/resultats_benchmark_extinction.md"]),
    ("eval.benchmark_serendipite", ["--k", "3", "--sortie", "eval/resultats_serendipite.md"]),
    ("eval.benchmark_invitations", ["--reseaux", "20", "--sortie", "eval/resultats_benchmark_invitations.md"]),
    ("eval.simulation_boucle", ["--reseaux", "5", "--mois", "3", "--sortie", "eval/resultats_simulation_boucle.md"]),
    ("eval.benchmark_categories", ["--sortie", "eval/resultats_benchmark_categories.md"]),
    ("eval.benchmark_pulse", []),                  # Club Pulse : détection, pièges, replanification (oracle), confidentialité
]


def main() -> int:
    echecs = 0
    for module, args in BENCHMARKS:
        t0 = time.perf_counter()
        p = subprocess.run([sys.executable, "-m", module, *args], cwd=RACINE, capture_output=True, text=True,
                           env={"HACKVS_SEMANTIQUE": "0", **__import__("os").environ})
        print(f"{'OK ' if p.returncode == 0 else 'ÉCHEC'} {module} ({time.perf_counter() - t0:.0f} s)")
        echecs += p.returncode != 0
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
