"""QUARANTAINE de `competition/` (produit d'avant le pivot) : chaque fichier Markdown commence par la bannière
« OBSOLÈTE — ne pas présenter », et chaque dossier qui contient autre chose que du Markdown (vidéo, captures, JSON,
sous-titres) porte un `OBSOLETE.md`. Un fichier ajouté ou régénéré sans elle fait échouer la suite."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from quarantaine_competition import BANNIERE, COMP  # noqa: E402


def test_chaque_markdown_porte_la_banniere():
    fichiers = [p for p in COMP.rglob("*.md") if p.name != "OBSOLETE.md"]
    assert len(fichiers) > 50
    sans = [str(p.relative_to(COMP)) for p in fichiers if not p.read_text(encoding="utf-8").startswith(BANNIERE)]
    assert not sans, sans


def test_chaque_dossier_non_markdown_est_signale():
    dossiers = {p.parent for p in COMP.rglob("*") if p.is_file() and p.suffix != ".md"}
    assert dossiers and all((d / "OBSOLETE.md").exists() for d in dossiers), sorted(map(str, dossiers))
