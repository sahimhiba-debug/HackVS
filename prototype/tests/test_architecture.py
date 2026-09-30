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
ADAPTATEURS_HTTP = {"app.main", "app.pulse_api", "app.essai_api", "app.capacites_api", "app.stage", "app.cycle_api", "app.decisions_api", "app.observabilite",
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
    for nom in ("pulse_api.py", "essai_api.py", "capacites_api.py"):
        imp = _imports(RACINE / "app" / nom)
        assert not _viole(imp, {"intelligence.activation", "intelligence.detection", "intelligence.identite", "intelligence.observateur",
                                "intelligence.essai", "intelligence.capacites", "plateforme"}), nom


# ---------------------------------------------------------------------- recomposition : NI → passerelle → AE → mémoire
NI = {"intelligence.observateur", "intelligence.detection", "intelligence.explication", "intelligence.modele"}
AE = {"intelligence.essai"}
MEMOIRE = {"intelligence.memoire_club"}


def _imports_domaine(nom: str) -> set[str]:
    """Imports d'un module de `intelligence/`, relatifs résolus (« from .essai import Banc » → intelligence.essai)."""
    res: set[str] = set()
    for n in ast.walk(ast.parse((RACINE / "intelligence" / f"{nom}.py").read_text(encoding="utf-8"))):
        if isinstance(n, ast.ImportFrom) and n.level == 1:
            res |= {f"intelligence.{n.module}"} if n.module else {f"intelligence.{a.name}" for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            res.add(n.module)
    return res


@pytest.mark.parametrize("nom", ["observateur", "detection", "explication", "modele"])
def test_la_network_intelligence_ne_connait_pas_le_banc_d_essai(nom):
    """Détecter n'est pas agir : la détection lit la mémoire sous forme de DONNÉES (listes), jamais le banc."""
    assert not (_imports_domaine(nom) & (AE | MEMOIRE | {"intelligence.passerelle", "intelligence.vues_essai"})), nom


def test_le_banc_d_essai_ne_connait_ni_la_detection_ni_la_memoire():
    assert not (_imports_domaine("essai") & (NI | MEMOIRE | {"intelligence.passerelle"}))


def test_la_memoire_ne_lit_que_le_banc():
    assert _imports_domaine("memoire_club") & (NI | {"intelligence.passerelle"}) == set()


def test_seule_la_passerelle_relie_les_deux_dans_le_domaine():
    domaine = ["observateur", "detection", "explication", "modele", "essai", "memoire_club", "passerelle"]
    relient = [n for n in domaine if _imports_domaine(n) & NI and _imports_domaine(n) & AE]
    assert relient == ["passerelle"]


def test_un_seul_moteur_d_activation():
    """L'ancien moteur (activation.py), ses vues et sa mémoire de « motifs » ont été retirés après portage de leurs
    propriétés (tests/test_essai_invariants.py, eval/benchmark_pulse.py) : ils ne reviennent pas par la bande."""
    for f in ("activation.py", "apprentissage.py", "vues.py"):
        assert not (RACINE / "intelligence" / f).exists(), f


# ---------------------------------------------------------------------- registre des capacités
def test_le_registre_des_capacites_n_a_qu_un_compositeur_et_aucune_ia():
    """Le registre compose avec le BANC (aucun second moteur) ; il ne connaît ni l'IA, ni la détection d'opportunités
    (leur « composition » sur profils ne doit pas revenir comme second compositeur)."""
    imp = _imports_domaine("capacites")
    assert "intelligence.essai" in imp
    assert not (imp & (NI | MEMOIRE | {"intelligence.ia", "intelligence.passerelle", "intelligence.club_pulse"}))
    assert "intelligence.capacites" not in _imports_domaine("ia")            # l'IA ne voit ni ne modifie les patrons
    assert "intelligence.capacites" not in _imports_domaine("essai")         # le banc ignore le registre qui le lit
