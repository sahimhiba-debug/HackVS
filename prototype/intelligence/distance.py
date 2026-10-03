"""MEMBRE À DISTANCE (Foire 2026 · F) — zone, langue préférée, et réponse à une demande DEPUIS L'E-MAIL.

- Le membre déclare sa ZONE (une liste fermée : Valais romand, Haut-Valais, Vaud, Genève, Haute-Savoie, Ain, autre) et
  sa LANGUE (fr / de) — un fait du journal (MEMBRE_DISTANCE), modifiable, qu'il voit dans « Mes données ».
- Suivi compte les membres hors Valais (k = 3) ; sans aucune zone déclarée : « zone non renseignée ».
- RÉPONSE DEPUIS L'E-MAIL : pour chaque demande qu'un membre à distance recevrait, trois liens (Oui / Non / Pas cette
  fois), SIGNÉS (HMAC du secret), À USAGE UNIQUE (l'usage est journalisé ; la réponse et la marque d'usage sont écrites
  dans la même transaction), EXPIRANTS (à l'échéance de la demande). Un lien ne vaut que pour SA demande, SON membre,
  SON choix, et tant que la demande lui est encore adressée.
- PAS DE SMTP : une « boîte de sortie » locale (console) montre les e-mails qui SERAIENT envoyés — calculée à la lecture
  (rien n'est écrit en lisant), étiquetée « simulé en démonstration ». Aucun message ne quitte la machine."""
from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import date
from typing import TYPE_CHECKING, Optional, Union

from plateforme.affirmations import Statut

from . import metiers
from .erreurs import Conflit, Introuvable, Invalide, NonAuthentifie

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

LANGUES = ("fr", "de")
CHOIX = {"o": ("oui", True, None), "n": ("non", False, "non"), "p": ("pas cette fois", False, "pas cette fois")}
SIMULE = "simulé en démonstration"
OBJET = {"fr": "Le Club vous demande : {libelle}", "de": "Der Club fragt Sie: {libelle}"}
CORPS = {"fr": "Bonjour {prenom},\n\n{texte}\n\nRépondez en un clic (chaque lien ne sert qu'une fois, jusqu'au {expire}) :",
         "de": "Guten Tag {prenom}\n\n{texte}\n\nAntworten Sie mit einem Klick (jeder Link gilt nur einmal, bis {expire}):"}
LIBELLES = {"fr": {"o": "Oui", "n": "Non", "p": "Pas cette fois"}, "de": {"o": "Ja", "n": "Nein", "p": "Diesmal nicht"}}
Nombre = Union[int, str]


# ------------------------------------------------------------------ zone et langue
def declarer(c: "ClubPulse", pid: str, zone: str, langue: str) -> dict:
    if zone not in metiers.ZONES:
        raise Invalide("zone inconnue")
    if langue not in LANGUES:
        raise Invalide("langue : fr ou de")
    c.banc._ecrire("MEMBRE_DISTANCE", [pid], Statut.DECLARE, membre=pid, zone=zone, langue=langue)
    return profil(c, pid) or {}


def profils(c: "ClubPulse") -> dict[str, dict]:
    res: dict[str, dict] = {}
    for e in c.journal.evenements("MEMBRE_DISTANCE"):
        if c.coffre.identite(e.donnees["membre"]) is not None:        # un compte effacé ne garde pas sa zone à l'écran
            res[e.donnees["membre"]] = {"zone": e.donnees["zone"], "langue": e.donnees["langue"], "le": e.le.isoformat()}
    return res


def profil(c: "ClubPulse", pid: str) -> Optional[dict]:
    return profils(c).get(pid)


def zones_membres(c: "ClubPulse", debut: Optional[date], k: int) -> Union[str, dict]:
    """Pour Suivi : membres hors Valais (zone déclarée ni Valais romand ni Haut-Valais), k = 3. Aucune zone : dit."""
    ps = profils(c)
    if not ps:
        return "zone non renseignée"
    from . import anonymat
    hors = {m for m, p in ps.items() if p["zone"] not in metiers.VALAIS}
    return {"membres": anonymat.seuil(c, hors, len(hors)), "zones_renseignees": anonymat.seuil(c, ps, len(ps))}


# ------------------------------------------------------------------ liens signés
def _b64(x: str) -> str:
    return base64.urlsafe_b64encode(x.encode()).decode().rstrip("=")


def _deb64(x: str) -> str:
    return base64.urlsafe_b64decode(x + "=" * (-len(x) % 4)).decode()


def _sig(c: "ClubPulse", pid: str, ask: str, choix: str, expire: str) -> str:
    return hmac.new(c.reglages.secret, f"courriel|{pid}|{ask}|{choix}|{expire}".encode(), hashlib.sha256).hexdigest()[:32]


def lien(c: "ClubPulse", pid: str, ask: str, choix: str, expire: str) -> str:
    return f"m1.{pid}.{_b64(ask)}.{choix}.{expire}.{_sig(c, pid, ask, choix, expire)}"


def _ouvrir(c: "ClubPulse", jeton: str) -> tuple[str, dict, str, str]:
    p = (jeton or "").split(".")
    if len(p) != 6 or p[0] != "m1" or p[3] not in CHOIX:
        raise NonAuthentifie("lien invalide")
    try:
        pid, ask, choix, expire = p[1], _deb64(p[2]), p[3], p[4]
        date.fromisoformat(expire)
    except ValueError:
        raise NonAuthentifie("lien invalide") from None
    if not hmac.compare_digest(p[5], _sig(c, pid, ask, choix, expire)):
        raise NonAuthentifie("lien invalide")
    if p[5] in {e.donnees["lien"] for e in c.journal.evenements("COURRIEL_LIEN")}:
        raise Conflit("ce lien a déjà servi : il est à usage unique")
    if c.jour > date.fromisoformat(expire):
        raise NonAuthentifie("lien expiré")
    if c.coffre.identite(pid) is None:
        raise NonAuthentifie("lien invalide")
    demande = next((a for a in c.vues_capacites.asks(pid) if a["id"] == ask), None)
    if demande is None:
        raise Introuvable("cette demande ne vous est plus adressée")
    return pid, demande, choix, p[5]


def lire_lien(c: "ClubPulse", jeton: str) -> dict:
    """Ce que montre la page de réponse (aucune écriture) : la demande, le choix du lien, les minimums si « oui »."""
    pid, demande, choix, _ = _ouvrir(c, jeton)
    langue = (profil(c, pid) or {}).get("langue", "fr")
    return {"titre": demande["titre"], "texte": demande["texte"], "libelle": demande["libelle"], "choix": CHOIX[choix][0],
            "minimums": demande.get("minimums", {}) if CHOIX[choix][1] else {}, "langue": langue, "expire": demande["expire"],
            "monde": "monde de démonstration", "fictif": True}


def repondre_lien(c: "ClubPulse", jeton: str, attributs: Optional[dict[str, int]] = None) -> dict:
    pid, demande, choix, sig = _ouvrir(c, jeton)
    _, oui, nuance = CHOIX[choix]
    with c.journal.transaction():                                  # tout ou rien : la réponse ET la marque d'usage
        c.repondre_ask(pid, demande["id"], oui, attributs if oui else None, None, choix=nuance)
        c.banc._ecrire("COURRIEL_LIEN", [pid], Statut.OBSERVE, lien=sig, ask=demande["id"], choix=CHOIX[choix][0])
    return {"reponse": CHOIX[choix][0], "titre": demande["titre"],
            "note": "Réponse enregistrée. Votre reçu est dans l'application, si vous avez dit oui." if oui else
                    "Réponse enregistrée. Personne ne vous demandera pourquoi."}


# ------------------------------------------------------------------ boîte de sortie (console)
def boite(c: "ClubPulse", base: str) -> dict:
    """Les e-mails qui SERAIENT envoyés aux membres à distance, pour les demandes qui leur sont adressées aujourd'hui.
    Calculée à la lecture, rien n'est envoyé ni écrit."""
    courriels = []
    for pid, p in sorted(profils(c).items()):
        per = c.coffre.identite(pid)
        if per is None:
            continue
        lg = p["langue"]
        for a in c.vues_capacites.asks(pid):
            courriels.append({
                "a": f"{per.nom} (personnage fictif)", "langue": lg, "zone": p["zone"],
                "objet": OBJET[lg].format(libelle=a["libelle"]),
                "corps": CORPS[lg].format(prenom=per.nom.split()[0], texte=a["texte"], expire=a["expire"]),
                "liens": [{"libelle": LIBELLES[lg][ch], "url": f"{base}/reponse#lien={lien(c, pid, a['id'], ch, a['expire'])}"}
                          for ch in ("o", "n", "p")]})
    return {"simule": SIMULE, "monde": "monde de démonstration", "fictif": True, "courriels": courriels,
            "note": "Aucun e-mail n'est envoyé : pas de serveur de messagerie. Cette boîte montre ce qui partirait."}
