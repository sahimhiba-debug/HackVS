"""Direction des dépendances, vérifiée sur le CODE (arbre syntaxique), pas seulement décrite dans docs/ARCHITECTURE.md.

Couches (de bas en haut) :
  plateforme/                    journal d'événements, affirmations, optimisation — n'importe RIEN du projet
  app/{models,taxonomy,…}        bibliothèques de domaine historiques (sans HTTP)
  intelligence/                  domaine et services Club Pulse (sans HTTP ; ia.py est la seule frontière réseau)
  app/{main,pulse_api,…}         adaptateurs HTTP / MCP : les SEULS à connaître FastAPI
"""
import ast
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
HTTP = {"fastapi", "starlette", "uvicorn"}
ADAPTATEURS_HTTP = {"app.main", "app.pulse_api", "app.stage", "app.cycle_api", "app.decisions_api", "app.observabilite",
                    "app.protections", "app.mcp_serveur"}
BIBLIOTHEQUES_APP = ["models", "taxonomy", "parser_rules", "parser_llm", "matching", "agenda", "securite", "semantique"]


def _imports(fichier: Path) -> set[str]:
    arbre = ast.parse(fichier.read_text(encoding="utf-8"))
    res: set[str] = set()
    for n in ast.walk(arbre):
        if isinstance(n, ast.Import):
            res |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            res.add(n.module)
            res |= {f"{n.module}.{a.name}" for a in n.names}          # « from app import agenda » → app.agenda
    return res


def _viole(imports: set[str], interdits: set[str]) -> list[str]:
    return sorted(i for i in imports if any(i == x or i.startswith(x + ".") for x in interdits))


def test_la_plateforme_n_importe_rien_du_projet():
    for f in (RACINE / "plateforme").glob("*.py"):
        assert not _viole(_imports(f), {"app", "intelligence", "adaptateurs"}), f.name


@pytest.mark.parametrize("f", sorted((RACINE / "intelligence").glob("*.py")), ids=lambda f: f.name)
def test_le_domaine_club_pulse_ignore_http(f):
    imp = _imports(f)
    assert not _viole(imp, HTTP | ADAPTATEURS_HTTP), f.name
    assert not _viole(imp, {"app.store", "app.soiree", "adaptateurs.club.cycle", "adaptateurs.club.reseau"}), f.name  # ancien produit
    if f.name != "ia.py":                                                  # une seule frontière réseau : le fournisseur IA
        assert "httpx" not in imp, f.name


@pytest.mark.parametrize("nom", BIBLIOTHEQUES_APP)
def test_les_bibliotheques_de_domaine_ignorent_http(nom):
    assert not _viole(_imports(RACINE / "app" / f"{nom}.py"), HTTP | ADAPTATEURS_HTTP), nom


def test_un_seul_endroit_choisit_le_fournisseur_ia():
    """Le reste du code ne construit jamais Apertus lui-même : il reçoit une `Intelligence`."""
    constructeurs = []
    for f in list((RACINE / "intelligence").glob("*.py")) + list((RACINE / "app").glob("*.py")):
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "Apertus":
                constructeurs.append(f.name)
    assert constructeurs == ["ia.py"]


def test_l_api_club_pulse_ne_contient_pas_de_regle_metier():
    """L'adaptateur HTTP n'accède au moteur qu'à travers le service (`ClubPulse`) : aucun import du moteur, de la
    détection, du coffre ou de la politique au-delà du spectateur."""
    imp = _imports(RACINE / "app" / "pulse_api.py")
    assert not _viole(imp, {"intelligence.activation", "intelligence.detection", "intelligence.identite", "intelligence.observateur",
                            "plateforme"})
