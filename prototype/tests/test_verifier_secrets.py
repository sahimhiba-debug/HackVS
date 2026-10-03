"""La porte « aucun secret » : elle trouve les vraies affectations, et ne crie pas sur une valeur vide, une phrase ou une
expansion shell (faux positifs qui la rendaient rouge sur .env.example, purge.sh, demo-tunnel.sh)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("vs", Path(__file__).resolve().parents[1] / "scripts" / "verifier_secrets.py")
vs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vs)


V = "Zq8v" + "R2mPk4Lw9xYb"          # assemblé : ce fichier, lui aussi scanné, ne contient aucune affectation littérale


def test_vraies_affectations_trouvees():
    assert vs.analyser("HACKVS_SECRET=" + V + "\n")
    assert vs.analyser('APERTUS_API_KEY: "' + V + '"\n')
    assert vs.analyser("      HACKVS_SECRET: " + V + "\n")                    # YAML sans guillemets
    assert vs.analyser("export HACKVS_CONSOLE_JETON='" + V + "'\n")
    assert vs.analyser("sk-ant-" + "a" * 30)


def test_faux_positifs_ecartes():
    assert vs.analyser("APERTUS_API_KEY=" + "\n" + "APERTUS_MODEL=swiss-ai/Apertus-v1.5-70B\n") == []      # valeur vide
    assert vs.analyser("# Refuse de démarrer sans HACKVS_CONSOLE_JETON : derrière un tunnel, toutes\n") == []   # prose
    assert vs.analyser(': "${HACKVS_CONSOLE_JETON:?HACKVS_CONSOLE_JETON vide}"\n') == []          # expansion shell
    assert vs.analyser("HACKVS_SECRET=un-secret-de-test-assez-long\n") == []                       # valeur de test


def test_le_depot_est_propre():
    assert vs.main() == 0
