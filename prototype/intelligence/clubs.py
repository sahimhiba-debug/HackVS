"""ANNÉE 1 · LOT 8 — Grandir : la notion de « club ».

- Un club PRINCIPAL (celui de la démonstration) ; d'autres clubs peuvent être déclarés, mais seulement comme EXEMPLES
  FICTIFS (marqués comme tels) : aucun partenaire n'est présenté comme acquis.
- L'adhésion croisée est demandée par le MEMBRE lui-même (son consentement), et retirable à tout moment ; elle dit
  seulement qu'il accepte d'être sollicité par l'autre club.
- Un membre peut se dire « à distance » (il ne se déplace pas) : déclaré, visible dans la console en décompte.
Limite, dite telle quelle : la mise en relation ne lit pas encore le club d'une demande (toutes les demandes sont celles
du club principal) ; `peut_etre_sollicite` est la règle prête à être branchée."""
from __future__ import annotations

from typing import TYPE_CHECKING

from plateforme.affirmations import Statut

from . import anonymat
from .erreurs import Interdit, Invalide

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

PRINCIPAL = "principal"


def _declares(c: "ClubPulse") -> dict[str, dict]:
    res = {PRINCIPAL: {"id": PRINCIPAL, "nom": "le Club (principal)", "region": "Valais", "pays": "CH", "fictif": True,
                       "principal": True}}
    for e in c.journal.evenements("CLUB_DECLARE"):
        res[e.donnees["id"]] = {**{k: e.donnees[k] for k in ("id", "nom", "region", "pays", "fictif")}, "principal": False}
    return res


def liste(c: "ClubPulse") -> list[dict]:
    return list(_declares(c).values())


def declarer(c: "ClubPulse", cid: str, nom: str, *, region: str, pays: str, fictif: bool) -> dict:
    if not fictif:
        raise Invalide("seul un club EXEMPLE FICTIF peut être déclaré : aucun partenaire n'est présenté comme acquis")
    if "fictif" not in nom.lower():
        raise Invalide("le nom d'un club exemple dit « fictif »")
    if not cid or len(cid) > 40 or not cid.replace("-", "").isalnum() or cid in _declares(c):
        raise Invalide("identifiant de club vide, invalide ou déjà pris")
    c.banc._ecrire("CLUB_DECLARE", [], Statut.SYNTHETIQUE, id=cid, nom=nom[:80], region=region[:60], pays=pays[:2].upper(),
                   fictif=True)
    return _declares(c)[cid]


def _croises(c: "ClubPulse") -> dict[str, set[str]]:
    res: dict[str, set[str]] = {}
    for e in c.journal.evenements("CLUB_ADHESION_CROISEE", "CLUB_DEPART"):
        s = res.setdefault(e.acteurs[0], set())
        (s.add if e.type == "CLUB_ADHESION_CROISEE" else s.discard)(e.donnees["club"])
    return res


def rejoindre(c: "ClubPulse", pid: str, cid: str) -> dict:
    if cid == PRINCIPAL:
        raise Interdit("c'est déjà votre club")
    if cid not in _declares(c):
        raise Invalide("club inconnu")
    if cid not in _croises(c).get(pid, set()):
        c.banc._ecrire("CLUB_ADHESION_CROISEE", [pid], Statut.DECLARE, club=cid)
    return clubs_de(c, pid)


def quitter(c: "ClubPulse", pid: str, cid: str) -> dict:
    if cid in _croises(c).get(pid, set()):
        c.banc._ecrire("CLUB_DEPART", [pid], Statut.DECLARE, club=cid)
    return clubs_de(c, pid)


def a_distance(c: "ClubPulse", pid: str, oui: bool) -> dict:
    c.banc._ecrire("MEMBRE_A_DISTANCE", [pid], Statut.DECLARE, oui=bool(oui))
    return clubs_de(c, pid)


def _a_distance(c: "ClubPulse") -> set[str]:
    res: set[str] = set()
    for e in c.journal.evenements("MEMBRE_A_DISTANCE"):
        (res.add if e.donnees["oui"] else res.discard)(e.acteurs[0])
    return res


def clubs_de(c: "ClubPulse", pid: str) -> dict:
    return {"principal": PRINCIPAL, "croises": sorted(_croises(c).get(pid, set())), "a_distance": pid in _a_distance(c)}


def peut_etre_sollicite(c: "ClubPulse", pid: str, cid: str) -> bool:
    """La règle (prête à brancher) : un membre est sollicitable par un club s'il en est membre, ou s'il a choisi
    l'adhésion croisée."""
    return cid == PRINCIPAL or cid in _croises(c).get(pid, set())


def vue_console(c: "ClubPulse") -> dict:
    croises = _croises(c)
    res = []
    for x in liste(c):
        qui = {pid for pid, s in croises.items() if x["id"] in s}
        res.append({**x, "membres_croises": anonymat.seuil(c, qui, len(qui))})
    loin = _a_distance(c)
    return {"clubs": res, "membres_a_distance": anonymat.seuil(c, loin, len(loin)),
            "limite": "la mise en relation ne lit pas encore le club d'une demande"}
