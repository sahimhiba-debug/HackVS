"""Durcissement H3 — la porte de mutation (`scripts/mutation_capacites.py`, exécutée par la CI) ne doit jamais être
VERTE sans avoir muté quoi que ce soit.

Avant : le code de sortie de `mutmut run` était ignoré et seuls les « survived » étaient comptés. Une campagne qui
plante (tests propres en échec, configuration cassée) ne listait aucun survivant → « 0 non classés » → succès, sans un
seul mutant testé. Les mutants « no tests » (code qu'aucun test n'exécute) et « not checked » (campagne interrompue)
passaient aussi en silence. mutmut est simulé ici : on teste la PORTE, pas mutmut."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mutation_capacites.py"


@pytest.fixture
def porte(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("porte_mutation", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    liste = tmp_path / "mutants_survivants.txt"
    liste.write_text(m.ENTETE + "x_f__mutmut_1 | ligne équivalente\n", encoding="utf-8")
    monkeypatch.setattr(m, "LISTE", liste)
    monkeypatch.setattr(m.sys, "argv", ["mutation_capacites.py"])

    def simuler(code_run: int, statuts: dict[str, str]):
        def _mutmut(*args):
            if args[0] == "run":
                return code_run, "⠋ 3/3  🎉 2 🫥 0  ⏰ 0  🤔 0  🙁 1  🔇 0\n"
            if args[0] == "results":
                return 0, "".join(f"    intelligence.capacites.{k}: {v}\n" for k, v in statuts.items())
            if args[0] == "show":
                return 0, "+ ligne équivalente\n"
            raise AssertionError(args)
        monkeypatch.setattr(m, "_mutmut", _mutmut)
        return m.main()
    return simuler


NORMAL = {"x_f__mutmut_1": "survived", "x_f__mutmut_2": "killed", "x_f__mutmut_3": "killed"}


def test_campagne_normale_survivants_classes_verte(porte):
    assert porte(0, NORMAL) == 0


def test_mutmut_en_echec_est_rouge(porte):
    assert porte(1, NORMAL) != 0


def test_campagne_vide_est_rouge(porte):
    assert porte(0, {}) != 0


def test_aucun_mutant_tue_est_rouge(porte):
    assert porte(0, {"x_f__mutmut_1": "survived"}) != 0


def test_campagne_interrompue_est_rouge(porte):
    assert porte(0, NORMAL | {"x_f__mutmut_4": "not checked"}) != 0


def test_code_sans_aucun_test_est_rouge(porte):
    assert porte(0, NORMAL | {"x_f__mutmut_5": "no tests"}) != 0


def test_survivant_non_classe_est_rouge(porte):
    assert porte(0, NORMAL | {"x_g__mutmut_9": "survived"}) != 0
