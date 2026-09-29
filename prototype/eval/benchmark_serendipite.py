"""EXP-G — Sérendipité structurelle : similarité de profil contre complémentarité prouvée (profils FICTIFS de démo).

Pour chaque membre (qui accepte les introductions), on compare :
- SIMILARITÉ : les k membres dont le texte de profil est le plus proche (TF-IDF, cosinus) — baseline « networking » ;
- COMPLÉMENTARITÉ (nous) : les membres dont l'offre couvre une recherche PROUVÉE (moteur existant, calculer_aides).
Mesures : part des paires entre familles de secteur différentes ; part des paires où une aide est prouvée (dans un sens
au moins) ; nombre de membres pour qui chaque méthode propose quelqu'un.

    python -m eval.benchmark_serendipite [--k 3] [--sortie eval/resultats_serendipite.md]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.matching import _Tfidf, meme_organisation, texte_profil
from app.models import Profil
from app.soiree import calculer_aides
from app.taxonomy import DATA_DIR, charger_taxonomie

TAX = charger_taxonomie()


def membres() -> list[Profil]:
    brut = json.loads((DATA_DIR / "profils_demo.json").read_text(encoding="utf-8"))["profils"]
    return [p for p in (Profil(**d) for d in brut) if p.type == "membre_club" and p.accepte_introductions]


def inter_secteur(a: Profil, b: Profil) -> bool:
    return not any(TAX.meme_famille(x, y) for x in a.secteurs for y in b.secteurs)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    ps = membres()
    par = {p.id: p for p in ps}
    tf = _Tfidf({p.id: texte_profil(p) for p in ps})
    aides = calculer_aides(ps, [], TAX)
    prouvees = {frozenset(k) for k in aides}
    sim_paires, comp_paires = set(), set()
    servis_sim, servis_comp = 0, 0
    for p in ps:
        autres = [q for q in ps if q.id != p.id and not meme_organisation(p, q)]
        top = sorted(autres, key=lambda q: (-tf.sim(texte_profil(p), q.id), q.id))[:a.k]
        sim_paires |= {frozenset((p.id, q.id)) for q in top}
        servis_sim += bool(top)
        mes = sorted({j for (i, j) in aides if i == p.id})[:a.k]
        comp_paires |= {frozenset((p.id, j)) for j in mes}
        servis_comp += bool(mes)

    def stats(paires: set) -> tuple[float, float, int]:
        l_ = [tuple(x) for x in paires]
        return (sum(inter_secteur(par[x], par[y]) for x, y in l_) / len(l_),
                sum(frozenset((x, y)) in prouvees for x, y in l_) / len(l_), len(l_))

    s, c = stats(sim_paires), stats(comp_paires)
    commun = len(sim_paires & comp_paires)
    lignes = ["# Sérendipité structurelle — similarité contre complémentarité prouvée (profils FICTIFS)", "",
              f"{len(ps)} membres acceptant les introductions ; top {a.k} par membre.", "",
              "| Méthode | Paires | Secteurs différents | Aide prouvée | Membres à qui l'on propose quelqu'un |", "|---|---|---|---|---|",
              f"| SIMILARITÉ (TF-IDF) | {s[2]} | {s[0]:.0%} | {s[1]:.0%} | {servis_sim}/{len(ps)} |",
              f"| COMPLÉMENTARITÉ PROUVÉE (nous) | {c[2]} | {c[0]:.0%} | {c[1]:.0%} | {servis_comp}/{len(ps)} |", "",
              f"Paires proposées par les deux méthodes : {commun}.",
              "Lecture : la similarité propose quelqu'un à chaque membre mais rarement une aide prouvée ; la "
              "complémentarité s'abstient pour qui n'a pas de besoin couvert. La part « secteurs différents » ne distingue "
              "PAS les deux méthodes sur ces profils (hypothèse EXP-G réfutée)."]
    texte = "\n".join(lignes) + "\n"
    print(texte)
    if a.sortie:
        Path(a.sortie).write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
