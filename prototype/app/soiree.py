"""Plan de rencontres d'une soirée du Club : qui doit rencontrer qui, à quel tour, et pourquoi.

1. Valeur d'une rencontre (i, j) = aide que j peut apporter à i + aide que i peut apporter à j.
   « Aide » = une recherche de i (besoin publié ou champ « recherche » du profil) que l'offre DÉCLARÉE de j couvre,
   selon le moteur habituel (filtres, consentement, preuves exactes). Bonus si l'aide est réciproque.
2. Plan sur R tours : au plus une rencontre par personne et par tour, jamais deux fois la même paire,
   et jamais deux personnes SANS LANGUE COMMUNE déclarée (contrainte dure, comme les filtres de la recherche).
3. Optimisation exacte par programme linéaire en nombres entiers (scipy.optimize.milp, solveur HiGHS) :
     max Σ v_e·x_{e,r} + λ·Σ_i y_i    avec y_i ≤ Σ_{e∋i, r} x_{e,r}, y_i ≤ 1
   (λ récompense chaque participant qui obtient au moins une rencontre utile : équité).
4. Références mesurées : glouton (meilleures paires d'abord) et aléatoire (moyenne sur 30 tirages).
"""
from __future__ import annotations

import random
import time
from itertools import combinations
from typing import Optional

import numpy as np

from .matching import rechercher
from .models import Besoin, Critere, Profil
from .taxonomy import Taxonomie

BONUS_RECIPROQUE = 0.3
LAMBDA_EQUITE = 0.5


def _recherches(p: Profil, besoins_publies: list, tax: Taxonomie) -> list[tuple[str, Besoin]]:
    """Ce que p cherche : besoins publiés NON anonymes + champ « recherche » du profil (concepts connus)."""
    res = [(f"besoin publié : {b.besoin.texte}", b.besoin) for b in besoins_publies if b.auteur_id == p.id and not b.anonyme]
    for r in p.recherche:
        if r.concept:
            res.append((f"recherche : {r.texte}", Besoin(texte=r.texte, criteres=[
                Critere(type="expertise", valeur=r.concept, libelle=tax.libelle(r.concept), obligatoire=True)])))
    return res


def _aide(i: Profil, j: Profil, besoins_i, tax: Taxonomie) -> Optional[dict]:
    """Meilleure aide que j peut apporter à i (avec preuve), ou None."""
    meilleure = None
    for source, besoin in besoins_i:
        res = rechercher(besoin, i, [i, j], tax)
        s = next((x for x in res.suggestions if x.profil.id == j.id), None)
        if s:
            valeur = 1.0 if s.niveau == "forte" else 0.5
            if meilleure is None or valeur > meilleure["valeur"]:
                meilleure = {"valeur": valeur, "besoin": source, "preuve": s.preuves[0].extrait, "niveau": s.niveau}
    return meilleure


def langues_communes(a: Profil, b: Profil) -> list[str]:
    return sorted(set(a.langues) & set(b.langues))


def valeurs(participants: list[Profil], besoins_publies: list, tax: Taxonomie,
            ecartees: Optional[dict] = None, deja: frozenset = frozenset()) -> dict[tuple[str, str], dict]:
    """Paires utiles. `ecartees` (facultatif) reçoit les paires utiles écartées faute de langue commune.
    `deja` : paires déjà en relation (coordonnées échangées) : inutile de leur réserver une table."""
    rech = {p.id: _recherches(p, besoins_publies, tax) for p in participants}
    aretes = {}
    for a, b in combinations(participants, 2):
        if frozenset((a.id, b.id)) in deja:
            continue
        ab, ba = _aide(a, b, rech[a.id], tax), _aide(b, a, rech[b.id], tax)
        if not ab and not ba:
            continue
        if not langues_communes(a, b):
            if ecartees is not None:
                ecartees[(a.id, b.id)] = True
            continue
        v = (ab["valeur"] if ab else 0) + (ba["valeur"] if ba else 0) + (BONUS_RECIPROQUE if ab and ba else 0)
        aretes[(a.id, b.id)] = {"valeur": round(v, 3), "b_aide_a": ab, "a_aide_b": ba, "langues": langues_communes(a, b)}
    return aretes


def _score(plan: list[list[tuple[str, str]]], aretes) -> dict:
    vus = {x for tour in plan for e in tour for x in e}
    utiles = {x for tour in plan for e in tour for x in e if aretes[e]["valeur"] > 0}
    aides = sum((aretes[e]["b_aide_a"] is not None) + (aretes[e]["a_aide_b"] is not None) for tour in plan for e in tour)
    return {"valeur_totale": round(sum(aretes[e]["valeur"] for tour in plan for e in tour), 2),
            "rencontres": sum(len(t) for t in plan), "participants_avec_rencontre_utile": len(utiles),
            "aides_couvertes": aides, "_vus": len(vus)}


def glouton(aretes, tours: int) -> list[list[tuple[str, str]]]:
    restantes = sorted(aretes, key=lambda e: -aretes[e]["valeur"])
    plan, pris = [], set()
    for _ in range(tours):
        occupes, tour = set(), []
        for e in restantes:
            if e not in pris and e[0] not in occupes and e[1] not in occupes:
                tour.append(e); occupes |= set(e); pris.add(e)
        plan.append(tour)
    return plan


def aleatoire(aretes, tours: int, graine: int) -> list[list[tuple[str, str]]]:
    rng = random.Random(graine)
    restantes = list(aretes)
    plan, pris = [], set()
    for _ in range(tours):
        rng.shuffle(restantes)
        occupes, tour = set(), []
        for e in restantes:
            if e not in pris and e[0] not in occupes and e[1] not in occupes:
                tour.append(e); occupes |= set(e); pris.add(e)
        plan.append(tour)
    return plan


def optimal(aretes, participants: list[str], tours: int, limite_s: float = 20.0) -> tuple[list[list[tuple[str, str]]], dict]:
    from scipy.optimize import Bounds, LinearConstraint, milp
    E = list(aretes)
    nE, nP = len(E), len(participants)
    idx_p = {p: k for k, p in enumerate(participants)}
    nx = nE * tours
    n = nx + nP  # x_{e,r} puis y_i
    c = np.zeros(n)
    for r in range(tours):
        for k, e in enumerate(E):
            c[r * nE + k] = -aretes[e]["valeur"]
    c[nx:] = -LAMBDA_EQUITE
    lignes, bas, haut = [], [], []
    # une rencontre au plus par personne et par tour
    for r in range(tours):
        for p in participants:
            ligne = np.zeros(n)
            for k, e in enumerate(E):
                if p in e:
                    ligne[r * nE + k] = 1
            lignes.append(ligne); bas.append(0); haut.append(1)
    # chaque paire au plus une fois
    for k in range(nE):
        ligne = np.zeros(n)
        for r in range(tours):
            ligne[r * nE + k] = 1
        lignes.append(ligne); bas.append(0); haut.append(1)
    # y_i ≤ nombre de rencontres de i
    for p in participants:
        ligne = np.zeros(n)
        ligne[nx + idx_p[p]] = 1
        for r in range(tours):
            for k, e in enumerate(E):
                if p in e:
                    ligne[r * nE + k] = -1
        lignes.append(ligne); bas.append(-np.inf); haut.append(0)
    t0 = time.perf_counter()
    res = milp(c, constraints=LinearConstraint(np.array(lignes), bas, haut), integrality=np.ones(n),
               bounds=Bounds(0, 1), options={"time_limit": limite_s})
    info = {"statut": res.message, "optimal_prouve": bool(res.status == 0), "duree_ms": round((time.perf_counter() - t0) * 1000),
            "variables": n, "contraintes": len(lignes)}
    x = np.round(res.x[:nx]).astype(int) if res.x is not None else np.zeros(nx, int)
    plan = [[E[k] for k in range(nE) if x[r * nE + k]] for r in range(tours)]
    return plan, info


def planifier(participants: list[Profil], besoins_publies: list, tax: Taxonomie, tours: int = 3,
              deja_en_relation: frozenset = frozenset()) -> dict:
    t0 = time.perf_counter()
    eligibles = [p for p in participants if p.type == "membre_club" and p.accepte_introductions and p.disponible]
    sans_langue: dict = {}
    aretes = valeurs(eligibles, besoins_publies, tax, sans_langue, deja_en_relation)
    ids = [p.id for p in eligibles]
    t_val = round((time.perf_counter() - t0) * 1000)
    plan_opt, info = optimal(aretes, ids, tours) if aretes else ([[] for _ in range(tours)], {"optimal_prouve": True})
    s_opt, s_glo = _score(plan_opt, aretes), _score(glouton(aretes, tours), aretes)
    tirages = [_score(aleatoire(aretes, tours, g), aretes) for g in range(30)]
    moy = lambda k: round(float(np.mean([t[k] for t in tirages])), 2)
    par_id = {p.id: p for p in eligibles}

    def carte(e, r, table):
        a = aretes[e]
        pa, pb = par_id[e[0]], par_id[e[1]]
        pub = lambda p: {"id": p.id, "nom": p.nom, "entreprise": p.entreprise}
        return {"tour": r + 1, "table": table, "a": pub(pa), "b": pub(pb), "valeur": a["valeur"],
                "b_aide_a": a["b_aide_a"], "a_aide_b": a["a_aide_b"], "reciproque": bool(a["b_aide_a"] and a["a_aide_b"]),
                "langues": a["langues"]}

    rencontres = [carte(e, r, t + 1) for r, tour in enumerate(plan_opt)
                  for t, e in enumerate(sorted(tour, key=lambda e: -aretes[e]["valeur"]))]
    for s in (s_opt, s_glo):
        s.pop("_vus", None)
    return {
        "membres": len([p for p in participants if p.type == "membre_club"]), "participants": len(eligibles), "tours": tours,
        "paires_utiles_possibles": len(aretes),
        "rencontres": rencontres,
        "comparaison": {"optimal": s_opt, "glouton": s_glo,
                        "aleatoire_moyenne_30": {k: moy(k) for k in ("valeur_totale", "rencontres", "participants_avec_rencontre_utile", "aides_couvertes")}},
        "solveur": info, "calcul_valeurs_ms": t_val,
        "sans_rencontre": [{"nom": p.nom, "raison": r} for p, r in sorted(
            ((p, _raison_absence(p, aretes, sans_langue, plan_opt, par_id)) for p in eligibles
             if not any(p.id in (m["a"]["id"], m["b"]["id"]) for m in rencontres)), key=lambda x: x[0].nom)],
        "paires_ecartees_sans_langue_commune": len(sans_langue),
        "paires_deja_en_relation": len(deja_en_relation),
        "contraintes": ["au plus une rencontre par personne et par tour", "jamais deux fois la même paire",
                        "langue commune déclarée obligatoire", "membres disponibles et acceptant les introductions",
                        "pas de table pour deux membres déjà en relation"],
    }


def _raison_absence(p: Profil, aretes, sans_langue, plan, par_id) -> str:
    """Pourquoi ce membre n'a aucune rencontre ciblée (jamais un reproche : une information pour l'animateur)."""
    siennes = [e for e in aretes if p.id in e]
    if not siennes:
        if any(p.id in e for e in sans_langue):
            return "complémentarités trouvées, mais aucune langue commune déclarée"
        return "aucune complémentarité prouvée avec les participants (compléter « je cherche / je propose »)"
    occupes = {x for tour in plan for e in tour for x in e if x != p.id}
    autres = sorted({par_id[x].nom for e in siennes for x in e if x != p.id})
    return (f"ses {len(autres)} partenaire(s) possible(s) ({', '.join(autres[:3])}{'…' if len(autres) > 3 else ''}) "
            "sont mieux employé(e)s ailleurs à chaque tour" if all(x in occupes for e in siennes for x in e if x != p.id)
            else "arbitrage de l'optimisation")


def _ics_texte(v: str) -> str:
    return v.replace("\\", "\\\\").replace(";", r"\;").replace(",", "\\,").replace("\n", "\\n")


def _plier(ligne: str) -> str:
    """RFC 5545 §3.1 : lignes de 75 octets au plus, continuation par une espace."""
    b, out = ligne.encode("utf-8"), []
    while len(b) > 75:
        coupe = 75 if not out else 74
        while (b[coupe] & 0xC0) == 0x80:  # ne pas couper un caractère UTF-8
            coupe -= 1
        out.append(b[:coupe].decode("utf-8"))
        b = b[coupe:]
    out.append(b.decode("utf-8"))
    return "\r\n ".join(out)


def programme_ics(plan: dict, membre_id: str, debut: str, duree_tour_min: int = 15, pause_min: int = 5) -> str:
    """Programme individuel d'une soirée au format iCalendar (une entrée par rencontre)."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    t0 = datetime.fromisoformat(debut).replace(tzinfo=ZoneInfo("Europe/Zurich"))
    utc = lambda d: d.astimezone(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    lignes = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Le Fil du Club//Soiree//FR", "CALSCALE:GREGORIAN"]
    for m in plan["rencontres"]:
        if membre_id not in (m["a"]["id"], m["b"]["id"]):
            continue
        moi, autre = (m["a"], m["b"]) if m["a"]["id"] == membre_id else (m["b"], m["a"])
        aide_recue = m["b_aide_a"] if m["a"]["id"] == membre_id else m["a_aide_b"]
        aide_donnee = m["a_aide_b"] if m["a"]["id"] == membre_id else m["b_aide_a"]
        d = t0 + timedelta(minutes=(m["tour"] - 1) * (duree_tour_min + pause_min))
        pourquoi = []
        if aide_recue:
            pourquoi.append(f"{autre['nom']} peut vous aider : « {aide_recue['preuve']} »")
        if aide_donnee:
            pourquoi.append(f"Vous pouvez l'aider : « {aide_donnee['preuve']} »")
        pourquoi.append("Données fictives (démonstration).")
        titre = f"Tour {m['tour']} · table {m['table']} · {autre['nom']}"
        lignes += ["BEGIN:VEVENT", f"UID:soiree-{plan['donnees']}-{m['tour']}-{m['a']['id']}-{m['b']['id']}@le-fil-du-club",
                   f"DTSTAMP:{utc(t0)}", f"DTSTART:{utc(d)}", f"DTEND:{utc(d + timedelta(minutes=duree_tour_min))}",
                   f"SUMMARY:{_ics_texte(titre)}",
                   f"LOCATION:{_ics_texte('Soirée du Club · table ' + str(m['table']))}",
                   f"DESCRIPTION:{_ics_texte(chr(10).join(pourquoi))}", "END:VEVENT"]
    lignes.append("END:VCALENDAR")
    return "\r\n".join(_plier(x) for x in lignes) + "\r\n"
