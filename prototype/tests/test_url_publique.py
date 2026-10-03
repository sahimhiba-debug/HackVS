"""PUBLIC_BASE_URL (Foire 2026 · §4.6) : tout lien et tout QR produit par le serveur part de PUBLIC_BASE_URL quand elle
est définie — jamais d'URL en dur. Compatibilité : HACKVS_URL_PUBLIQUE ; à défaut, l'adresse de la requête."""
import base64
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

CONSOLE = {"X-Pulse-Console": "1"}
client = TestClient(app)
PROTO = Path(__file__).resolve().parents[1]


def _qr_texte(data_uri: str) -> str:
    return base64.b64decode(data_uri.split(",", 1)[1]).decode()


def test_le_passe_decouverte_et_le_qr_jure_utilisent_public_base_url(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://pulse.exemple.ch/")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    p = client.post("/api/pulse/console/decouverte", headers=CONSOLE, json={"origine": "stand"}).json()
    assert p["url"].startswith("https://pulse.exemple.ch/decouverte#passe=")
    j = client.post("/api/pulse/console/jure", headers=CONSOLE, json={"persona": "s14", "minutes": 15}).json()
    assert j["url"].startswith("https://pulse.exemple.ch/app?jure=")
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)


def test_aucune_url_publique_en_dur_dans_le_serveur():
    """Aucun « https://… » de domaine propre au produit dans le code serveur (les URL d'API de fournisseurs IA exceptées)."""
    permis = ("api.openai.com", "api.anthropic.com", "apertus", "cscs", "example", "exemple", "localhost", "127.0.0.1",
              "w3.org", "schema", "json-schema", "github.com", "swiss-ai", "publicai", "fastapi", "googleapis")
    for f in list((PROTO / "app").glob("*.py")) + list((PROTO / "intelligence").glob("*.py")):
        for url in re.findall(r"https?://[\w.\-]+", f.read_text(encoding="utf-8")):
            assert any(p in url for p in permis), (f.name, url)
