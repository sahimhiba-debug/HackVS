"""Serveur MCP du Club : un assistant IA (Claude Desktop, Claude Code, tout client MCP) agit POUR un membre.

Principe de sécurité : ce serveur est un CLIENT MINCE de l'API HTTP du Fil du Club.
- Il ne détient aucune donnée et ne réimplémente aucune règle : consentement, filtres durs, preuves exactes,
  anonymat, rôles et machine d'états restent appliqués par le serveur, au même endroit que pour l'interface web.
- Les actions qui engagent le membre (publier un besoin, solliciter, proposer son aide, répondre) exigent une
  confirmation HUMAINE par « elicitation » MCP (formulaire affiché par le client, compatible avec les protocoles
  2025 et 2026-07-28). Un refus n'envoie rien. Un client sans elicitation est refusé, sauf si l'opérateur choisit
  HACKVS_MCP_CONFIRMATION=client (l'approbation d'outil du client fait alors foi, et c'est indiqué dans la réponse).
- Les messages de mise en relation sont, par défaut, le brouillon DÉTERMINISTE du serveur (fondé sur les preuves) :
  l'assistant n'invente pas ce que l'autre membre propose.
- Démo : l'identité est choisie par HACKVS_MCP_MEMBRE (personnage fictif). En mode réel, l'API refuse (501/503) :
  il faudrait une authentification par membre (OAuth MCP), non implémentée.

Lancement (stdio) : HACKVS_API_URL=http://localhost:8000 HACKVS_MCP_MEMBRE=p00 python -m app.mcp_serveur
"""
import os
from typing import Annotated, Literal, Optional

import httpx
from mcp.server.elicitation import AcceptedElicitation, ElicitationResult
from mcp.server.mcpserver import MCPServer, Resolve
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver.resolve import Elicit
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

LECTURE = ToolAnnotations(read_only_hint=True, open_world_hint=False)
ECRITURE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)

INSTRUCTIONS = (
    "Outils du Club des Affaires (démo, données fictives). Chaque membre proposé est justifié par une preuve citée "
    "mot pour mot de son profil : citez-la telle quelle, n'inventez jamais une compétence. Si le moteur s'abstient, "
    "dites-le et proposez de reformuler ou de publier le besoin dans la Bourse. Ne publiez ni ne sollicitez personne "
    "sans l'accord explicite du membre."
)


class Confirmation(BaseModel):
    confirmer: bool = Field(description="Confirmer l'action")


class ErreurClub(ToolError):
    """Refus lisible par l'assistant (règle du Club, refus du membre) — jamais masqué."""


def _http() -> httpx.Client:
    return httpx.Client(base_url=os.environ.get("HACKVS_API_URL", "http://localhost:8000"), timeout=30)


def creer_serveur(http: Optional[httpx.Client] = None, membre: Optional[str] = None) -> MCPServer:
    """`http` injectable (tests : TestClient FastAPI, qui est un httpx.Client)."""
    client = http or _http()
    qui = membre or os.environ.get("HACKVS_MCP_MEMBRE", "p00")
    srv = MCPServer("fil-du-club", title="Le Fil du Club", instructions=INSTRUCTIONS, version="0.4")

    def api(methode: str, chemin: str, **kw):
        r = client.request(methode, chemin, headers={"X-Membre": qui}, **kw)
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise ErreurClub(f"Refusé par le serveur du Club ({r.status_code}) : {detail}")
        return r.json()

    def resume(b: dict, res: dict) -> dict:
        return {
            "criteres": [{"type": c["type"], "libelle": c["libelle"], "obligatoire": c["obligatoire"]} for c in b["criteres"]],
            "exclusions": [e["libelle"] for e in b.get("exclusions", [])],
            "suggestions": [{"membre_id": s["profil"]["id"], "nom": s["profil"]["nom"], "entreprise": s["profil"]["entreprise"],
                             "niveau": s["niveau"],
                             "preuves": [{"critere": p["critere"], "champ": p["champ"], "extrait": p["extrait"], "nature": p["nature"]}
                                         for p in s["preuves"]],
                             "a_verifier": s.get("a_verifier", [])} for s in res["suggestions"]],
            "abstention": res["abstention"],
            "message": res.get("message", ""),
            "ecartes": [{"raison": e["raison"], "nombre": e["nombre"]} for e in res.get("ecartes", [])],
            "profils_examines": res.get("nb_profils_examines", 0),
        }

    def analyser(texte: str) -> dict:
        b = api("POST", "/api/analyser", json={"texte": texte})["besoin"]
        if b["ambiguites"]:
            raise ErreurClub("Besoin ambigu, précisez : " + " ; ".join(
                f"« {a['terme']} » = " + " ou ".join(o["libelle"] for o in a["options"]) for a in b["ambiguites"]))
        return b

    @srv.tool(annotations=LECTURE)
    def qui_suis_je() -> dict:
        """Le membre pour qui l'assistant agit (profil fictif en démo) et l'état du service."""
        etat = api("GET", "/api/etat")
        return {"membre": api("GET", "/api/moi"), "mode": etat["mode"], "donnees_fictives": etat["donnees_fictives"]}

    @srv.tool(annotations=LECTURE)
    def chercher_membres(besoin: str) -> dict:
        """Trouve les membres du Club qui peuvent répondre à un besoin décrit en langage naturel.

        Retourne les critères compris, les membres proposés avec leurs PREUVES (extraits exacts de leur profil)
        ou une abstention motivée. Rien n'est publié ni envoyé.
        """
        b = analyser(besoin)
        return resume(b, api("POST", "/api/rechercher", json={"besoin": b}))

    @srv.tool(annotations=LECTURE)
    def expliquer_correspondance(besoin: str, membre_id: str) -> dict:
        """Pourquoi ce membre est-il proposé (ou pas) pour ce besoin ? Critère par critère, avec les preuves citées.

        Si la raison relève du consentement ou de la disponibilité de la personne, elle n'est pas divulguée.
        """
        b = analyser(besoin)
        e = api("POST", "/api/expliquer", json={"besoin": b, "membre_id": membre_id})
        return {"membre": e["membre"]["nom"], "verdict": e["verdict"], "resume": e["resume"], "opaque": e["opaque"],
                "criteres": [{"critere": x["critere"], "statut": x["statut"], "detail": x["detail"],
                              "preuve": (x["preuve"] or {}).get("extrait")} for x in e["lignes"]]}

    @srv.tool(annotations=LECTURE)
    def planifier_soiree(tours: int = 3, donnees: Literal["club", "synthetique"] = "club", membre_id: Optional[str] = None) -> dict:
        """Plan de rencontres optimisé d'une soirée du Club (programme linéaire, optimum prouvé ou non indiqué).

        Avec `membre_id`, ne renvoie que le programme de ce membre. Chaque rencontre cite l'aide prouvée.
        """
        r = api("GET", "/api/soiree/plan", params={"tours": tours, "donnees": donnees})
        rdv = [m for m in r["rencontres"] if not membre_id or membre_id in (m["a"]["id"], m["b"]["id"])]
        return {"participants": r["participants"], "tours": r["tours"], "optimum_prouve": r["solveur"].get("optimal_prouve"),
                "comparaison": r["comparaison"], "sans_rencontre": len(r["sans_rencontre"]),
                "rencontres": [{"tour": m["tour"], "table": m["table"], "entre": f'{m["a"]["nom"]} et {m["b"]["nom"]}',
                                "pourquoi": [x["preuve"] for x in (m["b_aide_a"], m["a_aide_b"]) if x]} for m in rdv[:40]],
                "donnees_fictives": r["donnees_fictives"]}

    @srv.tool(annotations=LECTURE)
    def bourse() -> list[dict]:
        """Besoins publiés par d'autres membres auxquels le membre courant peut répondre (avec la raison)."""
        return [{"besoin_id": x["besoin"]["id"], "texte": x["besoin"]["besoin"]["texte"],
                 "auteur": x["besoin"]["auteur"]["nom"], "anonyme": x["besoin"]["anonyme"],
                 "preuves": [p["extrait"] for p in (x["correspondance"] or {}).get("preuves", [])],
                 "relation": (x["relation"] or {}).get("libelle_etat")} for x in api("GET", "/api/bourse")]

    @srv.tool(annotations=LECTURE)
    def mes_relations() -> list[dict]:
        """Mises en relation du membre (demandes et offres), avec l'action attendue de sa part."""
        return [{"relation_id": r["id"], "etat": r["libelle_etat"], "mon_role": r["mon_role"],
                 "je_dois_repondre": r["je_suis_destinataire"] and r["etat"] == "proposee",
                 "autre": (r["autre"] or {}).get("nom"), "besoin": r["besoin"]["besoin"]["texte"],
                 "besoin_modifie_depuis": r["besoin_modifie_depuis"]} for r in api("GET", "/api/relations")]

    exiger = os.environ.get("HACKVS_MCP_CONFIRMATION", "exigee") != "client"

    def demander(message: str):
        # Résolveur : exécuté AVANT le corps de l'outil ; le corps (effet de bord) ne tourne qu'après la réponse.
        return Elicit(message, Confirmation) if exiger else Confirmation(confirmer=True)

    def verifier(ok: ElicitationResult) -> str:
        if not isinstance(ok, AcceptedElicitation) or not ok.data.confirmer:
            raise ErreurClub("Action annulée par le membre : rien n'a été envoyé.")
        return "confirmée par le membre (elicitation MCP)" if exiger else "approbation d'outil du client (HACKVS_MCP_CONFIRMATION=client)"

    def criteres(b: dict) -> str:
        return ", ".join(c["libelle"] for c in b["criteres"]) or "aucun critère reconnu"

    def conf_publication(besoin: str, anonyme: bool = False):
        b = analyser(besoin)  # un besoin ambigu échoue ici, avant toute question au membre
        return demander(f"Publier dans la Bourse du Club{' (anonyme)' if anonyme else ''} ?\n« {besoin} »\nCritères : {criteres(b)}")

    def texte_relation(besoin_id: str, membre_id: Optional[str], message: Optional[str]) -> str:
        params = {"besoin_id": besoin_id} | ({"cible_id": membre_id} if membre_id else {})
        return message or api("GET", "/api/relations/brouillon", params=params)["message"]

    def conf_relation(besoin_id: str, membre_id: Optional[str] = None, message: Optional[str] = None):
        return demander(f"Envoyer ce message ?\n\n{texte_relation(besoin_id, membre_id, message)}")

    def conf_reponse(relation_id: str, action: str):
        return demander(f"{action.capitalize()} la mise en relation {relation_id} ?"
                        + (" Vos coordonnées seront partagées." if action == "accepter" else ""))

    @srv.tool(annotations=ECRITURE)
    def publier_besoin(besoin: str, ok: Annotated[ElicitationResult[Confirmation], Resolve(conf_publication)],
                       anonyme: bool = False) -> dict:
        """Publie un besoin dans la Bourse du Club (visible des membres qui peuvent y répondre). Confirmation humaine requise."""
        mode = verifier(ok)
        b = analyser(besoin)
        cree = api("POST", "/api/besoins", json={"besoin": b, "publier": True, "anonyme": anonyme})
        return {"besoin_id": cree["id"], "statut": cree["statut"], "criteres": criteres(b), "confirmation": mode}

    @srv.tool(annotations=ECRITURE)
    def mettre_en_relation(besoin_id: str, ok: Annotated[ElicitationResult[Confirmation], Resolve(conf_relation)],
                           membre_id: Optional[str] = None, message: Optional[str] = None) -> dict:
        """Sollicite un membre pour SON besoin (membre_id requis) ou propose son aide pour le besoin d'un autre.

        Le serveur revérifie que la correspondance est prouvée. Sans `message`, le brouillon fondé sur les preuves
        est utilisé. Confirmation humaine requise.
        """
        mode = verifier(ok)
        texte = texte_relation(besoin_id, membre_id, message)
        r = api("POST", "/api/relations", json={"besoin_id": besoin_id, "cible_id": membre_id, "message": texte})
        return {"relation_id": r["id"], "etat": r["libelle_etat"], "message": texte, "confirmation": mode}

    @srv.tool(annotations=ECRITURE)
    def repondre(relation_id: str, action: Literal["accepter", "decliner", "retirer", "annuler"],
                 ok: Annotated[ElicitationResult[Confirmation], Resolve(conf_reponse)]) -> dict:
        """Répond à une mise en relation. Accepter partage les coordonnées des deux côtés. Confirmation humaine requise."""
        mode = verifier(ok)
        r = api("POST", f"/api/relations/{relation_id}/{action}", json={})
        return {"relation_id": r["id"], "etat": r["libelle_etat"], "confirmation": mode}

    return srv


def main() -> None:
    creer_serveur().run("stdio")


if __name__ == "__main__":
    main()
