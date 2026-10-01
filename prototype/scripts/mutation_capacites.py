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


def _mutmut(*args: str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, "-m", "mutmut", *args], cwd=RACINE, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def statuts() -> dict[str, str]:
    """Chaque mutant et son statut (killed, survived, no tests, not checked, timeout, suspicious…)."""
    res = {}
    for ligne in _mutmut("results", "--all", "true")[1].splitlines():
        if ": " in ligne.strip():
            mid, statut = ligne.strip().rsplit(": ", 1)
            res[mid] = statut
    return res


def _ligne(mid: str) -> str:
    diff = [x for x in _mutmut("show", mid)[1].splitlines() if x.startswith("+ ")]
    return f"{mid.removeprefix('intelligence.capacites.')} | {diff[0][2:].strip()[:160] if diff else ''}"


def main() -> int:
    ecrire = "--ecrire" in sys.argv
    if "--sans-lancer" not in sys.argv:
        code, sortie = _mutmut("run")
        print(sortie.replace("\r", "\n").strip().splitlines()[-1] if sortie.strip() else "mutmut : aucune sortie")
        if code != 0:                                   # une campagne qui plante n'est JAMAIS un succès (H3)
            print(f"ÉCHEC : mutmut run a terminé avec le code {code}")
            return 2
    tous = statuts()
    compte: dict[str, int] = {}
    for s in tous.values():
        compte[s] = compte.get(s, 0) + 1
    tues, total = compte.get("killed", 0) + compte.get("timeout", 0), len(tous)
    a_classer = sorted(_ligne(m) for m, s in tous.items() if s in ("survived", "no tests", "suspicious"))
    print(f"population {total} : tués {tues} (dont timeout {compte.get('timeout', 0)}), survivants {compte.get('survived', 0)}, "
          f"sans test {compte.get('no tests', 0)}, non vérifiés {compte.get('not checked', 0)}, suspects {compte.get('suspicious', 0)}")
    if ecrire:
        LISTE.write_text(ENTETE + "\n".join(a_classer) + "\n", encoding="utf-8")
        print(f"{len(a_classer)} survivants écrits dans {LISTE.name} : classez chacun avant de valider.")
        return 0
    if total == 0 or tues == 0:
        print("ÉCHEC : aucun mutant tué — campagne vide ou cassée")
        return 3
    if compte.get("not checked", 0):
        print("ÉCHEC : campagne incomplète (mutants non vérifiés)")
        return 4
    classes = {x for x in LISTE.read_text(encoding="utf-8").splitlines() if x and not x.startswith("#")} if LISTE.exists() else set()
    nouveaux = [x for x in a_classer if x not in classes]
    for x in nouveaux:
        print("NON CLASSÉ :", x)
    print(f"{len(a_classer)} survivants (y compris sans test), {len(nouveaux)} non classés")
    return 1 if nouveaux else 0


if __name__ == "__main__":
    sys.exit(main())
