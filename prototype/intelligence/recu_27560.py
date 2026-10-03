"""REÇUS ALIGNÉS sur ISO/IEC TS 27560:2023 (P3 n°2) — « aligné », jamais « certifié ».

Le reçu de consentement existe déjà (`capacites.recus`, chemin surveillé par les campagnes de mutation : on ne le
touche pas). Ce module le PROJETTE, à la lecture, vers la structure d'un enregistrement de consentement ISO/IEC TS
27560 et l'exporte en JSON-LD avec le vocabulaire DPV (Data Privacy Vocabulary, W3C DPVCG).

Limites, dites telles quelles :
- la table de correspondance est proposée par l'équipe ; les termes DPV ont été choisis sans accès à la spécification
  pendant la nuit du 3 octobre (site inaccessible depuis la session) — **à relire** par quelqu'un qui la connaît ;
- la conformité testée ici est celle de NOTRE table : chaque champ marqué obligatoire est présent et non vide, le
  statut suit l'état du reçu, aucune identité ne sort (la personne concernée est un pseudonyme)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

ALIGNEMENT = "aligné sur ISO/IEC TS 27560:2023 — pas une certification"
CONTEXTE = {"dpv": "https://w3id.org/dpv#", "dct": "http://purl.org/dc/terms/", "xsd": "http://www.w3.org/2001/XMLSchema#"}
RESPONSABLE = "Club des Affaires (monde de démonstration)"

# champ 27560 (libellé de l'équipe) → champ de notre reçu → terme DPV ; obligatoire au sens de NOTRE test
CHAMPS: list[dict[str, Any]] = [
    {"champ_27560": "identifiant de l'enregistrement", "recu": "reference", "terme_dpv": "dpv:hasIdentifier", "obligatoire": True},
    {"champ_27560": "personne concernée", "recu": "(pseudonyme du membre)", "terme_dpv": "dpv:hasDataSubject", "obligatoire": True},
    {"champ_27560": "responsable du traitement", "recu": "(le Club)", "terme_dpv": "dpv:hasDataController", "obligatoire": True},
    {"champ_27560": "finalité", "recu": "titre + finalite", "terme_dpv": "dpv:hasPurpose", "obligatoire": True},
    {"champ_27560": "données personnelles", "recu": "piece + offre (la capacité déclarée)", "terme_dpv": "dpv:hasPersonalData", "obligatoire": True},
    {"champ_27560": "base légale", "recu": "(consentement)", "terme_dpv": "dpv:hasLegalBasis", "obligatoire": True},
    {"champ_27560": "statut du consentement", "recu": "etat", "terme_dpv": "dpv:hasConsentStatus", "obligatoire": True},
    {"champ_27560": "date de l'accord", "recu": "donne_le", "terme_dpv": "dpv:isIndicatedAtTime", "obligatoire": True},
    {"champ_27560": "méthode d'expression", "recu": "(geste « Oui » sur le téléphone)", "terme_dpv": "dpv:isIndicatedBy", "obligatoire": True},
    {"champ_27560": "durée de validité", "recu": "jusqu_au", "terme_dpv": "dpv:hasExpiryTime", "obligatoire": False},
    {"champ_27560": "destinataires", "recu": "partage", "terme_dpv": "dpv:hasRecipient", "obligatoire": False},
    {"champ_27560": "version de la notice", "recu": "version", "terme_dpv": "dpv:hasNotice", "obligatoire": False},
    {"champ_27560": "date du retrait", "recu": "retire_le", "terme_dpv": "dpv:hasWithdrawalTime", "obligatoire": False},
]
OBLIGATOIRES = [c["terme_dpv"] for c in CHAMPS if c["obligatoire"]]


def _statut(recu: dict) -> str:
    if recu.get("retire_le"):
        return "dpv:ConsentWithdrawn"
    if recu.get("etat") == "valable":
        return "dpv:ConsentGiven"
    return "dpv:ConsentExpired"                       # échu, ou devenu caduc (pièce ou portée changée) : plus valable


def enregistrement(recu: dict, sujet: str) -> dict:
    rec: dict[str, Any] = {
        "@type": "dpv:ConsentRecord",
        "dpv:hasIdentifier": recu["reference"],
        "dpv:hasDataSubject": sujet,
        "dpv:hasDataController": RESPONSABLE,
        "dpv:hasPurpose": {"dct:title": recu["titre"], "dct:identifier": recu["finalite"]},
        "dpv:hasPersonalData": {"dct:description": f"{recu['piece']} — {recu['offre']}"},
        "dpv:hasLegalBasis": "dpv:Consent",
        "dpv:hasConsentStatus": _statut(recu),
        "dpv:isIndicatedAtTime": recu["donne_le"],
        "dpv:isIndicatedBy": "geste « Oui » du membre sur son téléphone",
        "dpv:hasExpiryTime": recu.get("jusqu_au"),
        "dpv:hasRecipient": recu.get("partage"),
        "dpv:hasNotice": {"dct:hasVersion": recu.get("version")},
    }
    if recu.get("retire_le"):
        rec["dpv:hasWithdrawalTime"] = recu["retire_le"]
    return rec


def conforme(rec: dict) -> list[str]:
    """Les écarts à NOTRE table (vide = conforme) : champ obligatoire absent ou vide, retrait sans date."""
    ecarts = [f"{t} manquant" for t in OBLIGATOIRES if rec.get(t) in (None, "", {}, [])]
    if rec.get("@type") != "dpv:ConsentRecord":
        ecarts.append("@type n'est pas dpv:ConsentRecord")
    if rec.get("dpv:hasConsentStatus") == "dpv:ConsentWithdrawn" and not rec.get("dpv:hasWithdrawalTime"):
        ecarts.append("dpv:hasWithdrawalTime manquant pour un retrait")
    return ecarts


def export(c: "ClubPulse", pid: str) -> dict:
    sujet = c.coffre.pseudonyme(pid)
    return {"@context": CONTEXTE, "alignement": ALIGNEMENT,
            "@graph": [enregistrement(r, sujet) for r in c.capacites.recus(pid)]}
