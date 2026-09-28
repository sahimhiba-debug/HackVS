"""H2 : probabilité de DEVINER l'auteur d'une intention de cession, selon le mécanisme.

- Bourse anonyme actuelle : l'annonce « Un membre du Club · secteur S » est lue par tous ; deviner = 1 / (membres du secteur S).
- Intentions scellées : les non-compatibles n'apprennent RIEN (0) ; la contrepartie compatible (ou un faux acheteur
  qui sonde) apprend seulement la catégorie k-anonyme C : deviner = 1 / (membres de la catégorie C), ≤ 1/k par construction.
Hypothèse d'attaque : l'annuaire public du Club (secteurs) est connu de tous.
Usage (depuis prototype/) : python -m experiences.mesure_reidentification
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.models import Profil
from app.taxonomy import charger_taxonomie

from .intentions import generaliser

DATA = Path(__file__).resolve().parent.parent / "data"


def mesurer(fichier: str, k: int) -> dict:
    tax = charger_taxonomie()
    profils = [Profil(**p) for p in json.loads((DATA / fichier).read_text(encoding="utf-8"))["profils"]
               if p["type"] == "membre_club"]
    annuaire = Counter(s for p in profils for s in p.secteurs)
    parents = {c: tax.concepts[c].parent for c in tax.concepts}

    def taille_categorie(c: str) -> int:
        return len(profils) if c == "*" else sum(1 for p in profils if any(s == c or c in tax.ancetres(s) for s in p.secteurs))

    bourse = [1 / annuaire[p.secteurs[0]] for p in profils]
    scelle = [1 / taille_categorie(generaliser(p.secteurs[0], annuaire, parents, k)) for p in profils]
    return {"club": fichier, "membres": len(profils), "k": k,
            "bourse_anonyme_proba_moyenne_de_deviner": round(sum(bourse) / len(bourse), 3),
            "bourse_anonyme_auteurs_designes_a_coup_sur": sum(1 for x in bourse if x == 1.0),
            "scelle_proba_moyenne_pour_la_contrepartie": round(sum(scelle) / len(scelle), 3),
            "scelle_proba_max_pour_la_contrepartie": round(max(scelle), 3),
            "scelle_proba_pour_les_autres_membres": 0.0}


if __name__ == "__main__":
    for f in ("profils_demo.json", "profils_synthetiques.json"):
        for k in (3, 5):
            print(json.dumps(mesurer(f, k), ensure_ascii=False))
