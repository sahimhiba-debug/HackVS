"""L'image Docker démarre-t-elle ? Sans démon Docker (CI, poste), on reconstitue EXACTEMENT les fichiers que le
Dockerfile copie, puis on démarre l'application depuis cette copie avec l'environnement de l'image : un dossier oublié
dans le Dockerfile fait échouer ce test (défaut réel : `intelligence/` et `prompts/` n'étaient pas copiés — l'image
plantait au démarrage)."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def _copies() -> list[tuple[str, str]]:
    lignes = (RACINE / "Dockerfile").read_text(encoding="utf-8").splitlines()
    return [(m.group(1), m.group(2)) for ligne in lignes if (m := re.match(r"^COPY\s+(\S+)\s+(\S+)\s*$", ligne))]


def test_l_application_demarre_depuis_les_seuls_fichiers_de_l_image(tmp_path):
    for src, _ in _copies():
        s, d = RACINE / src, tmp_path / src
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(s, d)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("HACKVS_", "PYTHONPATH"))}
    env |= {"HACKVS_MODE": "demo", "HACKVS_DB": str(tmp_path / "fil.db"), "HACKVS_CYCLE_DB": ":memory:",
            "HACKVS_DECISIONS_DB": ":memory:", "HACKVS_SEMANTIQUE": "0", "PYTHONDONTWRITEBYTECODE": "1"}
    script = ("from fastapi.testclient import TestClient\nimport app.main as m\nc = TestClient(m.app)\n"
              "for chemin in ('/app', '/console', '/api/pulse/etat', '/demo/stage', '/'):\n"
              "    r = c.get(chemin)\n    assert r.status_code == 200, (chemin, r.status_code)\n"
              "assert c.post('/api/pulse/demo/aller/10', headers={'X-Pulse-Console': '1'}).status_code == 200\nprint('ok')\n")
    p = subprocess.run([sys.executable, "-c", script], cwd=tmp_path / "prototype", env=env, capture_output=True, text=True, timeout=300)
    assert p.returncode == 0 and "ok" in p.stdout, p.stderr[-2000:]
