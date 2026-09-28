"""Plan d'action : rien ne se passe sans décision humaine enregistrée, et rien de réel ne part en mode démo.

décision humaine (approuver / rejeter, par qui, pourquoi) → aperçu à blanc (dry run : ce qui SERAIT fait, à qui)
→ exécution (en démo : SIMULÉE, étiquetée comme telle) → vérification (le résultat correspond à l'aperçu)
→ dossier de preuves d'action (empreintes de l'exécution, de l'aperçu, de l'approbation).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .execution import ExecutionDecision, Journal, empreinte, maintenant


class DecisionHumaine(BaseModel):
    verdict: Literal["APPROUVER", "REJETER"]
    par: str = Field(min_length=1, max_length=80)
    motif: str = Field("", max_length=500)
    le: str = ""


class ErreurAction(ValueError):
    pass


def decider(journal: Journal, run_id: str, d: DecisionHumaine) -> ExecutionDecision:
    run = journal.lire(run_id)
    if run.decision_humaine:
        raise ErreurAction("une décision humaine est déjà enregistrée pour cette exécution (elle ne se réécrit pas)")
    if d.verdict == "APPROUVER" and (run.mediation or {}).get("decision") != "PROPOSER_A_L_HUMAIN":
        raise ErreurAction(f"impossible d'approuver : la plateforme a conclu « {(run.mediation or {}).get('decision') or run.compilation.get('decision')} »")
    run.decision_humaine = d.model_copy(update={"le": maintenant()}).model_dump()
    journal.enregistrer(run)
    return run


def apercu(run: ExecutionDecision, noms: dict[str, str]) -> dict:
    """Ce qui SERAIT envoyé : une invitation par participant, avec ses tours. Aucun envoi."""
    par_personne: dict[str, list] = {}
    for t, a, b in (run.retenue or {}).get("rencontres", []):
        par_personne.setdefault(a, []).append((t, b))
        par_personne.setdefault(b, []).append((t, a))
    invitations = [{"destinataire": p, "message": f"Bonjour {noms.get(p, p).split(' ')[0]}, voici vos rencontres proposées : "
                    + " ; ".join(f"tour {t} avec {noms.get(q, q)}" for t, q in sorted(v))}
                   for p, v in sorted(par_personne.items())]
    return {"action": "inviter_aux_rencontres", "destinataires": len(invitations), "invitations": invitations,
            "irreversible": True, "canal": "aucun (mode démo)"}


def executer(journal: Journal, run_id: str, noms: dict[str, str], mode: str = "demo") -> dict:
    run = journal.lire(run_id)
    d = run.decision_humaine
    if not d or d["verdict"] != "APPROUVER":
        raise ErreurAction("aucune approbation humaine : l'action est refusée")
    ap = apercu(run, noms)
    if mode != "reel":
        effectue = [{"destinataire": i["destinataire"], "etat": "SIMULE"} for i in ap["invitations"]]
    else:  # pas de canal d'envoi réel implémenté : on ne fait pas semblant
        raise ErreurAction("aucun canal d'envoi réel n'est configuré")
    verification = {"attendus": ap["destinataires"], "traites": len(effectue),
                    "conforme": sorted(e["destinataire"] for e in effectue) == sorted(i["destinataire"] for i in ap["invitations"])}
    return {"run_id": run_id, "statut": "SIMULE", "apercu_empreinte": empreinte(ap)[:16],
            "approbation": d, "approbation_empreinte": empreinte(d)[:16], "resultat_empreinte": run.resultat_empreinte[:16],
            "effectue": effectue, "verification": verification, "le": maintenant(),
            "avertissement": "mode démo : aucune invitation n'a été envoyée ; les destinataires sont fictifs"}


def noms_depuis(journal: Journal, run: ExecutionDecision) -> dict[str, str]:
    if not run.instantane_empreinte:
        return {}
    return {k: v.get("nom", k) for k, v in journal.instantane(run.instantane_empreinte)["participants"].items()}

