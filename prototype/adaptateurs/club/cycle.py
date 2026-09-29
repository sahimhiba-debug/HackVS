"""Cycle de vie d'une relation du Club : soirée → rencontre → (10 jours) → pourquoi reprendre contact ? → suivi →
nouvelle opportunité → soirée suivante.

Principe : on ne relance JAMAIS sans raison NOUVELLE et documentée. « Restez en contact » n'est pas une raison ;
une rencontre sans rien de nouveau depuis donne une abstention, comptée et affichée.

Raisons admises (chacune avec ses preuves citées) :
- NOUVEAU_BESOIN : l'un a publié un besoin APRÈS la rencontre, et l'autre peut y répondre (offre citée) ;
- PRESENTATION : proposée à l'INTERMÉDIAIRE (qui connaît déjà les deux personnes) — seulement si son lien avec la
  personne aidée a eu un SUIVI. La personne aidée n'apprend l'existence du lien que si l'intermédiaire accepte.
"""
from __future__ import annotations

import hashlib
from datetime import date
from types import SimpleNamespace
from typing import Optional

from app.matching import rechercher
from app.models import Profil
from app.parser_rules import analyser
from app.soiree import calculer_aides
from app.taxonomy import Taxonomie
from plateforme.affirmations import Statut
from plateforme.execution import Journal
from plateforme.memoire import Evt, Memoire, fermetures, force, graphe
from plateforme.optimisation import cle

DELAI_RELANCE_JOURS = 10
MAX_RELANCES_PAR_MEMBRE = 3     # budget d'attention (hypothèse de produit) : au-delà, reporté, jamais perdu


class ErreurCycle(ValueError):
    pass


def _id(*parts: str) -> str:
    return "r_" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:12]


# ------------------------------------------------------------------ soirée → rencontres
def enregistrer_soiree(m: Memoire, journal: Journal, run_id: str, nom: str, le: date, demo: bool = True) -> dict:
    """Une soirée n'entre dans la mémoire que depuis un plan APPROUVÉ par un humain. En démo, la présence n'est pas
    constatée : les rencontres sont SIMULE tant qu'un membre ne déclare pas « nous nous sommes vus »."""
    run = journal.lire(run_id)
    if (run.decision_humaine or {}).get("verdict") != "APPROUVER":
        raise ErreurCycle("seul un plan approuvé par un humain peut devenir une soirée")
    if not run.retenue:   # défensif : l'approbation l'exige déjà (plateforme/action.py)
        raise ErreurCycle("plan sans solution retenue : rien à enregistrer")
    if any(e.donnees.get("run_id") == run_id for e in m.evenements("EVENEMENT_TENU")):
        raise ErreurCycle("cette soirée est déjà enregistrée")
    # Collision : personne n'est à deux tables le même soir (deux plans approuvés enregistrés le même jour).
    places = {x for _, a, b in run.retenue["rencontres"] for x in (a, b)}
    deja = {x for e in m.evenements("RENCONTRE") if e.le == le and e.donnees.get("run_id") != run_id for x in e.acteurs}
    if places & deja:
        raise ErreurCycle(f"collision : {len(places & deja)} membre(s) déjà placé(s) à une autre soirée le même jour")
    # Plan devenu faux entre l'approbation et l'enregistrement : un refus d'introduction postérieur l'emporte.
    from .reseau import paires_declinees
    refus = {frozenset(p) for p in paires_declinees(m, le)}
    if any(frozenset((a, b)) in refus for _, a, b in run.retenue["rencontres"]):
        raise ErreurCycle("plan périmé : une introduction a été déclinée depuis l'approbation ; relancez le calcul")
    inst = journal.instantane(run.instantane_empreinte)
    st = Statut.SIMULE if demo else Statut.DECLARE
    m.ajouter(Evt(type="EVENEMENT_TENU", le=le, donnees={"nom": nom, "run_id": run_id, "rencontres": len(run.retenue["rencontres"])}, statut=st))
    for t, a, b in run.retenue["rencontres"]:
        raisons = [{"qui_aide": j, "qui_est_aide": i, "besoin": inst["aides"][f"{i}→{j}"]["besoin"],
                    "preuve": inst["aides"][f"{i}→{j}"]["preuve"]} for i, j in ((a, b), (b, a)) if f"{i}→{j}" in inst["aides"]]
        m.ajouter(Evt(type="RENCONTRE", le=le, acteurs=[a, b], statut=st,
                      donnees={"evenement": nom, "tour": t, "run_id": run_id, "raisons": raisons}))
    return {"evenement": nom, "rencontres": len(run.retenue["rencontres"]), "statut": st.value}


def confirmer_rencontre(m: Memoire, a: str, b: str, par: str, le: date) -> Evt:
    if par not in (a, b):
        raise ErreurCycle("seul un des deux membres peut déclarer la rencontre")
    if not graphe(m).has_edge(a, b):
        raise ErreurCycle("aucune rencontre enregistrée entre ces deux membres")
    return m.ajouter(Evt(type="RENCONTRE_CONFIRMEE", le=le, acteurs=sorted([a, b]), donnees={"par": par}, statut=Statut.DECLARE))


def publier_besoin(m: Memoire, auteur: str, texte: str, le: date, tax: Taxonomie, statut: Statut = Statut.OBSERVE) -> Evt:
    b = analyser(texte, tax)
    return m.ajouter(Evt(type="BESOIN_PUBLIE", le=le, acteurs=[auteur], statut=statut,
                         donnees={"texte": texte, "besoin": b.model_dump()}))


def besoins_publies(m: Memoire, jusqu_au: Optional[date] = None) -> list:
    """Besoins de la mémoire, au format attendu par le moteur (auteur_id, anonyme, besoin, statut_affirmation)."""
    from app.models import Besoin
    clos = {e.donnees["besoin_id"] for e in m.evenements("BESOIN_CLOS", jusqu_au=jusqu_au)}
    return [SimpleNamespace(auteur_id=e.acteurs[0], anonyme=False, besoin=Besoin(**e.donnees["besoin"]), le=e.le,
                            statut_affirmation=e.statut, evt=e.id)
            for e in m.evenements("BESOIN_PUBLIE", jusqu_au=jusqu_au) if e.donnees.get("besoin_id") not in clos]


# ------------------------------------------------------------------ 10 jours plus tard : pourquoi reprendre contact ?
def _traitees(m: Memoire) -> set[str]:
    return {e.donnees["relance_id"] for e in m.evenements("RELANCE_ACCEPTEE", "RELANCE_REFUSEE")}


def relances(m: Memoire, profils: list[Profil], tax: Taxonomie, maintenant: date, delai: int = DELAI_RELANCE_JOURS) -> dict:
    par_id = {p.id: p for p in profils}
    from .reseau import graphe_actuel
    g = graphe(m, maintenant)
    actuel = graphe_actuel(m, maintenant)
    sens_servis = _sens_servis(m, maintenant)
    deja, propositions, trop_tot, sans_raison = _traitees(m), [], [], []
    besoins = besoins_publies(m, maintenant)
    suivis = {cle(*e.acteurs) for e in m.evenements("SUIVI", jusqu_au=maintenant)}
    for a, b, d in sorted(g.edges(data=True), key=lambda x: (x[0], x[1])):
        if a not in par_id or b not in par_id:
            continue
        ecoule = (maintenant - d["derniere"]).days
        if ecoule < delai:
            trop_tot.append({"paire": [a, b], "eligible_le": date.fromordinal(d["derniere"].toordinal() + delai).isoformat()})
            continue
        raisons = []
        for x, y in ((a, b), (b, a)):  # x a un besoin nouveau, y peut aider
            for bp in besoins:
                if bp.auteur_id != x or bp.le <= d["derniere"]:
                    continue
                res = rechercher(bp.besoin, par_id[x], [par_id[x], par_id[y]], tax)
                s = next((s for s in res.suggestions if s.profil.id == y), None)
                if s:
                    raisons.append({"type": "NOUVEAU_BESOIN", "pour": x, "avec": y, "force": s.niveau,
                                    "message": f"{par_id[x].nom} a publié un besoin le {bp.le.isoformat()} ; {par_id[y].nom} peut y répondre.",
                                    "preuves": [{"statut": bp.statut_affirmation.value, "quoi": "besoin publié", "extrait": bp.besoin.texte},
                                                *[{"statut": "DECLARE" if p.nature == "declare" else "INFERE", "quoi": f"profil de {par_id[y].nom} ({p.champ})",
                                                   "extrait": p.extrait} for p in s.preuves[:2]]],
                                    "id": _id(a, b, "NOUVEAU_BESOIN", bp.evt)})
        # L'AUTRE SENS d'une rencontre : elle a servi un besoin de l'un ; l'autre cherche ce que le premier offre, et ce
        # n'était pas la raison documentée de la rencontre. Raison réelle (preuve citée), pas une relance de politesse.
        servis = sens_servis.get(cle(a, b), set())
        for x, y in ((a, b), (b, a)):  # y peut aider x
            if (x, y) in servis or any(r["type"] == "NOUVEAU_BESOIN" and r["pour"] == x for r in raisons):
                continue
            from .reseau import reciprocite_prouvee
            rp = reciprocite_prouvee(par_id[y], par_id[x], tax, besoins)
            if rp and servis:
                raisons.append({"type": "RECIPROCITE_OUVERTE", "pour": x, "avec": y, "force": rp["niveau"],
                                "message": f"Votre rencontre portait sur un besoin de {par_id[y].nom}. Dans l'autre sens, "
                                           f"{par_id[y].nom} propose ce que vous cherchez.",
                                "preuves": [{"statut": "DECLARE", "quoi": f"votre {rp['son_besoin'].split(' : ', 1)[0]}",
                                             "extrait": rp["son_besoin"].split(" : ", 1)[-1]},
                                            {"statut": "DECLARE" if rp["nature"] == "declare" else "INFERE",
                                             "quoi": f"profil de {par_id[y].nom}", "extrait": rp["votre_offre"]}],
                                "id": _id(x, y, "RECIPROCITE_OUVERTE")})
        for x, via in ((a, b), (b, a)):  # ami d'un ami : via a eu un suivi avec x, et connaît z qui peut aider x
            if cle(x, via) not in suivis or not actuel.has_edge(x, via):
                continue
            for z in sorted(actuel.neighbors(via)):   # lien via–z ACTUEL : pas une rencontre d'il y a deux ans
                if z in (x, via) or g.has_edge(x, z) or z not in par_id:
                    continue
                aide = calculer_aides([par_id[x], par_id[z]], besoins, tax).get((x, z))
                if aide:
                    # Adressée à l'INTERMÉDIAIRE, qui connaît déjà les deux : x n'apprend rien du lien via–z
                    # tant que via n'a pas accepté de faire la présentation (confidentialité par défaut).
                    raisons.append({"type": "PRESENTATION", "pour": via, "avec": x, "vers": z, "force": aide["niveau"],
                                    "message": f"Vous connaissez {par_id[x].nom} et {par_id[z].nom} ; {par_id[z].nom} peut aider "
                                               f"{par_id[x].nom}. Accepteriez-vous de les présenter ?",
                                    "preuves": [{"statut": g[via][z]["statut"].value, "quoi": f"rencontre {par_id[via].nom} – {par_id[z].nom}",
                                                 "extrait": f"le {g[via][z]['derniere'].isoformat()}"},
                                                {"statut": "INFERE" if aide["nature_preuve"] != "declare" else "DECLARE",
                                                 "quoi": f"{aide['besoin']}", "extrait": aide["preuve"]}],
                                    "id": _id(x, via, z, "PRESENTATION")})
        raisons = [r for r in raisons if r["id"] not in deja]
        if raisons:
            propositions.append({"paire": [a, b], "noms": [par_id[a].nom, par_id[b].nom], "derniere_interaction": d["derniere"].isoformat(),
                                 "jours": ecoule, "force_du_lien": force(d["derniere"], maintenant), "statut_du_lien": d["statut"].value,
                                 "raisons": raisons})
        else:
            sans_raison.append([a, b])
    propositions.sort(key=lambda p: (-sum(r["force"] == "forte" for r in p["raisons"]), p["force_du_lien"], p["paire"]))
    # Budget d'attention : un membre très relié ne reçoit pas 8 relances le même jour. Les plus fortes d'abord ; le
    # reste est REPORTÉ (compté) et réapparaît quand les premières ont reçu une réponse.
    recues: dict[str, int] = {}
    reportees = 0
    for prop in propositions:
        gardees = []
        for r in sorted(prop["raisons"], key=lambda r: (r["force"] != "forte", r["id"])):
            if recues.get(r["pour"], 0) < MAX_RELANCES_PAR_MEMBRE:
                recues[r["pour"]] = recues.get(r["pour"], 0) + 1
                gardees.append(r)
            else:
                reportees += 1
        prop["raisons"] = gardees
    propositions = [p for p in propositions if p["raisons"]]
    return {"maintenant": maintenant.isoformat(), "delai_jours": delai, "propositions": propositions,
            "abstentions": {"rien_de_nouveau": len(sans_raison), "trop_tot": len(trop_tot),
                            "reportees_budget_attention": reportees},
            "trop_tot": trop_tot[:5],
            "principe": "aucune relance sans raison NOUVELLE et documentée ; « restez en contact » n'en est pas une"}


def _sens_servis(m: Memoire, maintenant: date) -> dict[str, set[tuple[str, str]]]:
    """Par paire : directions (aidé, aidant) qui ÉTAIENT la raison documentée d'une rencontre (soirée ou introduction).
    Index construit en UNE passe (et non une lecture de la mémoire par paire : coût quadratique mesuré)."""
    besoin_auteur: dict[str, dict] = {}
    res: dict[str, set[tuple[str, str]]] = {}
    for e in m.evenements("INTRO_DEMANDEE", "INTRO_ACCEPTEE", "RENCONTRE", jusqu_au=maintenant):
        k = cle(*e.acteurs[:2])
        if e.type == "RENCONTRE":
            res.setdefault(k, set()).update((r["qui_est_aide"], r["qui_aide"]) for r in e.donnees.get("raisons", []))
        else:   # acteurs = [auteur du besoin, aidant]
            besoin_auteur.setdefault(k, {})[e.donnees.get("relation_id")] = (e.acteurs[0], e.acteurs[1])
    for k, sens in besoin_auteur.items():
        res.setdefault(k, set()).update(sens.values())
    return res


def trouver_raison(m: Memoire, profils, tax, maintenant: date, relance_id: str) -> tuple[dict, dict]:
    for p in relances(m, profils, tax, maintenant)["propositions"]:
        for r in p["raisons"]:
            if r["id"] == relance_id:
                return p, r
    raise ErreurCycle("relance inconnue, déjà traitée ou plus d'actualité")


def repondre(m: Memoire, profils, tax, maintenant: date, relance_id: str, accepte: bool, par: str) -> dict:
    """L'humain décide. Accepter crée un SUIVI (déclaré par le membre) : le lien est ravivé, et s'il y a un tiers,
    l'opportunité de présentation est ouverte pour la prochaine soirée."""
    p, r = trouver_raison(m, profils, tax, maintenant, relance_id)
    if par not in p["paire"]:
        raise ErreurCycle("seul un des deux membres concernés peut répondre")
    if not accepte:
        m.ajouter(Evt(type="RELANCE_REFUSEE", le=maintenant, acteurs=p["paire"], donnees={"relance_id": relance_id, "par": par}, statut=Statut.DECLARE))
        return {"suivi": False}
    m.ajouter(Evt(type="RELANCE_ACCEPTEE", le=maintenant, acteurs=p["paire"], donnees={"relance_id": relance_id, "par": par, "raison": r["type"]},
                  statut=Statut.DECLARE))
    m.ajouter(Evt(type="SUIVI", le=maintenant, acteurs=p["paire"], donnees={"relance_id": relance_id, "raison": r["message"]}, statut=Statut.DECLARE))
    ouvertes = []
    if r["type"] == "PRESENTATION":  # l'intermédiaire a accepté : la présentation devient visible pour les deux
        e = m.ajouter(Evt(type="OPPORTUNITE_OUVERTE", le=maintenant, acteurs=sorted([r["avec"], r["vers"]]),
                          donnees={"via": r["pour"], "raison": r["message"], "relance_id": relance_id}, statut=Statut.INFERE))
        ouvertes.append(e.acteurs)
    return {"suivi": True, "opportunites_ouvertes": ouvertes}


def opportunites(m: Memoire, profils: list[Profil], tax: Taxonomie, maintenant: date) -> list[dict]:
    """Opportunités pour la PROCHAINE soirée : présentations acceptées + triades ouvertes dont un lien a eu un suivi
    et où l'un peut aider l'autre (preuve). Toutes INFÉRÉES."""
    par_id = {p.id: p for p in profils}
    g = graphe(m, maintenant)
    suivis = {cle(*e.acteurs) for e in m.evenements("SUIVI", jusqu_au=maintenant)}
    res = {cle(*e.acteurs): {"a": e.acteurs[0], "c": e.acteurs[1], "via": e.donnees["via"], "raison": e.donnees["raison"]}
           for e in m.evenements("OPPORTUNITE_OUVERTE", jusqu_au=maintenant)}
    besoins = besoins_publies(m, maintenant)
    from .reseau import graphe_actuel
    for a, via, c in fermetures(graphe_actuel(m, maintenant)):   # triades sur les liens ACTUELS seulement
        k = cle(a, c)
        if g.has_edge(a, c) or k in res or a not in par_id or c not in par_id or not ({cle(a, via), cle(via, c)} & suivis):
            continue
        aides = calculer_aides([par_id[a], par_id[c]], besoins, tax)
        if aides:
            (i, j), aide = sorted(aides.items())[0]
            res[k] = {"a": a, "c": c, "via": via, "raison": f"{par_id[j].nom} peut aider {par_id[i].nom} ({aide['preuve']}) ; "
                                                             f"{par_id[via].nom} les connaît tous deux"}
    return sorted(res.values(), key=lambda o: (o["a"], o["c"]))


def relations(m: Memoire, maintenant: date) -> list[tuple[str, str]]:
    return sorted(graphe(m, maintenant).edges())
