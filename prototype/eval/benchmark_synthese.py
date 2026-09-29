"""G2 — Synthèse du diagnostic : GABARIT (code) contre IA SEULE contre HYBRIDE (IA + contrôle de fidélité).

- GABARIT   : texte produit par du code depuis le diagnostic structuré (exécuté).
- IA_SEULE  : le LLM reçoit les FAITS BRUTS (relations datées, membres) et écrit lui-même le diagnostic.
- HYBRIDE   : le LLM reçoit NOTRE diagnostic structuré et le met en mots ; `synthese.retenir` ne le montre que s'il
              est fidèle (sinon gabarit).
Mesures automatiques : fidélité (nombres, dates, identifiants, nombres en lettres, négation d'un phénomène détecté),
couverture des phénomènes, longueur. La LISIBILITÉ exige un jugement humain : non mesurée ici (dit).

    HACKVS_LLM=claude python -m eval.benchmark_synthese [--reseaux 5] [--sortie eval/resultats_benchmark_synthese.md]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
from pathlib import Path

from adaptateurs.club import cycle as cy
from adaptateurs.club import diagnostic as dg
from adaptateurs.club import synthese as sy
from app import parser_llm
from app.taxonomy import charger_taxonomie
from eval.perf_echelle import generer
from plateforme.memoire import graphe

TAX = charger_taxonomie()
CONSIGNE = ("Tu écris pour l'animateur d'un club d'affaires un diagnostic de son réseau en 8 lignes maximum, en français "
            "simple. Écris TOUS les nombres en chiffres. N'invente aucun fait, aucun nombre, aucun nom : n'utilise que les "
            "données fournies. Termine par les actions possibles, et dis clairement si aucune action n'est fondée.")


def _llm(client=None, apertus_http=None):
    if client is None and parser_llm.fournisseur() == "apertus":
        return lambda donnees: parser_llm.completer_apertus(
            CONSIGNE, json.dumps(donnees, ensure_ascii=False, default=str), None, apertus_http)
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    modele = os.environ.get("HACKVS_CLAUDE_MODEL", parser_llm.MODELE_PAR_DEFAUT)

    def ecrire(donnees: dict) -> str:
        r = client.messages.create(model=modele, max_tokens=1200, system=CONSIGNE,
                                   messages=[{"role": "user", "content": json.dumps(donnees, ensure_ascii=False, default=str)}])
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    return ecrire


def faits_bruts(m, t, membres) -> dict:
    g = graphe(m, t)
    return {"aujourd_hui": t.isoformat(), "membres": membres,
            "relations": [{"a": a, "b": b, "derniere_interaction": d["derniere"].isoformat()} for a, b, d in g.edges(data=True)],
            "regle": "une relation sans interaction depuis plus de 90 jours n'est plus actuelle"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reseaux", type=int, default=5)
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    dispo = parser_llm.llm_configure()
    ecrire = _llm() if dispo else None
    mesures: dict[str, list] = {"GABARIT": [], "IA_SEULE": [], "HYBRIDE": []}
    for s in range(a.reseaux):
        p, m, t = generer(120, 1500 + s)
        ids = {x.id for x in p}
        membres = sorted(x.id for x in p if x.type == "membre_club")
        d = dg.diagnostic(m, p, cy.besoins_publies(m, t), TAX, t)
        textes = {"GABARIT": sy.gabarit(d)}
        if ecrire:
            textes["IA_SEULE"] = ecrire(faits_bruts(m, t, membres))
            textes["HYBRIDE"] = ecrire({k: d[k] for k in ("comprendre", "diagnostiquer", "voir_venir")} | {"plans": d["agir"]["plans_nommes"]})
        for bras, texte in textes.items():
            v = sy.verifier(texte, d, ids)
            mesures[bras].append({"fidele": v["fidele"], "couverture": v["couverture"], "mots": len(texte.split()),
                                  "inventes": len(v["nombres_inventes"]) + len(v["identifiants_inventes"]),
                                  "contradictions": len(v["contradictions"])})
    lignes = ["# G2 — Synthèse du diagnostic : gabarit, IA seule, hybride contrôlé", "",
              f"{a.reseaux} réseaux GÉNÉRÉS de 120 membres. Contrôle automatique : `adaptateurs/club/synthese.verifier`.", "",
              "| Bras | Textes fidèles | Nombres/identifiants inventés | Contradictions | Couverture moyenne | Mots (moyenne) |",
              "|---|---|---|---|---|---|"]
    for bras, v in mesures.items():
        if not v:
            lignes.append(f"| {bras} | NON EXÉCUTÉ | — | — | — | — |")
            continue
        cov = statistics.mean(int(x["couverture"].split("/")[0]) / max(1, int(x["couverture"].split("/")[1])) for x in v)
        lignes.append(f"| {bras} | {sum(x['fidele'] for x in v)}/{len(v)} | {sum(x['inventes'] for x in v)} | "
                      f"{sum(x['contradictions'] for x in v)} | {cov:.0%} | {statistics.mean(x['mots'] for x in v):.0f} |")
    if not dispo:
        lignes += ["", "Aucun modèle génératif configuré : bras IA non exécutés, aucun chiffre donné pour eux."]
    lignes += ["", "La lisibilité (le vrai apport attendu de l'IA) n'est PAS mesurée automatiquement."]
    texte = "\n".join(lignes) + "\n"
    print(texte)
    if a.sortie:
        Path(a.sortie).write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
