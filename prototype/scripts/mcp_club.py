"""Lanceur du serveur MCP du Club, utilisable depuis n'importe quel dossier (Claude Desktop, Claude Code…).

  claude mcp add fil-du-club -e HACKVS_API_URL=http://localhost:8000 -e HACKVS_MCP_MEMBRE=p00 \\
      -- python /chemin/vers/prototype/scripts/mcp_club.py
L'API (uvicorn app.main:app) doit tourner. Options : --http --port 8790 (jeton porteur obligatoire).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.mcp_serveur import main  # noqa: E402

if __name__ == "__main__":
    main()
