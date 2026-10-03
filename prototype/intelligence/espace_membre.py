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
# champs TECHNIQUES jamais traités comme du texte libre (identifiants, dates, états, nombres) — AUDIT B1 : la purge ne
# touche que des TEXTES, repérés par leur forme ; une date, une heure ou un identifiant n'en est jamais un
GARDES = {"membre", "auteur", "id", "type", "finalite", "concept", "statut", "kind", "nature", "essai", "etape", "oui",
          "reponse", "valide_du", "valide_au", "valid_until", "recorded_at", "le", "n", "t", "jusqu_au", "seq", "du", "au",
          "superseded_at", "provenance", "sens", "disponible", "accepte_introductions", "jour", "debut", "fin", "echeance",
          "offre_id", "nonce", "empreinte", "trace", "role", "langue", "canal", "resultat", "emplacement", "ask"}
EFFACE = "[effacé]"


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


def membres_en_pause(c: "ClubPulse") -> frozenset[str]:
    return frozenset(pid for pid, fin in _pauses(c).items() if fin is not None and c.jour <= fin)


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
    ident, org = c.coffre.identite(pid), c.coffre.organisation_de(pid)
    # AUDIT des lots 2-3, I6 (droit d'accès, LPD art. 25 / RGPD art. 15 et 20) : l'identité du coffre et le CONTENU des
    # notes privées, en plus de ce que le moteur sait de moi
    return {"format": "clubpulse-export-membre", "version": 2, "membre": pid, "genere_le": c.jour.isoformat(),
            "fictif": True,
            "identite": None if ident is None else {"nom": ident.nom, "courriel": ident.courriel, "telephone": ident.telephone,
                                                    "organisation": getattr(org, "nom", None)},
            "notes_privees": c.vues.notes_de(pid),
            "mes_donnees": c.vues_capacites.mes_donnees(pid), "preferences": preferences(c, pid),
            "pause": etat_pause(c, pid), "demandes": mes_demandes(c, pid), "reciprocite": reciprocite.balance(c, pid)}


def _texte_libre(cle: str, x: str) -> bool:
    """Un TEXTE libre (à purger) : pas une clé technique, et plusieurs mots ou une lettre accentuée / majuscule — jamais
    un identifiant (`of-1a2b`, `c00012`, `salle`), une date (`2026-10-06`) ou une heure (`13:30`)."""
    import re
    if cle in GARDES or len(x) < 6 or x == EFFACE:
        return False
    if re.fullmatch(r"[0-9T:+\-. Z]+", x) or re.fullmatch(r"[a-z0-9_:\-.@/]+", x):
        return False
    return " " in x.strip() or any(ch.isupper() or not ch.isascii() for ch in x)


def _textes(x: Any, cle: str = "") -> set[str]:
    if isinstance(x, dict):
        return set().union(*[_textes(v, k) for k, v in x.items()]) if x else set()
    if isinstance(x, list):
        return set().union(*[_textes(v, cle) for v in x]) if x else set()
    return {x} if isinstance(x, str) and _texte_libre(cle, x) else set()


def textes_du_membre(c: "ClubPulse", pid: str) -> set[str]:
    """Ce que le membre a ÉCRIT (faits dont il est l'auteur ou l'acteur), plus son nom, son courriel et son téléphone."""
    res: set[str] = set()
    for e in c.journal.evenements():
        b, o = e.donnees.get("besoin"), e.donnees.get("offre")
        if pid in e.acteurs or e.donnees.get("membre") == pid or (isinstance(b, dict) and b.get("auteur") == pid) \
                or (isinstance(o, dict) and o.get("auteur") == pid):
            res |= _textes(e.donnees)
    ident = c.coffre.identite(pid)
    if ident is not None:
        res |= {x for x in (ident.nom, ident.courriel, ident.telephone) if x and len(x) >= 4}
    return res


def _remplacer(x: Any, textes: list[str], cle: str = "") -> Any:
    if isinstance(x, dict):
        return {k: _remplacer(v, textes, k) for k, v in x.items()}
    if isinstance(x, list):
        return [_remplacer(v, textes, cle) for v in x]
    if isinstance(x, str) and cle not in GARDES:
        if x in textes:
            return EFFACE
        for t in textes:                              # le plus long d'abord : une copie dans une phrase plus longue
            if len(t) >= 12 and t in x:
                x = x.replace(t, EFFACE)
    return x


def _verifier_rejouable(c: "ClubPulse", evts: list[Evt]) -> None:
    """AUDIT B1 : AVANT d'écrire, le monde purgé est rejoué dans une copie en mémoire et TOUT y est relu (offres,
    capacités, protocoles, état complet). Une lecture qui échoue : rien n'est écrit."""
    import dataclasses

    from .club_pulse import ClubPulse
    from .ia import Intelligence
    copie = ClubPulse(c.tax, ia=Intelligence(c.tax, None), reglages=dataclasses.replace(c.reglages, essais_db=":memory:"), neuf=True)
    copie.journal.vider()
    with copie.journal.transaction():
        for e in evts:
            copie.journal.ajouter(e)
    copie._restaurer()
    copie.banc.offres()
    for eid in copie.banc.essais():
        copie.banc.protocole(eid)
    copie.projection_capacites()
    copie.empreinte_etat()
    copie.vues_capacites.console()


def _purger(c: "ClubPulse", textes: list[str], trace: Optional[Evt]) -> int:
    def transformer(e: Evt) -> Evt:
        d = _remplacer(e.donnees, textes)
        return e if d == e.donnees else e.model_copy(update={"donnees": d})
    avant = c.journal.evenements()
    apres = [transformer(e) for e in avant]
    n = sum(1 for a, b in zip(avant, apres, strict=True) if a is not b)
    if n:
        _verifier_rejouable(c, apres)
    if n or trace is not None:
        c.journal.reecrire(transformer, trace.model_copy(update={"donnees": trace.donnees | {"faits": n}}) if trace else None)
    return n


def effacer_definitivement(c: "ClubPulse", pid: str) -> dict:
    """Suppression du compte avec PURGE RÉELLE (audit des lots 2-3 : B1, B2, I3, I7).

    1. On repère ce que le membre a écrit (et son nom, son courriel, son téléphone) ; chaque texte est remplacé par
       « [effacé] » PARTOUT dans le journal, y compris là où il a été recopié (adaptations, protocoles, accords
       d'autres membres). Dates, heures, identifiants : jamais touchés.
    2. Le monde purgé est rejoué et relu dans une copie AVANT toute écriture ; puis la réécriture est tout ou rien.
    3. SEULEMENT ENSUITE, l'effacement (`ClubPulse.effacer` : retraits, coffre, notes) ; puis une seconde passe pour ce
       que l'effacement aurait recopié. Si l'effacement échoue après la purge, recommencer est sans danger.
    Une trace PURGE unique (sans contenu) : deux suppressions le même jour ne se confondent jamais."""
    import secrets
    with c.verrou:
        if c.coffre.identite(pid) is None:
            from .erreurs import Introuvable
            raise Introuvable("membre inconnu")
        textes = sorted(textes_du_membre(c, pid), key=len, reverse=True)
        trace = Evt(type="PURGE", le=c.jour, acteurs=[], statut=Statut.OBSERVE, donnees={"trace": secrets.token_hex(6)})
        n = _purger(c, textes, trace)
        bilan = c.effacer(pid)
        n += _purger(c, textes, None)
        c._reconstruire_membres()
    return bilan | {"faits_purges": n, "reste": "vos textes, votre nom et vos coordonnées sont retirés du journal, y compris "
                                               "là où ils avaient été recopiés ; il garde des faits sans contenu (dates, "
                                               "identifiants techniques). Les sauvegardes antérieures suivent leur durée "
                                               "de conservation."}
