"""ANNONCES SOUS CHIFFRE (P3 n°9) — relayées par le secrétariat jusqu'à l'accord mutuel.

Un membre publie sous une référence (« A-001 ») : aucun auteur n'est affiché. Un membre intéressé le dit au relais ;
l'auteur ne voit qu'« intérêt n° 1 », sans nom. L'auteur accepte un intérêt : c'est l'accord MUTUEL (l'intéressé
s'était déjà manifesté). Alors, et alors seulement, les deux — et eux seuls — voient le nom et l'entreprise de l'autre.
Le secrétariat ne voit que des décomptes. Journal : ANNONCE, ANNONCE_INTERET, ANNONCE_ACCORD ; le texte passe par la
frontière du moteur (aucune identité du coffre dans le journal)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from plateforme.affirmations import Statut

from . import anonymat
from .erreurs import Conflit, Interdit, Introuvable, Invalide

if TYPE_CHECKING:
    from .club_pulse import ClubPulse


def _annonces(c: "ClubPulse") -> dict[str, dict]:
    res: dict[str, dict] = {}
    for e in c.journal.evenements("ANNONCE", "ANNONCE_INTERET", "ANNONCE_ACCORD"):
        d = e.donnees
        if e.type == "ANNONCE":
            res[d["chiffre"]] = {"chiffre": d["chiffre"], "texte": d["texte"], "auteur": e.acteurs[0], "le": e.le.isoformat(),
                                 "interets": [], "accords": set()}
        elif d.get("chiffre") in res:
            a = res[d["chiffre"]]
            if e.type == "ANNONCE_INTERET" and e.acteurs[0] not in a["interets"]:
                a["interets"].append(e.acteurs[0])
            elif e.type == "ANNONCE_ACCORD":
                a["accords"].add(d["membre"])
    return {k: v for k, v in res.items() if c.coffre.identite(v["auteur"]) is not None}


def _contact(c: "ClubPulse", pid: str) -> Optional[dict]:
    per, org = c.coffre.identite(pid), c.coffre.organisation_de(pid)
    return {"nom": per.nom, "entreprise": org.nom if org else None} if per else None


def publier(c: "ClubPulse", pid: str, texte: str) -> dict:
    t = c._net(texte.strip())
    if not 5 <= len(t) <= 400:
        raise Invalide("annonce vide ou trop longue")
    # AUDIT D4 : compté sur TOUT le journal (annonces d'auteurs effacés comprises) — un chiffre n'est jamais réattribué
    chiffre = f"A-{len(c.journal.evenements('ANNONCE')) + 1:03d}"
    c.banc._ecrire("ANNONCE", [pid], Statut.DECLARE, chiffre=chiffre, texte=t)
    return {"chiffre": chiffre}


def interet(c: "ClubPulse", pid: str, chiffre: str) -> dict:
    a = _annonces(c).get(chiffre)
    if a is None:
        raise Introuvable("annonce inconnue")
    if a["auteur"] == pid:
        raise Conflit("c'est votre annonce")
    if pid not in a["interets"]:
        c.banc._ecrire("ANNONCE_INTERET", [pid], Statut.DECLARE, chiffre=chiffre)
    return {"chiffre": chiffre, "relaye": "votre intérêt est transmis, sans votre nom"}


def accepter(c: "ClubPulse", pid: str, chiffre: str, n: int) -> dict:
    a = _annonces(c).get(chiffre)
    if a is None:
        raise Introuvable("annonce inconnue")
    if a["auteur"] != pid:
        raise Interdit("seul l'auteur accepte un intérêt")
    if not 1 <= n <= len(a["interets"]):
        raise Introuvable("intérêt inconnu")
    membre = a["interets"][n - 1]
    if membre not in a["accords"]:
        c.banc._ecrire("ANNONCE_ACCORD", [pid], Statut.DECLARE, chiffre=chiffre, membre=membre)
    return {"chiffre": chiffre, "accord": "mutuel : vous voyez chacun le nom de l'autre"}


def pour_membre(c: "ClubPulse", pid: str) -> list[dict]:
    """Toutes les annonces, sans auteur ; le contact de l'auteur seulement si CE membre a un accord mutuel."""
    res = []
    for a in _annonces(c).values():
        x = {"chiffre": a["chiffre"], "texte": a["texte"], "le": a["le"], "mienne": a["auteur"] == pid,
             "interet_dit": pid in a["interets"]}
        if pid in a["accords"]:
            x["contact"] = _contact(c, a["auteur"])
        res.append(x)
    return res


def mes_annonces(c: "ClubPulse", pid: str) -> list[dict]:
    res = []
    for a in _annonces(c).values():
        if a["auteur"] != pid:
            continue
        interets = []
        for i, m in enumerate(a["interets"], start=1):
            interets.append({"n": i} | ({"contact": _contact(c, m)} if m in a["accords"] else {}))
        res.append({"chiffre": a["chiffre"], "texte": a["texte"], "le": a["le"], "interets": interets})
    return res


def agregats(c: "ClubPulse") -> dict:
    tout = _annonces(c).values()
    qui = {m for a in tout for m in a["interets"]}
    accords = {m for a in tout for m in a["accords"]}
    return {"annonces": len(tout), "interets": anonymat.seuil(c, qui, sum(len(a["interets"]) for a in tout)),
            "accords_mutuels": anonymat.seuil(c, accords, len(accords)), "regle": "décomptes seulement ; jamais un auteur"}
