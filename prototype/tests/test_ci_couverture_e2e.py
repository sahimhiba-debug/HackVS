"""Le parcours démontré doit être GARDÉ par la CI : chaque fichier de bout en bout (vrai navigateur) est exécuté dans
une étape où un navigateur absent est un ÉCHEC (HACKVS_E2E_OBLIGATOIRE), en CI comme dans `make e2e`.
Défaut trouvé à l'audit (2026-09-30) : `test_e2e_action.py` — le parcours de la démonstration — n'était exécuté
nulle part en CI (sauté faute de Chromium dans le job qualité, absent du job reproductibilité)."""
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def _obligatoires(texte: str) -> set[str]:
    """Fichiers E2E cités sur une ligne de commande qui porte HACKVS_E2E_OBLIGATOIRE (même ligne ou bloc `env` juste avant)."""
    res: set[str] = set()
    lignes = texte.splitlines()
    for i, l in enumerate(lignes):
        if "test_e2e_" in l and any("HACKVS_E2E_OBLIGATOIRE" in x for x in lignes[max(0, i - 4):i + 1]):
            res |= set(re.findall(r"test_e2e_\w+\.py", l))
    return res


def test_chaque_test_de_bout_en_bout_est_obligatoire_en_ci_et_dans_make():
    fichiers = {p.name for p in (RACINE / "prototype" / "tests").glob("test_e2e_*.py")}
    assert fichiers and "test_e2e_action.py" in fichiers
    ci = _obligatoires((RACINE / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    make = _obligatoires((RACINE / "Makefile").read_text(encoding="utf-8"))
    assert fichiers <= ci, f"absents de la CI : {sorted(fichiers - ci)}"
    assert fichiers <= make, f"absents de make e2e : {sorted(fichiers - make)}"
