"""Mode SCÈNE (/demo/stage) : un monde ISOLÉ, déterministe et rejouable, pour présenter le parcours central.

- Données : `data/stage_reseau.json`, réseau FICTIF lisible (16 membres, 3 grappes, un seul pont faible, un membre
  dormant, un membre qui refuse les introductions, un profil ancien) ; aucune donnée du Club.
- Moteur : EXACTEMENT les mêmes fonctions que l'application (analyse des besoins, moteur de mise en relation, magasin
  et son workflow en double accord, mémoire du réseau, relances documentées, simulation, micro-cercle). Seule la
  mise en scène est propre à ce module.
- Horloge : fixe au départ (date simulée), avancée par les étapes ; secondes incrémentales pour un ordre stable.
- État côté serveur : un rafraîchissement du navigateur ne perd rien ; « précédent » = réinitialiser puis rejouer.
"""
from __future__ import annotations

import json
import re
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Optional

import networkx as nx
from fastapi import APIRouter, HTTPException, Query

from adaptateurs.club import diagnostic as dg
from adaptateurs.club import interventions, pareto, reseau, sante
from adaptateurs.club import cycle as cy
from plateforme import memoire as me
from plateforme.affirmations import Statut

from . import parser_llm
from .matching import rechercher
from .models import Profil
from .parser_rules import analyser
from .store import Magasin
from .taxonomy import DATA_DIR, Taxonomie

SOPHIE = "n01"


_IA: dict[str, tuple] = {}     # une interprétation IA par texte et par processus : le rejeu reste identique


def interpreter_ia(texte: str, tax: Taxonomie) -> Optional[tuple]:
    """Interprétation par le modèle génératif CONFIGURÉ (validée par `parser_llm.valider`), ou None s'il n'y en a pas.
    Jamais de sortie simulée : sans modèle, la scène le dit."""
    if not parser_llm.llm_configure():
        return None
    if texte not in _IA:
        _IA[texte] = parser_llm.analyser(texte, tax)
    return _IA[texte]


class Monde:
    def __init__(self, tax: Taxonomie, interpreter: Optional[Callable[[str], Optional[tuple]]] = None):
        self.tax = tax
        self.interpreter = interpreter or (lambda texte: interpreter_ia(texte, tax))
        self.donnees = json.loads((DATA_DIR / "stage_reseau.json").read_text(encoding="utf-8"))
        self.debut = date.fromisoformat(self.donnees["debut"])
        self.memoire = me.Memoire()
        self._secondes = 0
        self.magasin = Magasin(":memory:", horloge=self._horloge)
        self.base = [Profil(**p) for p in self.donnees["profils"]]
        for r in self.donnees["rencontres_passees"]:
            self.memoire.ajouter(me.Evt(type="RENCONTRE", le=date.fromisoformat(r["le"]), acteurs=[r["a"], r["b"]],
                                        statut=Statut.SIMULE, donnees={"evenement": r["evenement"], "raisons": []}))
        self.etape = 0
        self.traces: list[dict] = []
        self.ctx: dict = {}
        self.depart = self.instantane_graphe()

    # ------------------------------------------------------------ temps et données
    def jour(self) -> date:
        return self.memoire.maintenant(self.debut)

    def _horloge(self) -> str:
        self._secondes += 1
        base = datetime.combine(self.jour(), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=9)
        return (base + timedelta(seconds=self._secondes)).isoformat(timespec="seconds")

    def profils(self) -> list[Profil]:
        consent = self.magasin.consentements()
        res = []
        for p in self.base + [Profil(**d) for d in self.magasin.membres_ajoutes()]:
            res.append(p.model_copy(update={"accepte_introductions": consent[p.id]}) if p.id in consent else p)
        return res

    def par_id(self) -> dict[str, Profil]:
        return {p.id: p for p in self.profils()}

    def synchroniser(self) -> date:
        reseau.projeter(self.memoire, self.magasin.relations(), self.magasin.besoins())
        return self.jour()

    def graphe(self) -> nx.Graph:
        return reseau.graphe_de_confiance(self.memoire, self.synchroniser())

    def instantane_graphe(self) -> dict:
        t = self.synchroniser()
        g = self.graphe()
        return {"le": t.isoformat(), "indicateurs": me.indicateurs(g, t),
                "liens": sorted([sorted([a, b]) for a, b in g.edges()])}

    def avancer(self, jours: int) -> date:
        return self.memoire.avancer(jours, self.debut)


# ------------------------------------------------------------------ les étapes : trois scènes, un seul monde
# A — un membre exprime librement un besoin ; B — l'organisatrice compare, voit la fragilité, simule une perte ;
# C — le système refuse ce qui n'est pas fondé et explique son silence. Chaque étape raconte UNE chose.
def _nom(w: Monde, i: str) -> str:
    return w.par_id()[i].nom if i in w.par_id() else i


def _membres(w: Monde) -> list[str]:
    return sorted(p.id for p in w.profils() if p.type == "membre_club")


def _g_actuel(w: Monde) -> nx.Graph:
    t = w.synchroniser()
    g = reseau.graphe_actuel(w.memoire, t)
    g.add_nodes_from(_membres(w))
    return g


def _compris(b) -> list[dict]:
    res = [{"quoi": f"{c.libelle} ({'obligatoire' if c.obligatoire else 'souhaité'})", "extrait": c.extrait} for c in b.criteres]
    res += [{"quoi": f"exclure : {e.libelle}", "extrait": e.extrait} for e in b.exclusions]
    if b.exclure_concurrents:
        res.append({"quoi": "exclure les concurrents directs", "extrait": None})
    return res


def _sophie_rejoint(w: Monde) -> None:
    s = w.donnees["sophie"]
    p = Profil(id=SOPHIE, nom=s["nom"], fonction=s["fonction"], entreprise=s["entreprise"], commune=s["commune"],
               type="membre_club", secteurs=["boissons"], offre=s["offre"], recherche=s["recherche"], langues=s["langues"],
               zones_service=s["zones_service"], creneaux=s["creneaux"], accepte_introductions=False, maj=w.jour().isoformat())
    w.magasin.ajouter_membre(p.model_dump())                 # invisible par défaut…
    w.magasin.changer_consentement(SOPHIE, True)             # …puis elle choisit d'être recommandable


def _a1_besoin_libre(w: Monde) -> dict:
    _sophie_rejoint(w)
    s = w.donnees["sophie"]
    texte = s["besoin_complexe"]
    moi = w.par_id()[SOPHIE]
    regles = analyser(texte, w.tax)
    r_regles = rechercher(regles, moi, w.profils(), w.tax)
    ia = w.interpreter(texte)
    ia_ok = ia is not None and not ia[1].get("erreur") and any(c.type in ("expertise", "texte_libre") for c in ia[0].criteres)
    faits = {"texte": texte,
             "regles": {"compris": _compris(regles), "propositions": len(r_regles.suggestions),
                        "decision": "S_ABSTENIR" if r_regles.abstention else "PROPOSER"}}
    if ia is None:
        faits["ia"] = {"etat": "NON_CONFIGUREE", "message": "Aucun modèle génératif configuré ici : rien n'est simulé à sa place."}
    else:
        b, tele = ia
        faits["ia"] = {"etat": "UTILISEE" if ia_ok else "REPLI", "analyseur": tele.get("analyseur"), "modele": tele.get("modele"),
                       "latence_ms": tele.get("latence_ms"), "compris": _compris(b), "avertissements": b.avertissements,
                       "controle": "catégories du vocabulaire fermé seulement ; chaque extrait doit figurer dans le texte"}
    if ia_ok:
        besoin, faits["retenu"] = ia[0], "INTERPRETATION_IA_VERIFIEE"
    elif not r_regles.abstention:
        besoin, faits["retenu"] = regles, "REGLES"
    else:
        besoin = analyser(s["besoin"], w.tax)             # le produit demande une reformulation courte
        faits["retenu"], faits["reformulation"] = "REFORMULATION", s["besoin"]
        faits["reformulation_comprise"] = _compris(besoin)
    w.ctx["besoin_id"] = w.magasin.creer_besoin(SOPHIE, besoin, publier=True, anonyme=False).id
    return {"scene": "A", "titre": "Sophie écrit son besoin, avec ses mots",
            "dit": "Une phrase réelle : plusieurs besoins, une langue, une exclusion. Qui la comprend, et comment le vérifie-t-on ?",
            "faits": faits}


def _a2_proposition(w: Monde) -> dict:
    t = w.synchroniser()
    ids = w.par_id()
    b = w.magasin.besoin(w.ctx["besoin_id"])
    res = rechercher(b.besoin, ids[SOPHIE], w.profils(), w.tax)
    g = w.graphe()
    cartes = []
    for s in res.suggestions:
        d = reseau.dimensions(w.memoire, ids[SOPHIE], s.model_dump(), ids, t, t, g, w.tax, w.magasin.besoins())
        cartes.append({"id": s.profil.id, "nom": s.profil.nom, "entreprise": s.profil.entreprise, "niveau": s.niveau,
                       "preuves": [{"extrait": p.extrait, "nature": p.nature, "champ": p.champ} for p in s.preuves],
                       "a_verifier": s.a_verifier, "dimensions": d})
    w.ctx["candidat"] = next((c["id"] for c in cartes if c["dimensions"]["reciprocite"]["etablie"]), cartes[0]["id"] if cartes else None)
    return {"scene": "A", "titre": "Une proposition vérifiable",
            "dit": "Pas une liste de noms : seulement des personnes dont le profil PROUVE qu'elles peuvent aider — et ce qui reste inconnu.",
            "faits": {"candidats": cartes, "examines": res.nb_profils_examines,
                      "ecartes_par_leur_choix": sum(e.nombre for e in res.ecartes if "sollicités" in e.raison),
                      "ecartes_autres": [{"raison": e.raison, "nombre": e.nombre} for e in res.ecartes if "sollicités" not in e.raison],
                      "coordonnees": "jamais affichées : partagées seulement après l'accord des deux"}}


def _a3_introduction(w: Monde) -> dict:
    c = w.ctx["candidat"]
    r = w.magasin.creer_relation(w.ctx["besoin_id"], SOPHIE, c, "Bonjour, j'aimerais vous présenter nos tisanes.",
                                 autre_accepte=True, autre_eligible=True)
    w.ctx["relation"] = r.id
    avant = r.coordonnees_partagees
    boite = reseau.boite(w.memoire, w.par_id()[c], w.profils(), w.magasin.relations(c), {}, w.synchroniser())
    r = w.magasin.transition(r.id, "accepter", c)
    w.avancer(7)
    w.magasin.transition(w.ctx["relation"], "planifier", c, date_rencontre=w.jour().isoformat())
    w.magasin.transition(w.ctx["relation"], "confirmer_rencontre", SOPHIE)
    m = reseau.memoire_relation(w.memoire, SOPHIE, c, w.synchroniser())
    return {"scene": "A", "titre": f"{_nom(w, c).split(' ')[0]} accepte ; ils se rencontrent",
            "dit": "Une introduction, pas un numéro. Il pouvait refuser. Les coordonnées ne circulent qu'après son accord.",
            "faits": {"introductions_a_repondre_pour_lui": len(boite["introductions_a_repondre"]),
                      "coordonnees_avant_accord": avant, "coordonnees_apres_accord": r.coordonnees_partagees,
                      "ligne_de_temps": m["ensuite"], "quand": m["quand"], "etat_relation": m["etat"]}}


def _lisible(texte: str) -> str:
    """Affichage de scène : retire les listes brutes de tailles (« ([[8, 5], [8, 5]]) ») ; le calcul reste inchangé."""
    return re.sub(r"\s*\(\[[^()]*\]\)", "", texte)


def _diagnostic(w: Monde) -> dict:
    t = w.synchroniser()
    return dg.diagnostic(w.memoire, w.profils(), cy.besoins_publies(w.memoire, t), w.tax, t, k=1)


def _b1_diagnostic(w: Monde) -> dict:
    d = _diagnostic(w)
    act, membres = _g_actuel(w), _membres(w)
    # seulement les ponts FRAGILES (même définition que le phénomène : ≥ 3 membres de chaque côté), pas les bouts de chaîne
    ponts = [r["paire"] for r in (sante.sans_relation(act, membres, *e) for e in sorted(tuple(sorted(e)) for e in nx.bridges(act.subgraph(membres))))
             if min(len(r["coupes_de_leur_groupe"]), r["taille_du_groupe"] - len(r["coupes_de_leur_groupe"])) >= sante.SEUILS["groupe_min"]]
    return {"scene": "B", "titre": "La vue de l'organisatrice",
            "dit": "Le même réseau, vu d'en haut : ce qu'aucun membre ne voit seul. Des faits, puis leur lecture.",
            "faits": {"etat": d["comprendre"]["etat"],
                      "phenomenes": [{"code": p["phenomene"], "observation": _lisible(p["observation"]), "lecture": p["interpretation"],
                                      "action_possible": p["intervention_possible"]} for p in d["diagnostiquer"]["phenomenes"]],
                      "ponts": ponts, "nature": "OBSERVATION du graphe (réseau FICTIF) ; lectures et seuils = hypothèses de produit"}}


def _b2_deux_plans(w: Monde) -> dict:
    d = _diagnostic(w)
    plans = d["agir"]["plans_nommes"]
    ids = w.par_id()

    def rendu(p: dict) -> dict:
        consolide = p["objectifs"]["cohesion_robuste"] >= max(q["objectifs"]["cohesion_robuste"] for q in plans)
        reunit = p["objectifs"]["cohesion"] >= max(q["objectifs"]["cohesion"] for q in plans)
        libelle = ("Réunir et consolider" if consolide and reunit else "Consolider" if consolide
                   else "Réunir les îlots" if reunit else "Autre compromis")
        return {"libelle": libelle, "noms_moteur": p["noms"], "paires": p["paires"], "plus_grand_groupe": p["objectifs"]["cohesion"],
                "groupe_robuste": p["objectifs"]["cohesion_robuste"], "membres_relies": p["objectifs"]["inclusion"],
                "pourquoi": [{"qui": [_nom(w, x) for x in q["paire"]],
                              "preuve": [f"{ids[x['aide']].nom} offre « {x['preuve']} » — {ids[x['aide_a']].nom} cherche "
                                         f"« {x['besoin'].split(' : ', 1)[-1]} »" for x in q["preuves"]]} for q in p["pourquoi"]]}
    act = _g_actuel(w)
    avant = {"plus_grand_groupe": max(len(c) for c in nx.connected_components(act.subgraph(_membres(w)))),
             "groupe_robuste": pareto.plus_grand_groupe_robuste(act, _membres(w))}
    return {"scene": "B", "titre": "Une seule introduction ce mois-ci : laquelle ?",
            "dit": "Deux plans défendables. Aucun ne gagne sur tout. Le système montre le prix de chacun ; l'humain choisit.",
            "faits": {"budget": 1, "avant": avant, "plans": [rendu(p) for p in plans], "un_seul_plan": len(plans) < 2,
                      "nature": "SIMULATION : chaque introduction est supposée acceptée ; rien n'est envoyé",
                      "lexique": {"plus_grand_groupe": "membres reliés entre eux, directement ou non",
                                  "groupe_robuste": "membres qui restent reliés même si UNE relation quelconque disparaît"}}}


def _b3_disparition(w: Monde) -> dict:
    act, membres = _g_actuel(w), _membres(w)
    e = sante.relation_la_plus_critique(act, membres)
    r = sante.sans_relation(act, membres, *e) if e else {"existe": False}
    if e:
        r["noms"] = [_nom(w, x) for x in r["paire"]]
        r["coupes_noms"] = [_nom(w, x) for x in r["coupes_de_leur_groupe"]]
    return {"scene": "B", "titre": "Et si une relation s'éteignait ?",
            "dit": "Une seule relation tient deux parties du réseau. Si elle s'endort, voici ce que le Club perd — calculé, pas deviné.",
            "faits": r | {"interactif": "cliquer sur n'importe quelle relation du graphe pour simuler sa disparition"}}


def _c1_silence(w: Monde) -> dict:
    t = w.avancer(10)
    w.synchroniser()
    rel = cy.relances(w.memoire, w.profils(), w.tax, t)
    ids = w.par_id()
    props = [{"paire": p["noms"], "raisons": [{"type": r["type"], "pour": ids[r["pour"]].nom, "message": r["message"],
                                               "preuves": r["preuves"]} for r in p["raisons"]]} for p in rel["propositions"]]
    return {"scene": "C", "titre": "Dix jours plus tard : parler, ou se taire ?",
            "dit": "Une relance seulement s'il existe une raison NOUVELLE et prouvée. « Restez en contact » n'en est pas une.",
            "faits": {"relances": props, "silences": rel["abstentions"], "principe": rel["principe"]}}


def _c2_refus(w: Monde) -> dict:
    t = w.synchroniser()
    s = w.donnees["sophie"]
    membres = _membres(w)
    act = _g_actuel(w)
    bes = w.magasin.besoins() + cy.besoins_publies(w.memoire, t)
    etats = reseau.etats_par_paire(w.memoire, t)
    b = analyser(s["besoin_sans_preuve"], w.tax)
    japon = rechercher(b, w.par_id()[SOPHIE], w.profils(), w.tax)
    refuse = next(p.id for p in w.profils() if p.type == "membre_club" and not p.accepte_introductions)
    seul = next(x for x in membres if act.degree(x) == 0 and x != refuse)      # sans aucune relation actuelle

    def raisons(a: str, b: str) -> list[str]:
        return interventions.refus_motives(a, b, w.profils(), bes, w.tax, act, etats)
    # « relier quelqu'un qui est seul, à n'importe qui » : le 1er membre (ordre des identifiants) sans aide prouvée
    autre = next(y for y in membres if y not in (seul, refuse) and raisons(seul, y) and raisons(seul, y)[0].startswith("aucune aide"))
    tentatives = [
        {"qui": "Sophie", "demande": s["besoin_sans_preuve"], "decision": "S_ABSTENIR" if japon.abstention else "PROPOSER",
         "raisons": [japon.message] if japon.abstention else []},
        {"qui": "L'organisatrice", "demande": "Présenter Sophie à un membre qui a refusé d'être présenté (non nommé ici)",
         "decision": "REFUSER", "raisons": raisons(SOPHIE, refuse)},
        {"qui": "L'organisatrice", "decision": "REFUSER",
         "demande": f"Présenter {_nom(w, seul)}, sans aucune relation actuelle, à {_nom(w, autre)} « pour qu'elle ne reste pas seule »",
         "raisons": raisons(seul, autre)},
    ]
    return {"scene": "C", "titre": "Ce que le système refuse de faire",
            "dit": "Plutôt aucune proposition qu'une mauvaise. Chaque refus a une raison que l'on peut vérifier.",
            "faits": {"tentatives": tentatives}}


def _c3_bilan(w: Monde) -> dict:
    t = w.synchroniser()
    return {"scene": "C", "titre": "Ce que vous venez de voir",
            "dit": "Trois rôles, un seul réseau, les mêmes règles. Et une frontière nette entre ce qui est observé et ce qui est simulé.",
            "faits": {"faits_enregistres": sum(1 for e in w.memoire.evenements() if e.type != "HORLOGE"), "le": t.isoformat(),
                      "natures": [
                          {"quoi": "rencontres passées, introduction, accord, rencontre, relance", "nature": "FAIT enregistré (réseau FICTIF)"},
                          {"quoi": "phénomènes du réseau (îlots, ponts fragiles)", "nature": "OBSERVATION calculée sur ces faits"},
                          {"quoi": "effet des deux plans, disparition d'une relation", "nature": "SIMULATION (rien n'est écrit)"},
                          {"quoi": "interprétation par IA", "nature": "VÉRIFIÉE par le code, ou absente — jamais simulée"},
                          {"quoi": "valeur pour un vrai Club", "nature": "NON MESURÉE : à établir par un pilote"}]}}


ETAPES: list[Callable[[Monde], dict]] = [_a1_besoin_libre, _a2_proposition, _a3_introduction,
                                          _b1_diagnostic, _b2_deux_plans, _b3_disparition,
                                          _c1_silence, _c2_refus, _c3_bilan]


def rejouer_jusqu_a(tax: Taxonomie, n: int, interpreter=None) -> Monde:
    w = Monde(tax, interpreter)
    for i in range(max(0, min(n, len(ETAPES)))):
        w.traces.append(ETAPES[i](w) | {"etape": i, "le": w.jour().isoformat()})
        w.etape = i + 1
    return w


# ------------------------------------------------------------------ graphe pour l'affichage (positions stables)
def positions(w: Monde) -> dict[str, list[float]]:
    """Disposition calculée UNE fois sur le réseau complet de scène (graine fixe) : les nœuds ne sautent pas."""
    g = nx.Graph()
    g.add_nodes_from([p.id for p in w.base] + [SOPHIE])
    g.add_edges_from((r["a"], r["b"]) for r in w.donnees["rencontres_passees"])
    g.add_edges_from([(SOPHIE, "s14"), (SOPHIE, "s10"), (SOPHIE, "s01"), (SOPHIE, "s03")])
    relies = g.subgraph(max(nx.connected_components(g), key=len)).copy()
    pos = nx.kamada_kawai_layout(relies)                  # déterministe (pas d'aléa), grappes bien séparées
    xs = [x for x, _ in pos.values()]
    ys = [y for _, y in pos.values()]
    for i, n in enumerate(sorted(set(g.nodes) - set(relies.nodes))):   # isolés : rangés à part, hors de l'échelle
        pos[n] = (min(xs) + 0.12 * i, max(ys) + 0.25)
    return {n: [round(float(x), 4), round(float(y), 4)] for n, (x, y) in pos.items()}


def vue(w: Monde, pos: dict) -> dict:
    t = w.synchroniser()
    g = w.graphe()
    ids = w.par_id()
    # Aucun drapeau de consentement dans la vue : qui refuse les introductions ne doit pas se DEVINER sur le graphe.
    noeuds = [{"id": n, "nom": ids[n].nom if n in ids else n, "x": pos[n][0], "y": pos[n][1], "present": n in ids} for n in pos]
    liens = [{"a": a, "b": b, "statut": d["statut"].value, "types": sorted(d["types"]),
              "force": me.force(d["derniere"], t)} for a, b, d in sorted(g.edges(data=True))]
    return {"etape": w.etape, "total": len(ETAPES), "le": t.isoformat(), "horloge": "SIMULEE",
            "noeuds": noeuds, "liens": liens, "traces": w.traces,
            "avertissement": "Réseau de scène FICTIF : personnes et entreprises inventées, aucune donnée du Club."}


def creer_routeur(tax: Taxonomie) -> APIRouter:
    r = APIRouter(prefix="/api/stage", tags=["scène"])
    verrou = threading.Lock()
    etat = {"monde": Monde(tax)}
    pos = positions(etat["monde"])

    @r.get("")
    def lire():
        with verrou:
            return vue(etat["monde"], pos)

    @r.post("/reinitialiser")
    def reinitialiser():
        with verrou:
            etat["monde"] = Monde(tax)
            return vue(etat["monde"], pos)

    @r.post("/suivant")
    def suivant():
        with verrou:  # double clic : la seconde requête attend, puis avance d'UNE étape, jamais deux fois la même
            w = etat["monde"]
            if w.etape >= len(ETAPES):
                raise HTTPException(409, "La démonstration est terminée : réinitialisez ou rejouez.")
            w.traces.append(ETAPES[w.etape](w) | {"etape": w.etape, "le": w.jour().isoformat()})
            w.etape += 1
            return vue(w, pos)

    @r.get("/sans_relation")
    def sans_relation(a: str = Query(..., max_length=64), b: str = Query(..., max_length=64)):
        """Contrefactuel à la demande (clic sur une relation) : calcul PUR, rien n'est écrit."""
        with verrou:
            w = etat["monde"]
            res = sante.sans_relation(_g_actuel(w), _membres(w), a, b)
            if not res["existe"]:
                raise HTTPException(404, res["raison"])
            return res | {"noms": [_nom(w, x) for x in res["paire"]], "coupes_noms": [_nom(w, x) for x in res["coupes_de_leur_groupe"]]}

    @r.post("/aller/{n}")
    def aller(n: int):
        if not 0 <= n <= len(ETAPES):
            raise HTTPException(422, "Étape hors limites.")
        with verrou:  # « précédent » et « rejouer » : on reconstruit depuis zéro — déterministe
            etat["monde"] = rejouer_jusqu_a(tax, n)
            return vue(etat["monde"], pos)

    return r
