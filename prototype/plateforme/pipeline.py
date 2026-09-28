"""Boucle de décision complète, générique : ne dépend que d'un ADAPTATEUR (protocole ci-dessous).

intention → compilation → spécification → aperçu du plan → stratégie de contexte → instantané → problème formel →
frontière → solution retenue → validation L0..L6 (+ validateurs du domaine) → critique → gardien → médiation →
L8 humain → certificat. Chaque étape est tracée avec sa durée réelle ; tout est rejouable depuis l'instantané.
"""
from __future__ import annotations

from datetime import date
from typing import Callable, Optional, Protocol

import scipy

from . import critique as cr
from . import graphe as gr
from . import optimisation as op
from . import validation as va
from .affirmations import Registre
from .compilateur import Grammaire, compiler
from .execution import Budget, ExecutionDecision, Journal, Traceur, empreinte, maintenant, nouvel_id
from .specification import Domaine, SpecDecision, resume


class Adaptateur(Protocol):
    domaine: Domaine
    grammaire: Grammaire

    def instantane_courant(self) -> dict: ...
    def probleme(self, inst: dict, spec: SpecDecision) -> tuple[op.Probleme, dict[str, str], dict[str, list[str]]]: ...
    def validateurs(self, inst: dict, spec: SpecDecision, pb: op.Probleme) -> list[Callable]: ...
    def regles_gardien(self, inst: dict, spec: SpecDecision) -> list[Callable]: ...


AXES_PARETO = ["valeur_aide", "couverture", "diversite", "reciprocite"]


def plan_apercu(spec: SpecDecision) -> tuple[list[str], dict]:
    """Aperçu du plan et stratégie de contexte : on dit aussi ce qui N'est PAS utilisé."""
    plan = ["instantané des affirmations (registre)", "graphe des aides prouvées",
            "problème formel (contraintes dures de la spécification)", "frontière de Pareto (solveur HiGHS)",
            "validation indépendante L0-L6", "critique", "gardien (politique)", "médiation", "certificat", "revue humaine (L8)"]
    strategie = {"relations": "graphe", "contraintes_numeriques": "solveur", "corpus_textuel": "non utilisé (aucun RAG nécessaire)",
                 "recherche_externe": "non utilisée", "llm": "non utilisé (compilation par grammaire)",
                 "pourquoi": "données structurées et petites : graphe + solveur suffisent, un LLM n'ajouterait que du risque"}
    return plan, strategie


def executer(ad: Adaptateur, demande: str, journal: Journal, inst: Optional[dict] = None, spec: Optional[SpecDecision] = None,
             parent_id: Optional[str] = None, intervention: Optional[dict] = None, jour: Optional[date] = None,
             sensibilite: bool = True) -> ExecutionDecision:
    tr = Traceur()
    budget = Budget()
    run = ExecutionDecision(run_id=nouvel_id(), cree_le=maintenant(), parent_id=parent_id, intervention=intervention,
                            demande=demande, compilation={},
                            versions={"plateforme": "0.1", "solveur": f"HiGHS via scipy {scipy.__version__}", "compilateur": "grammaire"})
    with tr.etape("compilateur") as r:
        if spec is None:
            comp = compiler(demande, ad.grammaire, ad.domaine)
            run.compilation = comp.model_dump(mode="json", exclude={"spec"})
            spec = comp.spec if comp.decision == "AGIR" else None
        else:
            run.compilation = {"decision": "AGIR", "compilateur": "spécification fournie (branche)"}
        r["decision"] = run.compilation.get("decision")
    if spec is None:
        run.etapes = tr.etapes
        run.resultat_empreinte = empreinte({"compilation": run.compilation})
        journal.enregistrer(run)
        return run
    run.spec = spec.model_dump(mode="json")
    run.plan, run.strategie_contexte = plan_apercu(spec)
    with tr.etape("instantané") as r:
        inst = inst if inst is not None else ad.instantane_courant()
        run.instantane_empreinte = empreinte(inst)
        reg = Registre.importer(inst["affirmations"])
        r.update(affirmations=len(reg), par_statut=reg.comptes())
    with tr.etape("problème formel") as r:
        pb, ecartes, preuves = ad.probleme(inst, spec)
        r.update(participants=len(pb.participants), aretes=len(pb.aretes), exclues=len(pb.exclues), ecartes=len(ecartes))
    with tr.etape("graphe") as r:
        g = gr.construire(pb.participants, [tuple(k.split("|")) for k in pb.aretes])
        run.graphe = gr.metriques(g)
        r.update(run.graphe)
    with tr.etape("optimisation") as r:
        poids = {o.nom: o.poids for o in spec.objectifs}
        frontiere = op.frontiere(pb, AXES_PARETO)
        budget.appels_solveur += 3 ** len(AXES_PARETO) - 1
        retenue = max(frontiere, key=lambda s: (sum(poids.get(k, 0) * s.objectifs.get(k, 0) for k in AXES_PARETO),
                                                 tuple(s.objectifs.get(k, 0) for k in AXES_PARETO))) if frontiere \
            else op.resoudre(pb, poids)
        run.frontiere = [s.model_dump() for s in frontiere]
        run.retenue = retenue.model_dump()
        r.update(points_pareto=len(frontiere), rencontres=len(retenue.rencontres), optimum_prouve=retenue.optimum_prouve)
    sens = []
    if sensibilite and retenue.rencontres:
        with tr.etape("sensibilité") as r:
            principal = max(poids, key=poids.get)
            sens = op.sensibilite(pb, poids, principal)
            budget.appels_solveur += 3
            r["variations"] = sens
    with tr.etape("validation") as r:
        verdicts = va.echelle(spec, ad.domaine, pb, retenue, preuves, reg, jour or date.today(), ad.validateurs(inst, spec, pb))
        r.update({v.niveau + " " + v.nom: v.etat for v in verdicts})
    with tr.etape("critique") as r:
        avis_c = cr.critique(pb, retenue, preuves, reg, sens)
        r.update(position=avis_c.position, objections=len(avis_c.objections))
    with tr.etape("gardien") as r:
        avis_g = cr.gardien(retenue, ad.regles_gardien(inst, spec))
        r.update(position=avis_g.position, objections=len(avis_g.objections))
    with tr.etape("médiation") as r:
        med = cr.mediateur(verdicts, [avis_c, avis_g], retenue)
        r.update(decision=med.decision)
    verdicts.append(va.l8_humain())
    run.verdicts = [v.model_dump() for v in verdicts]
    run.avis = [avis_c.model_dump(), avis_g.model_dump()]
    run.mediation = med.model_dump()
    run.budget = budget
    run.etapes = tr.etapes
    run.graphe |= {"ecartes": ecartes, "exclues": len(pb.exclues), "statuts_des_preuves_utilisees": va.statuts_utilises(retenue, preuves, reg),
                   "preuves_par_rencontre": {op.cle(a, b): preuves.get(op.cle(a, b), []) for _, a, b in retenue.rencontres}}
    run.resultat_empreinte = empreinte({"spec": resume(spec), "rencontres": retenue.rencontres,
                                        "verdicts": [(v.niveau, v.etat) for v in verdicts], "mediation": med.decision})
    journal.enregistrer(run, inst)
    return run


def rejouer(ad: Adaptateur, journal: Journal, run_id: str) -> dict:
    """Réexécute depuis l'INSTANTANÉ ENREGISTRÉ et la spécification enregistrée ; compare les empreintes de résultat."""
    ancien = journal.lire(run_id)
    if not ancien.spec:
        return {"rejouable": False, "raison": "exécution sans spécification (abstention ou escalade)"}
    inst = journal.instantane(ancien.instantane_empreinte)
    nouveau = executer(ad, ancien.demande, Journal(), inst=inst, spec=SpecDecision(**ancien.spec), sensibilite=True)
    courant = empreinte(ad.instantane_courant())
    return {"rejouable": True, "identique": nouveau.resultat_empreinte == ancien.resultat_empreinte,
            "empreinte_originale": ancien.resultat_empreinte, "empreinte_rejeu": nouveau.resultat_empreinte,
            "donnees_vivantes_ont_change": courant != ancien.instantane_empreinte}


def delta(parent: ExecutionDecision, enfant: ExecutionDecision) -> dict:
    a = {(x, y) for _, x, y in (parent.retenue or {}).get("rencontres", [])}
    b = {(x, y) for _, x, y in (enfant.retenue or {}).get("rencontres", [])}
    oa, ob = (parent.retenue or {}).get("objectifs", {}), (enfant.retenue or {}).get("objectifs", {})
    touches = sorted({p for pair in a ^ b for p in pair})
    return {"rencontres_ajoutees": len(b - a), "rencontres_retirees": len(a - b),
            "objectifs": {k: round(ob.get(k, 0) - oa.get(k, 0), 3) for k in sorted(set(oa) | set(ob))},
            "participants_touches": len(touches), "graphe_avant": parent.graphe.get("composantes"),
            "graphe_apres": enfant.graphe.get("composantes"),
            "hypotheses": ["contre-factuel sur le MODÈLE formel ; ce n'est pas une prédiction du comportement des membres"]}


def contrefactuel(ad: Adaptateur, journal: Journal, run_id: str, modif: dict) -> tuple[ExecutionDecision, dict]:
    """« Et si… ? » : même instantané, spécification modifiée (contraintes levées/ajoutées, poids, tours).
    La politique s'applique : une contrainte obligatoire ne peut pas être levée."""
    parent = journal.lire(run_id)
    inst = journal.instantane(parent.instantane_empreinte)
    s = SpecDecision(**parent.spec)
    retirer, ajouter = set(modif.get("retirer_contraintes", [])), modif.get("ajouter_contraintes", [])
    s = s.model_copy(update={"contraintes_dures": [c for c in s.contraintes_dures if c not in retirer] + [c for c in ajouter if c not in s.contraintes_dures],
                             "parametres": s.parametres | modif.get("parametres", {})})
    from .specification import ErreurSpec, valider
    try:
        valider(s, ad.domaine)
    except ErreurSpec as e:
        raise ErreurSpec(f"branche refusée par la politique : {e}") from e
    enfant = executer(ad, parent.demande, journal, inst=inst, spec=s, parent_id=run_id, intervention=modif)
    return enfant, delta(parent, enfant)


def stress(ad: Adaptateur, journal: Journal, run_id: str, n: int, regle: str = "articulation", graine: int = 0) -> tuple[ExecutionDecision, dict]:
    """Retire N participants (règle structurelle ou tirage reproductible), mesure la dégradation, puis RÉPARE :
    le plan est ré-optimisé sur le réseau restant, et on compte les participants orphelins de nouveau servis."""
    parent = journal.lire(run_id)
    inst = journal.instantane(parent.instantane_empreinte)
    s = SpecDecision(**parent.spec)
    pb, _, _ = ad.probleme(inst, s)
    g = gr.construire(pb.participants, [tuple(k.split("|")) for k in pb.aretes])
    retires = gr.selection_retrait(g, n, regle, graine)
    avant = gr.metriques(g)
    g2 = g.copy()
    g2.remove_nodes_from(retires)
    apres = gr.metriques(g2)
    inst2 = {**inst, "participants": {k: v for k, v in inst["participants"].items() if k not in retires},
             "aides": {k: v for k, v in inst["aides"].items() if not set(k.split("→")) & set(retires)}}
    enfant = executer(ad, parent.demande, journal, inst=inst2, spec=s, parent_id=run_id,
                      intervention={"stress": {"retires": retires, "regle": regle}})
    avant_rdv = {(x, y) for _, x, y in parent.retenue["rencontres"]}
    orphelins = sorted({p for x, y in avant_rdv if set((x, y)) & set(retires) for p in (x, y)} - set(retires))
    servis_apres = {p for _, x, y in enfant.retenue["rencontres"] for p in (x, y)}
    return enfant, {"retires": retires, "graphe_avant": avant, "graphe_apres": apres,
                    "orphelins": len(orphelins), "orphelins_resservis_par_la_reparation": sum(1 for p in orphelins if p in servis_apres),
                    "delta": delta(parent, enfant)}
