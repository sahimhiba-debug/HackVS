"""ANNÉE 1 · LOT 9 — Allumage Foire (interrupteur HACKVS_FOIRE_ALLUMAGE, éteint par défaut).

- BORNE de stand : un appareil sans personne derrière, ouvert par un jeton émis par le secrétariat ; chaque visiteur prend
  un passe découverte (QR) ; un passe à la fois (BORNE_INTERVALLE_S), BORNE_PAR_JOUR au plus.
- IMPORT d'une liste d'EXPOSANTS (CSV : exposant ; métier ; stand) : un passe par exposant, dédoublonné ; le fichier rendu
  (exposant ; métier ; stand ; lien) sert à les inviter — il n'est PAS gardé : le journal n'a que des décomptes.
- Passes à GRANDE ÉCHELLE : des lots de 500 au plus.
- MESURE des adhésions venues du passe : émis → activés → ont aidé → intention → ADHÉSION, celle-ci CONFIRMÉE par le
  secrétariat (une intention n'est jamais une adhésion) ; « < 3 » compté en entreprises distinctes."""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import secrets
import time
from typing import TYPE_CHECKING, Callable, Optional, Union

from plateforme.affirmations import Statut

from . import club_cherche, metiers
from .erreurs import ErreurMetier, Invalide, NonAuthentifie

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

LOT_MAX = 500
BORNE_INTERVALLE_S = 3.0
BORNE_PAR_JOUR = 500
ORIGINES = ("stand", "demande", "startup", "exposant", "borne")
Nombre = Union[int, str, None]


class TropVite(ErreurMetier):
    statut_http = 429


def emettre_lot(c: "ClubPulse", n: int, origine: str = "stand") -> list[dict]:
    if not 1 <= n <= LOT_MAX:
        raise Invalide(f"de 1 à {LOT_MAX} passes par lot")
    if origine not in ("stand", "exposant", "borne"):
        raise Invalide("origine d'un lot : stand, exposant ou borne")
    with c.journal.transaction():                       # un lot : tout ou rien
        return [c.decouverte.emettre(origine) for _ in range(n)]


# ------------------------------------------------------------------ exposants
COLONNES_EXPOSANT = ("exposant", "entreprise", "nom", "raison sociale")


def importer_exposants(c: "ClubPulse", texte: str, base: str) -> dict:
    lecteur = csv.DictReader(io.StringIO(texte.lstrip("﻿")), delimiter=";" if ";" in texte.split("\n", 1)[0] else ",")
    cols = {(x or "").strip().lower(): x for x in (lecteur.fieldnames or [])}
    col_nom = next((cols[k] for k in COLONNES_EXPOSANT if k in cols), None)
    col_metier = next((cols[k] for k in club_cherche.COLONNES_METIER if k in cols), None)
    col_stand = cols.get("stand")
    if col_nom is None:
        raise Invalide("colonne « exposant » (ou « entreprise », « nom ») introuvable")
    lignes, vus, doublons, sans_metier = [], set(), 0, 0
    for ligne in lecteur:
        nom = " ".join((ligne.get(col_nom) or "").split())
        if not nom:
            continue
        cle = club_cherche.normaliser(nom)
        if cle in vus:
            doublons += 1
            continue
        vus.add(cle)
        brut = (ligne.get(col_metier) or "") if col_metier else ""
        mid = club_cherche._metier_csv(brut) if brut.strip() else None
        sans_metier += mid is None
        lignes.append((nom, mid or "", (ligne.get(col_stand) or "").strip() if col_stand else ""))
    if len(lignes) > LOT_MAX:
        raise Invalide(f"au plus {LOT_MAX} exposants par import")
    passes = emettre_lot(c, len(lignes), origine="exposant") if lignes else []
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=";", lineterminator="\n")
    w.writerow(["exposant", "metier", "stand", "lien", "reference"])
    for (nom, mid, stand), p in zip(lignes, passes, strict=True):
        w.writerow([_cellule(nom), metiers.libelle(mid) if mid else "", _cellule(stand), base.rstrip("/") + p["chemin"],
                    _ref(p["nonce"])])
    par_metier: dict[str, int] = {}
    for _, mid, _ in lignes:
        par_metier[mid or "inconnu"] = par_metier.get(mid or "inconnu", 0) + 1
    c.banc._ecrire("EXPOSANTS_IMPORTES", [], Statut.DECLARE, importes=len(lignes), doublons=doublons,
                   sans_metier=sans_metier, par_metier=par_metier)
    return {"importes": len(lignes), "doublons": doublons, "sans_metier": sans_metier, "csv": sortie.getvalue(),
            "note": "fichier à télécharger maintenant : il n'est pas gardé (le Club ne garde que des décomptes)"}


def _cellule(x: str) -> str:
    """Pas de formule dans un tableur (audit des lots 9-10, I3) : la liste vient d'un tiers ; une cellule qui commence par
    = + - @ (ou une tabulation, un retour) est préfixée d'une apostrophe, que le tableur affiche comme du texte."""
    return "'" + x if x[:1] in ("=", "+", "-", "@", "\t", "\r") else x


# ------------------------------------------------------------------ entonnoir et adhésions
def _ref(nonce: str) -> str:
    return "P-" + hashlib.sha256(nonce.encode()).hexdigest()[:8].upper()


def intentions(c: "ClubPulse") -> list[dict]:
    """Les passes dont l'invité a dit vouloir adhérer : une RÉFÉRENCE (celle que l'invité voit sur son passe), rien d'autre
    (ni métier ni région : audit des lots 9-10, I2). Usage interne : la console ne reçoit plus cette liste."""
    faites = {e.donnees["reference"] for e in c.journal.evenements("ADHESION_CONFIRMEE")}
    res = []
    for p in c.decouverte.passes().values():
        if p["intention"] and not p["revoque"]:          # un invité qui a retiré son consentement n'est plus listé (I2)
            res.append({"reference": _ref(p["nonce"]), "confirmee": _ref(p["nonce"]) in faites})
    return res


def confirmer_adhesion(c: "ClubPulse", reference: str, par: str = "") -> dict:
    connues = {x["reference"]: x for x in intentions(c)}
    if reference not in connues:
        raise Invalide("référence inconnue (seule une intention d'adhésion peut devenir une adhésion)")
    if connues[reference]["confirmee"]:
        raise Invalide("adhésion déjà confirmée")
    c.banc._ecrire("ADHESION_CONFIRMEE", [], Statut.DECLARE, reference=reference, par=par[:60])
    return {"reference": reference, "adhesion": True}


def entonnoir(c: "ClubPulse") -> dict:
    k = c.reglages.k_anonymat
    faites = {e.donnees["reference"] for e in c.journal.evenements("ADHESION_CONFIRMEE")}

    def ent(p: dict) -> str:
        return (p["declaration"] or {}).get("cle_entreprise") or f"passe:{p['nonce']}"

    def kk(g: list[dict]) -> Nombre:
        return f"< {k}" if g and len({ent(p) for p in g}) < k else len(g)
    res = {}
    passes = list(c.decouverte.passes().values())
    for o in ORIGINES:
        ps = [p for p in passes if p["origine"] == o]
        if not ps:
            continue
        actives = [p for p in ps if p["active_le"] is not None]
        adh = [p for p in ps if _ref(p["nonce"]) in faites]
        assez = len({ent(p) for p in adh}) >= k
        res[o] = {"emis": len(ps), "actives": kk(actives), "ont_aide": kk([p for p in ps if any(r["aide"] for r in p["reponses"])]),
                  "intentions": kk([p for p in ps if p["intention"] and not p["revoque"]]), "adhesions": kk(adh),
                  "taux_adhesion": round(100 * len(adh) / len(ps)) if adh and assez else None}
    return {"par_origine": res, "regle": f"adhésions CONFIRMÉES par le secrétariat ; « < {k} » compté en entreprises ; "
                                         "taux = adhésions / passes émis"}


# ------------------------------------------------------------------ borne
BORNE_DUREE_S = 14 * 24 * 3600                       # une Foire (10 jours) et sa marge : au-delà, un nouveau jeton


def _nom_borne(nom: str) -> str:
    # ASCII seulement (audit final : un caractère Unicode ne doit ni viser une autre borne ni faire échouer la comparaison)
    return "".join(ch for ch in nom if (ch.isascii() and ch.isalnum()) or ch in "-_")[:40] or "borne"


def jeton_borne(secret: bytes, nom: str, jusqu_a: Optional[int] = None) -> str:
    """Jeton « b2 » : nom de la borne + ÉCHÉANCE (secondes Unix), signés (audit des lots 9-10, M1 : un appareil perdu
    n'émet plus rien après l'échéance, et le secrétariat peut le révoquer avant)."""
    nom = _nom_borne(nom)
    fin = int(jusqu_a if jusqu_a is not None else time.time() + BORNE_DUREE_S)
    return f"b2.{nom}.{fin}.{hmac.new(secret, f'borne|{nom}|{fin}'.encode(), hashlib.sha256).hexdigest()[:32]}"


def verifier_borne(secret: bytes, jeton: str, revoquees: frozenset[str] = frozenset(),
                   maintenant: Optional[float] = None) -> str:
    morceaux = (jeton or "").split(".")
    if (len(morceaux) != 4 or morceaux[0] != "b2" or not (morceaux[2].isascii() and morceaux[2].isdigit())
            or morceaux[1] != _nom_borne(morceaux[1]) or not morceaux[3].isascii()):
        raise NonAuthentifie("borne inconnue")          # forme refusée AVANT toute comparaison (jamais une erreur 500)
    nom, fin = morceaux[1], int(morceaux[2])
    if not hmac.compare_digest(jeton_borne(secret, nom, fin), jeton):
        raise NonAuthentifie("borne inconnue")
    if (time.time() if maintenant is None else maintenant) >= fin:
        raise NonAuthentifie("jeton de borne échu : demandez-en un nouveau au secrétariat")
    if nom in revoquees:
        raise NonAuthentifie("borne révoquée par le secrétariat")
    return nom


def creer_borne(c: "ClubPulse", secret: bytes, par: str = "") -> dict:
    nom = nouveau_nom_borne()
    jeton = jeton_borne(secret, nom)
    fin = int(jeton.split(".")[2])
    c.banc._ecrire("BORNE_CREEE", [], Statut.DECLARE, nom=nom, jusqu_a=fin, par=par[:60])   # le nom seul, jamais le jeton
    return {"nom": nom, "jeton": jeton, "jusqu_a": fin}


def revoquer_borne(c: "ClubPulse", nom: str, par: str = "") -> dict:
    # la borne CRÉÉE de ce nom, sans tenir compte de la casse (une tablette ajoute une majuscule) ; inconnue : refusé,
    # jamais « révoquée » pour rien (audit final, I-A)
    creees = {e.donnees["nom"].lower(): e.donnees["nom"] for e in c.journal.evenements("BORNE_CREEE")}
    if _nom_borne(nom).lower() not in creees:
        raise Invalide("borne inconnue : vérifiez le nom dans la liste des bornes (rien n'a été révoqué)")
    nom = creees[_nom_borne(nom).lower()]
    c.banc._ecrire("BORNE_REVOQUEE", [], Statut.DECLARE, nom=nom, par=par[:60])
    return {"nom": nom, "revoquee": True}


def bornes_revoquees(c: "ClubPulse") -> frozenset[str]:
    return frozenset(e.donnees["nom"] for e in c.journal.evenements("BORNE_REVOQUEE"))


def bornes(c: "ClubPulse") -> list[dict]:
    rev = bornes_revoquees(c)
    maintenant = time.time()

    def etat(nom: str, fin: int) -> str:
        return "révoquée" if nom in rev else ("échue" if maintenant >= fin else "active")
    return [{"nom": e.donnees["nom"], "jusqu_au": time.strftime("%Y-%m-%d", time.gmtime(e.donnees["jusqu_a"])),
             "revoquee": e.donnees["nom"] in rev, "etat": etat(e.donnees["nom"], e.donnees["jusqu_a"])}
            for e in c.journal.evenements("BORNE_CREEE")]


class Borne:
    """Le rythme de chaque borne (en mémoire) : un visiteur à la fois, un plafond par jour."""

    def __init__(self, secret: bytes, horloge: Callable[[], float] = time.time):
        self._secret, self._h = secret, horloge
        self._dernier: dict[str, float] = {}
        self._jour: dict[tuple[str, str], int] = {}

    def passe(self, c: "ClubPulse", jeton: str) -> dict:
        maintenant = self._h()
        nom = verifier_borne(self._secret, jeton, bornes_revoquees(c), maintenant)
        if maintenant - self._dernier.get(nom, -1e9) < BORNE_INTERVALLE_S:
            raise TropVite("un visiteur à la fois : un instant")
        # le jour RÉEL de l'horloge, pas la date simulée du Club (avancer le temps ne remet pas le plafond à zéro : M2)
        cle = (nom, time.strftime("%Y-%m-%d", time.gmtime(maintenant)))
        if self._jour.get(cle, 0) >= BORNE_PAR_JOUR:
            raise TropVite("plafond du jour atteint pour cette borne")
        self._dernier[nom] = maintenant
        p = c.decouverte.emettre("borne")
        self._jour[cle] = self._jour.get(cle, 0) + 1                 # compté seulement si le passe a bien été émis
        return p | {"reference": _ref(p["nonce"])}


def nouveau_nom_borne() -> str:
    return "borne-" + secrets.token_hex(3)
