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
from fastapi import APIRouter, HTTPException

from adaptateurs.club import cercles, reseau
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


# ------------------------------------------------------------------ les étapes (chacune raconte UNE chose)
def _e0_club(w: Monde) -> dict:
    ind = w.depart["indicateurs"]
    return {"titre": "Le Club aujourd'hui", "dit": "Des rencontres ont eu lieu. Mais le réseau reste fait d'îlots.",
            "faits": {"membres": len(w.base), "liens": ind["liens"], "groupes_separes": ind["composantes"],
                      "rencontres_sans_suite_depuis_90_jours": sum(1 for r in w.donnees["rencontres_passees"]
                                                                   if (w.jour() - date.fromisoformat(r["le"])).days > 90)}}


def _e1_adhesion(w: Monde) -> dict:
    s = w.donnees["sophie"]
    proposition = extraire_profil(s["description"], w.tax)
    p = Profil(id=SOPHIE, nom=s["nom"], fonction=s["fonction"], entreprise=s["entreprise"], commune=s["commune"],
               type="membre_club", secteurs=["boissons"], offre=s["offre"], recherche=s["recherche"], langues=s["langues"],
               zones_service=s["zones_service"], creneaux=s["creneaux"], accepte_introductions=False, maj=w.jour().isoformat())
    w.magasin.ajouter_membre(p.model_dump())
    invisible = not w.par_id()[SOPHIE].accepte_introductions
    w.magasin.changer_consentement(SOPHIE, True)
    return {"titre": "Sophie rejoint le Club", "dit": "Elle ne connaît personne. Elle décrit son entreprise ; le système propose, elle valide.",
            "faits": {"description": s["description"],
                      "propose": [f"{'offre' if k == 'offre' else 'recherche'} : {o['libelle']} — « {o['texte']} »"
                                  for k in ("offre", "recherche") for o in proposition[k]],
                      "valide": [f"offre : {w.tax.libelle(o['concept'])} — « {o['texte']} »" for o in s["offre"]]
                                + [f"recherche : {w.tax.libelle(o['concept'])} — « {o['texte']} »" for o in s["recherche"]],
                      "corrections_de_sophie": "« tisanes » hors catalogue → classée en Boissons ; « étiquetage » écarté (elle cherche une traduction)",
                      "invisible_par_defaut": invisible, "puis": "elle choisit d'être recommandable",
                      "coordonnees_enregistrees": "aucune"}}


def _e2_besoin(w: Monde) -> dict:
    s = w.donnees["sophie"]
    b = analyser(s["besoin"], w.tax)
    enr = w.magasin.creer_besoin(SOPHIE, b, publier=True, anonyme=False)
    w.ctx["besoin_id"] = enr.id
    return {"titre": "Elle exprime un besoin", "dit": f"« {s['besoin']} »",
            "faits": {"compris": [f"{c.libelle} ({'obligatoire' if c.obligatoire else 'souhaité'})" for c in b.criteres],
                      "analyse": "règles locales (aucun appel à un modèle externe)"}}


def _e3_candidats(w: Monde) -> dict:
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
        # (pas de simulation sur la carte : « portée après le lien » révélerait le nombre de relations du candidat)
    w.ctx["candidat"] = cartes[0]["id"] if cartes else None
    return {"titre": "Le réseau cherche", "dit": "Pas une liste de noms : seulement les personnes dont le profil PROUVE qu'elles peuvent aider.",
            "faits": {"candidats": cartes, "examines": res.nb_profils_examines,
                      "ecartes_par_leur_choix": sum(e.nombre for e in res.ecartes if "sollicités" in e.raison),
                      "ecartes_autres": [{"raison": e.raison, "nombre": e.nombre} for e in res.ecartes if "sollicités" not in e.raison]}}


def _e4_limites(w: Monde) -> dict:
    s = w.donnees["sophie"]
    b = analyser(s["besoin_sans_preuve"], w.tax)
    res = rechercher(b, w.par_id()[SOPHIE], w.profils(), w.tax)
    return {"titre": "Ce que le système refuse de faire", "dit": "Il ne donne pas le numéro de Markus. Et quand il ne sait pas, il le dit.",
            "faits": {"coordonnees": "jamais affichées : partagées seulement après l'accord des deux (double accord)",
                      "autre_demande": s["besoin_sans_preuve"], "decision": "S_ABSTENIR" if res.abstention else "PROPOSER",
                      "message": res.message}}


def _e5_introduction(w: Monde) -> dict:
    c = w.ctx["candidat"]
    r = w.magasin.creer_relation(w.ctx["besoin_id"], SOPHIE, c, "Bonjour, j'aimerais vous présenter nos tisanes.",
                                 autre_accepte=True, autre_eligible=True)
    w.ctx["relation"] = r.id
    t = w.synchroniser()
    boite = reseau.boite(w.memoire, w.par_id()[c], w.profils(), w.magasin.relations(c), {}, t)
    return {"titre": "Une introduction, pas un numéro",
            "dit": f"Sophie demande une introduction. {w.par_id()[c].nom} reçoit une demande — il est libre de refuser.",
            "faits": {"etat": r.libelle_etat, "coordonnees_partagees": r.coordonnees_partagees,
                      "boite_de_markus": {"introductions_a_repondre": len(boite["introductions_a_repondre"])}}}


def _e6_accord(w: Monde) -> dict:
    c = w.ctx["candidat"]
    r = w.magasin.transition(w.ctx["relation"], "accepter", c)
    etat = reseau.etat_relation(w.memoire, SOPHIE, c, w.synchroniser())
    return {"titre": f"{w.par_id()[c].nom.split(' ')[0]} accepte",
            "dit": "Maintenant seulement, les coordonnées sont partagées. Une relation naît dans le graphe.",
            "faits": {"coordonnees_partagees": r.coordonnees_partagees, "etat_relation": etat["etat"], "libelle": etat["libelle"]}}


def _e7_rencontre(w: Monde) -> dict:
    c = w.ctx["candidat"]
    w.avancer(7)
    w.magasin.transition(w.ctx["relation"], "planifier", c, date_rencontre=w.jour().isoformat())
    w.magasin.transition(w.ctx["relation"], "confirmer_rencontre", SOPHIE)
    m = reseau.memoire_relation(w.memoire, SOPHIE, c, w.synchroniser())
    return {"titre": "Ils se rencontrent", "dit": "La rencontre est enregistrée, avec son contexte.",
            "faits": {"quand": m["quand"], "ou": m["ou"], "etat_relation": m["etat"], "ensuite": m["ensuite"]}}


def _e8_dix_jours(w: Monde) -> dict:
    t = w.avancer(10)
    w.synchroniser()
    rel = cy.relances(w.memoire, w.profils(), w.tax, t)
    ids = w.par_id()
    props = [{"paire": p["noms"], "raisons": [{"type": r["type"], "pour": ids[r["pour"]].nom, "message": r["message"],
                                               "preuves": r["preuves"], "id": r["id"]} for r in p["raisons"]]} for p in rel["propositions"]]
    w.ctx["relance"] = next((r["id"] for p in rel["propositions"] for r in p["raisons"] if SOPHIE in p["paire"]), None)
    a_raviver = [p for p in w.profils() if reseau.etat_relation(w.memoire, "s04", p.id, t)["etat"] == "A_RAVIVER"]
    return {"titre": "Dix jours plus tard", "dit": "Là où les cartes de visite finissent dans un tiroir, le système cherche une raison réelle de se reparler.",
            "faits": {"relances": props, "silences": rel["abstentions"],
                      "principe": rel["principe"], "relations_a_raviver_exemple": [p.nom for p in a_raviver][:2]}}


def _e9_suivi(w: Monde) -> dict:
    c = w.ctx["candidat"]
    rep = cy.repondre(w.memoire, w.profils(), w.tax, w.jour(), w.ctx["relance"], True, c) if w.ctx.get("relance") else {"suivi": False}
    w.magasin.transition(w.ctx["relation"], "cloturer", SOPHIE, resultat="affaire_en_cours")
    etat = reseau.etat_relation(w.memoire, SOPHIE, c, w.synchroniser())
    return {"titre": "Le suivi, puis l'opportunité",
            "dit": "Markus donne suite. Sophie note : affaire en cours. C'est une opportunité, pas encore un résultat.",
            "faits": {"suivi": rep.get("suivi"), "etat_relation": etat["etat"], "libelle": etat["libelle"],
                      "ligne_de_temps": [f["type"] for f in etat["faits"]]}}


def _e10_combinaison(w: Monde) -> dict:
    t = w.synchroniser()
    g = w.graphe()
    opps = cy.opportunites(w.memoire, w.profils(), w.tax, t)
    cercle = cercles.proposer(SOPHIE, w.profils(), w.magasin.besoins(), w.tax, g, theme="Export vers l'Allemagne", maintenant=t)
    w.ctx["cercle"] = cercle
    ids = w.par_id()
    return {"titre": "Une nouvelle combinaison apparaît", "dit": "Le réseau voit ce qu'aucun membre ne voit seul.",
            "faits": {"presentations_possibles": [{"a": ids[o["a"]].nom, "c": ids[o["c"]].nom, "via": ids[o["via"]].nom,
                                                  "confidentialite": f"proposée d'abord à {ids[o['via']].nom}, qui les connaît tous deux"} for o in opps],
                      "micro_cercle": cercle}}


def _e11_avant_apres(w: Monde) -> dict:
    t = w.synchroniser()
    g = w.graphe()
    cercle = w.ctx.get("cercle") or {}
    ajouts = [tuple(p) for p in cercle.get("nouveaux_liens", [])]
    sim = reseau.simuler(g, ajouts, t, focus=[SOPHIE])
    return {"titre": "Le réseau, avant et après", "dit": "Avant d'agir, on simule. L'humain décide.",
            "faits": {"depart": _visibles(w.depart["indicateurs"]), "maintenant": _visibles(me.indicateurs(g, t)),
                      "si_le_cercle_a_lieu": _visibles(sim["apres"]),
                      "nouveaux_ponts": len(sim["nouveaux_ponts"]), "nature": "SIMULATION", "hypothese": sim["hypothese"],
                      "decision": "Proposé à la décision humaine : l'organisatrice et chaque membre décident. Rien n'est envoyé."}}


def _visibles(ind: dict) -> dict:
    """Seulement des COMPTES factuels ; « liens actifs » dépend d'une hypothèse de décroissance : pas affiché en scène."""
    return {k: ind[k] for k in ("membres_relies", "liens", "composantes", "plus_grande_composante", "portee_moyenne_2_sauts")}


ETAPES: list[Callable[[Monde], dict]] = [_e0_club, _e1_adhesion, _e2_besoin, _e3_candidats, _e4_limites, _e5_introduction,
                                          _e6_accord, _e7_rencontre, _e8_dix_jours, _e9_suivi, _e10_combinaison, _e11_avant_apres]


def rejouer_jusqu_a(tax: Taxonomie, n: int) -> Monde:
    w = Monde(tax)
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

    @r.post("/aller/{n}")
    def aller(n: int):
        if not 0 <= n <= len(ETAPES):
            raise HTTPException(422, "Étape hors limites.")
        with verrou:  # « précédent » et « rejouer » : on reconstruit depuis zéro — déterministe
            etat["monde"] = rejouer_jusqu_a(tax, n)
            return vue(etat["monde"], pos)

    return r
