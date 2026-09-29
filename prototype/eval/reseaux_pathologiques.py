"""Générateur de réseaux PATHOLOGIQUES (vérité connue) et benchmark de l'observatoire (données GÉNÉRÉES).

Un réseau « sain » de référence, puis une pathologie injectée à la fois. Question : l'observatoire nomme-t-il la
pathologie injectée, et seulement elle ? Baseline : les indicateurs globaux d'un tableau de bord classique (membres,
relations, densité, degré moyen) — détectent-ils seulement qu'il se passe quelque chose ?
Les seuils de l'observatoire ont été fixés AVANT la première exécution (adaptateurs/club/sante.py) ; le générateur est
le nôtre : risque de circularité déclaré, d'où la mesure de la frontière de détection (intensité variable).

    python -m eval.reseaux_pathologiques [--graines 20] [--sortie eval/resultats_observatoire.md]
"""
from __future__ import annotations

import argparse
import random
import statistics
from datetime import date, timedelta
from pathlib import Path

import networkx as nx

from adaptateurs.club.sante import phenomenes

T = date(2026, 10, 1)
SECTEURS = ["agro", "construction", "services", "tourisme"]


def sain(graine: int, n: int = 60) -> dict:
    rnd = random.Random(graine)
    membres = [f"m{i:02d}" for i in range(n)]
    secteurs = {m: SECTEURS[i % 4] for i, m in enumerate(membres)}
    g = nx.Graph()
    g.add_nodes_from(membres)
    for m in membres:                       # ~4 relations actuelles par membre, 40 % dans le même secteur
        for _ in range(2):
            meme = rnd.random() < 0.4
            autres = [x for x in membres if x != m and (secteurs[x] == secteurs[m]) == meme]
            g.add_edge(m, rnd.choice(autres), derniere=T - timedelta(days=rnd.randint(0, 80)))
    hist = g.copy()
    for _ in range(n // 3):                 # quelques relations passées (non actuelles)
        a, b = rnd.sample(membres, 2)
        if not hist.has_edge(a, b):
            hist.add_edge(a, b, derniere=T - timedelta(days=rnd.randint(120, 400)))
    return {"membres": membres, "secteurs": secteurs, "g_act": g, "g_hist": hist,
            "sollicitations": {m: rnd.randint(0, 3) for m in membres}, "attendu": set()}


def _reconstruire(r: dict, aretes: list[tuple[str, str]], rnd: random.Random) -> None:
    g = nx.Graph()
    g.add_nodes_from(r["membres"])
    for a, b in aretes:
        if a != b:
            g.add_edge(a, b, derniere=T - timedelta(days=rnd.randint(0, 80)))
    r["g_act"] = g
    # l'historique = le nouveau réseau + les relations passées d'origine (celles qui n'étaient PAS actuelles) :
    # garder les anciennes relations actuelles ferait paraître le réseau « vieilli » (artefact du générateur, corrigé)
    passees = [(a, b, d) for a, b, d in r["g_hist"].edges(data=True) if not r["g_act_origine"].has_edge(a, b)]
    r["g_hist"] = g.copy()
    r["g_hist"].add_edges_from(passees)


def pathologique(nom: str, graine: int, intensite: float = 1.0) -> dict:
    rnd = random.Random(1000 + graine)
    r = sain(graine)
    m, g = r["membres"], r["g_act"]
    r["g_act_origine"] = g.copy()
    if nom == "ISOLES":
        for x in rnd.sample(m, round(10 * intensite)):
            g.remove_edges_from(list(g.edges(x)))
        r["attendu"] = {"ISOLEMENT"}
    elif nom == "HUB":                     # une personne relie tout le monde ; le reste est clairsemé
        hub = m[0]
        base = rnd.sample([e for e in g.edges() if hub not in e], 15)
        _reconstruire(r, base + [(hub, x) for x in m[1:]], rnd)
        r["attendu"] = {"CONCENTRATION"}
    elif nom == "FAUSSE_DIVERSITE":        # large en apparence, porté par 3 personnes
        hubs, reste = m[:3], m[3:]
        base = rnd.sample([e for e in g.edges() if not set(e) & set(hubs)], 12)
        _reconstruire(r, base + [(hubs[i % 3], x) for i, x in enumerate(reste)] + [(hubs[0], hubs[1]), (hubs[1], hubs[2])], rnd)
        r["attendu"] = {"CONCENTRATION"}
    elif nom == "SILOS":                   # trois communautés sans relation entre elles
        comm = {x: i % 3 for i, x in enumerate(m)}
        _reconstruire(r, [(a, b) for a, b in g.edges() if comm[a] == comm[b]]
                      + [(x, rnd.choice([y for y in m if comm[y] == comm[x] and y != x])) for x in m], rnd)
        r["attendu"] = {"FRAGMENTATION"}
    elif nom == "PONT_FRAGILE":            # deux communautés reliées par UNE relation
        comm = {x: i % 2 for i, x in enumerate(m)}
        intra = [(a, b) for a, b in g.edges() if comm[a] == comm[b]] + [(x, rnd.choice([y for y in m if comm[y] == comm[x] and y != x])) for x in m]
        _reconstruire(r, intra + [(m[0], m[1])], rnd)
        r["attendu"] = {"PONT_FRAGILE"}
    elif nom == "PASSAGE_UNIQUE":          # deux communautés reliées par UNE personne (2 relations de chaque côté)
        comm = {x: i % 2 for i, x in enumerate(m[1:])}
        intra = [(a, b) for a, b in g.edges() if a != m[0] and b != m[0] and comm[a] == comm[b]]
        intra += [(x, rnd.choice([y for y in m[1:] if comm[y] == comm[x] and y != x])) for x in m[1:]]
        pont = [(m[0], y) for c in (0, 1) for y in rnd.sample([z for z in m[1:] if comm[z] == c], 2)]
        _reconstruire(r, intra + pont, rnd)
        r["attendu"] = {"PASSAGE_UNIQUE"}
    elif nom == "VIEILLISSEMENT":          # beaucoup d'historique, peu d'actuel
        garder = rnd.sample(list(g.edges()), round(len(g.edges()) * (1 - 0.7 * intensite)))
        for a, b in list(g.edges()):
            if (a, b) not in garder:
                g.remove_edge(a, b)
                r["g_hist"].add_edge(a, b, derniere=T - timedelta(days=200))
        r["attendu"] = {"VIEILLISSEMENT"}
    elif nom == "SUR_SOLLICITATION":
        for x in rnd.sample(m, 3):
            r["sollicitations"][x] = 6 + round(4 * intensite)
        r["attendu"] = {"SUR_SOLLICITATION"}
    elif nom == "ENTRE_SOI":               # uniquement des relations dans le même secteur (donc aussi 4 groupes)
        _reconstruire(r, [(a, b) for a, b in g.edges() if r["secteurs"][a] == r["secteurs"][b]]
                      + [(x, rnd.choice([y for y in m if r["secteurs"][y] == r["secteurs"][x] and y != x])) for x in m], rnd)
        r["attendu"] = {"ENTRE_SOI", "FRAGMENTATION"}
    return r


def verite_independante(r: dict) -> set[str]:
    """Phénomènes RÉELLEMENT présents dans le réseau généré, recalculés sans sante.py (définitions minimales écrites à part)."""
    g, m = r["g_act"].subgraph(r["membres"]).copy(), r["membres"]
    g.add_nodes_from(m)
    e, vrai = g.number_of_edges(), set()
    if e < 6:
        return vrai
    iso = sum(1 for x in m if g.degree(x) == 0)
    if iso >= 3 or iso / len(m) > 0.10:
        vrai.add("ISOLEMENT")
    top = sorted(m, key=lambda x: -g.degree(x))[:3]
    if sum(1 for a, b in g.edges() if a in top or b in top) / e > 0.5:
        vrai.add("CONCENTRATION")
    if sum(1 for c in nx.connected_components(g) if len(c) >= 3) >= 2:
        vrai.add("FRAGMENTATION")
    for a, b in nx.bridges(g):
        h = g.copy()
        h.remove_edge(a, b)
        if min(len(nx.node_connected_component(h, a)), len(nx.node_connected_component(h, b))) >= 3:
            vrai.add("PONT_FRAGILE")
            break
    ext = {x for a, b in nx.bridges(g) for x in (a, b)
           if min(len(nx.node_connected_component(nx.restricted_view(g, [], [(a, b)]), y)) for y in (a, b)) >= 3}
    for x in nx.articulation_points(g):
        if x not in ext and sum(1 for c in nx.connected_components(nx.restricted_view(g, [x], [])) if len(c) >= 3) >= 2:
            vrai.add("PASSAGE_UNIQUE")
    hist = r["g_hist"].subgraph(m).number_of_edges()
    if hist and 1 - e / hist > 0.5:
        vrai.add("VIEILLISSEMENT")
    if any(c > 5 for c in r["sollicitations"].values()):
        vrai.add("SUR_SOLLICITATION")
    if sum(1 for a, b in g.edges() if r["secteurs"][a] == r["secteurs"][b]) / e > 0.8:
        vrai.add("ENTRE_SOI")
    return vrai


PATHOLOGIES = ["ISOLES", "HUB", "FAUSSE_DIVERSITE", "SILOS", "PONT_FRAGILE", "PASSAGE_UNIQUE", "VIEILLISSEMENT", "SUR_SOLLICITATION", "ENTRE_SOI"]


def observer(r: dict) -> set[str]:
    return {p["phenomene"] for p in phenomenes(r["g_hist"], r["g_act"], r["membres"], r["secteurs"], r["sollicitations"])["phenomenes"]}


def kpi(r: dict) -> dict:
    g = r["g_act"]
    return {"relations": g.number_of_edges(), "densite": nx.density(g), "degre_moyen": 2 * g.number_of_edges() / len(r["membres"])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graines", type=int, default=20)
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    graines = range(a.graines)
    sains = [sain(g) for g in graines]
    fp_sain = [observer(r) for r in sains]
    ref = {k: (statistics.mean(kpi(r)[k] for r in sains), statistics.pstdev(kpi(r)[k] for r in sains)) for k in ("relations", "densite", "degre_moyen")}

    def kpi_alerte(r: dict) -> bool:        # baseline : un indicateur global à plus de 2 écarts-types de la référence saine
        return any(abs(kpi(r)[k] - mu) > 2 * max(sd, 1e-9) for k, (mu, sd) in ref.items())

    lignes = ["# Observatoire du réseau — benchmark sur réseaux PATHOLOGIQUES générés (SYNTHETIC)", "",
              f"{a.graines} graines par cas ; 60 membres ; seuils fixés avant la première exécution.", "",
              "| Cas | Phénomènes attendus | Exact (nommé, rien d'autre) | Attendu manqué | Fausse alerte en plus "
              "| Baseline KPI : « quelque chose d'anormal » |",
              "|---|---|---|---|---|---|",
              f"| SAIN | — | {sum(not o for o in fp_sain)}/{a.graines} | — | {sum(bool(o) for o in fp_sain)}/{a.graines} "
              f"({sorted(set().union(*fp_sain)) or '—'}) | {sum(kpi_alerte(r) for r in sains)}/{a.graines} |"]
    faux_pos_total, faux_neg_total = [0], [0]
    for p in PATHOLOGIES:
        rs = [pathologique(p, g) for g in graines]
        obs = [observer(r) for r in rs]
        exact = sum(o == r["attendu"] for o, r in zip(obs, rs, strict=True))
        manque = sum(bool(r["attendu"] - o) for o, r in zip(obs, rs, strict=True))
        extra = [o - r["attendu"] for o, r in zip(obs, rs, strict=True)]
        faux = [o - verite_independante(r) for o, r in zip(obs, rs, strict=True)]   # alerte sans phénomène réel
        rates = [verite_independante(r) - o for o, r in zip(obs, rs, strict=True)]  # phénomène réel non signalé
        faux_pos_total[0] += sum(len(x) for x in faux)
        faux_neg_total[0] += sum(len(x) for x in rates)
        lignes.append(f"| {p} | {', '.join(sorted(rs[0]['attendu']))} | {exact}/{a.graines} | {manque}/{a.graines} | "
                      f"{sum(bool(x) for x in extra)}/{a.graines} ({sorted(set().union(*extra)) or '—'}) | "
                      f"{sum(kpi_alerte(r) for r in rs)}/{a.graines} |")
    lignes += ["", f"Contre la vérité INDÉPENDANTE (phénomènes réellement présents, recalculés sans l'observatoire) : "
               f"{faux_pos_total[0]} alerte(s) sans phénomène réel, {faux_neg_total[0]} phénomène(s) réel(s) non signalé(s). "
               "Les « fausses alertes en plus » de la table sont donc des phénomènes CO-PRÉSENTS (ex. un réseau vieilli est "
               "aussi fragmenté), pas des erreurs."]
    lignes += ["", "## Frontière de détection (intensité variable, 20 graines)", "", "| Pathologie | Intensité | Détectée |", "|---|---|---|"]
    for p, attendu in (("ISOLES", "ISOLEMENT"), ("VIEILLISSEMENT", "VIEILLISSEMENT")):
        for i in (0.3, 0.6, 1.0):
            d = sum(attendu in observer(pathologique(p, g, i)) for g in graines)
            lignes.append(f"| {p} | {i} | {d}/{a.graines} |")
    lignes += ["", "Lecture : la baseline KPI dit au mieux « quelque chose a changé » ; elle ne nomme jamais le phénomène ni "
               "l'intervention. Seuils et générateur sont les nôtres (circularité possible, déclarée)."]
    texte = "\n".join(lignes) + "\n"
    print(texte)
    if a.sortie:
        Path(a.sortie).write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
