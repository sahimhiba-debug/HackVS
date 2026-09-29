"""SYNTHETIC BENCHMARK de Club Pulse — ce que le moteur fait sur des clubs GÉNÉRÉS dont on connaît la vérité.

    python -m eval.benchmark_pulse                 # résultats déterministes → eval/resultats_benchmark_pulse.{md,json}
    python -m eval.benchmark_pulse --performance   # + temps d'analyse 150 → 5000 membres → eval/performance_pulse.md

Quatre questions, chacune avec une référence qui peut PERDRE :
1. DÉTECTION — les vraies situations plantées sont-elles trouvées ? Les pièges (concurrent, refus d'introduction,
   profil obsolète, même organisation, aucune langue commune, introduction déclinée, indisponible, déjà en relation,
   simple ressemblance) sont-ils évités ? Comparé à deux références naïves : l'appariement par capacité (tout besoin ×
   tout offreur de la capacité) et la ressemblance (profils qui offrent la même chose).
2. REPLANIFICATION — après un refus, l'alternative proposée est-elle éligible (JUSTE) et en propose-t-on une chaque
   fois qu'il en existe (COMPLÈTE) ? Oracle : les règles dures réappliquées par force brute à TOUS les membres
   (réécrites ici, pas appelées dans le moteur ; seule l'observation — qui offre quoi, âges, relations — est partagée).
3. CONFIDENTIALITÉ — identités dans ce que voit le moteur ; nom d'une personne qui a décliné ou texte d'une note
   privée dans les écrans d'un AUTRE membre (démonstration complète, 150 membres, chaque écran).
4. MÉMOIRE — la situation plantée « déjà résolue dans le Club » est-elle retrouvée ?

Limites déclarées : données SYNTHÉTIQUES ; générateur et détecteur partagent la taxonomie (on mesure le respect des
règles et la robustesse aux pièges, PAS la pertinence humaine ni un impact) ; la précision sur le FOND n'est pas
mesurable (aucune vérité terrain pour les situations non plantées). Aucun modèle de langage n'est appelé.
"""
from __future__ import annotations

import json
import platform
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from app.matching import organisation
from app.taxonomy import charger_taxonomie
from intelligence.activation import BUDGET_ATTENTION, Moteur
from intelligence.club_synthetique import generer
from intelligence.demo import NOTE_SOPHIE, Demo
from intelligence.detection import Detecteur, scanner
from intelligence.identite import AdhesionsSynthetiques, Coffre
from intelligence.observateur import PROFIL_OBSOLETE_JOURS
from intelligence.politique import Spectateur

ICI = Path(__file__).resolve().parent
TAX = charger_taxonomie()
GRAINES = range(1, 11)
TAILLES = (150, 500)
K_ACTIVATIONS = 12                     # refus provoqués par club généré


def _membres(o) -> frozenset:
    return frozenset(r.membre for r in o.roles)


# ---------------------------------------------------------------------- 1. détection
def _references(r) -> dict[str, set[frozenset]]:
    """Deux références naïves (ce que ferait un annuaire intelligent sans règles) : paires proposées."""
    offreurs = defaultdict(set)
    for p in r.profils:
        for o in p.offre:
            if o.concept:
                offreurs[o.concept].add(p.id)
    capacite, ressemblance = set(), set()
    demandes = [(b.auteur, c.valeur) for b in r.besoins for c in b.besoin.criteres if c.type == "expertise"]
    demandes += [(p.id, x.concept) for p in r.profils for x in p.recherche if x.concept]
    for auteur, c in demandes:
        capacite |= {frozenset((auteur, q)) for q in offreurs.get(c, ()) if q != auteur}
    for ids in offreurs.values():
        ids_ = sorted(ids)
        if len(ids_) <= 40:                                                 # les capacités de fond sont trop larges pour être « ressemblance »
            ressemblance |= {frozenset((a, b)) for i, a in enumerate(ids_) for b in ids_[i + 1:]}
    return {"appariement par capacité": capacite, "ressemblance de profils": ressemblance}


def detection(n: int, graine: int) -> dict:
    r, v = generer(n, graine)
    ops = scanner(r, TAX)["opportunites"]
    trouvees = Counter()
    for t in v["vraies"]:
        ok = any(t["type"] in (o.type, *o.mecanismes) and set(t["membres"]) <= _membres(o) and set(t["concepts"]) <= set(o.capacites)
                 for o in ops)
        trouvees[(t["type"], ok)] += 1
    refs = _references(r)
    pieges = []
    for t in v["pieges"]:
        cible = frozenset(t["membres"])
        pieges.append({"type": t["type"], "moteur": any(cible <= _membres(o) for o in ops),
                       **{nom: cible in paires for nom, paires in refs.items()}})
    return {"trouvees": trouvees, "pieges": pieges, "opportunites": len(ops)}


# ---------------------------------------------------------------------- 2. replanification
def _oracle(r, mo: Moteur, benef, concept: str, hors: set[str], ouvertes: dict[str, int]) -> set[str]:
    """Règles dures réécrites (pas d'appel au moteur de décision) sur TOUS les membres. `ouvertes` : sollicitations en
    cours AU MOMENT du refus (après, l'alternative choisie compte une sollicitation de plus)."""
    e = Detecteur(r, TAX).e                                                 # observation seulement : offreurs, âges, relations
    org_b = organisation(benef)
    res = set()
    for p in r.profils:
        if p.id in hors or p.id == benef.id or p.id in mo.exclus:
            continue
        if not any(pid == p.id for pid, _, _ in e.offreurs.get(concept, [])):
            continue
        age = e.age_profil(p)
        paire = frozenset((benef.id, p.id))
        if (organisation(p) and organisation(p) == org_b) or not p.accepte_introductions or not p.disponible \
                or age is None or age > PROFIL_OBSOLETE_JOURS or not set(p.langues) & set(benef.langues) \
                or paire in e.declinees or paire in e.relies or ouvertes.get(p.id, 0) >= BUDGET_ATTENTION:
            continue
        res.add(p.id)
    return res


def replanification(n: int, graine: int) -> list[dict]:
    r, _ = generer(n, graine, plantes=True)
    le: date = r.aujourd_hui
    mo = Moteur(r, TAX)
    cas = []
    for o in scanner(r, TAX)["opportunites"]:
        if len(cas) >= K_ACTIVATIONS or not o.beneficiaire or o.type in ("CONVERGENCE", "LACUNE"):
            continue
        aid = mo.creer(o, le)
        plan = mo.plan(aid)
        etape = next((e for e in plan["etapes"] if e["type"] == "contribution" and e.get("concept")), None)
        if etape is None or mo.ouvertes().get(o.beneficiaire, 0) >= BUDGET_ATTENTION:
            continue
        try:
            mo.lancer(aid, le)
            mo.repondre(aid, le, o.beneficiaire, True)
        except Exception as e:                                              # refus métier (budget) : cas non comptés
            if type(e).__name__ in ("Conflit", "Interdit", "Invalide", "Limite"):
                continue
            raise
        refuseur = etape["membre"]
        if (etape["id"], refuseur) not in mo._sollicitations(aid):
            continue
        benef = r.par_id()[o.beneficiaire]
        dans_plan = {x["membre"] for x in plan["etapes"] if x.get("membre")}
        ouvertes = mo.ouvertes()
        ouvertes[refuseur] = ouvertes.get(refuseur, 1) - 1                  # son refus libère sa place (il reste exclu)
        oracle = _oracle(r, mo, benef, etape["concept"], dans_plan | {refuseur}, ouvertes)
        mo.repondre(aid, le, refuseur, False)
        j = mo.journal(aid)
        alt = next((t["details"].get("alternative") for t in reversed(j) if t["etat"] == "ALTERNATIVE_PROPOSEE"), None)
        final = "ALTERNATIVE_PROPOSEE" if alt else ("ABANDONNEE" if mo.etat(aid) == "ABANDONNEE" else mo.etat(aid))
        refus_seq = mo._reponses(aid)[(etape["id"], refuseur)].seq
        relance = any(ev.acteurs[0] == refuseur and ev.donnees["aid"] == aid and ev.seq > refus_seq
                      for ev in r.memoire.evenements("SOLLICITATION_PRIVEE"))
        cas.append({"oracle": len(oracle), "resultat": final, "juste": alt is None or alt in oracle, "relance_du_refus": relance})
    return cas


# ---------------------------------------------------------------------- 3. confidentialité
def confidentialite_moteur(n: int, graine: int) -> dict:
    r, _ = generer(n, graine)
    imp = AdhesionsSynthetiques(r.profils).importer()
    coffre = Coffre(imp, secret=b"graine-du-banc-synthetique-32-octets")
    vus = json.dumps([coffre.pseudonymiser(p).model_dump(mode="json") for p in r.profils], ensure_ascii=False)
    fuites = 0
    for p in r.profils:
        per = coffre.identite(p.id)
        fuites += sum(1 for x in (per.nom if per else "", per.courriel if per else "", p.entreprise or "") if x and x in vus)
    return {"profils": len(r.profils), "identites_verifiees": 3 * len(r.profils), "fuites": fuites}


def confidentialite_ecrans() -> dict:
    d = Demo(TAX)
    d.rejouer(len(Demo.ETAPES))
    c = d.club
    refus = [(ev.donnees["aid"], ev.acteurs[0]) for ev in c.r.memoire.evenements("REPONSE") if not ev.donnees["accepte"]]
    decliners = {m for _, m in refus}
    auteurs_notes = set(c.notes)
    ecrans, fuites = 0, []
    for pid in sorted(c.coffre._personnes):
        sp = Spectateur("membre", pid)
        vues = [c.vues.pouls_membre(pid), c.vues.activations_de(pid), c.vues.demandes_pour(pid), c.vues.memoire_club(sp),
                c.vues.evenements_de(pid)]
        vues += [c.vues.vue_activation(a["id"], sp) for a in c.vues.activations_de(pid)]
        ecrans += len(vues)
        texte = json.dumps(vues, ensure_ascii=False)
        for m in decliners - {pid}:
            per = c.coffre.identite(m)
            if per and per.nom in texte:
                fuites.append(("nom d'une personne qui a décliné", pid))
        if pid not in auteurs_notes and NOTE_SOPHIE[:40] in texte:
            fuites.append(("note privée d'un autre membre", pid))
    return {"membres": len(c.coffre._personnes), "ecrans": ecrans, "refus_dans_la_demo": len(refus), "fuites": fuites}


# ---------------------------------------------------------------------- exécution et rapport
def executer() -> dict:
    det = [(n, g, detection(n, g)) for n in TAILLES for g in GRAINES]
    par_type: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for _, _, d in det:
        for (typ, ok), k in d["trouvees"].items():
            par_type[typ][0] += k if ok else 0
            par_type[typ][1] += k
    pieges: dict[str, Counter] = defaultdict(Counter)
    for _, _, d in det:
        for p in d["pieges"]:
            pieges[p["type"]]["total"] += 1
            for k in ("moteur", "appariement par capacité", "ressemblance de profils"):
                pieges[p["type"]][k] += int(p[k])
    rep = [c for n in TAILLES for g in GRAINES for c in replanification(n, g)]
    avec = [c for c in rep if c["oracle"] > 0]
    sans = [c for c in rep if c["oracle"] == 0]
    return {
        "configuration": {"tailles": list(TAILLES), "graines": list(GRAINES), "clubs": len(det), "activations_par_club": K_ACTIVATIONS},
        "detection": {"par_type": {k: {"trouvees": v[0], "plantees": v[1]} for k, v in sorted(par_type.items())},
                      "pieges": {k: dict(v) for k, v in sorted(pieges.items())},
                      "opportunites_par_club_moyenne": round(sum(d["opportunites"] for *_, d in det) / len(det), 1)},
        "replanification": {"refus_provoques": len(rep), "avec_alternative_selon_oracle": len(avec),
                            "alternative_proposee_quand_il_en_existe": sum(c["resultat"] == "ALTERNATIVE_PROPOSEE" for c in avec),
                            "alternatives_eligibles": sum(c["juste"] for c in rep if c["resultat"] == "ALTERNATIVE_PROPOSEE"),
                            "alternatives_proposees": sum(c["resultat"] == "ALTERNATIVE_PROPOSEE" for c in rep),
                            "sans_alternative_selon_oracle": len(sans),
                            "abandon_propre_quand_il_n_en_existe_pas": sum(c["resultat"] == "ABANDONNEE" for c in sans),
                            "refus_relances": sum(c["relance_du_refus"] for c in rep)},
        "confidentialite": {"moteur": [confidentialite_moteur(n, 1) for n in TAILLES], "ecrans": confidentialite_ecrans()},
    }


def rapport(res: dict) -> str:
    d, rp, cf = res["detection"], res["replanification"], res["confidentialite"]
    cfg = res["configuration"]
    lignes = ["# SYNTHETIC BENCHMARK — Club Pulse", "",
              f"Données **SYNTHÉTIQUES** : {cfg['clubs']} clubs générés (tailles {cfg['tailles']}, graines {cfg['graines'][0]}–{cfg['graines'][-1]}), "
              "vérité terrain plantée. Aucun modèle de langage. Résultats déterministes (rejouables à l'octet). "
              "Ce banc mesure le respect des règles et la robustesse aux pièges — **pas** la pertinence humaine ni un impact.", "",
              "## 1. Détection des situations plantées", "", "| Type | Trouvées / plantées |", "|---|---|"]
    lignes += [f"| {k} | {v['trouvees']} / {v['plantees']} |" for k, v in d["par_type"].items()]
    lignes += ["", "### Pièges : combien de fois la paire interdite est-elle proposée ?", "",
               "| Piège | Moteur | Appariement par capacité | Ressemblance de profils |", "|---|---|---|---|"]
    for k, v in d["pieges"].items():
        lignes.append(f"| {k} | {v.get('moteur', 0)} / {v['total']} | {v.get('appariement par capacité', 0)} / {v['total']} | "
                      f"{v.get('ressemblance de profils', 0)} / {v['total']} |")
    total = {k: sum(v.get(k, 0) for v in d["pieges"].values()) for k in ("moteur", "appariement par capacité", "ressemblance de profils", "total")}
    t = total["total"]
    lignes += [f"| **total** | **{total['moteur']} / {t}** | **{total['appariement par capacité']} / {t}** | **{total['ressemblance de profils']} / {t}** |",
               "", f"Opportunités détectées par club (moyenne) : {d['opportunites_par_club_moyenne']} — leur précision sur le FOND n'est "
               "pas mesurable (aucune vérité terrain hors situations plantées).", "",
               "## 2. Replanification après un refus", "",
               f"{rp['refus_provoques']} refus provoqués (le premier contributeur sollicité décline). Oracle : règles dures réécrites et "
               "appliquées par force brute à tous les membres, budget d'attention compris.", "",
               "| Mesure | Résultat |", "|---|---|",
               "| Alternative proposée quand l'oracle en trouve une (complétude) | "
               f"{rp['alternative_proposee_quand_il_en_existe']} / {rp['avec_alternative_selon_oracle']} |",
               f"| Alternative proposée éligible selon l'oracle (justesse) | {rp['alternatives_eligibles']} / {rp['alternatives_proposees']} |",
               "| Abandon propre quand il n'existe aucune alternative | "
               f"{rp['abandon_propre_quand_il_n_en_existe_pas']} / {rp['sans_alternative_selon_oracle']} |",
               f"| Personne ayant décliné sollicitée à nouveau | {rp['refus_relances']} |", "",
               "## 3. Confidentialité", "", "| Contrôle | Résultat |", "|---|---|"]
    for m in cf["moteur"]:
        lignes.append(f"| Identités (nom, courriel, organisation) dans ce que voit le moteur — {m['profils']} membres | "
                      f"{m['fuites']} fuite(s) sur {m['identites_verifiees']} contrôles |")
    e = cf["ecrans"]
    lignes += [f"| Nom d'une personne qui a décliné, ou note privée d'autrui, dans les écrans d'un autre membre — {e['membres']} membres, "
               f"{e['ecrans']} écrans, {e['refus_dans_la_demo']} refus | {len(e['fuites'])} fuite(s) |", "",
               "## 4. Mémoire", "",
               f"Situation plantée « déjà résolue dans le Club » retrouvée : {d['par_type'].get('MEMOIRE', {}).get('trouvees', 0)} / "
               f"{d['par_type'].get('MEMOIRE', {}).get('plantees', 0)}.", "",
               "## Ce que ce banc ne dit pas", "",
               "- rien sur de vrais membres, une vraie adoption ou un impact mesuré ;",
               "- rien sur la qualité d'un modèle de langage (aucun n'est appelé) ;",
               "- le générateur et le moteur partagent la taxonomie : un piège que la taxonomie ne sait pas exprimer n'est pas testé.", ""]
    return "\n".join(lignes)


def performance() -> str:
    lignes = ["# Performance de l'analyse du réseau (dépend de la machine)", "",
              f"Mesuré le {date.today().isoformat()} · Python {platform.python_version()} · {platform.machine()} · médiane de 3 · graine 11 · "
              "données SYNTHÉTIQUES.", "", "| Membres | Analyse complète (ms) | Opportunités |", "|---|---|---|"]
    for n in (150, 500, 1000, 5000):
        r, _ = generer(n, 11)
        mesures, k = [], 0
        for _ in range(3):
            t0 = time.perf_counter()
            k = len(scanner(r, TAX)["opportunites"])
            mesures.append((time.perf_counter() - t0) * 1000)
        lignes.append(f"| {n} | {sorted(mesures)[1]:.0f} | {k} |")
    lignes += ["", "Croissance plus que linéaire au-delà de 1000 membres (les intérêts latents comparent chaque recherche aux offreurs "
               "de la capacité). Le Club visé compte ~160 représentants : l'analyse se refait à chaque changement, en quelques millisecondes.", ""]
    return "\n".join(lignes)


def main() -> int:
    res = executer()
    (ICI / "resultats_benchmark_pulse.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    (ICI / "resultats_benchmark_pulse.md").write_text(rapport(res), encoding="utf-8")
    print(rapport(res))
    if "--performance" in sys.argv:
        (ICI / "performance_pulse.md").write_text(performance(), encoding="utf-8")
        print(performance())
    rp, cf = res["replanification"], res["confidentialite"]
    garde_fous = [rp["alternatives_eligibles"] == rp["alternatives_proposees"], rp["refus_relances"] == 0,
                  all(m["fuites"] == 0 for m in cf["moteur"]), not cf["ecrans"]["fuites"],
                  sum(v.get("moteur", 0) for v in res["detection"]["pieges"].values()) == 0]
    return 0 if all(garde_fous) else 1                    # une règle dure violée est un échec, pas un chiffre


if __name__ == "__main__":
    sys.exit(main())
