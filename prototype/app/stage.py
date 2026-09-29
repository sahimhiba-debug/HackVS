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
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Callable

import networkx as nx
from fastapi import APIRouter, HTTPException, Query

from adaptateurs.club import diagnostic as dg
from adaptateurs.club import interventions, pareto, reseau, sante
from adaptateurs.club.interventions import indicateurs_actuels
from adaptateurs.club import cycle as cy
from plateforme import memoire as me
from plateforme.affirmations import Statut

from .matching import rechercher
from .models import Profil
from .parser_rules import analyser, extraire_profil
from .store import Magasin
from .taxonomy import DATA_DIR, Taxonomie

SOPHIE = "n01"


class Monde:
    def __init__(self, tax: Taxonomie):
        self.tax = tax
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


# ------------------------------------------------------------------ les étapes : UNE histoire, un seul monde
# nouveau membre → besoin → candidats (pourquoi) → consentement → rencontre → suivi → opportunité → le réseau qui
# évolue → l'abstention (« je pourrais… ») → la saturation → le bilan. Chaque étape raconte UNE chose ; chaque chiffre
# est calculé par le moteur réutilisable (aucune règle propre à la scène).
def _nom(w: Monde, i: str) -> str:
    return w.par_id()[i].nom if i in w.par_id() else i


def _membres(w: Monde) -> list[str]:
    return sorted(p.id for p in w.profils() if p.type == "membre_club")


def _g_actuel(w: Monde) -> nx.Graph:
    t = w.synchroniser()
    g = reseau.graphe_actuel(w.memoire, t)
    g.add_nodes_from(_membres(w))
    return g


def _contexte_reseau(w: Monde) -> tuple:
    t = w.synchroniser()
    return _g_actuel(w), cy.besoins_actifs(w.magasin.besoins(), w.memoire, t), reseau.etats_par_paire(w.memoire, t)


def _e1_nouveau_membre(w: Monde) -> dict:
    s = w.donnees["sophie"]
    proposition = extraire_profil(s["description"], w.tax)
    p = Profil(id=SOPHIE, nom=s["nom"], fonction=s["fonction"], entreprise=s["entreprise"], commune=s["commune"],
               type="membre_club", secteurs=["boissons"], offre=s["offre"], recherche=s["recherche"], langues=s["langues"],
               zones_service=s["zones_service"], creneaux=s["creneaux"], accepte_introductions=False, maj=w.jour().isoformat())
    w.magasin.ajouter_membre(p.model_dump())                 # invisible par défaut…
    invisible = not w.par_id()[SOPHIE].accepte_introductions
    w.magasin.changer_consentement(SOPHIE, True)             # …puis elle choisit d'être recommandable
    return {"titre": "Sophie rejoint le Club", "dit": "Elle ne connaît personne. Une phrase suffit pour son profil.",
            "faits": {"description": s["description"],
                      "propose": [f"{k} : {o['libelle']}" for k in ("offre", "recherche") for o in proposition[k]],
                      "valide": [f"offre : {w.tax.libelle(o['concept'])}" for o in s["offre"]]
                                + [f"recherche : {w.tax.libelle(o['concept'])}" for o in s["recherche"]],
                      "invisible_par_defaut": invisible, "coordonnees_enregistrees": "aucune"}}


def _e2_besoin(w: Monde) -> dict:
    s = w.donnees["sophie"]
    b = analyser(s["besoin"], w.tax)
    w.ctx["besoin_id"] = w.magasin.creer_besoin(SOPHIE, b, publier=True, anonyme=False).id
    exp = [c for c in b.criteres if c.type == "expertise"]
    compris = [{"role": "besoin principal" if c is (exp[0] if exp else None) else ("langue" if c.type == "langue" else "critère"),
                "quoi": c.libelle, "extrait": c.extrait, "note": c.note} for c in b.criteres]
    if b.exclure_concurrents:
        compris.append({"role": "contrainte", "quoi": "pas un concurrent direct", "extrait": None, "note": None})
    return {"titre": "Son besoin, avec ses mots", "dit": f"« {s['besoin']} »",
            "faits": {"compris": compris, "incertain": [a.terme for a in b.ambiguites] + b.avertissements,
                      "analyse": "règles locales et vérifiables : aucune IA générative, aucun appel réseau"}}


def _e3_candidats(w: Monde) -> dict:
    t = w.synchroniser()
    ids = w.par_id()
    b = w.magasin.besoin(w.ctx["besoin_id"])
    res = rechercher(b.besoin, ids[SOPHIE], w.profils(), w.tax)
    g = w.graphe()
    cartes = []
    for sug in res.suggestions:
        d = reseau.dimensions(w.memoire, ids[SOPHIE], sug.model_dump(), ids, t, t, g, w.tax, w.magasin.besoins())
        cartes.append({"id": sug.profil.id, "nom": sug.profil.nom, "entreprise": sug.profil.entreprise, "niveau": sug.niveau,
                       "preuves": [{"extrait": p.extrait, "nature": p.nature, "champ": p.champ} for p in sug.preuves],
                       "dimensions": d})
    w.ctx["candidat"] = next((c["id"] for c in cartes if c["dimensions"]["reciprocite"]["etablie"]), cartes[0]["id"] if cartes else None)
    return {"titre": "Qui peut l'aider — et pourquoi", "dit": "Pas une liste de noms : une preuve pour chaque proposition.",
            "faits": {"candidats": cartes, "examines": res.nb_profils_examines,
                      "ecartes_par_leur_choix": sum(e.nombre for e in res.ecartes if "sollicités" in e.raison)}}


def _e4_consentement(w: Monde) -> dict:
    c = w.ctx["candidat"]
    r = w.magasin.creer_relation(w.ctx["besoin_id"], SOPHIE, c, "Bonjour, j'aimerais vous présenter nos tisanes.",
                                 autre_accepte=True, autre_eligible=True)
    w.ctx["relation"] = r.id
    avant = r.coordonnees_partagees
    boite = reseau.boite(w.memoire, w.par_id()[c], w.profils(), w.magasin.relations(c), {}, w.synchroniser())
    r = w.magasin.transition(r.id, "accepter", c)
    return {"titre": "Une introduction, pas un numéro", "dit": f"{_nom(w, c).split(' ')[0]} reçoit la demande. Il peut refuser.",
            "faits": {"introductions_a_repondre_pour_lui": len(boite["introductions_a_repondre"]),
                      "coordonnees_avant_accord": avant, "coordonnees_apres_accord": r.coordonnees_partagees}}


def _e5_rencontre(w: Monde) -> dict:
    c = w.ctx["candidat"]
    w.avancer(7)
    w.magasin.transition(w.ctx["relation"], "planifier", c, date_rencontre=w.jour().isoformat())
    w.magasin.transition(w.ctx["relation"], "confirmer_rencontre", SOPHIE)
    m = reseau.memoire_relation(w.memoire, SOPHIE, c, w.synchroniser())
    return {"titre": "Ils se rencontrent", "dit": "Une relation naît, avec son contexte : quand, pourquoi, et la suite.",
            "faits": {"quand": m["quand"], "etat_relation": m["etat"], "ligne_de_temps": m["ensuite"]}}


def _e6_suivi(w: Monde) -> dict:
    t = w.avancer(10)
    w.synchroniser()
    rel = cy.relances(w.memoire, w.profils(), w.tax, t)
    ids = w.par_id()
    props = [{"paire": p["noms"], "raisons": [{"type": r["type"], "pour": ids[r["pour"]].nom, "message": r["message"],
                                               "preuves": r["preuves"], "id": r["id"]} for r in p["raisons"]]} for p in rel["propositions"]]
    w.ctx["relance"] = next((r["id"] for p in rel["propositions"] for r in p["raisons"] if SOPHIE in p["paire"]), None)
    return {"titre": "Dix jours plus tard : parler, ou se taire ?",
            "dit": "Une relance seulement s'il existe une raison NOUVELLE et prouvée.",
            "faits": {"relances": props, "silences": rel["abstentions"], "principe": rel["principe"]}}


def _e7_opportunite(w: Monde) -> dict:
    c = w.ctx["candidat"]
    rep = cy.repondre(w.memoire, w.profils(), w.tax, w.jour(), w.ctx["relance"], True, c) if w.ctx.get("relance") else {"suivi": False}
    w.magasin.transition(w.ctx["relation"], "cloturer", SOPHIE, resultat="affaire_en_cours")
    etat = reseau.etat_relation(w.memoire, SOPHIE, c, w.synchroniser())
    return {"titre": "Le suivi devient une opportunité", "dit": "Une affaire en cours : une opportunité, pas encore un résultat.",
            "faits": {"suivi": rep.get("suivi"), "etat_relation": etat["etat"], "libelle": etat["libelle"],
                      "ligne_de_temps": [f["type"] for f in etat["faits"]]}}


def _mesure(g: nx.Graph, membres: list[str]) -> dict:
    i = indicateurs_actuels(g, membres)
    return {"groupes": i["groupes_actuels"], "plus_grand_groupe": i["plus_grand_groupe"],
            "isoles": i["sans_relation_actuelle"], "groupe_robuste": pareto.plus_grand_groupe_robuste(g, membres)}


def _e8_reseau(w: Monde) -> dict:
    t = w.synchroniser()
    membres = _membres(w)
    d = dg.diagnostic(w.memoire, w.profils(), cy.besoins_publies(w.memoire, t), w.tax, t, k=3)
    plans = d["agir"]["plans_nommes"]
    avant = _g_actuel(w)
    if not plans:
        return {"titre": "Le réseau qui évolue", "dit": "Aucune action fondée : ne rien faire.", "faits": {"plan": None}}
    plan = next((p for p in plans if "EQUILIBRE" in p["noms"]), plans[0])
    apres, ponts = avant.copy(), 0
    for a, b in plan["paires"]:
        ponts += not nx.has_path(apres, a, b)
        apres.add_edge(a, b)
    preuves = [x for q in plan["pourquoi"] for x in q["preuves"]]
    return {"titre": "Le réseau qui évolue", "dit": "Ce mois-ci, trois introductions prouvées. Avant, après.",
            "faits": {"avant": _mesure(avant, membres), "apres": _mesure(apres, membres), "paires": plan["paires"],
                      "introductions": [{"qui": [_nom(w, x) for x in q["paire"]], "reciproque": q["reciproque"]} for q in plan["pourquoi"]],
                      "nouveaux_ponts": ponts, "membres_servis": len({x["aide_a"] for x in preuves}),
                      "besoins_couverts": len({(x["aide_a"], x["besoin"]) for x in preuves}),
                      "reciproques": sum(q["reciproque"] for q in plan["pourquoi"]),
                      "autres_plans": len(plans) - 1, "nature": "SIMULATION : introductions supposées acceptées ; rien n'est envoyé",
                      "lexique": "robuste = reste relié même si UNE relation quelconque disparaît"}}


def _e9_abstention(w: Monde) -> dict:
    g, bes, etats = _contexte_reseau(w)
    seul = next(x for x in _membres(w) if g.degree(x) == 0 and w.par_id()[x].accepte_introductions)
    r = interventions.relier_sans_preuve(seul, w.profils(), bes, w.tax, g, etats)
    japon = rechercher(analyser(w.donnees["sophie"]["besoin_sans_preuve"], w.tax), w.par_id()[SOPHIE], w.profils(), w.tax)
    ress = r["par_ressemblance"]
    return {"titre": "Je pourrais inventer une connexion. Je préfère m'abstenir.",
            "dit": f"{_nom(w, seul)} n'a aucune relation. La relier ferait baisser l'indicateur « isolés ».",
            "faits": {"membre": _nom(w, seul), "membre_id": seul, "introductions_possibles": r["introductions_possibles"],
                      "introductions_fondees": len(r["introductions_fondees"]), "decision": r["decision"],
                      "raisons": r["raisons"], "ce_qui_changerait": r["ce_qui_changerait"],
                      "par_ressemblance": ({"id": ress["membre"], "nom": _nom(w, ress["membre"]), "ressemblance": ress["ressemblance"]}
                                           if ress else None),
                      "japon": {"demande": w.donnees["sophie"]["besoin_sans_preuve"],
                                "decision": "S_ABSTENIR" if japon.abstention else "PROPOSER", "examines": japon.nb_profils_examines}}}


def _e10_saturation(w: Monde) -> dict:
    g, bes, _ = _contexte_reseau(w)
    r = cy.soirees_successives(w.profils(), bes, w.tax, g, n=3, tours=3)
    return {"titre": "Trois soirées de suite", "dit": "Les rencontres utiles s'épuisent. Le système ne les fabrique pas.",
            "faits": r}


def _e11_bilan(w: Monde) -> dict:
    t = w.synchroniser()
    return {"titre": "Des rencontres ponctuelles, un réseau vivant",
            "dit": "Ce qui est un fait, ce qui est simulé, ce qui reste à prouver.",
            "faits": {"faits_enregistres": sum(1 for e in w.memoire.evenements() if e.type != "HORLOGE"), "le": t.isoformat(),
                      "natures": [
                          {"quoi": "rencontres, introduction, accord, relance, opportunité", "nature": "FAIT enregistré (réseau FICTIF)"},
                          {"quoi": "réseau avant / après, soirées successives", "nature": "SIMULATION (rien n'est écrit)"},
                          {"quoi": "compréhension du besoin", "nature": "RÈGLES vérifiables, sans IA générative"},
                          {"quoi": "valeur pour un vrai Club", "nature": "NON MESURÉE : à établir par un pilote"}]}}


ETAPES: list[Callable[[Monde], dict]] = [_e1_nouveau_membre, _e2_besoin, _e3_candidats, _e4_consentement, _e5_rencontre,
                                          _e6_suivi, _e7_opportunite, _e8_reseau, _e9_abstention, _e10_saturation, _e11_bilan]


def rejouer_jusqu_a(tax: Taxonomie, n: int) -> Monde:
    w = Monde(tax)
    for i in range(max(0, min(n, len(ETAPES)))):
        w.traces.append(ETAPES[i](w) | {"etape": i, "le": w.jour().isoformat()})
        w.etape = i + 1
    return w


# ------------------------------------------------------------------ tour de contrôle (vue organisation, lecture seule)
def tour(w: Monde) -> list[dict]:
    """Que se passe-t-il dans le réseau ? Chaque chiffre = une définition + les éléments comptés (aucun score)."""
    t = w.synchroniser()
    g, bes, etats = _contexte_reseau(w)
    membres = _membres(w)
    ids = w.par_id()
    nom = lambda x: ids[x].nom if x in ids else x  # noqa: E731
    rel = cy.relances(w.memoire, w.profils(), w.tax, t)
    cands = interventions.candidates(w.profils(), bes, w.tax, g, etats)
    comp = {x: i for i, c in enumerate(nx.connected_components(g.subgraph(membres))) for x in c}
    ponts = [c for c in cands if comp.get(c.a) != comp.get(c.b)]
    par_etat: dict[str, list] = {}
    for cle_paire, e in sorted(etats.items()):
        par_etat.setdefault(e, []).append(" – ".join(nom(x) for x in cle_paire.split("|")))
    ajoutes = [d["nom"] for d in w.magasin.membres_ajoutes()]
    return [
        {"cle": "nouveaux_membres", "libelle": "nouveaux membres", "valeur": len(ajoutes), "elements": ajoutes,
         "definition": "membres inscrits depuis le début de la démonstration"},
        {"cle": "besoins_actifs", "libelle": "besoins actifs", "valeur": len(bes),
         "elements": [f"{nom(b.auteur_id)} : {b.besoin.texte[:70]}" for b in bes],
         "definition": "besoins publiés et non clos (brouillons privés exclus)"},
        {"cle": "introductions", "libelle": "introductions", "valeur": len(w.magasin.relations()),
         "elements": [f"{nom(r.auteur_id)} → {nom(r.aidant_id)} : {r.libelle_etat}" for r in w.magasin.relations()],
         "definition": "demandes d'introduction, quel que soit leur état (double accord)"},
        {"cle": "suivis", "libelle": "relances fondées", "valeur": sum(len(p["raisons"]) for p in rel["propositions"]),
         "elements": [" – ".join(p["noms"]) + " : " + ", ".join(r["type"] for r in p["raisons"]) for p in rel["propositions"]],
         "definition": f"raison NOUVELLE et prouvée ; {rel['abstentions']['rien_de_nouveau']} paires sans rien de nouveau (silence)"},
        {"cle": "opportunites", "libelle": "opportunités", "valeur": len(par_etat.get("OPPORTUNITE", [])),
         "elements": par_etat.get("OPPORTUNITE", []), "definition": "relations où une affaire est déclarée en cours (pas un résultat)"},
        {"cle": "a_raviver", "libelle": "relations endormies", "valeur": len(par_etat.get("A_RAVIVER", [])),
         "elements": par_etat.get("A_RAVIVER", []), "definition": "aucune interaction depuis plus de 90 jours (hypothèse de produit)"},
        {"cle": "isoles", "libelle": "membres sans relation actuelle", "valeur": sum(1 for x in membres if g.degree(x) == 0),
         "elements": [nom(x) for x in membres if g.degree(x) == 0], "definition": "aucune relation de moins de 90 jours"},
        {"cle": "ponts_potentiels", "libelle": "ponts potentiels", "valeur": len(ponts),
         "elements": [f"{nom(c.a)} – {nom(c.b)} : « {c.preuves[0]['preuve'][:60]} »" for c in ponts],
         "definition": "introductions avec aide prouvée qui relieraient deux groupes aujourd'hui séparés"},
    ]


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

    @r.get("/tour")
    def tour_de_controle():
        """Vue ORGANISATION du même monde : chaque chiffre avec sa définition et ce qu'il compte (lecture seule)."""
        with verrou:
            w = etat["monde"]
            return {"le": w.jour().isoformat(), "indicateurs": tour(w), "donnees_fictives": True}

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
