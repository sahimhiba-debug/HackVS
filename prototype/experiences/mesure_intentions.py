"""Banc de mesure des intentions scellées sur le Club SYNTHÉTIQUE (150 membres générés, intentions générées).

AUCUNE donnée réelle. Les proportions d'intentions sont des hypothèses de génération, calées sur un seul ordre de
grandeur public : ≈ 1 PME suisse sur 6 cherche un successeur (Dun & Bradstreet, cité par le SECO, 2024).

Usage (depuis prototype/) : python -m experiences.mesure_intentions [--k 3]
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import time
from collections import Counter
from pathlib import Path

from app.models import Profil
from app.taxonomy import charger_taxonomie

from . import psi
from .intentions import Agent, Intention, Relais, compatibilite, generaliser

DATA = Path(__file__).resolve().parent.parent / "data"


def generer(profils: list[Profil], graine: int = 7) -> dict[str, list[Intention]]:
    rng = random.Random(graine)
    secteurs = sorted({s for p in profils for s in p.secteurs})
    res: dict[str, list[Intention]] = {}
    for p in profils:
        r, its = rng.random(), []
        region = "Valais"
        if r < 0.16:                       # ≈ 1 sur 6 : cherche un successeur
            its.append(Intention("ceder", tuple(p.secteurs[:1]), region))
            if rng.random() < 0.4:
                its.append(Intention("chercher_dirigeant", tuple(p.secteurs[:1]), region))
        elif r < 0.22:
            its.append(Intention("reprendre", tuple(rng.sample(secteurs, k=rng.choice([1, 2, 3]))), region))
        elif r < 0.30:
            its.append(Intention("lever_fonds", tuple(p.secteurs[:1]), region))
        elif r < 0.34:
            its.append(Intention("investir", tuple(rng.sample(secteurs, k=rng.choice([2, 3]))), region))
        elif r < 0.37:
            its.append(Intention("devenir_dirigeant", tuple(rng.sample(secteurs, k=2)), region))
        if its:
            res[p.id] = its
    return res


def verite(intents: dict[str, list[Intention]], general) -> set[frozenset]:
    """Référence EN CLAIR (ce qu'un serveur omniscient calculerait) avec les mêmes jetons."""
    paires = set()
    for a, b in itertools.combinations(intents, 2):
        sa = {x for it in intents[a] for x in it.jetons(general)[0]}
        va = {x for it in intents[a] for x in it.jetons(general)[1]}
        sb = {x for it in intents[b] for x in it.jetons(general)[0]}
        vb = {x for it in intents[b] for x in it.jetons(general)[1]}
        if sa & vb and va & sb:
            paires.add(frozenset((a, b)))
    return paires


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--tous", action="store_true", help="tous les membres participent (trafic de couverture) : plus lent")
    a = ap.parse_args()
    tax = charger_taxonomie()
    profils = [Profil(**p) for p in json.loads((DATA / "profils_synthetiques.json").read_text(encoding="utf-8"))["profils"]]
    intents = generer(profils)
    annuaire = Counter(s for p in profils for s in p.secteurs)          # information PUBLIQUE du Club
    parents = {c: tax.concepts[c].parent for c in tax.concepts}
    precis = lambda s: s
    gen = lambda s: generaliser(s, annuaire, parents, a.k)

    n_int = sum(len(v) for v in intents.values())
    rares = sum(1 for v in intents.values() for it in v for s in it.secteurs if gen(s) != s)
    tot_sect = sum(len(it.secteurs) for v in intents.values() for it in v)
    ref_precis, ref_gen = verite(intents, precis), verite(intents, gen)

    participants = [p.id for p in profils] if a.tous else sorted(intents)
    agents = {pid: Agent(pid, intents.get(pid, []), general=gen) for pid in participants}
    relais = Relais()
    t0 = time.perf_counter()
    trouves = set()
    for x, y in itertools.combinations(participants, 2):
        if compatibilite(agents[x], agents[y], relais):
            trouves.add(frozenset((x, y)))
    duree = time.perf_counter() - t0

    # ATTAQUE 1 — Club curieux, dictionnaire COMPLET : il hache tous les jetons possibles et les cherche dans ce qu'il a vu.
    from .intentions import COMPLEMENTS
    roles = {r for pair in COMPLEMENTS.values() for r in pair}
    secteurs_possibles = set(tax.concepts) | {"*"}
    dico = {psi.hacher(f"{r}|{s}|Valais").hex() for r in roles for s in secteurs_possibles}
    vus = [j for (_, _, charge) in relais.vus for j in charge]
    succes_dico = sum(1 for j in vus if j in dico)
    # ATTAQUE 2 — relier des sessions : un même point revu deux fois permettrait de suivre une intention d'une session à l'autre.
    repetes = sum(n - 1 for n in Counter(vus).values() if n > 1)
    # RÉFÉRENCE : notre Bourse anonyme actuelle publie « Un membre du Club · secteur · zone ». Combien d'auteurs
    # d'intentions de cession y seraient ré-identifiables (secteur partagé par moins de k membres dans l'annuaire) ?
    cedants = [(pid, it) for pid, v in intents.items() for it in v if it.type == "ceder"]
    reidentifiables = sum(1 for _, it in cedants if annuaire.get(it.secteurs[0], 0) < a.k)
    vp = len(trouves & ref_gen)
    print(json.dumps({
        "donnees": "SYNTHÉTIQUES (profils et intentions générés)",
        "moteur_crypto": psi.MOTEUR,
        "membres": len(profils), "membres_avec_intention": len(intents), "intentions": n_int,
        "repartition": dict(Counter(it.type for v in intents.values() for it in v)),
        "k_anonymat": a.k, "secteurs_generalises": f"{rares}/{tot_sect}",
        "paires_compatibles_reference_precise": len(ref_precis),
        "paires_compatibles_reference_k_anonyme": len(ref_gen),
        "paires_trouvees_par_psi": len(trouves),
        "precision_vs_reference_meme_jetons": round(vp / len(trouves), 3) if trouves else None,
        "rappel_vs_reference_meme_jetons": round(vp / len(ref_gen), 3) if ref_gen else None,
        "compatibilites_a_affiner_a_l_etape_2": len(ref_gen - ref_precis),
        "points_vus_par_le_club": len(vus),
        "attaque_dictionnaire_complet_succes": f"{succes_dico}/{len(vus)} (dictionnaire de {len(dico)} jetons)",
        "points_identiques_entre_sessions": repetes,
        "bourse_anonyme_actuelle_cedants_reidentifiables": f"{reidentifiables}/{len(cedants)} (secteur < {a.k} membres)",
        "intentions_scellees_jetons_sous_k": 0,
        "sessions_psi": len(relais.vus) // 3, "octets_transportes": relais.octets,
        "duree_s": round(duree, 2), "participants": len(participants),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
