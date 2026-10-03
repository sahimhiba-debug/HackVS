"""« LE CLUB CHERCHE » (Foire 2026 · E) — les demandes restées sans réponse, regroupées par MÉTIER, avec leur nombre et
leur âge ; pour chacune, « Inviter un contact » émet un passe découverte LIÉ à la demande (texte FR/DE prêt à envoyer).

Métiers présents / absents : si `docs/data/entreprises.csv` existe (ou `HACKVS_ENTREPRISES_CSV`), il sert UNIQUEMENT à
COMPTER, par métier, les entreprises de la liste. Jamais une offre attribuée à une vraie entreprise, jamais un nom
d'entreprise lu ni affiché : seule la colonne du métier est lue. Sans le fichier, l'écran le dit."""
from __future__ import annotations

import csv
import os
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from . import metiers

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

CSV_DEFAUT = Path(__file__).resolve().parents[2] / "docs" / "data" / "entreprises.csv"
COLONNES_METIER = ("metier", "métier", "secteur", "branche", "activite", "activité")

INVITATION = {
    "fr": "Bonjour, le Club des entrepreneurs cherche : {quoi} ({metier}). Vous pouvez l'aider sans être membre, pendant "
          "{jours} jours, avec ce passe découverte (à usage unique) : {url}",
    "de": "Guten Tag, der Unternehmerclub sucht: {quoi} ({metier}). Sie können ohne Mitgliedschaft helfen, {jours} Tage "
          "lang, mit diesem Schnupperpass (einmalig gültig): {url}",
}


def _metier_csv(valeur: str) -> Optional[str]:
    v = " ".join(valeur.lower().split())
    if not v:
        return None
    termes = {m["id"]: {m["id"], *[x.strip() for x in (m["fr"] + "," + m["de"]).lower().split(",")]} for m in metiers.metiers()}
    for mid, t in termes.items():                                 # 1. le libellé exact
        if v in t:
            return mid
    mots = set(v.replace("/", " ").replace("-", " ").split())
    for mid, t in termes.items():                                 # 2. un terme du métier dans la valeur (« transport de personnes »)
        if mid != "autre" and t & mots:
            return mid
    return None



def entreprises_par_metier(chemin: Optional[Path] = None) -> Optional[dict]:
    """Décompte PAR MÉTIER des entreprises de la liste ; None si le fichier est absent. Seule la colonne du métier est lue."""
    p = chemin or Path(os.environ.get("HACKVS_ENTREPRISES_CSV") or CSV_DEFAUT)
    if not p.is_file():
        return None
    with p.open(encoding="utf-8-sig", newline="") as f:
        separateur = ";" if ";" in f.readline() else ","
        f.seek(0)
        lecteur = csv.DictReader(f, delimiter=separateur)
        col = next((c for c in (lecteur.fieldnames or []) if c and c.strip().lower() in COLONNES_METIER), None)
        if col is None:
            return {"lignes": 0, "par_metier": {}, "non_classees": 0, "note": "aucune colonne métier reconnue"}
        compte, non_classees, n = Counter[str](), 0, 0
        for ligne in lecteur:
            n += 1
            mid = _metier_csv(ligne.get(col) or "")
            if mid:
                compte[mid] += 1
            else:
                non_classees += 1
    return {"lignes": n, "par_metier": dict(compte), "non_classees": non_classees}


def calculer(c: "ClubPulse") -> dict:
    jour = c.jour
    semis = c.journal.evenements("SEMIS")[0].le
    repondues = {e.donnees["ask"] for e in c.journal.evenements("ASK_REPONSE")}
    # une PROPOSITION d'invité (passe découverte) : le manque est peut-être comblé — à confirmer par le Club (jamais qui)
    proposees = {e.donnees["ask"] for e in c.journal.evenements("DECOUVERTE_REPONSE") if e.donnees.get("aide")}
    groupes: dict[str, dict] = {}
    for i in c.projection_capacites():
        if i.ask is None or i.ask.id in repondues:
            continue
        p = c.capacites.patron(i.finalite)
        em = next(e for e in p.emplacements if e.id == i.ask.emplacement)
        naissance = max([semis, *[x.le for x in c.journal.evenements("RETRAIT") if x.donnees.get("finalite") == i.finalite]])
        mid = metiers.par_role(em.role)
        g = groupes.setdefault(mid, {"metier": mid, "libelle": metiers.libelle(mid), "libelle_de": metiers.libelle(mid, "de"),
                                     "demandes": []})
        g["demandes"].append({"id": i.ask.id, "titre": p.titre, "piece": em.libelle, "texte": i.ask.texte,
                              "age_jours": (jour - naissance).days, "proposition_invite": i.ask.id in proposees})
    liste = sorted(groupes.values(), key=lambda g: (-len(g["demandes"]), g["metier"]))
    for g in liste:
        g["nombre"] = len(g["demandes"])
        g["age_max_jours"] = max(d["age_jours"] for d in g["demandes"])
    ent = entreprises_par_metier()
    if ent is not None:
        for g in liste:
            g["entreprises_de_ce_metier"] = ent["par_metier"].get(g["metier"], 0)
        presents = [m["id"] for m in metiers.metiers() if ent["par_metier"].get(m["id"])]
        marche = {"source": "liste d'entreprises (décomptes seulement, aucun nom)", "lignes": ent["lignes"],
                  "non_classees": ent["non_classees"], "metiers_presents": len(presents),
                  "metiers_absents": len(metiers.metiers()) - len(presents)}
    else:
        marche = {"source": "absente", "note": "liste d'entreprises non fournie : métiers présents / absents non calculés"}
    return {"date": jour.isoformat(), "monde": "monde de démonstration", "fictif": True, "metiers": liste, "marche": marche}


def invitation(quoi: str, metier: str, url: str, jours: int) -> dict[str, str]:
    return {lg: t.format(quoi=quoi, metier=metiers.libelle(metier, lg), url=url, jours=jours) for lg, t in INVITATION.items()}
