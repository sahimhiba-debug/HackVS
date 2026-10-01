"""Chaque document de `docs/` est classé (à jour / daté / historique) dans `docs/README.md`, chaque lien de cet index mène
à un fichier, et chaque document historique porte sa bannière : un relecteur ne prend jamais un document de l'ancien
produit pour une description du produit actuel (constat F16)."""
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2] / "docs"
INDEX = (DOCS / "README.md").read_text(encoding="utf-8")


def _section(titre: str) -> str:
    return INDEX.split(f"## {titre}", 1)[1].split("\n## ", 1)[0]


def _liens() -> list[str]:
    return [x for x in re.findall(r"\]\(([^)#]+)\)", INDEX) if x.endswith((".md", ".txt"))]


def _fichier(lien: str) -> Path:
    return DOCS.parent / lien.lstrip("/") if lien.startswith("/") else DOCS / lien


def test_chaque_document_est_classe():
    cites = {_fichier(x).resolve() for x in _liens()}
    tous = {p.resolve() for p in DOCS.rglob("*.md") if "captures" not in p.parts and p != DOCS / "README.md"}
    adr = {p for p in tous if p.parent.name == "ADR"}                    # classées dans ADR/README.md
    assert tous - adr - cites == set(), sorted(str(p.relative_to(DOCS)) for p in tous - adr - cites)


def test_chaque_lien_de_l_index_mene_a_un_fichier():
    assert [x for x in _liens() if not _fichier(x).exists()] == []


def test_chaque_document_historique_porte_sa_banniere():
    historiques = re.findall(r"\]\(([^)]+\.md)\)", _section("Historique"))
    assert len(historiques) >= 19
    for f in historiques:
        debut = (DOCS / f).read_text(encoding="utf-8")[:400]
        assert "HISTORIQUE" in debut, f


def test_le_registre_des_claims_ne_cite_que_des_tests_qui_existent():
    """Un claim classé A renvoie à un test : ce test doit exister (fichier et fonction), sinon la preuve est fictive."""
    txt = (DOCS / "audit" / "CLAIMS.md").read_text(encoding="utf-8")
    tests = Path(__file__).resolve().parent
    fichiers = set(re.findall(r"`(test_\w+\.py)", txt))
    noms = set(re.findall(r"(?:::|`)(test_\w+)(?=`|\s|\))", txt)) - {f[:-3] for f in fichiers}
    source = "".join(p.read_text(encoding="utf-8") for p in tests.glob("test_*.py"))
    assert fichiers and noms
    assert [f for f in fichiers if not (tests / f).exists()] == []
    assert [n for n in noms if f"def {n}(" not in source] == []
