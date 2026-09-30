"""MÉMOIRE du Club : ce que les essais terminés permettent de dire — et rien de plus.

Une entrée de mémoire est une PROJECTION du journal du banc d'essai (aucun stockage de plus, aucune copie qui
divergerait). Elle dit :
    « Dans ce contexte (question, capacités), cette contribution a été reçue ; la personne aidée a déclaré ce résultat,
      avec ces limites ; la personne qui a contribué l'a confirmé — ou contesté. »
Elle ne dit JAMAIS « cette personne est experte, disponible, fiable ». Chaque partie garde sa nature :
- `constat`      : le porteur a constaté la contribution (une déclaration datée) ;
- `declaration`  : l'observation du porteur (texte, qualification, limites) — DÉCLARÉE, versionnée (révisions) ;
- `confirmation` : l'avis de chaque contributeur sur la DERNIÈRE révision — CONFIRMÉE ou CONTESTÉE ;
- `niveau`       : qui peut la réutiliser (le plus restrictif des droits de CHACUN des participants).
Une correction crée une nouvelle révision ; une contestation reste visible ; rien n'est effacé.
"""
from __future__ import annotations

from .essai import Banc

POSITIFS = {"positif", "mitige"}


def souvenirs(banc: Banc) -> list[dict]:
    res = []
    for eid in banc.essais():
        obs = banc._evs(eid, "OBSERVATION")
        if not obs:
            continue
        p, porteur = banc.protocole(eid), banc.porteur(eid)
        dern = obs[-1]
        recus = banc._evs(eid, "CONTRIBUTION")
        contributeurs = sorted({x.donnees["contributeur"] for x in recus if x.donnees.get("contributeur")})
        avis = {e.acteurs[0]: e.donnees for e in banc._evs(eid, "AVIS") if e.donnees["revision"] == dern.donnees["revision"]}
        contestes = [m for m, a in avis.items() if a["avis"] == "conteste"]
        confirmes = [m for m, a in avis.items() if a["avis"] == "confirme"]
        statut = ("contestee" if contestes else "confirmee" if contributeurs and set(contributeurs) <= set(confirmes) else "declaree")
        droits = banc.droits(eid)
        res.append({
            "essai": eid, "question": p.question, "porteur": porteur, "contributeurs": contributeurs,
            "concepts": list((p.origine or {}).get("concepts", [])), "origine": p.origine,
            "qualification": dern.donnees["qualification"], "limites": dern.donnees["limites"], "texte": dern.donnees["texte"],
            "le": dern.le.isoformat(), "revision": dern.donnees["revision"], "revisions": len(obs), "tardive": dern.donnees.get("tardive", False),
            "statut": statut, "contestations": [{"par": m, "raison": avis[m]["raison"]} for m in contestes],
            "constats": [{"par": x.acteurs[0], "etape": x.donnees["etape"], "le": x.le.isoformat()} for x in recus],
            "niveau": banc.niveau_partage(eid), "mentions": {m: d["mention"] for m, d in droits.items()},
        })
    return res


def _sans_attribution_refusee(s: dict) -> dict:
    """Mention « anonyme » : l'apprentissage reste réutilisable, mais la contribution n'est ATTRIBUÉE à personne hors de
    l'essai — ni comme preuve (« cette personne a déjà aidé »), ni pour la faire passer devant dans une découverte."""
    return s | {"contributeurs": [c for c in s["contributeurs"] if s.get("mentions", {}).get(c, "nom") == "nom"]}


def accessibles(tous: list[dict], pour: str) -> list[dict]:
    """Ce qu'on peut utiliser AU PROFIT de `pour` : la mémoire partagée avec le Club par TOUS ses participants, ou celle
    dont `pour` est lui-même participant. Jamais au-delà (une nouvelle audience n'hérite d'aucun ancien accord)."""
    return [s if pour == s["porteur"] or pour in s["contributeurs"] else _sans_attribution_refusee(s)
            for s in tous if s["niveau"] == "club" or pour == s["porteur"] or pour in s["contributeurs"]]


def reutilisables_par_le_club(tous: list[dict]) -> list[dict]:
    """Ce que la détection peut lire pour TOUT membre : partagé « club » par chacun, confirmé, positif ou mitigé ;
    attribué seulement à qui l'accepte."""
    return [_sans_attribution_refusee(s) for s in tous
            if s["niveau"] == "club" and s["statut"] == "confirmee" and s["qualification"] in POSITIFS]
