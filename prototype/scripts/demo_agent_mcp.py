"""Démonstration « agent externe » : un vrai client MCP (SDK officiel) pilote le Club comme le ferait un assistant IA.

Ce script JOUE le rôle de l'agent (enchaînement d'appels écrit à l'avance, aucun LLM) : il montre ce que l'agent
reçoit et ce qu'il ne peut pas faire. Les confirmations humaines (elicitation) sont simulées et affichées.
Sortie : transcription Markdown (docs/captures/agent_mcp.md). Données fictives.

Usage (depuis prototype/) : python scripts/demo_agent_mcp.py [--sortie ../docs/captures/agent_mcp.md]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("HACKVS_DB", ":memory:")
os.environ.setdefault("HACKVS_SEMANTIQUE", "0")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from mcp import Client  # noqa: E402
from mcp import types as t  # noqa: E402

import logging  # noqa: E402

from app.main import app  # noqa: E402

logging.getLogger("httpx").setLevel(logging.WARNING)
from app.mcp_serveur import creer_serveur  # noqa: E402

http = TestClient(app)
lignes: list[str] = []


def dire(qui: str, texte: str) -> None:
    lignes.append(f"**{qui}** — {texte}\n")


def bloc(obj) -> None:
    lignes.append("```json\n" + json.dumps(obj, ensure_ascii=False, indent=1)[:1800] + "\n```\n")


def membre_humain(reponse: bool, **champs):
    async def cb(ctx, params: t.ElicitRequestParams):
        dire("Formulaire de confirmation montré au membre", "« " + params.message.replace("\n", " ") + " »")
        dire("Membre", "confirme" if reponse else "refuse")
        return t.ElicitResult(action="accept", content={"confirmer": True, **champs}) if reponse else t.ElicitResult(action="decline")
    return cb


async def appel(membre: str, outil: str, args: dict, elicitation=None):
    async with Client(creer_serveur(http, membre), elicitation_callback=elicitation) as c:
        dire(f"Agent → outil `{outil}`", "`" + json.dumps(args, ensure_ascii=False) + "`")
        r = await c.call_tool(outil, args)
        texte = "".join(x.text for x in r.content if isinstance(x, t.TextContent))
        if r.is_error:
            dire("Serveur du Club", f"refus : `{texte.split(': ', 1)[-1]}`")
            return None
        res = r.structured_content or json.loads(texte)
        res = res["result"] if isinstance(res, dict) and set(res) == {"result"} else res
        bloc(res)
        return res


async def scenario() -> None:
    http.post("/api/demo/reinitialiser")
    lignes.append("# Un agent IA externe utilise le Club via MCP\n")
    lignes.append("> Transcription générée par `scripts/demo_agent_mcp.py` : l'agent est **scripté** (aucun LLM), les "
                  "confirmations humaines sont simulées. Serveur MCP et API réels ; données fictives.\n")

    lignes.append("## 1. Un besoin hors du catalogue : l'agent n'invente rien\n")
    dire("Utilisatrice (Sophie, via son assistant)", "« J'ai besoin de quelqu'un du Club qui m'aide à comprendre la "
         "comptabilité carbone, en français, disponible pour 30 minutes la semaine prochaine. »")
    r = await appel("p00", "chercher_membres", {"besoin": "Je cherche quelqu'un pour m'aider à comprendre la comptabilité "
                                                          "carbone, en français."})
    if r and r["abstention"]:
        dire("Agent", "Le Club n'a personne qui déclare cette compétence : je ne vous propose donc personne plutôt qu'un "
             "contact au hasard. Voulez-vous publier le besoin dans la Bourse, pour qu'un membre qui la propose le voie ?")
    lignes.append("## 2. Un besoin couvert : preuves, explication, confirmation\n")
    besoin = ("On lance nos jus d'abricot en Suisse alémanique. Je cherche un transporteur frigorifique qui livre Zurich, "
              "idéalement germanophone, et pas un concurrent.")
    dire("Utilisatrice", f"« {besoin} »")
    r = await appel("p00", "chercher_membres", {"besoin": besoin})
    choisi = r["suggestions"][0]
    dire("Agent", f"{choisi['nom']} ({choisi['entreprise']}) correspond ; preuve citée de son profil : "
         f"« {choisi['preuves'][0]['extrait']} ». Voici le détail critère par critère :")
    await appel("p00", "expliquer_correspondance", {"besoin": besoin, "membre_id": choisi["membre_id"]})
    dire("Utilisatrice", "« Et Stefan, de Viège ? Pourquoi pas lui ? »")
    await appel("p00", "expliquer_correspondance", {"besoin": besoin, "membre_id": "p04"})
    dire("Agent", "Le Club ne communique pas la raison : elle touche aux choix de cette personne.")

    lignes.append("## 3. Publier et solliciter : rien ne part sans le membre\n")
    await appel("p00", "publier_besoin", {"besoin": besoin}, membre_humain(False))
    pub = await appel("p00", "publier_besoin", {"besoin": besoin}, membre_humain(True))
    dire("Agent (tentative de solliciter un membre qui ne correspond pas)", "")
    await appel("p00", "mettre_en_relation", {"besoin_id": pub["besoin_id"], "membre_id": "p15", "message": "Bonjour"},
                membre_humain(True))
    rel = await appel("p00", "mettre_en_relation", {"besoin_id": pub["besoin_id"], "membre_id": choisi["membre_id"]},
                      membre_humain(True, message="Bonjour Julien, pouvons-nous en parler 20 minutes jeudi ?"))

    lignes.append("## 4. L'autre membre répond avec SON assistant\n")
    await appel(choisi["membre_id"], "mes_relations", {})
    dire("Agent de Sophie (tentative : accepter à la place de Julien)", "")
    await appel("p00", "repondre", {"relation_id": rel["relation_id"], "action": "accepter"}, membre_humain(True))
    dire("Agent de Julien", "Sophie vous sollicite pour un transport frigorifique vers Zurich. Acceptez-vous ?")
    await appel(choisi["membre_id"], "repondre", {"relation_id": rel["relation_id"], "action": "accepter"}, membre_humain(True))
    await appel("p00", "repondre", {"relation_id": rel["relation_id"], "action": "planifier", "date_rencontre": "2026-10-08"},
                membre_humain(True))

    lignes.append("## 5. Préparer la prochaine soirée du Club\n")
    await appel(choisi["membre_id"], "planifier_soiree", {"tours": 3, "membre_id": choisi["membre_id"]})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default=str(Path(__file__).resolve().parents[2] / "docs" / "captures" / "agent_mcp.md"))
    a = ap.parse_args()
    asyncio.run(scenario())
    Path(a.sortie).write_text("\n".join(lignes), encoding="utf-8")
    print(f"Transcription : {a.sortie} ({len(lignes)} blocs)")
