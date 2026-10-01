"""Les tests ne touchent jamais les bases de var/ : tout en mémoire."""
import os

os.environ.setdefault("HACKVS_DB", ":memory:")
os.environ.setdefault("HACKVS_DECISIONS_DB", ":memory:")
os.environ.setdefault("HACKVS_CYCLE_DB", ":memory:")
# L'ancien prototype n'est plus servi par défaut (tests/test_service_ancien.py) ; ses propres tests, conservés tant que son
# code l'est, l'activent explicitement — y compris pour les serveurs lancés par les tests de bout en bout.
os.environ.setdefault("HACKVS_ANCIEN_PROTOTYPE", "1")
# HERMÉTIQUES : une clé de modèle présente sur la machine (APERTUS_*, ANTHROPIC_API_KEY) ne doit ni changer le résultat
# des tests ni partir vers un vrai fournisseur. Un test qui veut un modèle le configure lui-même (faux serveur, maquette).
# Les mesures réelles passent par `make sonde-ia`, `make banc-ia`, `make latence-ia` — jamais par la suite de tests.
for _k in [k for k in os.environ if k.startswith("APERTUS_")] + ["ANTHROPIC_API_KEY", "HACKVS_LLM"]:
    os.environ.pop(_k, None)


# Tests de bout en bout : sur échec, chaque page ouverte est capturée (écran + HTML) avant la fermeture du navigateur.
from tests.capture_e2e import installer as _installer_capture  # noqa: E402

_installer_capture()
