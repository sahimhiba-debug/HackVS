"""ANNÉE 1 · LOT 3 — L'espace membre : mode pause, préférences (langue, région, canaux), mes demandes envoyées, export
de mes données, effacement DÉFINITIF avec purge réelle du journal.

Tout est journalisé (PAUSE, PAUSE_FIN, MEMBRE_PREFERENCES, PURGE) : l'état survit au redémarrage et au changement de
moteur. La pause rend le membre non sollicitable (`ClubPulse._membre_peut`) jusqu'à sa date : il ne reçoit plus rien.
Rien de tout cela n'apparaît dans la démo tant qu'aucun membre ne s'en sert (routes derrière HACKVS_ESPACE_MEMBRE)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Optional

from plateforme.affirmations import Statut
from plateforme.memoire import Evt

from .erreurs import Invalide

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

LANGUES = ("fr", "de", "en", "it")
CANAUX = ("app", "email", "sms")
PAUSE_MAX_JOURS = 183
# champs d'identité technique conservés à la purge (sans eux, le journal ne se rejoue plus) — jamais un texte libre
GARDES = {"membre", "auteur", "id", "type", "finalite", "concept", "statut", "kind", "nature", "objet", "essai", "etape",
          "oui", "reponse", "valide_du", "valide_au", "valid_until", "recorded_at", "le", "n", "t", "jusqu_au", "seq",
          "superseded_at", "provenance", "sens", "disponible", "accepte_introductions"}


def _pauses(c: "ClubPulse") -> dict[str, Optional[date]]:
    """Fin de pause par membre (None : pas de pause), recalculée seulement quand le journal change."""
    v = c.journal.version()
    cache = c.__dict__.get("_cache_pauses")
    if cache and cache[0] == v:
        return cache[1]
    fins: dict[str, Optional[date]] = {}
    for e in c.journal.evenements("PAUSE", "PAUSE_FIN"):
        fins[e.acteurs[0]] = date.fromisoformat(e.donnees["jusqu_au"]) if e.type == "PAUSE" else None
    c.__dict__["_cache_pauses"] = (v, fins)
    return fins


def en_pause(c: "ClubPulse", pid: str) -> bool:
    fin = _pauses(c).get(pid)
    return fin is not None and c.jour <= fin


def etat_pause(c: "ClubPulse", pid: str) -> dict:
    fin = _pauses(c).get(pid)
    return {"en_pause": en_pause(c, pid), "jusqu_au": fin.isoformat() if fin and en_pause(c, pid) else None}


def mettre_en_pause(c: "ClubPulse", pid: str, jusqu_au: date) -> dict:
    if not c.jour <= jusqu_au <= c.jour + timedelta(days=PAUSE_MAX_JOURS):
        raise Invalide(f"la pause va d'aujourd'hui à {PAUSE_MAX_JOURS} jours au plus")
    c.banc._ecrire("PAUSE", [pid], Statut.DECLARE, jusqu_au=jusqu_au.isoformat())
    return etat_pause(c, pid)


def reprendre(c: "ClubPulse", pid: str) -> dict:
    c.banc._ecrire("PAUSE_FIN", [pid], Statut.DECLARE)
    return etat_pause(c, pid)


def regler_preferences(c: "ClubPulse", pid: str, *, langue: str, region: str, canaux: list[str]) -> dict:
    if langue not in LANGUES:
        raise Invalide(f"langue : {', '.join(LANGUES)}")
    if not canaux or any(x not in CANAUX for x in canaux):
        raise Invalide(f"au moins un canal parmi {', '.join(CANAUX)} (pour ne plus rien recevoir : la pause)")
    if len(region) > 60:
        raise Invalide("région trop longue")
    c.banc._ecrire("MEMBRE_PREFERENCES", [pid], Statut.DECLARE, langue=langue, region=region.strip(),
                   canaux=[x for x in CANAUX if x in canaux])
    return preferences(c, pid)


def preferences(c: "ClubPulse", pid: str) -> dict:
    p = [e for e in c.journal.evenements("MEMBRE_PREFERENCES") if e.acteurs[0] == pid]
    if not p:
        return {"langue": "fr", "region": "", "canaux": ["app"]}
    d = p[-1].donnees
    return {"langue": d["langue"], "region": d["region"], "canaux": list(d["canaux"])}


def mes_demandes(c: "ClubPulse", pid: str) -> list[dict]:
    return [{"le": e.le.isoformat(), "id": e.donnees["besoin"]["id"], "texte": e.donnees["besoin"]["texte"]}
            for e in c.journal.evenements("BESOIN") if e.donnees.get("besoin", {}).get("auteur") == pid]


def exporter(c: "ClubPulse", pid: str) -> dict:
    """Mes données, en un fichier : ce que le Club sait de moi, mes préférences, ma pause, mes demandes, mon solde."""
    from . import reciprocite
    return {"format": "clubpulse-export-membre", "version": 1, "membre": pid, "genere_le": c.jour.isoformat(),
            "fictif": True, "mes_donnees": c.vues_capacites.mes_donnees(pid), "preferences": preferences(c, pid),
            "pause": etat_pause(c, pid), "demandes": mes_demandes(c, pid), "reciprocite": reciprocite.balance(c, pid)}


def _expurger(x: Any, pid: str, cle: str = "") -> Any:
    if isinstance(x, dict):
        return {k: _expurger(v, pid, k) for k, v in x.items()}
    if isinstance(x, list):
        return [_expurger(v, pid, cle) for v in x]
    if isinstance(x, str) and cle not in GARDES and x != pid:
        return "[effacé]"
    return x


def effacer_definitivement(c: "ClubPulse", pid: str) -> dict:
    """L'effacement du membre (retraits, coffre, notes : `ClubPulse.effacer`), PUIS la purge réelle : chaque fait du
    journal qui porte ce membre perd ses textes libres (« [effacé] »). Une seule trace : le fait PURGE, sans contenu."""
    bilan = c.effacer(pid)

    def transformer(e: Evt) -> Evt:
        if pid not in e.acteurs and e.donnees.get("membre") != pid and e.donnees.get("besoin", {}).get("auteur") != pid:
            return e
        return e.model_copy(update={"donnees": _expurger(e.donnees, pid) | {"purge_seq": e.seq}})
    with c.verrou:
        n = sum(1 for e in c.journal.evenements() if transformer(e) is not e)
        c.journal.reecrire(transformer, Evt(type="PURGE", le=c.jour, acteurs=[], statut=Statut.OBSERVE, donnees={"faits": n}))
        c._reconstruire_membres()
    return bilan | {"faits_purges": n, "reste": "plus aucun texte libre de votre part dans le journal ; il garde seulement "
                                               "des faits sans contenu (dates, identifiant technique)."}
