"""Optimisation générique : affectation de rencontres par tours (programme linéaire en nombres entiers, HiGHS).

    max  Σ_e Σ_r ( Σ_t w_t · terme_t(e) ) · x_{e,r}  +  w_couv · Σ_i y_i
    s.c. Σ_{e ∋ i} x_{e,r} ≤ 1          (une rencontre au plus par personne et par tour)
         Σ_r x_{e,r} ≤ 1                  (une paire au plus une fois)
         y_i ≤ Σ_{e ∋ i, r} x_{e,r}, y_i ≤ 1   (i est « servi » s'il a au moins une rencontre)
         Σ_i y_i ≥ couverture_min         (optionnel : contrainte ε pour explorer la frontière)

Les arêtes interdites (contraintes dures du domaine) ne sont PAS des variables : l'adaptateur les exclut et les
déclare, et le validateur indépendant vérifie qu'aucune n'a été utilisée. Aucun LLM ici.
"""
from __future__ import annotations

import time
from itertools import product
from typing import Optional

import numpy as np
from pydantic import BaseModel
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix, vstack

Paire = tuple[str, str]


class Probleme(BaseModel):
    participants: list[str]
    aretes: dict[str, dict[str, float]]      # « a|b » → {terme: valeur}
    exclues: dict[str, str] = {}             # « a|b » → raison (contrainte dure qui l'interdit)
    tours: int = 3

    def paires(self) -> list[Paire]:
        return [tuple(k.split("|")) for k in self.aretes]  # type: ignore[misc]


class Solution(BaseModel):
    poids: dict[str, float]
    statut: str
    optimum_prouve: bool
    duree_ms: float
    rencontres: list[tuple[int, str, str]]    # (tour, a, b)
    objectifs: dict[str, float]               # valeurs réalisées de chaque terme (non pondérées)


def cle(a: str, b: str) -> str:
    return f"{a}|{b}" if a < b else f"{b}|{a}"


def resoudre(pb: Probleme, poids: dict[str, float], couverture_min: int = 0, limite_s: float = 30.0) -> Solution:
    E = list(pb.aretes)
    nE, R, P = len(E), pb.tours, len(pb.participants)
    idx = {p: k for k, p in enumerate(pb.participants)}
    termes = sorted({t for v in pb.aretes.values() for t in v})
    nx = nE * R
    n = nx + P
    if n == 0:  # aucun participant : rien à résoudre (et HiGHS refuse un vecteur vide)
        return Solution(poids=poids, statut="probleme_vide", optimum_prouve=False, duree_ms=0.0, rencontres=[], objectifs={})
    c = np.zeros(n)
    gain = np.array([sum(poids.get(t, 0.0) * pb.aretes[e].get(t, 0.0) for t in termes) for e in E])
    for r in range(R):
        c[r * nE:(r + 1) * nE] = -gain
    c[nx:] = -poids.get("couverture", 0.0)
    lignes, cols, vals, bas, haut, k = [], [], [], [], [], 0
    extremites = [tuple(e.split("|")) for e in E]
    for r in range(R):                                     # 1 rencontre / personne / tour
        par_p: dict[str, list[int]] = {}
        for j, (a, b) in enumerate(extremites):
            par_p.setdefault(a, []).append(r * nE + j)
            par_p.setdefault(b, []).append(r * nE + j)
        for p in pb.participants:
            for v in par_p.get(p, []):
                lignes.append(k), cols.append(v), vals.append(1)
            bas.append(0), haut.append(1)
            k += 1
    for j in range(nE):                                    # paire unique
        for r in range(R):
            lignes.append(k), cols.append(r * nE + j), vals.append(1)
        bas.append(0), haut.append(1)
        k += 1
    incid: dict[str, list[int]] = {}
    for j, (a, b) in enumerate(extremites):
        incid.setdefault(a, []).append(j)
        incid.setdefault(b, []).append(j)
    for p in pb.participants:                              # y_i ≤ Σ x
        lignes.append(k), cols.append(nx + idx[p]), vals.append(1)
        for j in incid.get(p, []):
            for r in range(R):
                lignes.append(k), cols.append(r * nE + j), vals.append(-1)
        bas.append(-np.inf), haut.append(0)
        k += 1
    A = coo_matrix((vals, (lignes, cols)), shape=(k, n)).tocsr()
    contraintes = [LinearConstraint(A, bas, haut)]
    if couverture_min:
        ligne = coo_matrix((np.ones(P), (np.zeros(P, int), np.arange(nx, n))), shape=(1, n)).tocsr()
        contraintes.append(LinearConstraint(vstack([ligne]), couverture_min, np.inf))
    t0 = time.perf_counter()
    res = milp(c, constraints=contraintes, integrality=np.ones(n), bounds=Bounds(0, 1), options={"time_limit": limite_s})
    duree = (time.perf_counter() - t0) * 1000
    if res.x is None:
        return Solution(poids=poids, statut=res.message, optimum_prouve=False, duree_ms=round(duree, 1), rencontres=[],
                        objectifs={})
    x = np.round(res.x[:nx]).astype(int)
    rencontres = sorted((r + 1, *extremites[j]) for r in range(R) for j in range(nE) if x[r * nE + j])
    return Solution(poids=poids, statut="optimal" if res.status == 0 else res.message, optimum_prouve=res.status == 0,
                    duree_ms=round(duree, 1), rencontres=rencontres, objectifs=mesurer(pb, rencontres, termes))


def mesurer(pb: Probleme, rencontres: list[tuple[int, str, str]], termes: Optional[list[str]] = None) -> dict[str, float]:
    termes = termes or sorted({t for v in pb.aretes.values() for t in v})
    tot = {t: round(sum(pb.aretes[cle(a, b)].get(t, 0.0) for _, a, b in rencontres), 3) for t in termes}
    tot["couverture"] = len({p for _, a, b in rencontres for p in (a, b)})
    return tot


def domine(u: dict[str, float], v: dict[str, float], axes: list[str]) -> bool:
    return all(u.get(a, 0) >= v.get(a, 0) for a in axes) and any(u.get(a, 0) > v.get(a, 0) for a in axes)


def frontiere(pb: Probleme, axes: list[str], niveaux=(0.0, 1.0, 3.0)) -> list[Solution]:
    """Points SUPPORTÉS de la frontière de Pareto : balayage de poids sur les axes, puis filtre de dominance.
    (Les points non supportés, entre deux sommets, ne sont pas garantis : c'est dit, pas caché.)"""
    vus: dict[tuple, Solution] = {}
    for combo in product(niveaux, repeat=len(axes)):
        if not any(combo):
            continue
        s = resoudre(pb, dict(zip(axes, combo, strict=True)))
        if s.objectifs:
            vus.setdefault(tuple(s.objectifs.get(a, 0) for a in axes), s)
    sols = list(vus.values())
    return sorted([s for s in sols if not any(domine(o.objectifs, s.objectifs, axes) for o in sols)],
                  key=lambda s: tuple(-s.objectifs.get(a, 0) for a in axes))


def sensibilite(pb: Probleme, poids: dict[str, float], terme: str, facteurs=(0.5, 2.0)) -> list[dict]:
    """Que change une variation du poids d'un terme ? (part des rencontres modifiées, variation des objectifs)."""
    base = resoudre(pb, poids)
    b = {(a, c) for _, a, c in base.rencontres}
    res = []
    for f in facteurs:
        s = resoudre(pb, poids | {terme: poids.get(terme, 0) * f})
        n = {(a, c) for _, a, c in s.rencontres}
        res.append({"terme": terme, "facteur": f, "paires_changees": len(b ^ n),
                    "part_changee": round(len(b ^ n) / max(1, len(b | n)), 3),
                    "delta": {k: round(s.objectifs.get(k, 0) - base.objectifs.get(k, 0), 3) for k in base.objectifs}})
    return res
