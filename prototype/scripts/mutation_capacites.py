"""Campagne de MUTATION du registre des capacités (mutmut, config : setup.cfg) et contrôle de la liste CLASSÉE.

    python scripts/mutation_capacites.py            # lance mutmut, puis échoue si un survivant n'est pas classé
    python scripts/mutation_capacites.py --ecrire   # réécrit la liste (après avoir classé chaque nouveau survivant)

La liste `docs/audit/mutants_survivants.txt` contient chaque survivant jugé ÉQUIVALENT (identifiant et ligne mutée).
Un survivant absent de cette liste est un comportement que la suite ne distingue pas d'une variante fausse : on
écrit le test qui le tue, ou on le classe explicitement comme équivalent (et on dit pourquoi dans le compte rendu).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
LISTE = RACINE.parent / "docs" / "audit" / "mutants_survivants.txt"
ENTETE = ("# Mutants SURVIVANTS classés ÉQUIVALENTS — mutmut sur prototype/intelligence/capacites.py.\n"
          "# Mis à jour à chaque campagne (scripts/mutation_capacites.py --ecrire) ; classement : docs/audit/PHASE_1.md § 4.\n"
          "# format : fonction__mutmut_n | ligne mutée\n")


def _mutmut(*args: str) -> str:
    p = subprocess.run([sys.executable, "-m", "mutmut", *args], cwd=RACINE, capture_output=True, text=True)
    return p.stdout + p.stderr


def survivants() -> list[str]:
    res = []
    for ligne in _mutmut("results").splitlines():
        if ligne.strip().endswith(": survived"):
            mid = ligne.strip().split(":")[0]
            diff = [x for x in _mutmut("show", mid).splitlines() if x.startswith("+ ")]
            res.append(f"{mid.removeprefix('intelligence.capacites.')} | {diff[0][2:].strip()[:160] if diff else ''}")
    return sorted(res)


def main() -> int:
    ecrire = "--ecrire" in sys.argv
    if "--sans-lancer" not in sys.argv:
        sortie = _mutmut("run")
        print(sortie.replace("\r", "\n").strip().splitlines()[-2] if sortie.strip() else "mutmut : aucune sortie")
    trouves = survivants()
    if ecrire:
        LISTE.write_text(ENTETE + "\n".join(trouves) + "\n", encoding="utf-8")
        print(f"{len(trouves)} survivants écrits dans {LISTE.name} : classez chacun avant de valider.")
        return 0
    classes = {x for x in LISTE.read_text(encoding="utf-8").splitlines() if x and not x.startswith("#")} if LISTE.exists() else set()
    nouveaux = [x for x in trouves if x not in classes]
    for x in nouveaux:
        print("NON CLASSÉ :", x)
    print(f"{len(trouves)} survivants, {len(nouveaux)} non classés")
    return 1 if nouveaux else 0


if __name__ == "__main__":
    sys.exit(main())
