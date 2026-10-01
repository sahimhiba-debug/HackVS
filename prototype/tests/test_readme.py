"""F30 — le README (premier fichier qu'un jury ouvre) ne promet que ce que le code fait : chaque page qu'il cite est
SERVIE dans la configuration du produit, chaque cible `make` existe, chaque lien mène à un fichier, et il ne renvoie
plus vers l'ancien prototype comme si c'était le produit (`/demo/stage` répond 404 sans le drapeau)."""
import re
from pathlib import Path

from app.protections import club_pulse

RACINE = Path(__file__).resolve().parents[2]
README = (RACINE / "README.md").read_text(encoding="utf-8")


def test_chaque_page_citee_est_servie_par_le_produit():
    pages = set(re.findall(r"`(/[a-z][a-z/_-]*)`", README))
    assert pages, "aucune page citée"
    assert {p for p in pages if not club_pulse(p)} == set()
    assert "/demo/stage" not in README


def test_chaque_cible_make_existe():
    cibles = set(re.findall(r"^([a-z][a-z0-9-]*):", (RACINE / "Makefile").read_text(encoding="utf-8"), re.M))
    citees = set(re.findall(r"make ([a-z][a-z0-9-]*)", README))
    assert citees and citees <= cibles, citees - cibles


def test_chaque_lien_mene_a_un_fichier():
    liens = [x for x in re.findall(r"\]\(([^)#]+)\)", README) if not x.startswith("http")]
    assert liens and [x for x in liens if not (RACINE / x).exists()] == []


def test_rien_de_livre_n_est_annonce_comme_non_implemente():
    """Défaut constaté : « NON IMPLÉMENTÉ : levier, composants critiques, … QR juré » alors que tout est livré et testé."""
    for livre in ("levier", "composants critiques", "QR juré", "Pulse", "parité"):
        lignes = [x for x in README.splitlines() if "NON IMPLÉMENTÉ" in x and livre in x]
        assert not lignes, (livre, lignes)
