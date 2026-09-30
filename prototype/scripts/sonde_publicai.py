"""SONDE de l'API Public AI (compatible OpenAI) : ce que le fournisseur fait VRAIMENT, mesuré, jamais supposé.

    python scripts/sonde_publicai.py                  # écrit docs/audit/probe_publicai.md
    python scripts/sonde_publicai.py --sortie X.md

Configuration (environnement uniquement, jamais dans le code ni le dépôt) :
    APERTUS_API_KEY     la clé (lue, jamais écrite nulle part : ni rapport, ni trace)
    APERTUS_BASE_URL    défaut https://api.publicai.co/v1
    APERTUS_MODEL       facultatif ; sinon choisi dans GET /models : un modèle Apertus « instruct », jamais un modèle
                        dont l'identifiant annonce un raisonnement (« think », « reason »)

Sans clé, ou si l'hôte est injoignable : chaque capacité est UNKNOWN, et le rapport dit pourquoi.
Avec clé, quatre essais, chacun consigné avec sa requête (sans en-tête d'autorisation) et sa réponse BRUTE :
  1. JSON simple      : consigne « réponds en JSON » dans le prompt, sans contrainte côté serveur ;
  2. json_schema      : response_format {type: json_schema, strict}, schéma que le PROMPT NE DÉCRIT PAS — une sortie
                        conforme ne peut venir que de la contrainte ;
  3. tools            : un outil déclaré, tool_choice « required » ;
  4. non-thinking     : aucun champ de raisonnement ni balise <think> dans les réponses.
Verdicts : SUPPORTED · IGNORED (accepté, non appliqué) · REJECTED (HTTP 4xx) · ERROR · UNKNOWN."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit" / "probe_publicai.md"
BASE_DEFAUT = "https://api.publicai.co/v1"
RAISONNEMENT = re.compile(r"think|reason", re.I)

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["canton", "code_postal_min"],
          "properties": {"canton": {"type": "string", "enum": ["VS", "VD", "GE"]},
                         "code_postal_min": {"type": "integer"}}}
OUTIL = {"type": "function", "function": {
    "name": "enregistrer_offre", "description": "Enregistre une offre d'aide d'un membre du Club.",
    "parameters": {"type": "object", "additionalProperties": False, "required": ["nature", "places"],
                   "properties": {"nature": {"type": "string", "enum": ["objet", "lieu", "competence"]},
                                  "places": {"type": "integer"}}}}}


@dataclass
class Essai:
    nom: str
    verdict: str = "UNKNOWN"
    raison: str = ""
    requete: Optional[dict] = None
    statut_http: Optional[int] = None
    brut: str = ""
    duree_ms: Optional[int] = None
    notes: list[str] = field(default_factory=list)


def _json(texte: str) -> Any:
    t = texte.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    return json.loads(t)


def _conforme(v: Any) -> bool:
    return (isinstance(v, dict) and set(v) == {"canton", "code_postal_min"} and v["canton"] in ("VS", "VD", "GE")
            and isinstance(v["code_postal_min"], int) and not isinstance(v["code_postal_min"], bool))


def _raisonnement(corps: dict) -> list[str]:
    """Traces d'un mode « thinking » dans une réponse : champ dédié ou balise dans le texte."""
    vus = []
    for c in corps.get("choices") or []:
        m = c.get("message") or {}
        for k in ("reasoning_content", "reasoning", "thinking"):
            if m.get(k):
                vus.append(f"champ « {k} » présent")
        if "<think>" in (m.get("content") or ""):
            vus.append("balise <think> dans le texte")
    return vus


class Sonde:
    def __init__(self, env: Optional[dict] = None, http: Any = None, horloge: Callable[[], float] = time.monotonic):
        e = os.environ if env is None else env
        self.cle = e.get("APERTUS_API_KEY") or ""
        self.base = (e.get("APERTUS_BASE_URL") or BASE_DEFAUT).rstrip("/")
        self.modele = e.get("APERTUS_MODEL") or ""
        self.http, self.horloge = http, horloge
        self.modeles: list[str] = []
        self.essais: list[Essai] = []
        self.global_: str = ""

    # ---------------------------------------------------------------- transport
    def _client(self):
        if self.http is None:
            import httpx
            self.http = httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0))
        return self.http

    def _appel(self, e: Essai, methode: str, chemin: str, corps: Optional[dict] = None) -> Optional[dict]:
        e.requete = {"methode": methode, "url": self.base + chemin, **({"corps": corps} if corps else {})}
        t = self.horloge()
        try:
            r = self._client().request(methode, self.base + chemin, json=corps,
                                       headers={"Authorization": f"Bearer {self.cle}", "Content-Type": "application/json"})
        except Exception as x:                                   # réseau, proxy, délai : on le dit
            e.verdict, e.raison = "UNKNOWN", f"injoignable : {type(x).__name__}: {str(x)[:200]}"
            return None
        e.duree_ms = int((self.horloge() - t) * 1000)
        e.statut_http, e.brut = r.status_code, r.text
        if r.status_code >= 400:
            e.verdict = "REJECTED" if r.status_code < 500 and r.status_code not in (401, 403, 429) else "ERROR"
            e.raison = f"HTTP {r.status_code}"
            return None
        try:
            return r.json()
        except ValueError:
            e.verdict, e.raison = "ERROR", "réponse non JSON"
            return None

    def _chat(self, e: Essai, corps: dict) -> Optional[dict]:
        rep = self._appel(e, "POST", "/chat/completions", {"model": self.modele, "temperature": 0, "max_tokens": 300, **corps})
        if rep is not None:
            e.notes += _raisonnement(rep)
        return rep

    # ---------------------------------------------------------------- essais
    def lancer(self) -> "Sonde":
        noms = ["modèles", "JSON simple (prompt)", "response_format json_schema (strict)", "tools (tool_choice required)",
                "non-thinking"]
        if not self.cle:
            self.global_ = "UNKNOWN — aucune clé : APERTUS_API_KEY absente de l'environnement. Rien n'a été appelé."
            self.essais = [Essai(n, raison="aucune clé") for n in noms]
            return self
        m = Essai(noms[0])
        rep = self._appel(m, "GET", "/models")
        self.essais.append(m)
        if rep is None:
            self.global_ = f"UNKNOWN — {m.raison or m.verdict} sur GET /models : aucun autre essai n'est significatif."
            self.essais += [Essai(n, raison="GET /models a échoué") for n in noms[1:]]
            return self
        self.modeles = sorted(str(x.get("id")) for x in rep.get("data") or [] if isinstance(x, dict))
        m.verdict, m.raison = "SUPPORTED", f"{len(self.modeles)} modèles listés"
        if not self.modele:
            candidats = [x for x in self.modeles if "apertus" in x.lower() and "instruct" in x.lower() and not RAISONNEMENT.search(x)]
            self.modele = candidats[-1] if candidats else ""
        if not self.modele:
            self.global_ = "UNKNOWN — aucun modèle Apertus « instruct » sans raisonnement dans la liste ; fixer APERTUS_MODEL."
            self.essais += [Essai(n, raison="aucun modèle choisi") for n in noms[1:]]
            return self
        if RAISONNEMENT.search(self.modele):
            m.notes.append(f"ATTENTION : le modèle imposé « {self.modele} » annonce un raisonnement")
        self.essais += [self._json_simple(noms[1]), self._schema(noms[2]), self._outils(noms[3])]
        self.essais.append(self._non_thinking(noms[4]))
        self.global_ = f"exécutée contre {self.base} avec le modèle « {self.modele} »"
        return self

    def _texte(self, rep: dict) -> str:
        return str(((rep.get("choices") or [{}])[0].get("message") or {}).get("content") or "")

    def _json_simple(self, nom: str) -> Essai:
        e = Essai(nom)
        rep = self._chat(e, {"messages": [
            {"role": "system", "content": "Réponds UNIQUEMENT par un objet JSON, sans texte autour."},
            {"role": "user", "content": 'Donne {"ville": <ville principale du Valais>, "langues": [<langues officielles>]}.'}]})
        if rep is None:
            return e
        try:
            v = _json(self._texte(rep))
            ok = isinstance(v, dict) and {"ville", "langues"} <= set(v)
            e.verdict, e.raison = ("SUPPORTED", "JSON valide avec les clés demandées") if ok else ("IGNORED", "JSON valide, clés absentes")
        except ValueError:
            e.verdict, e.raison = "IGNORED", "texte non JSON"
        return e

    def _schema(self, nom: str) -> Essai:
        e = Essai(nom)
        rep = self._chat(e, {"messages": [{"role": "user", "content": "Dans quel canton se trouve Sion ?"}],   # le format n'est PAS décrit
                             "response_format": {"type": "json_schema", "json_schema": {"name": "reponse", "schema": SCHEMA, "strict": True}}})
        if rep is None:
            return e
        try:
            ok = _conforme(_json(self._texte(rep)))
        except ValueError:
            ok = False
        e.verdict, e.raison = ("SUPPORTED", "sortie conforme à un schéma absent du prompt") if ok else \
            ("IGNORED", "paramètre accepté, sortie NON conforme au schéma")
        return e

    def _outils(self, nom: str) -> Essai:
        e = Essai(nom)
        rep = self._chat(e, {"messages": [{"role": "user", "content": "Je peux prêter mon minibus de 14 places vendredi."}],
                             "tools": [OUTIL], "tool_choice": "required"})
        if rep is None:
            return e
        appels = ((rep.get("choices") or [{}])[0].get("message") or {}).get("tool_calls") or []
        if not appels:
            e.verdict, e.raison = "IGNORED", "paramètre accepté, aucun tool_call dans la réponse"
            return e
        try:
            f = appels[0]["function"]
            args = json.loads(f["arguments"]) if isinstance(f["arguments"], str) else f["arguments"]
            ok = f["name"] == "enregistrer_offre" and isinstance(args, dict) and {"nature", "places"} <= set(args)
        except (KeyError, TypeError, ValueError):
            ok = False
        e.verdict, e.raison = ("SUPPORTED", "tool_call valide") if ok else ("IGNORED", "tool_call présent mais arguments invalides")
        return e

    def _non_thinking(self, nom: str) -> Essai:
        e = Essai(nom)
        faits = [n for x in self.essais for n in x.notes if "champ" in n or "balise" in n]
        appels = [x for x in self.essais[1:] if x.statut_http and x.statut_http < 400]
        if not appels:
            e.raison = "aucune réponse de chat à examiner"
        elif faits:
            e.verdict, e.raison = "IGNORED", "traces de raisonnement : " + "; ".join(sorted(set(faits)))
        else:
            e.verdict, e.raison = "SUPPORTED", f"aucune trace de raisonnement dans {len(appels)} réponses"
        return e

    # ---------------------------------------------------------------- rapport
    def rapport(self) -> str:
        quand = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        l = ["# Sonde Public AI — ce que l'API fait vraiment",
             "", "> Écrit par `prototype/scripts/sonde_publicai.py` : réponses BRUTES, aucune retouche. La clé n'est jamais écrite ;",
             "> les requêtes sont consignées sans en-tête d'autorisation. Un verdict ne vaut que pour la date, l'hôte et le modèle ci-dessous.",
             "", f"- Date : {quand}", f"- Hôte : `{self.base}`", f"- Clé fournie : {'oui' if self.cle else 'NON'}",
             f"- Modèle : `{self.modele or '—'}`", f"- **État : {self.global_}**", "",
             "| Essai | Verdict | Raison | HTTP | Durée |", "|---|---|---|---|---|"]
        for e in self.essais:
            l.append(f"| {e.nom} | **{e.verdict}** | {e.raison.replace('|', '/')} | {e.statut_http or '—'} | "
                     f"{f'{e.duree_ms} ms' if e.duree_ms is not None else '—'} |")
        if self.modeles:
            l += ["", "## Modèles listés (GET /models)", "", *[f"- `{m}`" for m in self.modeles]]
        for e in self.essais:
            if e.requete is None and not e.brut:
                continue
            l += ["", f"## {e.nom}", ""] + [f"- {n}" for n in e.notes]
            l += ["", "Requête :", "", "```json", json.dumps(e.requete, ensure_ascii=False, indent=2), "```",
                  "", f"Réponse brute (HTTP {e.statut_http or '—'}) :", "", "```", e.brut or e.raison, "```"]
        texte = "\n".join(l) + "\n"
        if self.cle and self.cle in texte:                       # garde-fou : jamais la clé dans le dépôt
            raise RuntimeError("la clé apparaîtrait dans le rapport : écriture refusée")
        return texte


def main(argv: list[str]) -> int:
    sortie = Path(argv[argv.index("--sortie") + 1]) if "--sortie" in argv else SORTIE
    s = Sonde().lancer()
    sortie.write_text(s.rapport(), encoding="utf-8")
    print(f"{s.global_}\n" + "\n".join(f"  {e.nom} : {e.verdict} ({e.raison})" for e in s.essais) + f"\n→ {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
