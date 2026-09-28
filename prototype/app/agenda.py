"""Créneaux de rencontre : chaque membre déclare ses demi-journées habituelles (« mar-matin », « jeu-apres-midi »).

Confidentialité : les créneaux d'un membre ne sont JAMAIS exposés en recherche ni aux autres membres. Seule
l'INTERSECTION des créneaux des deux personnes est calculée, et montrée à elles seules, après acceptation.
"""
from __future__ import annotations

from datetime import date, timedelta

JOURS = ("lun", "mar", "mer", "jeu", "ven")
MOMENTS = ("matin", "apres-midi")
CRENEAUX = tuple(f"{j}-{m}" for j in JOURS for m in MOMENTS)
_NOMS_JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi")
_NOMS_MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")


def valides(creneaux: list[str]) -> list[str]:
    return [c for c in dict.fromkeys(creneaux) if c in CRENEAUX]


def communs(a: list[str], b: list[str], depuis: date, jours: int = 14, limite: int = 4) -> list[dict]:
    """Prochaines demi-journées (à partir du lendemain de `depuis`) où les deux personnes se sont déclarées disponibles."""
    inter = set(valides(a)) & set(valides(b))
    res = []
    for k in range(1, jours + 1):
        d = depuis + timedelta(days=k)
        if d.weekday() > 4:
            continue
        for m in MOMENTS:
            if f"{JOURS[d.weekday()]}-{m}" in inter:
                res.append({"date": d.isoformat(), "moment": m,
                            "libelle": f"{_NOMS_JOURS[d.weekday()]} {d.day} {_NOMS_MOIS[d.month - 1]}, {'après-midi' if m == 'apres-midi' else m}"})
                if len(res) >= limite:
                    return res
    return res
