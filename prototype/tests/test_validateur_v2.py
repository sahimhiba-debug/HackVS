"""Audit IMPORTANT 7 : la porte des affirmations lit aussi ce qui sera projeté et dit (deck v2, script v2)."""
import importlib.util
import shutil
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vc", RACINE / "prototype" / "scripts" / "validate_competition_claims.py")
vc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vc)


def test_le_depot_passe():
    assert vc.verifier_v2() == []


def test_formulation_interdite_et_nombre_sans_source_attrapes(tmp_path, monkeypatch):
    for rel in ("docs/audit/club-pulse-pivot/PREUVES.md", "docs/roadmap/ROADMAP.md", "docs/roadmap/etat.yaml",
                "docs/presentation/deck/data/gel.json", "docs/presentation/05_FILM_INTEGRATION.md"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(RACINE / rel, tmp_path / rel)
    (tmp_path / "docs/presentation/03b_SCRIPT_A_DIRE_v2.md").write_text("Apertus, servi par Public AI. Nous avons 987654 membres.\n",
                                                                        encoding="utf-8")
    monkeypatch.setattr(vc, "RACINE", tmp_path)
    echecs = " ".join(vc.verifier_v2())
    assert "Public AI" in echecs and "987654" in echecs
