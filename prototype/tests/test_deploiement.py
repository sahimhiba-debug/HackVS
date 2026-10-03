"""Fichiers de DÉPLOIEMENT (Foire 2026 · §4.7) : aucun secret dans le dépôt, PUBLIC_BASE_URL partout, scripts valides,
une santé à vérifier. Le déploiement lui-même se fait depuis la session locale d'Hiba (docs/DEPLOIEMENT.md)."""
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

RACINE = Path(__file__).resolve().parents[2]
SECRETS = ("HACKVS_SECRET", "HACKVS_CONSOLE_JETON", "APERTUS_API_KEY", "DOMAINE", "PUBLIC_BASE_URL", "DOMAINE_VISITE", "PUBLIC_VISITE_URL")


def test_env_example_ne_contient_aucune_valeur_secrete():
    lignes = dict(l.split("=", 1) for l in (RACINE / ".env.example").read_text().splitlines() if l and not l.startswith("#"))
    for cle in SECRETS:
        assert cle in lignes and lignes[cle] == "", cle


def test_env_n_est_jamais_versionne():
    r = subprocess.run(["git", "check-ignore", ".env"], cwd=RACINE, capture_output=True, text=True)
    assert r.returncode == 0


def test_scripts_valides_et_sans_url_en_dur():
    for f in ("deploy.sh", "purge.sh"):
        assert subprocess.run(["bash", "-n", str(RACINE / f)]).returncode == 0, f
        texte = (RACINE / f).read_text()
        assert "PUBLIC_BASE_URL" in texte and not re.search(r"https?://(?!\$)", texte.replace("https://${", "")), f


def test_compose_une_instance_volume_et_sante_caddy_https():
    c = (RACINE / "docker-compose.prod.yml").read_text()
    assert "env_file: .env" in c and "/sante" in c and "pulse:/srv/prototype/var" in c and "replicas" not in c
    assert "{$DOMAINE}" in (RACINE / "Caddyfile").read_text()


def test_route_de_sante():
    r = TestClient(app).get("/sante")
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_script_de_charge_coherent_sur_un_petit_echantillon():
    """Le script de charge lui-même (3 téléphones, serveur local) : cohérent, y compris quand l'écran dit « < 3 »."""
    import sys
    r = subprocess.run([sys.executable, "scripts/charge_salle.py", "--local", "--n", "6"], cwd=RACINE / "prototype",
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]


def test_lanceur_tunnel_exige_jeton_et_https():
    """docs/DEMO_TUNNEL.md : derrière un tunnel tout arrive de 127.0.0.1 — le lanceur refuse sans jeton de console."""
    import os
    import subprocess
    script = RACINE / "demo-tunnel.sh"
    base = {k: v for k, v in os.environ.items() if k not in ("PUBLIC_BASE_URL", "HACKVS_CONSOLE_JETON")} | {"VERIFIER_SEULEMENT": "1"}

    def lancer(**env):
        return subprocess.run(["bash", str(script)], env=base | env, capture_output=True, text=True, timeout=20)
    assert lancer().returncode != 0
    assert lancer(PUBLIC_BASE_URL="https://mac.exemple.ts.net").returncode != 0
    assert lancer(PUBLIC_BASE_URL="http://mac.exemple.ts.net", HACKVS_CONSOLE_JETON="x" * 24).returncode != 0
    assert lancer(PUBLIC_BASE_URL="https://mac.exemple.ts.net", HACKVS_CONSOLE_JETON="court").returncode != 0
    ok = lancer(PUBLIC_BASE_URL="https://mac.exemple.ts.net", HACKVS_CONSOLE_JETON="x" * 24)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "--host 127.0.0.1" in script.read_text() and "caffeinate" in script.read_text()
