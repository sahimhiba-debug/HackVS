"""H3 : un seul Club a-t-il assez de volume pour que des intentions de cession trouvent un repreneur ?

Monte-Carlo (modèle SYNTHÉTIQUE, pas une prévision) : chaque membre a un secteur parmi S (loi de Zipf, comme un annuaire
réel où quelques secteurs dominent) ; 16 % cherchent un repreneur (Dun & Bradstreet, CH 2024) ; une proportion b veut
reprendre, dans 1 à 3 secteurs. Mesure : nombre moyen de cédants qui ont au moins un repreneur compatible.
Fédération : plusieurs clubs confrontent leurs intentions scellées sans partager aucune donnée (même protocole PSI).
Usage : python -m experiences.sensibilite_volume
"""
from __future__ import annotations

import json
import random


def simuler(n: int, b: float, s: int = 30, essais: int = 400, graine: int = 1) -> float:
    rng = random.Random(graine)
    poids = [1 / (i + 1) for i in range(s)]
    total = 0
    for _ in range(essais):
        secteurs = rng.choices(range(s), poids, k=n)
        cedants = [secteurs[i] for i in range(n) if rng.random() < 0.16]
        cherches = set()
        for _ in range(n):
            if rng.random() < b:
                cherches |= set(rng.choices(range(s), poids, k=rng.choice([1, 2, 3])))
        total += sum(1 for c in cedants if c in cherches)
    return total / essais


if __name__ == "__main__":
    lignes = []
    for n, lib in ((100, "1 club (100)"), (150, "1 club (150)"), (300, "3 clubs fédérés"), (1000, "10 clubs / CCI")):
        for b in (0.01, 0.02, 0.04):
            lignes.append({"membres": lib, "part_de_repreneurs": b, "cedants_moyens": round(0.16 * n, 1),
                           "cedants_avec_un_repreneur_compatible": round(simuler(n, b), 2)})
    print(json.dumps(lignes, ensure_ascii=False, indent=0))
