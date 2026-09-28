"""Crée un jeton d'accès au serveur MCP distant pour UN membre, avec ses portées.

Le jeton est affiché UNE fois dans le terminal de l'opérateur ; seule son empreinte SHA-256 est enregistrée
(var/mcp_jetons.json, hors Git). Ne jamais le coller dans un chat, un ticket ou un dépôt.

Usage : python scripts/creer_jeton_mcp.py --membre p00 [--portees lecture,ecriture] [--fichier var/mcp_jetons.json]
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.mcp_serveur import PORTEES, empreinte  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--membre", required=True)
    ap.add_argument("--portees", default="lecture")
    ap.add_argument("--fichier", default=str(Path(__file__).resolve().parent.parent / "var" / "mcp_jetons.json"))
    a = ap.parse_args()
    portees = [p for p in a.portees.split(",") if p]
    if not portees or any(p not in PORTEES for p in portees):
        raise SystemExit(f"Portées possibles : {', '.join(PORTEES)}")
    f = Path(a.fichier)
    entrees = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    jeton = secrets.token_urlsafe(32)
    entrees.append({"sha256": empreinte(jeton), "membre": a.membre, "portees": portees})
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(entrees, indent=1), encoding="utf-8")
    print(jeton)
