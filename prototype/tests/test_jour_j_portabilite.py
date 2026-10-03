"""Les double-clics du jour J tournent sur macOS : /bin/bash 3.2, outils BSD, et parfois le Python 3.9 d'Apple (sans
.venv). Ce test refuse ce qui ne marcherait que sous Linux. Le test de bout en bout (test_lanceur_jour_j.py) se relance
sous un vrai bash 3.2 avec JOUR_J_BASH=<chemin> (bash 3.2.57 compilé depuis la source d'Apple, 03.10 : 6/6)."""
import ast
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[2]
SCRIPTS = [RACINE / "1 - Lancer Club Pulse.command", RACINE / "2 - Arrêter et effacer.command",
           RACINE / "3 - Passer en v1.command", RACINE / "prototype" / "scripts" / "jour_j_commun.sh", RACINE / "demo-tunnel.sh"]
BASH4 = {  # construction → depuis quelle version de bash
    r"\bdeclare\s+-[a-zA-Z]*[Aln]": "declare -A / -n / -l (bash 4)", r"\b(mapfile|readarray|coproc)\b": "bash 4",
    r"\$\{[A-Za-z_][A-Za-z0-9_]*(,,?|\^\^?)\}": "${var,,} ${var^^} (bash 4)", r"&>>": "&>> (bash 4)", r"\|&": "|& (bash 4)",
    r"\bwait\s+-n\b": "wait -n (bash 4.3)", r"\blocal\s+-n\b": "local -n (bash 4.3)", r"\[\[\s+-v\b": "[[ -v ]] (bash 4.2)",
    r"\$\{[A-Za-z_][A-Za-z0-9_]*@[QEPAaKku]\}": "${var@Q} (bash 4.4)", r"\bprintf\s+-v\b": "printf -v (bash 3.1 : à éviter)",
    r"\bEPOCH(SECONDS|REALTIME)\b": "bash 5", r";;&|;&": "case ;& (bash 4)",
}
GNU = {  # option propre à GNU → l'équivalent BSD / macOS
    r"\bsed\s+-i(\s|$)(?!'')": "sed -i sans argument (macOS : sed -i '')", r"\bstat\s+-c\b": "stat -c (macOS : stat -f)",
    r"\bdate\s+-d\b": "date -d (macOS : date -j -f)", r"\breadlink\s+-f\b": "readlink -f (absent avant macOS 12.3)",
    r"\bgrep\s+-[a-zA-Z]*P": "grep -P (absent sur macOS)", r"(^|[;&|]\s*|\$\(\s*)timeout\s": "timeout (absent sur macOS)",
    r"\bxargs\s+-r\b": "xargs -r (GNU)", r"\bfind\s+[^|]*-printf\b": "find -printf (GNU)", r"\bsetsid\b": "setsid (absent sur macOS)",
}


def _code(f: Path) -> list[tuple[int, str]]:
    return [(n, ligne) for n, ligne in enumerate(f.read_text(encoding="utf-8").splitlines(), 1) if not ligne.lstrip().startswith("#")]


@pytest.mark.parametrize("f", SCRIPTS, ids=lambda f: f.name)
def test_rien_de_bash_4_ni_de_gnu(f):
    trouves = [(n, raison) for n, ligne in _code(f) for motifs in (BASH4, GNU) for m, raison in motifs.items() if re.search(m, ligne)]
    assert trouves == [], trouves


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck absent (pip install shellcheck-py)")
def test_shellcheck_sans_avertissement():
    r = subprocess.run(["shellcheck", "-s", "bash", "-S", "warning", "-x", *map(str, SCRIPTS)], capture_output=True, text=True,
                       cwd=RACINE)
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("f", ["prototype/app/jour_j.py", "prototype/scripts/jour_j.py", "docs/presentation/deck/lancer.py"])
def test_le_python_du_lanceur_se_lit_en_python_3_9(f):
    """Sans .venv, le lanceur tombe sur le python3 d'Apple (3.9) : ni « match », ni « X | Y » évalué, ni zip(strict=)."""
    source = (RACINE / f).read_text(encoding="utf-8")
    ast.parse(source, feature_version=(3, 9))
    assert "strict=" not in source, f


@pytest.mark.parametrize("ligne", ["declare -A t", "mapfile -t l < f", 'echo "${x,,}"', "cmd &>> log", "a |& b", "wait -n",
                                   "sed -i 's/a/b/' f", "stat -c %s f", "date -d @1", "readlink -f x", "grep -P '\\d'",
                                   "x=$(timeout 5 cmd)", "setsid cmd"])
def test_les_detecteurs_attrapent_vraiment(ligne):
    assert any(re.search(m, ligne) for motifs in (BASH4, GNU) for m in motifs), ligne


def test_sed_i_avec_argument_vide_est_permis():
    assert not any(re.search(m, "sed -i '' 's/a/b/' f") for m in GNU)
