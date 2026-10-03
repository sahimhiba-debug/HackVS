"""PARTENARIATS (Foire 2026, B) — les quatre étapes d'un partenariat et la CLÔTURE d'un reçu.

Un partenariat, dans le registre des capacités, naît d'une DEMANDE (la pièce qui manque), devient un ACCORD quand un
membre répond oui (son reçu de consentement), un ESSAI quand la capacité qu'il complète est réellement possible
(ACTIVE) ou que son jour est passé avec l'accord encore valable, et un RÉSULTAT quand le demandeur — le Club, auteur des
capacités — le CLÔTURE avec un résultat déclaré. Un accord retiré sort du chemin (« retiré »), sans jamais dire qui.

La machine à états est EXPLICITE (`TRANSITIONS`) : toute autre transition est refusée. La clôture est un fait du journal
(CLOTURE) ; une ligne nominative (qui, quel résultat) n'est montrée au Club que si LES DEUX parties l'ont permis
(VISIBILITE : le membre ET le Club) — sinon, des agrégats seulement (intelligence/suivi.py)."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from .erreurs import Conflit, Introuvable, Invalide

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

ETAPES = ("demande", "accord", "essai", "resultat")
RESULTATS = ("signé", "test sans suite", "contact établi", "abandonné")
NOTE_MAX = 140
# (étape, fait) → étape suivante. Rien d'autre n'est possible.
TRANSITIONS: dict[tuple[str, str], str] = {
    ("demande", "oui"): "accord",
    ("accord", "capacite_possible"): "essai",
    ("accord", "jour_passe"): "essai",
    ("accord", "cloture"): "resultat",          # le demandeur peut clôturer dès l'accord (« abandonné », « contact établi »)
    ("essai", "cloture"): "resultat",
    ("accord", "retrait"): "retire",
    ("essai", "retrait"): "retire",
}
CLUB = "club"                                   # le demandeur des capacités du registre (la commission des événements)


def suivante(etape: str, fait: str) -> str:
    try:
        return TRANSITIONS[(etape, fait)]
    except KeyError:
        raise Conflit(f"transition impossible : « {fait} » depuis l'étape « {etape} »") from None


def _clotures(c: "ClubPulse") -> dict[str, dict]:
    return {e.donnees["reference"]: {"resultat": e.donnees["resultat"], "note": e.donnees.get("note"), "le": e.le.isoformat()}
            for e in c.journal.evenements("CLOTURE")}


def _visibles(c: "ClubPulse") -> dict[str, set[str]]:
    vis: dict[str, set[str]] = {}
    for e in c.journal.evenements("VISIBILITE"):
        parts = vis.setdefault(e.donnees["reference"], set())
        (parts.add if e.donnees["visible"] else parts.discard)(e.donnees["partie"])
    return vis


def recus_du_club(c: "ClubPulse") -> list[dict]:
    """TOUS les reçus (un par accord), avec leur étape — pour les agrégats et la console. Le membre y figure par son
    identifiant interne seulement ; le nom n'est ajouté que par la vue nominative, sous double accord."""
    membres = sorted({e.acteurs[0] for e in c.journal.evenements("ACCORD") if e.acteurs and e.donnees.get("finalite")})
    actives = {i.finalite for i in c.projection_capacites() if i.statut == "ACTIVE"}
    clotures, vis, jour = _clotures(c), _visibles(c), c.jour
    res = []
    for m in membres:
        for r in c.capacites.recus(m):
            etape = "accord"
            if r["retire_le"] or r["etat"] == "consentement retiré":
                etape = "retire"
            elif r["reference"] in clotures:
                etape = "resultat"
            elif r["etat"] == "valable" and (r["finalite"] in actives or date.fromisoformat(r["fenetre"]["jour"]
                                                                                             if isinstance(r["fenetre"], dict) else r["jusqu_au"]) < jour):
                etape = "essai"
            res.append(r | {"membre": m, "etape": etape, "cloture": clotures.get(r["reference"]),
                            "visible": sorted(vis.get(r["reference"], set()))})
    return res


def cloturer(c: "ClubPulse", reference: str, resultat: str, note: Optional[str] = None) -> dict:
    """Le DEMANDEUR (le Club, depuis la console) clôture UN reçu avec un résultat. Refus : reçu inconnu, retiré, déjà
    clôturé, résultat hors liste, note de plus de 140 caractères. La note passe par le même filtre que les textes libres."""
    if resultat not in RESULTATS:
        raise Invalide("résultat inconnu : " + " / ".join(RESULTATS))
    if note is not None and len(note) > NOTE_MAX:
        raise Invalide(f"note de {NOTE_MAX} caractères au plus")
    r = next((x for x in recus_du_club(c) if x["reference"] == reference), None)
    if r is None:
        raise Introuvable("reçu inconnu")
    suivante(r["etape"], "cloture")                              # refuse « retiré » et « résultat » (déjà clôturé)
    c.banc._ecrire("CLOTURE", [r["membre"]], reference=reference, finalite=r["finalite"], resultat=resultat,
                   note=c._net(note) if note else None)
    return {"reference": reference, "etape": "resultat", "resultat": resultat}


def rendre_visible(c: "ClubPulse", reference: str, partie: str, visible: bool, membre: Optional[str] = None) -> dict:
    """« Visible par le Club » : chaque partie le décide pour SON reçu. Le membre seulement pour un reçu qui est le sien."""
    r = next((x for x in recus_du_club(c) if x["reference"] == reference), None)
    if r is None or (partie != CLUB and r["membre"] != membre):
        raise Introuvable("reçu inconnu")
    c.banc._ecrire("VISIBILITE", [r["membre"]] if partie != CLUB else [], reference=reference,
                   partie="membre" if partie != CLUB else CLUB, visible=visible)
    return {"reference": reference, "visible": sorted(_visibles(c).get(reference, set()))}
