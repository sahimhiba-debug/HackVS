"""SYNTHETIC BENCHMARK de Club Pulse — ce que le moteur fait sur des clubs GÉNÉRÉS dont on connaît la vérité.

    python -m eval.benchmark_pulse                 # résultats déterministes → eval/resultats_benchmark_pulse.{md,json}
    python -m eval.benchmark_pulse --performance   # + temps d'analyse 150 → 5000 membres → eval/performance_pulse.md

Quatre questions, chacune avec une référence qui peut PERDRE :
1. DÉTECTION — les vraies situations plantées sont-elles trouvées ? Les pièges (concurrent, refus d'introduction,
   profil obsolète, même organisation, aucune langue commune, introduction déclinée, indisponible, déjà en relation,
   simple ressemblance) sont-ils évités ? Comparé à deux références naïves : l'appariement par capacité (tout besoin ×
   tout offreur de la capacité) et la ressemblance (profils qui offrent la même chose).
2. ADAPTATION — après une perturbation réelle d'un essai (retrait, disponibilité réduite), le remplacement proposé
   est-il admissible (JUSTE) et en propose-t-on un chaque fois qu'il en existe (COMPLET) ? Oracle : les règles
   réécrites ici et appliquées par force brute à TOUTES les offres volontaires (pas appelées dans le banc ; seule
   l'observation — âges, relations — est partagée).
3. CONFIDENTIALITÉ — identités dans ce que voit le moteur ; nom d'une personne qui a décliné ou texte d'une note
   privée dans les écrans d'un AUTRE membre (démonstration complète, 150 membres, chaque écran).
4. MÉMOIRE — une contribution confirmée et partagée fait-elle choisir la personne qui a déjà aidé (et seulement
   grâce à elle : sans la mémoire, la même situation choisit quelqu'un d'autre) ?

Limites déclarées : données SYNTHÉTIQUES ; générateur et détecteur partagent la taxonomie (on mesure le respect des
règles et la robustesse aux pièges, PAS la pertinence humaine ni un impact) ; la précision sur le FOND n'est pas
mesurable (aucune vérité terrain pour les situations non plantées). Aucun modèle de langage n'est appelé.
"""
from __future__ import annotations

import json
import platform
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from app.matching import organisation
from app.taxonomy import charger_taxonomie
from intelligence.club_synthetique import generer
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.detection import scanner
from intelligence.erreurs import ErreurMetier
from intelligence.essai import Banc, Etape, Protocole
from intelligence.identite import AdhesionsSynthetiques, Coffre
from intelligence.observateur import PROFIL_OBSOLETE_JOURS, observer
from intelligence.passerelle import CRITERE_SUGGERE, brouillon
from plateforme.memoire import Memoire

ICI = Path(__file__).resolve().parent
TAX = charger_taxonomie()
GRAINES = range(1, 11)
TAILLES = (150, 500)
K_ESSAIS = 12                          # essais perturbés par club généré


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


def _trouvee(t: dict, ops: list) -> bool:
    return any(t["type"] in (o.type, *o.mecanismes) and set(t["membres"]) <= _membres(o) and set(t["concepts"]) <= set(o.capacites)
               for o in ops)


def detection(n: int, graine: int) -> dict:
    r, v = generer(n, graine)
    ops = scanner(r, TAX, souvenirs=v["souvenirs"])["opportunites"]
    trouvees = Counter()
    for t in v["vraies"]:
        trouvees[(t["type"], _trouvee(t, ops))] += 1
    sans_memoire = scanner(r, TAX)["opportunites"]                          # la mémoire est-elle DÉCISIVE ?
    memoire_decisive = sum(not _trouvee(t, sans_memoire) for t in v["vraies"] if t["type"] == "mémoire du Club")
    refs = _references(r)
    pieges = []
    for t in v["pieges"]:
        cible = frozenset(t["membres"])
        pieges.append({"type": t["type"], "moteur": any(cible <= _membres(o) for o in ops),
                       **{nom: cible in paires for nom, paires in refs.items()}})
    return {"trouvees": trouvees, "pieges": pieges, "opportunites": len(ops), "memoire_decisive": memoire_decisive}


# ---------------------------------------------------------------------- 2. adaptation (banc d'essai)
DUREES = (15, 30, 60, 90)


def _semer_offres(r, banc: Banc, rnd: random.Random) -> None:
    """Offres volontaires SYNTHÉTIQUES : un membre sur deux qui déclare une capacité publie une disponibilité pour l'une
    d'elles (durée, capacité, validité au hasard) — dont des offres trop courtes, expirées, à venir ou d'une autre
    capacité : l'adaptation doit les écarter."""
    j = r.aujourd_hui
    for p in r.profils:
        if not p.offre or rnd.random() < 0.5:
            continue
        du = j + timedelta(days=rnd.choice([-30, -5, 0, 0, 0, 3]))
        au = du + timedelta(days=rnd.choice([2, 10, 20, 40]))
        declaree = rnd.choice(p.offre)                                     # une capacité DÉCLARÉE dans son profil
        banc.publier_offre(p.id, "competence", declaree.texte, rnd.choice([1, 2]), du, au, duree_max_min=rnd.choice(DUREES),
                           concept=declaree.concept)


def _oracle(r, e_obs, banc: Banc, eid: str, etape_id: str, hors: set[str]) -> set[str]:
    """Offres qui PEUVENT remplacer ce geste : règles réécrites ici (pas d'appel aux règles du banc ni aux exclusions de
    l'observateur), appliquées par force brute à TOUTES les offres publiques. Seule l'observation (âges, refus
    d'introduction passés) est partagée."""
    p = banc.protocole(eid)
    e = next(x for x in p.etapes if x.id == etape_id)
    par_id = r.par_id()
    benef = par_id[banc.porteur(eid)]
    autres = {x.contributeur for x in p.etapes if x.contributeur and x.id != etape_id}
    res = set()
    for o in banc.offres(publiques=True):
        c = par_id[o.auteur]
        age = e_obs.age_profil(c)
        if o.auteur in hors | autres or o.auteur == benef.id or retiree(banc, o.id) \
                or not o.du <= r.aujourd_hui <= o.au or o.au < p.echeance or o.nature != e.nature \
                or (e.concept is not None and o.concept != e.concept) \
                or (o.duree_max_min is not None and o.duree_max_min < e.duree_min) \
                or (organisation(c) or c.id) == (organisation(benef) or benef.id) or not c.accepte_introductions or not c.disponible \
                or age is None or age > PROFIL_OBSOLETE_JOURS or not set(c.langues) & set(benef.langues) \
                or frozenset((benef.id, c.id)) in e_obs.declinees:
            continue
        res.add(o.id)
    return res


def retiree(banc: Banc, oid: str) -> bool:
    return any(e.donnees["offre"] == oid for e in banc.m.evenements("OFFRE_RETIREE"))


def adaptation(n: int, graine: int) -> list[dict]:
    """Pour chaque opportunité à bénéficiaire : le bénéficiaire propose l'essai (passerelle), la personne invitée accepte
    (elle DÉCLARE 60 min), puis une perturbation réelle — elle se retire, ou n'a plus que 20 min. Le banc propose-t-il
    une adaptation chaque fois qu'il en existe une (COMPLET), seulement des adaptations admissibles (JUSTE), et
    s'arrête-t-il proprement sinon ? Chaque cas a son propre banc (aucune capacité partagée entre cas)."""
    r, _ = generer(n, graine, plantes=True)
    e_obs = observer(r, TAX)
    par_id = r.par_id()
    cas = []
    for o in scanner(r, TAX)["opportunites"]:
        if len(cas) >= K_ESSAIS or not o.beneficiaire or o.type in ("CONVERGENCE", "LACUNE"):
            continue
        rnd = random.Random(f"{graine}-{o.id}")
        banc = Banc(Memoire(), lambda: r.aujourd_hui, lambda pid: organisation(par_id[pid]) or pid,
                    lambda porteur, cand: e_obs.exclusion(par_id[porteur], par_id[cand], None, introduction=False))
        _semer_offres(r, banc, rnd)
        p = brouillon(o, r, TAX, r.aujourd_hui)
        if not p.etapes:
            continue
        eid = banc.brouillon(o.beneficiaire, p.model_copy(update={"critere": CRITERE_SUGGERE}))
        try:
            v = banc.proposer(o.beneficiaire, eid, 0)
            invite = p.etapes[0].contributeur or ""
            banc.decider(invite, eid, v, True)
        except ErreurMetier:                                                # désignée non sollicitable : refusé, compté
            cas.append({"perturbation": "aucune", "resultat": "refus à la publication"})
            continue
        perturbation = rnd.choice(["retrait", "reduction"])
        if perturbation == "retrait":
            banc.retirer(invite, eid)
        else:
            banc.modifier_offre(invite, banc.offre_de(eid, banc.protocole(eid).etapes[0]).id, duree_max_min=20)  # type: ignore[union-attr]
        oracle = _oracle(r, e_obs, banc, eid, "e1", {invite} if perturbation == "retrait" else set())
        alts = banc.alternatives(eid) if banc.etat(eid) == "A_ADAPTER" else []
        remplacer = [a for a in alts if a["type"] == "remplacer"]
        raccourcir = [a for a in alts if a["type"] == "raccourcir"]
        releve = {"perturbation": perturbation, "oracle": len(oracle), "etat": banc.etat(eid),
                  "remplacer": len(remplacer), "remplacer_admissibles": sum(a["offre"] in oracle for a in remplacer),
                  "raccourcir": len(raccourcir), "raccourcir_meme_personne": sum(a["membre"] == invite for a in raccourcir)}
        if remplacer:                                                       # choisir : la personne partie n'est pas redemandée
            banc.choisir_alternative(o.beneficiaire, eid, banc.version(eid), remplacer[0]["id"])
            releve["redemande_apres_retrait"] = perturbation == "retrait" and invite in {x.contributeur for x in banc.protocole(eid).etapes}
        cas.append(releve)
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


NOTE_PRIVEE = "Note privée : Markus hésite à représenter des tisanes, ne pas le brusquer."
IDENTIFIANT_INTERNE = re.compile(r"\b(?:[sd]\d{2}|n01|c\d{5})\b")


def confidentialite_ecrans() -> dict:
    """La démonstration complète, plus ce qui doit rester privé : une note privée, un refus sur un essai à offres
    (Léa → Markus décline), un essai observé mais NON partagé (Pauline, niveau « participants »). Puis CHAQUE écran de
    CHAQUE membre (150) et de la console : ni nom de qui a décliné (sauf chez qui l'a invité), ni note privée d'autrui,
    ni observation hors de ses participants, ni pseudonyme non rendu, ni identifiant interne."""
    d = Demo(TAX)
    d.rejouer(len(Demo.ETAPES))
    c, b = d.club, d.club.banc
    c.capturer(md.SOPHIE, NOTE_PRIVEE)
    geste = Etape(id="e1", nature="temps", geste="Regarder notre étiquette 10 secondes", duree_min=10)
    lea = b.brouillon(md.LEA, Protocole(question="Notre étiquette est-elle lisible ?", critere="combien la lisent", echeance=c.jour + timedelta(days=5),
                                         etapes=[geste]))
    v = b.proposer(md.LEA, lea, 0, {"e1": next(o.id for o in b.offres(publiques=True) if o.auteur == md.MARKUS)})
    b.decider(md.MARKUS, lea, v, False)                                     # refus sur un essai à offres
    pauline = b.brouillon(md.PAULINE, Protocole(question="Le présentoir attire-t-il ?", critere="combien s'arrêtent",
                                                echeance=c.jour + timedelta(days=5), etapes=[geste]))
    v = b.proposer(md.PAULINE, pauline, 0, {"e1": next(o.id for o in b.offres(publiques=True) if o.auteur == md.LEA)})
    b.decider(md.LEA, pauline, v, True)
    b.lancer(md.PAULINE, pauline, v)
    b.constater(md.PAULINE, pauline, "e1")
    secret = "OBSERVATION-NON-PARTAGEE-4c1e"
    b.observer(md.PAULINE, pauline, secret, "mitige", "une seule personne")   # niveau par défaut : participants
    refus = {(x.donnees["essai"], x.acteurs[0]) for x in b.m.evenements("ACCORD") if not x.donnees["accepte"]}
    ecrans, fuites = 0, []

    def controler(qui: str, vues: list, pid=None) -> None:
        nonlocal ecrans
        ecrans += len(vues)
        texte = json.dumps(vues, ensure_ascii=False)
        if pid != md.SOPHIE and "ne pas le brusquer" in texte:
            fuites.append(("note privée d'un autre membre", qui))
        if pid not in b.participants(pauline) and secret in texte:
            fuites.append(("observation hors de ses participants", qui))
        if "MEMBRE-" in texte:
            fuites.append(("pseudonyme non rendu", qui))
        if IDENTIFIANT_INTERNE.search(texte):
            fuites.append(("identifiant interne de membre", qui))

    for pid in sorted(c.coffre._personnes):
        vues = [c.vues.decouvertes_de(pid), c.vues.notes_de(pid), c.vues_essai.actions(pid), c.vues_essai.souvenirs(pid), c.vues.vue_profil(pid)]
        vues += [c.vues_essai.essai(eid, pid) for eid in b.essais() if pid in b.personnes(eid) and (pid == b.porteur(eid) or b.etat(eid) != "BROUILLON")]
        controler(pid, vues, pid)
    controler("console", [c.vues.panneau(), c.vues_essai.console()] + [c.vues_essai.essai(eid, None, console=True) for eid in b.essais()])
    for eid, m in refus:                        # qui a décliné : jamais nommé dans CET essai, sauf à qui l'avait invité(e)
        nom = c.coffre.identite(m).nom  # type: ignore[union-attr]
        invite = any(e.get("invitation") and e.get("contributeur") == m for v_ in b._versions(eid) for e in v_.donnees["protocole"]["etapes"])
        spectateurs = [(x, c.vues_essai.essai(eid, x)) for x in b.personnes(eid) - {m} if not (invite and x == b.porteur(eid))]
        spectateurs += [("console", [c.vues_essai.essai(eid, None, console=True), [x for x in c.vues_essai.console()["essais"] if x["id"] == eid]])]
        ecrans += len(spectateurs)
        fuites += [("nom d'une personne qui a décliné", x) for x, vue in spectateurs if nom in json.dumps(vue, ensure_ascii=False)]
    return {"membres": len(c.coffre._personnes), "ecrans": ecrans, "refus": len(refus), "fuites": fuites}


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
    ad = [c for n in TAILLES for g in GRAINES for c in adaptation(n, g)]
    perturbes = [c for c in ad if c["perturbation"] != "aucune"]
    avec = [c for c in perturbes if c["oracle"] > 0]
    sans = [c for c in perturbes if c["oracle"] == 0]
    reduits = [c for c in perturbes if c["perturbation"] == "reduction"]
    return {
        "configuration": {"tailles": list(TAILLES), "graines": list(GRAINES), "clubs": len(det), "essais_par_club": K_ESSAIS},
        "detection": {"par_type": {k: {"trouvees": v[0], "plantees": v[1]} for k, v in sorted(par_type.items())},
                      "pieges": {k: dict(v) for k, v in sorted(pieges.items())},
                      "opportunites_par_club_moyenne": round(sum(d["opportunites"] for *_, d in det) / len(det), 1),
                      "memoire_decisive": sum(d["memoire_decisive"] for *_, d in det)},
        "adaptation": {"essais_perturbes": len(perturbes), "refus_a_la_publication": len(ad) - len(perturbes),
                       "retraits": sum(c["perturbation"] == "retrait" for c in perturbes), "reductions": len(reduits),
                       "avec_remplacement_selon_oracle": len(avec),
                       "remplacement_propose_quand_il_en_existe": sum(c["remplacer"] > 0 for c in avec),
                       "remplacements_proposes": sum(c["remplacer"] for c in perturbes),
                       "remplacements_admissibles": sum(c["remplacer_admissibles"] for c in perturbes),
                       "sans_remplacement_selon_oracle": len(sans),
                       "arret_ou_raccourci_quand_il_n_en_existe_pas": sum(c["etat"] == "IMPOSSIBLE" or c["raccourcir"] > 0 for c in sans),
                       "raccourcir_propose_apres_reduction": sum(c["raccourcir_meme_personne"] > 0 for c in reduits),
                       "retire_redemande": sum(bool(c.get("redemande_apres_retrait")) for c in perturbes)},
        "confidentialite": {"moteur": [confidentialite_moteur(n, 1) for n in TAILLES], "ecrans": confidentialite_ecrans()},
    }


def rapport(res: dict) -> str:
    d, ad, cf = res["detection"], res["adaptation"], res["confidentialite"]
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
               "## 2. Adaptation après une perturbation (banc d'essai)", "",
               f"{ad['essais_perturbes']} essais proposés depuis une opportunité détectée ; la personne invitée accepte (elle déclare "
               f"60 min) puis se retire ({ad['retraits']}) ou n'a plus que 20 min ({ad['reductions']}). Oracle : règles réécrites et "
               "appliquées par force brute à toutes les offres volontaires publiques (synthétiques, dont des offres trop courtes, "
               f"expirées, à venir ou d'une autre capacité). {ad['refus_a_la_publication']} publication(s) refusée(s).", "",
               "| Mesure | Résultat |", "|---|---|",
               "| Remplacement proposé quand l'oracle en trouve un (complétude) | "
               f"{ad['remplacement_propose_quand_il_en_existe']} / {ad['avec_remplacement_selon_oracle']} |",
               f"| Remplacements proposés admissibles selon l'oracle (justesse) | {ad['remplacements_admissibles']} / {ad['remplacements_proposes']} |",
               "| Sans remplacement possible : arrêt propre (IMPOSSIBLE) ou raccourcir avec la même personne | "
               f"{ad['arret_ou_raccourci_quand_il_n_en_existe_pas']} / {ad['sans_remplacement_selon_oracle']} |",
               f"| « Raccourcir avec la même personne » proposé après une réduction | {ad['raccourcir_propose_apres_reduction']} / {ad['reductions']} |",
               f"| Personne retirée redésignée après adaptation | {ad['retire_redemande']} |", "",
               "## 3. Confidentialité", "", "| Contrôle | Résultat |", "|---|---|"]
    for m in cf["moteur"]:
        lignes.append(f"| Identités (nom, courriel, organisation) dans ce que voit le moteur — {m['profils']} membres | "
                      f"{m['fuites']} fuite(s) sur {m['identites_verifiees']} contrôles |")
    e = cf["ecrans"]
    lignes += [f"| Écrans de chaque membre et de la console ({e['membres']} membres, {e['ecrans']} écrans, {e['refus']} refus) : nom de qui a "
               "décliné (hors la personne qui l'a invité), note privée d'autrui, observation non partagée, pseudonyme non rendu, "
               f"identifiant interne | {len(e['fuites'])} fuite(s) |", "",
               "## 4. Mémoire", "",
               "Situation plantée : deux membres déclarent la même capacité ; l'un a déjà aidé (contribution confirmée par les deux "
               "parties et partagée avec le Club), l'autre a un profil plus récent et passerait devant sans mémoire.", "",
               f"- retrouvée avec la mémoire : {d['par_type'].get('mémoire du Club', {}).get('trouvees', 0)} / "
               f"{d['par_type'].get('mémoire du Club', {}).get('plantees', 0)} ;",
               f"- la même situation SANS la mémoire n'est pas retrouvée (la mémoire est décisive) : {d['memoire_decisive']} / "
               f"{d['par_type'].get('mémoire du Club', {}).get('plantees', 0)}.", "",
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
    ad, cf = res["adaptation"], res["confidentialite"]
    garde_fous = [ad["remplacements_admissibles"] == ad["remplacements_proposes"], ad["retire_redemande"] == 0,
                  ad["remplacement_propose_quand_il_en_existe"] == ad["avec_remplacement_selon_oracle"],
                  all(m["fuites"] == 0 for m in cf["moteur"]), not cf["ecrans"]["fuites"],
                  sum(v.get("moteur", 0) for v in res["detection"]["pieges"].values()) == 0]
    return 0 if all(garde_fous) else 1                    # une règle dure violée est un échec, pas un chiffre


if __name__ == "__main__":
    sys.exit(main())
