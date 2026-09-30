"""Un chiffre PUBLIÉ ne diverge jamais du code : le benchmark du banc d'essai est recalculé ici et comparé À L'OCTET
aux fichiers commités (même sérialisation que `python -m eval.benchmark_pulse`). Défaut trouvé à l'audit (2026-09-30) :
`resultats_benchmark_pulse.*` annonçait 763 écrans quand le code en produisait 767 — la CI (job reproductibilité)
était rouge depuis 7 poussées. La CI rejoue en plus TOUS les benchmarks du sprint (`scripts/reproduire_sprint.py`)."""
import json
from pathlib import Path

from eval.benchmark_pulse import executer, rapport

ICI = Path(__file__).resolve().parent.parent / "eval"


def test_le_benchmark_publie_est_celui_que_produit_le_code():
    res = executer()
    assert json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n" == (ICI / "resultats_benchmark_pulse.json").read_text(encoding="utf-8")
    assert rapport(res) == (ICI / "resultats_benchmark_pulse.md").read_text(encoding="utf-8")
