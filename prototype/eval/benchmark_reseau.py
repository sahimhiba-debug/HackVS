"""SYNTHETIC_BENCHMARK — recommandation de connexions : notre optimiseur contre cinq baselines, sur des réseaux générés
où les objectifs sont EN CONFLIT (pertinence vs diversité, membres populaires vs négligés, réciprocité vs ponts).

Usage : python -m eval.benchmark_reseau   (depuis prototype/ ; aucun réseau, aucun LLM ; ≈ 1 min)
Produit eval/resultats_benchmark_reseau.md. RIEN ici n'est une donnée du Club : membres, besoins et vérité sont générés.

Anti-circularité : les méthodes ne voient que les données DÉCLARÉES (offres, besoins, relations). L'utilité est
mesurée contre une vérité LATENTE du générateur : 20 % des offres déclarées sont périmées (plus vraies), et un besoin
n'est réellement servi que si l'offre est vraie. Aucune méthode ne voit la vérité latente.
"""
from __future__ import annotations

import random
import statistics
import time
from itertools import combinations
from pathlib import Path

import networkx as nx

from plateforme import optimisation as op

ICI = Path(__file__).resolve().parent
ETIQUETTE = "SYNTHETIC_BENCHMARK"
BUDGET_PAR_MEMBRE = 2          # fatigue : au plus 2 introductions par membre (= 2 « tours »)


def generer(graine: int, n: int = 60, communautes: int = 4, concepts: int = 24) -> dict:
    rnd = random.Random(graine)
    com = {f"m{i:02d}": i % communautes for i in range(n)}
    # chaque communauté a ses concepts « maison » (les membres se ressemblent) + des concepts transverses rares
    maison = {c: list(range(c * 5, c * 5 + 5)) for c in range(communautes)}
    transverses = list(range(communautes * 5, concepts))
    populaires = set(rnd.sample(sorted(com), 6))            # offrent beaucoup : attirent toutes les recommandations
    nouveaux = set(rnd.sample(sorted(set(com) - populaires), 8))  # aucune relation (cold start)
    offres, besoins, vraies = {}, {}, {}
    for m, c in com.items():
        k = 6 if m in populaires else rnd.randint(1, 3)
        pool = maison[c] * 3 + transverses                    # surtout des concepts de sa communauté
        offres[m] = set(rnd.sample(pool, min(k, len(set(pool))))) if k else set()
        besoins[m] = set(rnd.sample(maison[(c + rnd.randint(0, communautes - 1)) % communautes] + transverses, rnd.randint(1, 2))) - offres[m]
        vraies[m] = {o for o in offres[m] if rnd.random() > 0.2}  # 20 % d'offres périmées (déclarées, plus vraies)
    g = nx.Graph()
    g.add_nodes_from(com)
    for a, b in combinations(sorted(com), 2):
        if a in nouveaux or b in nouveaux:
            continue
        p = 0.18 if com[a] == com[b] else 0.01               # communautés denses, rares ponts
        if rnd.random() < p:
            g.add_edge(a, b)
    consent = {m: rnd.random() > 0.1 for m in com}            # 10 % refusent les introductions
    return {"com": com, "offres": offres, "besoins": besoins, "vraies": vraies, "g": g, "consent": consent,
            "populaires": populaires, "nouveaux": nouveaux, "etiquette": ETIQUETTE}


def candidats(d: dict) -> list[tuple[str, str]]:
    """Paires admissibles pour TOUTES les méthodes : consentement des deux, pas déjà en relation, et au moins un besoin
    DÉCLARÉ couvert (règle commune : jamais d'introduction sans raison). Les méthodes ne diffèrent que par leur CHOIX."""
    ms = sorted(m for m in d["com"] if d["consent"][m])
    return [(a, b) for a, b in combinations(ms, 2) if not d["g"].has_edge(a, b) and sum(pertinence(d, a, b)) > 0]


def pertinence(d: dict, a: str, b: str) -> tuple[int, int]:
    """(besoins de a couverts par les offres DÉCLARÉES de b, et inversement)."""
    return len(d["besoins"][a] & d["offres"][b]), len(d["besoins"][b] & d["offres"][a])


# ------------------------------------------------------------------ méthodes (toutes sous la même contrainte de budget)
def _glouton(paires_triees: list[tuple[str, str]]) -> list[tuple[str, str]]:
    charge: dict[str, int] = {}
    res = []
    for a, b in paires_triees:
        if charge.get(a, 0) < BUDGET_PAR_MEMBRE and charge.get(b, 0) < BUDGET_PAR_MEMBRE:
            res.append((a, b))
            charge[a], charge[b] = charge.get(a, 0) + 1, charge.get(b, 0) + 1
    return res


def m_aleatoire(d, cand, graine):
    c = list(cand)
    random.Random(graine).shuffle(c)
    return _glouton(c)


def m_similarite(d, cand, graine):
    """« Des gens comme vous » : similarité de profil (Jaccard des concepts) — la baseline des annuaires."""
    def sim(a, b):
        x, y = d["offres"][a] | d["besoins"][a], d["offres"][b] | d["besoins"][b]
        return len(x & y) / max(1, len(x | y))
    return _glouton(sorted(cand, key=lambda p: (-sim(*p), p)))


def m_pertinence(d, cand, graine):
    """Matchmaking unilatéral : maximise la pertinence (besoin couvert), sans autre considération."""
    return _glouton(sorted(cand, key=lambda p: (-sum(pertinence(d, *p)), p)))


def m_reciproque(d, cand, graine):
    """Réciprocité d'abord (min des deux sens), puis pertinence totale."""
    return _glouton(sorted(cand, key=lambda p: (-min(pertinence(d, *p)), -sum(pertinence(d, *p)), p)))


def m_graphe(d, cand, graine):
    """Ami d'ami : nombre de voisins communs (fermeture de triade) — la baseline des réseaux sociaux."""
    g = d["g"]
    return _glouton(sorted(cand, key=lambda p: (-len(list(nx.common_neighbors(g, *p))), -sum(pertinence(d, *p)), p)))


def probleme(d, cand) -> op.Probleme:
    aretes = {}
    for a, b in cand:
        ab, ba = pertinence(d, a, b)
        aretes[op.cle(a, b)] = {"valeur_aide": float(ab + ba), "reciprocite": float(ab > 0 and ba > 0),
                                "diversite": float(d["com"][a] != d["com"][b])}
    return op.Probleme(participants=sorted({x for k in aretes for x in k.split("|")}), aretes=aretes, tours=BUDGET_PAR_MEMBRE)


POIDS = {"valeur_aide": 1.0, "reciprocite": 1.0, "diversite": 1.0, "couverture": 1.5}


def m_optimise(d, cand, graine):
    """Le MÊME solveur que la plateforme (plateforme.optimisation) : valeur collective sous contraintes."""
    s = op.resoudre(probleme(d, cand), POIDS)
    return [(a, b) for _, a, b in s.rencontres]


METHODES = {"aléatoire": m_aleatoire, "similarité": m_similarite, "pertinence gloutonne": m_pertinence,
            "réciprocité gloutonne": m_reciproque, "graphe (ami d'ami)": m_graphe, "optimiseur (plateforme)": m_optimise}


# ------------------------------------------------------------------ mesures (vérité LATENTE + phénomènes du réseau)
def mesurer(d: dict, paires: list[tuple[str, str]]) -> dict:
    n = max(1, len(paires))
    vrai = lambda a, b: len(d["besoins"][a] & d["vraies"][b])   # noqa: E731  — besoin RÉELLEMENT servi
    utiles = sum(1 for a, b in paires if vrai(a, b) or vrai(b, a))
    reciproques = sum(1 for a, b in paires if vrai(a, b) and vrai(b, a))
    ponts = sum(1 for a, b in paires if d["com"][a] != d["com"][b])
    g2 = d["g"].copy()
    g2.add_edges_from(paires)
    isoles_avant = sum(1 for m in d["com"] if d["g"].degree(m) == 0)
    isoles_apres = sum(1 for m in d["com"] if g2.degree(m) == 0)
    charge: dict[str, int] = {}
    for a, b in paires:
        charge[a], charge[b] = charge.get(a, 0) + 1, charge.get(b, 0) + 1
    vers_populaires = sum(1 for a, b in paires if a in d["populaires"] or b in d["populaires"])
    servis = {x for p in paires for x in p}
    besoins_servis = sum(1 for m in d["com"] if any(vrai(m, o) for a, b in paires for o in (a, b) if m in (a, b) and o != m))
    nouveaute = sum(1 for a, b in paires if not (a in d["g"] and b in d["g"] and nx.has_path(d["g"], a, b)
                                                 and nx.shortest_path_length(d["g"], a, b) <= 2))
    return {"introductions": len(paires), "utiles_%": round(100 * utiles / n, 1), "reciproques_%": round(100 * reciproques / n, 1),
            "membres_avec_besoin_servi": besoins_servis, "ponts_%": round(100 * ponts / n, 1),
            "composantes": nx.number_connected_components(g2), "isoles_restants": isoles_apres, "isoles_avant": isoles_avant,
            "nouveaux_servis": len(servis & d["nouveaux"]), "vers_populaires_%": round(100 * vers_populaires / n, 1),
            "nouveaute_%": round(100 * nouveaute / n, 1), "charge_max": max(charge.values(), default=0), "membres_servis": len(servis)}


def main(graines=(1, 2, 3, 4, 5)) -> dict:
    tous: dict[str, list[dict]] = {k: [] for k in METHODES}
    duree: dict[str, list[float]] = {k: [] for k in METHODES}
    pareto = []
    for gr in graines:
        d = generer(gr)
        cand = candidats(d)
        for nom, f in METHODES.items():
            t0 = time.perf_counter()
            paires = f(d, cand, gr)
            duree[nom].append((time.perf_counter() - t0) * 1000)
            tous[nom].append(mesurer(d, paires))
        pb = probleme(d, cand)
        pareto.append(len(op.frontiere(pb, ["valeur_aide", "reciprocite", "diversite", "couverture"], niveaux=(0.0, 1.0, 3.0))))
    cles = list(next(iter(tous.values()))[0])
    moy = {nom: {k: round(statistics.mean(r[k] for r in rs), 1) for k in cles} | {"ms": round(statistics.mean(duree[nom]), 1)}
           for nom, rs in tous.items()}
    lignes = [f"# {ETIQUETTE} — recommandation de connexions : optimiseur vs baselines", "",
              f"**Données générées** (graines {list(graines)}, 60 membres, 4 communautés, 6 membres « populaires », 8 nouveaux "
              "sans relation, 20 % d'offres périmées, 10 % sans consentement). **Aucune donnée du Club.** Budget : au plus "
              f"{BUDGET_PAR_MEMBRE} introductions par membre, pour toutes les méthodes. Moyennes sur {len(graines)} réseaux.", "",
              "Utilité et réciprocité sont mesurées contre la vérité LATENTE (offres réellement valides), que personne ne voit.", "",
              "| Méthode | Intros | Utiles % | Réciproques % | Membres dont un besoin est servi | Ponts % | Nouveauté % | Isolés restants | Nouveaux servis | Vers populaires % | Composantes | ms |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for nom, m in moy.items():
        lignes.append(f"| {nom} | {m['introductions']} | {m['utiles_%']} | {m['reciproques_%']} | {m['membres_avec_besoin_servi']} | "
                      f"{m['ponts_%']} | {m['nouveaute_%']} | {m['isoles_restants']} (sur {m['isoles_avant']}) | {m['nouveaux_servis']} | "
                      f"{m['vers_populaires_%']} | {m['composantes']} | {m['ms']} |")
    lignes += ["", f"Frontière de Pareto (points supportés, 4 objectifs) : {pareto} points selon le réseau "
               f"(médiane {statistics.median(pareto)}).", ""]
    (ICI / "resultats_benchmark_reseau.md").write_text("\n".join(lignes), encoding="utf-8")
    print("\n".join(lignes))
    return {"moyennes": moy, "pareto": pareto}


if __name__ == "__main__":
    main()
