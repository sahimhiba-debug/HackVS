"""QUARANTAINE du dossier `competition/` : il décrit le produit d'AVANT le pivot (« intelligence relationnelle »), pas le
registre des capacités. Chaque fichier Markdown porte la bannière en tête ; les générateurs (`generer_competition.py`,
`validate_competition_claims.py`) la réécrivent eux-mêmes, et `tests/test_quarantaine_competition.py` refuse un fichier
qui l'aurait perdue. La réécriture du pitch est faite par l'équipe, pas ici.

    python scripts/quarantaine_competition.py      # pose la bannière là où elle manque (idempotent)
"""
from __future__ import annotations

import sys
from pathlib import Path

COMP = Path(__file__).resolve().parents[2] / "competition"
BANNIERE = ("> ⛔ **OBSOLÈTE — produit d'avant le pivot, ne pas présenter.** Ce dossier décrit l'ancien produit "
            "(« intelligence relationnelle »), pas le registre des capacités. La réécriture du pitch est en cours "
            "(équipe) ; voir `TODO-DEMO.md`.\n\n")
NOTE_DOSSIER = ("# OBSOLÈTE — ne pas présenter\n\n" + BANNIERE +
                "Les fichiers de ce dossier qui ne sont pas du Markdown (vidéo, captures, sous-titres, JSON) sont "
                "concernés de la même façon.\n")


def avec_banniere(texte: str) -> str:
    return texte if texte.startswith(BANNIERE) else BANNIERE + texte


def appliquer() -> list[Path]:
    touches = []
    for p in sorted(COMP.rglob("*.md")):
        if p.name == "OBSOLETE.md":
            continue
        t = p.read_text(encoding="utf-8")
        if not t.startswith(BANNIERE):
            p.write_text(avec_banniere(t), encoding="utf-8")
            touches.append(p)
    for d in sorted({COMP, *(x for x in COMP.rglob("*") if x.is_dir())}):
        if any(f.is_file() and f.suffix != ".md" for f in d.iterdir()):
            (d / "OBSOLETE.md").write_text(NOTE_DOSSIER, encoding="utf-8")
    return touches


if __name__ == "__main__":
    n = appliquer()
    print(f"bannière posée sur {len(n)} fichier(s) ; dossiers non-Markdown signalés par OBSOLETE.md")
    sys.exit(0)
