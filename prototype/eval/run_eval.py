"""Évaluation exploratoire : moteur « Le Fil du Club » vs référence mots-clés.

Usage : python -m eval.run_eval            (depuis prototype/)
        python -m eval.run_eval --claude   (analyse par Claude si configurée : coûte des appels API)

Mesures (top 3 affiché à l'utilisateur) :
- succès@3 : au moins un profil attendu dans les 3 premiers (cas non-abstention) ;
- violations : profil interdit (contrainte violée ou faux ami) dans les 3 premiers ;
- abstention correcte : s'abstient quand il faut, et seulement quand il faut ;
- preuves vérifiées : part des justifications retrouvées mot pour mot dans le profil ;
- invariants : aucun visiteur, aucun profil refusant les introductions, jamais.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from app import parser_llm, parser_rules
from app.baseline import rechercher_mots_cles
from app.matching import preuve_valide, rechercher
from app.models import Profil
from app.taxonomy import DATA_DIR, charger_taxonomie

ICI = Path(__file__).resolve().parent


def charger():
    brut = json.loads((DATA_DIR / "profils_demo.json").read_text(encoding="utf-8"))
    profils = [Profil(**p) for p in brut["profils"]]
    par_id = {p.id: p for p in profils}
    return profils, par_id, par_id[brut["utilisateur_demo"]]


JEUX = {"base": "cas.json", "adversarial": "cas_adversariaux.json", "reserve": "cas_reserve.json", "reserve2": "cas_reserve2.json",
        "reserve3": "cas_reserve3.json", "reserve4": "cas_reserve4.json"}


def _critere_ok(attendu: dict, criteres) -> bool:
    return any(c.type == attendu["type"] and c.valeur == attendu["valeur"]
               and ("obligatoire" not in attendu or c.obligatoire == attendu["obligatoire"]) for c in criteres)


def confirmer_simule(besoin, voulus: set, tax):
    """Reproduit le clic du membre dans l'interface (web/js/composants.js, editeurCriteres) :
    il choisit l'option qui correspond à son vrai besoin si elle est proposée, sinon « Aucune ».
    HYPOTHÈSE (borne haute) : le membre reconnaît toujours la bonne compétence ; hors catalogue, il ne choisit rien."""
    from app.models import Critere
    for a in list(besoin.ambiguites):
        choix = next((o for o in a.options if any(tax.meme_famille(o.valeur, v) for v in voulus)), None)
        besoin.ambiguites.remove(a)
        if choix:
            for x in besoin.criteres:
                if x.type == "expertise":
                    x.obligatoire = False
            besoin.criteres = [Critere(type="expertise", valeur=choix.valeur, libelle=choix.libelle, obligatoire=True,
                                       extrait=a.extrait, note="précisé par vous")] + [x for x in besoin.criteres if x.type != "texte_libre"]
            besoin.avertissements = []
    return besoin


def evaluer(claude: bool = False, jeu: str = "base", semantique: bool = False, membre_simule: bool = False) -> dict:
    tax = charger_taxonomie()
    profils, par_id, moi = charger()
    cas = json.loads((ICI / JEUX[jeu]).read_text(encoding="utf-8"))["cas"]
    crit_ok = crit_total = 0
    interdits_globaux = {p.id for p in profils if p.type == "visiteur" or not p.accepte_introductions}
    lignes, agg = [], {"moteur": [], "reference": []}
    latences_analyse, preuves_total, preuves_ok = [], 0, 0
    telemetries: list[dict] = []
    suggestions: list[bool] = []

    for c in cas:
        t0 = time.perf_counter()
        if claude:
            besoin, tele = parser_llm.analyser(c["texte"], tax)
            regles = parser_rules.analyser(c["texte"], tax)
            cle = lambda b: sorted((x.type, x.valeur, x.obligatoire) for x in b.criteres)
            telemetries.append({**tele, "id": c["id"], "accord_regles": cle(besoin) == cle(regles)})
        elif semantique:
            from app.analyse import analyser_hybride
            besoin, _ = analyser_hybride(c["texte"], tax)
        else:
            besoin = parser_rules.analyser(c["texte"], tax)
        latences_analyse.append((time.perf_counter() - t0) * 1000)
        if semantique and not c["abstention"] and besoin.ambiguites and not any(x.type == "expertise" for x in besoin.criteres):
            # mesure de l'aide à la clarification : une compétence des profils attendus figure-t-elle parmi les suggestions ?
            concepts_attendus = {o.concept for pid in c["attendus"] for o in par_id[pid].offre if o.concept}
            options = {o.valeur for a in besoin.ambiguites for o in a.options}
            suggestions.append(bool(options & {x for x in tax.concepts if any(tax.meme_famille(x, y) for y in concepts_attendus)}))
        if membre_simule and besoin.ambiguites:
            voulus = set() if c["abstention"] else {o.concept for pid in c["attendus"] for o in par_id[pid].offre if o.concept}
            besoin = confirmer_simule(besoin, voulus, tax)
        resultats = {
            "moteur": rechercher(besoin, moi, profils, tax),
            "reference": rechercher_mots_cles(besoin, moi, profils, tax),
        }
        for a in c.get("criteres_attendus", []):
            crit_total += 1
            crit_ok += _critere_ok(a, besoin.criteres)
        for a in c.get("criteres_interdits", []):
            crit_total += 1
            crit_ok += not _critere_ok(a, besoin.criteres)
        ligne = {"id": c["id"], "categorie": c["categorie"],
                 "criteres": [f"{x.type}:{x.valeur}{'' if x.obligatoire else '?'}" for x in besoin.criteres]}
        for nom, r in resultats.items():
            top = [s.profil.id for s in r.suggestions[:3]]
            succes = None if c["abstention"] else bool(set(top) & set(c["attendus"]))
            violation = bool(set(top) & (set(c["interdits"]) | interdits_globaux))
            abst_ok = r.abstention == c["abstention"]
            if nom == "moteur":
                for s in r.suggestions + r.pistes_elargies:
                    for pr in s.preuves + ([s.reciprocite] if s.reciprocite else []):
                        preuves_total += 1
                        preuves_ok += preuve_valide(par_id[s.profil.id], pr)
            ligne[nom] = {"top3": top, "succes": succes, "violation": violation, "abstention_ok": abst_ok,
                          "duree_ms": r.duree_ms}
            agg[nom].append(ligne[nom])
        lignes.append(ligne)

    def synthese(rs):
        avec = [r for r in rs if r["succes"] is not None]
        return {
            "succes@3": f"{sum(r['succes'] for r in avec)}/{len(avec)}",
            "violations": f"{sum(r['violation'] for r in rs)}/{len(rs)}",
            "abstention_correcte": f"{sum(r['abstention_ok'] for r in rs)}/{len(rs)}",
        }

    return {
        "analyseur": ("claude" if claude else ("regles+semantique" if semantique else "regles"))
        + (" + membre simulé" if membre_simule else ""),
        "jeu": jeu,
        "nb_cas": len(cas),
        "nb_profils": len(profils),
        "criteres_corrects": f"{crit_ok}/{crit_total}",
        "moteur": synthese(agg["moteur"]),
        "reference": synthese(agg["reference"]),
        "preuves_verifiees": f"{preuves_ok}/{preuves_total}",
        "latence_analyse_ms_mediane": round(statistics.median(latences_analyse), 2),
        "latence_recherche_ms_mediane": round(statistics.median(r["duree_ms"] for r in agg["moteur"]), 2),
        "detail": lignes,
        "telemetrie_claude": telemetries,
        "questions_avec_bonne_suggestion": f"{sum(suggestions)}/{len(suggestions)}",
    }


def en_markdown(res: dict) -> str:
    o = ["# Résultats d'évaluation (exploratoire, données fictives)\n",
         f"Jeu : **{res['jeu']}** · analyseur : **{res['analyseur']}** · {res['nb_cas']} cas · généré par `python -m eval.run_eval --jeu {res['jeu']}`\n",
         (f"Critères extraits conformes (type, valeur, obligatoire/souhaité ; critères interdits absents) : {res['criteres_corrects']}\n"
          if not res['criteres_corrects'].endswith("/0") else ""),
         "| Mesure | Le Fil du Club | Mots-clés + mêmes filtres |", "|---|---|---|"]
    for k in ("succes@3", "violations", "abstention_correcte"):
        o.append(f"| {k} | {res['moteur'][k]} | {res['reference'][k]} |")
    o.append(f"\nPreuves citées retrouvées mot pour mot dans le profil : {res['preuves_verifiees']} "
             "(vrai par construction pour l'extraction par règles ; le garde-fou compte surtout si un LLM rédige un jour les explications).")
    o.append(f"\nLatence médiane : analyse {res['latence_analyse_ms_mediane']} ms, recherche {res['latence_recherche_ms_mediane']} ms "
             f"(machine locale, {res['nb_profils']} profils).\n")
    o.append("| Cas | Catégorie | Critères extraits | Moteur top 3 | ok | Référence top 3 | ok |")
    o.append("|---|---|---|---|---|---|---|")
    for l in res["detail"]:
        def ok(r):
            s = "✓" if (r["succes"] or r["succes"] is None) and not r["violation"] and r["abstention_ok"] else "✗"
            return s + (" (viol.)" if r["violation"] else "")
        o.append(f"| {l['id']} | {l['categorie']} | {', '.join(l['criteres']) or '—'} | "
                 f"{', '.join(l['moteur']['top3']) or 'abstention'} | {ok(l['moteur'])} | "
                 f"{', '.join(l['reference']['top3']) or 'abstention'} | {ok(l['reference'])} |")
    o.append(f"\n**Limites** : cas écrits par l'auteur de la taxonomie (circularité), {res['nb_profils']} profils fictifs, "
             "aucun utilisateur réel. Ces chiffres montrent que le mécanisme fonctionne comme conçu, pas qu'il est utile aux membres.")
    return "\n".join(o) + "\n"


def _num(x: str) -> int:
    return int(x.split("/")[0])


def verifier(reference: Path) -> int:
    """Non-régression (CI) : aucun jeu ne doit perdre un succès, une abstention correcte, ni gagner une violation.
    N'écrit aucun fichier de résultats (pas d'artefact muté par la CI)."""
    ref, echecs = json.loads(reference.read_text(encoding="utf-8")), []
    for jeu, attendu in ref["jeux"].items():
        m = evaluer(claude=False, jeu=jeu, semantique=False)["moteur"]
        for k in ("succes@3", "abstention_correcte"):
            if _num(m[k]) < _num(attendu[k]):
                echecs.append(f"{jeu} : {k} {m[k]} < référence {attendu[k]}")
        if _num(m["violations"]) > _num(attendu["violations"]):
            echecs.append(f"{jeu} : violations {m['violations']} > référence {attendu['violations']}")
        print(f"{jeu:12} succès@3 {m['succes@3']:>6}  violations {m['violations']:>5}  abstention {m['abstention_correcte']:>6}")
    for e in echecs:
        print("RÉGRESSION :", e)
    return 1 if echecs else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--claude", action="store_true", help="analyse par le LLM configuré (HACKVS_LLM=claude|apertus)")
    ap.add_argument("--jeu", choices=list(JEUX) + ["tous"], default="tous")
    ap.add_argument("--semantique", action="store_true", help="analyse hybride : règles + IA sémantique locale calibrée")
    ap.add_argument("--archive", help="étiquette : copie aussi le résultat dans eval/archives/<étiquette>_<jeu>.md")
    ap.add_argument("--membre-simule", action="store_true",
                    help="le membre répond aux questions (borne haute : il reconnaît la bonne compétence si elle est proposée)")
    ap.add_argument("--verifier", action="store_true", help="CI : compare à eval/reference_ci.json, code de sortie 1 si régression")
    a = ap.parse_args()
    if a.verifier:
        raise SystemExit(verifier(ICI / "reference_ci.json"))
    for jeu in (list(JEUX) if a.jeu == "tous" else [a.jeu]):
        res = evaluer(claude=a.claude, jeu=jeu, semantique=a.semantique, membre_simule=a.membre_simule)
        suffixe = ("_claude" if a.claude else ("_semantique" if a.semantique else "")) + ("_membre_simule" if a.membre_simule else "")
        (ICI / f"resultats_{jeu}{suffixe}.md").write_text(en_markdown(res), encoding="utf-8")
        if a.archive:
            (ICI / "archives").mkdir(exist_ok=True)
            (ICI / "archives" / f"{a.archive}_{jeu}{suffixe}.md").write_text(en_markdown(res), encoding="utf-8")
        print(json.dumps({k: v for k, v in res.items() if k != "detail"}, ensure_ascii=False, indent=2))
