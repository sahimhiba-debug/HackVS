"""ANNÉE 1 · LOT 12 — Passe de cohérence avec docs/design/DESIGN_SYSTEM.md (ADR 0010) : les pages de l'année 1 n'écrivent
AUCUNE couleur hors des jetons du Design System (ou de tokens.css) et s'appuient sur les feuilles communes. Les écrans
de la DÉMO ne sont pas concernés : leurs couleurs propres (projecteur, régie) sont voulues et ne changent pas sans la
barrière."""
import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
PAGES_ANNEE_1 = ("espace.html", "secretariat.html", "borne.html", "attestation.html", "compte.html", "desinscription.html")
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b")


def _jetons() -> set[str]:
    textes = (RACINE.parent / "docs/design/DESIGN_SYSTEM.md").read_text(encoding="utf-8") + \
        (RACINE / "web/pulse/tokens.css").read_text(encoding="utf-8")
    return {h.upper() for h in HEX.findall(textes)}


@pytest.mark.parametrize("page", PAGES_ANNEE_1)
def test_aucune_couleur_hors_jetons(page):
    t = (RACINE / "web/pulse" / page).read_text(encoding="utf-8")
    hors = sorted({h.upper() for h in HEX.findall(t)} - _jetons())
    assert not hors, f"{page} : couleurs hors du Design System {hors} — utiliser var(--…)"


@pytest.mark.parametrize("page", PAGES_ANNEE_1)
def test_feuilles_communes_du_design_system(page):
    t = (RACINE / "web/pulse" / page).read_text(encoding="utf-8")
    assert '/static/pulse/pulse.css' in t                      # pulse.css importe tokens.css (jetons figés)
    assert "font-family" not in t                              # la typographie vient des feuilles communes


def test_contre_preuve_une_couleur_inventee_est_vue():
    assert "#123456" not in _jetons() and HEX.findall("color: #123456") == ["#123456"]
