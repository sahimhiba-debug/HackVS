"""Mode SCÈNE « Le Club répond » (/demo/club-repond) : une demande débloquée, de bout en bout, puis le jury essaie.

- Données : `data/stage_reseau.json` (réseau FICTIF de scène, aucune donnée du Club) ; moteur :
  `adaptateurs.club.deblocage` + l'analyse de phrases et le moteur de mise en relation de l'application.
- Les gestes HUMAINS (accepter, contribuer, confirmer) sont JOUÉS par la présentation et marqués « joué » ;
  tout le reste est CALCULÉ en direct par le moteur. Horloge simulée. Aucune IA générative, aucun appel réseau.
- Le mode jury (`/essayer`) est un calcul PUR : il n'écrit rien et ne sollicite personne.
"""
from __future__ import annotations

import json
import threading
from datetime import date, timedelta
from typing import Callable

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from adaptateurs.club import deblocage as db
from plateforme.memoire import Memoire

from .models import Profil
from .parser_rules import analyser
from .taxonomy import DATA_DIR, Taxonomie

SOPHIE, PAULINE = "n01", "s01"
DEMANDE = ("Pour le salon de Munich, je dois faire traduire mes étiquettes en allemand et décrocher un rendez-vous avec "
           "un distributeur en Allemagne, pas un concurrent, qui parle français.")
PROCHAINE = "des étiquettes en allemand prêtes à imprimer et un rendez-vous fixé avec un distributeur pour le salon"
DEMANDE_2 = "Je dois faire traduire mes étiquettes de vin en allemand pour un salon à Stuttgart."
DEMANDE_3 = "Je cherche un distributeur au Japon pour nos tisanes."
FICHE_TITRE = "Fiche : étiqueter un produit alimentaire pour l'Allemagne"
FICHE = """Mentions à traduire (règlement européen sur l'information des consommateurs, dit « INCO ») :
1. Dénomination de vente (Bezeichnung des Lebensmittels) : décrire le produit, pas seulement la marque.
2. Liste des ingrédients (Zutaten), par ordre décroissant ; allergènes mis en évidence (gras).
3. Quantité nette (Nettofüllmenge) et date de durabilité minimale (« mindestens haltbar bis »).
4. Nom et adresse de l'exploitant ; pays d'origine lorsque son omission pourrait induire en erreur.
5. Déclaration nutritionnelle (Nährwertdeklaration) sous forme de tableau.
Pièges fréquents : traduire mot à mot « tisane » (Kräutertee), oublier l'allemand sur l'étiquette arrière,
confondre « à consommer de préférence avant » et « à consommer jusqu'au » (verbrauchen bis).
À faire relire par un professionnel avant impression : cette fiche est une aide, pas un avis juridique."""
INTRO = ("Rendez-vous de 20 minutes proposé sur le salon, le mardi matin (créneau commun). Markus place déjà des produits "
         "alimentaires dans des magasins bio en Allemagne ; il apportera sa grille de conditions de représentation.")


class Monde:
    def __init__(self, tax: Taxonomie):
        self.tax = tax
        d = json.loads((DATA_DIR / "stage_reseau.json").read_text(encoding="utf-8"))
        s = d["sophie"]
        self.debut = date.fromisoformat(d["debut"])
        self.profils = [Profil(**p) for p in d["profils"]] + [Profil(
            id=SOPHIE, nom=s["nom"], fonction=s["fonction"], entreprise=s["entreprise"], commune=s["commune"],
            type="membre_club", secteurs=["boissons"], offre=s["offre"], recherche=s["recherche"], langues=s["langues"],
            zones_service=s["zones_service"], creneaux=s["creneaux"], accepte_introductions=True, maj=d["debut"])]
        self.par_id = {p.id: p for p in self.profils}
        self.m = Memoire()
        self.jour = self.debut
        self.etape = 0
        self.traces: list[dict] = []
        self.ctx: dict = {}

    def nom(self, i: str) -> str:
        return self.par_id[i].nom if i in self.par_id else i

    def plan(self, texte: str, demandeur: str) -> tuple:
        b = analyser(texte, self.tax)
        return b, db.plan(b, self.par_id[demandeur], self.profils, self.tax, db.charge(self.m))


def _ligne_plan(e: dict) -> dict:
    return {"etape": e["libelle"], "extrait": e["extrait"],
            "qui": e["principal"]["nom"] if e["principal"] else None,
            "preuve": e["principal"]["preuve"] if e["principal"] else None,
            "niveau": e["principal"]["niveau"] if e["principal"] else None,
            "reserve": e["reserve"]["nom"] if e["reserve"] else None, "manque": e["manque"]}


# ------------------------------------------------------------------ l'histoire, en 8 temps
def _t1_demande(w: Monde) -> dict:
    b, pl = w.plan(DEMANDE, SOPHIE)
    w.ctx["b"], w.ctx["plan"] = b, pl
    w.ctx["d1"] = db.ouvrir(w.m, w.jour, w.par_id[SOPHIE], DEMANDE, PROCHAINE, b, anonyme=True)
    return {"titre": "Sophie formule UNE demande", "dit": f"« {DEMANDE} »", "joue": ["Sophie écrit sa demande"],
            "faits": {"etapes": [{"etape": e["libelle"], "extrait": e["extrait"]} for e in pl["etapes"]],
                      "contraintes": [c["libelle"] + (f" ← « {c['extrait']} »" if c["extrait"] else "") for c in pl["contraintes"]],
                      "effet_attendu": PROCHAINE, "question": db.question_decisive(b, w.par_id[SOPHIE], w.profils, w.tax),
                      "analyse": "règles locales et vérifiables : chaque étape cite le mot qui la justifie"}}


def _t2_plan(w: Monde) -> dict:
    pl = w.ctx["plan"]
    return {"titre": "Deux personnes, pas une liste", "dit": "Le plus petit groupe qui couvre toute la demande, sur preuve.",
            "joue": [], "faits": {"plan": [_ligne_plan(e) for e in pl["etapes"]], "sollicitees": pl["personnes_sollicitees"],
                                  "non_derangees": pl["membres_non_derange"], "couverture": pl["couverture"],
                                  "coulisses": "vue de démonstration : Sophie, elle, ne voit aucun nom avant un accord"}}


def _t3_sollicitations(w: Monde) -> dict:
    pl, d1 = w.ctx["plan"], w.ctx["d1"]
    for e in pl["etapes"]:
        ok = {x["id"] for x in (e["principal"], e["reserve"]) if x}
        db.solliciter(w.m, w.jour, d1, e["id"], e["principal"]["id"], ok)
    anna = pl["etapes"][0]["principal"]["id"]
    return {"titre": "Chacun ne voit que sa part", "dit": "Anna reçoit une sollicitation privée. Voici exactement ce qu'elle voit.",
            "joue": [], "faits": {"vue_anna": db.vue_sollicitation(w.m, d1, anna, w.profils),
                                  "vue_sophie": db.vue_demandeur(w.m, d1, SOPHIE, w.profils),
                                  "invisible": "Anna ignore l'étape « Allemagne » et Markus ; Sophie ignore qui a été sollicité"}}


def _t4_contributions(w: Monde) -> dict:
    pl, d1 = w.ctx["plan"], w.ctx["d1"]
    w.jour += timedelta(days=2)
    trad, exp = pl["etapes"]
    anna, markus = trad["principal"]["id"], exp["principal"]["id"]
    db.repondre(w.m, w.jour, d1, trad["id"], anna, True)
    db.repondre(w.m, w.jour, d1, exp["id"], markus, True)
    w.ctx["c_fiche"] = db.contribuer(w.m, w.jour, d1, trad["id"], anna, "ressource", FICHE_TITRE, FICHE,
                                     reutilisation="club", attribution=True)
    w.ctx["c_intro"] = db.contribuer(w.m, w.jour, d1, exp["id"], markus, "introduction", "Rendez-vous au salon", INTRO,
                                     reutilisation="non")
    return {"titre": "Deux contributions, pas deux contacts", "dit": "Anna envoie une fiche. Markus propose un rendez-vous.",
            "joue": ["Anna et Markus acceptent", "Anna rédige la fiche", "Markus propose le rendez-vous"],
            "faits": {"contributions": [
                {"qui": w.nom(anna), "nature": "ressource", "titre": FICHE_TITRE, "reutilisation": "tout le Club, avec son nom",
                 "telecharger": f"/api/club-repond/ressource/{w.ctx['c_fiche']}"},
                {"qui": w.nom(markus), "nature": "introduction", "titre": "Rendez-vous au salon", "texte": INTRO,
                 "reutilisation": "pour Sophie seulement"}],
                "etat": db.etat(w.m, d1)["etat"], "pourquoi": "une contribution n'est pas encore un effet"}}


def _t5_confirmation(w: Monde) -> dict:
    d1 = w.ctx["d1"]
    w.jour += timedelta(days=5)
    db.confirmer(w.m, w.jour, d1, w.ctx["c_fiche"], SOPHIE, "debloque")
    db.confirmer(w.m, w.jour, d1, w.ctx["c_intro"], SOPHIE, "debloque")
    return {"titre": "DEMANDE DÉBLOQUÉE", "dit": "Seule Sophie peut le dire. Elle confirme les deux étapes.",
            "joue": ["Sophie confirme l'effet de chaque contribution"],
            "faits": {"etat": db.etat(w.m, d1), "memoire": [{"titre": x["titre"], "auteur": w.nom(x["auteur"]) if x["auteur"] else None,
                                                             "confirmations": len(x["confirmations"])} for x in db.memoire_verifiee(w.m)],
                      "regle": "le système ne peut pas fabriquer cet état : il vient du bénéficiaire"}}


def _t6_memoire(w: Monde) -> dict:
    w.jour += timedelta(days=7)
    b2, pl2 = w.plan(DEMANDE_2, PAULINE)
    trouve = db.chercher_en_memoire(w.m, b2, w.par_id[PAULINE])
    d2 = db.ouvrir(w.m, w.jour, w.par_id[PAULINE], DEMANDE_2, "étiquettes de vin traduites pour le salon", b2)
    avant = len(w.m.evenements("SOLLICITATION"))
    for x in trouve:
        db.reutiliser(w.m, w.jour, d2, x["contribution_id"], PAULINE)
    return {"titre": "Une semaine plus tard : le Club se souvient", "dit": f"Pauline, vigneronne : « {DEMANDE_2} »",
            "joue": ["Pauline écrit sa demande"],
            "faits": {"depuis_la_memoire": [{"titre": x["titre"], "auteur": w.nom(x["auteur"]) if x["auteur"] else None,
                                             "confirmations": [c["verdict"] for c in x["confirmations"]],
                                             "differences": x["differences"],
                                             "telecharger": f"/api/club-repond/ressource/{x['contribution_id']}"} for x in trouve],
                      "personnes_derangees": len(w.m.evenements("SOLLICITATION")) - avant,
                      "sans_memoire": [_ligne_plan(e) for e in pl2["etapes"]], "ecartees": pl2["ecartees"],
                      "jamais_montre": "qui avait demandé la fiche la première fois"}}


def _t7_manque(w: Monde) -> dict:
    b3, pl3 = w.plan(DEMANDE_3, SOPHIE)
    b4, pl4 = w.plan("Je cherche un emballage en allemand pour nos coffrets", SOPHIE)
    return {"titre": "Quand le Club ne peut pas aider, il le dit", "dit": f"« {DEMANDE_3} »", "joue": [],
            "faits": {"japon": [_ligne_plan(e) for e in pl3["etapes"]],
                      "levee": {"demande": "Je cherche un emballage en allemand pour nos coffrets",
                                "etapes": [_ligne_plan(e) for e in pl4["etapes"]]},
                      "pour_l_animatrice": "ce qui manque au Club : " + ", ".join(
                          e["libelle"] + (f" ({e['extrait']})" if e["extrait"] else "")
                          for e in pl3["etapes"] if not e["principal"] and e["manque"]["certain"])}}


def _t8_bilan(w: Monde) -> dict:
    evts = w.m.evenements()
    return {"titre": "Ce que vous avez vu", "dit": "Une demande débloquée. Une réponse réutilisée. Un manque avoué.",
            "joue": [], "faits": {
                "calcule": ["étapes et mots justificatifs", "plan de deux personnes sur preuve", "vues privées",
                            "état « débloquée » dérivé des confirmations", "réponse depuis la mémoire vérifiée",
                            "manque et plus petite levée"],
                "joue": ["accords, contributions et confirmations : gestes humains joués par la présentation"],
                "fictif": "réseau de scène inventé : aucun membre réel, aucun impact mesuré",
                "journal": len(evts), "empreinte": w.m.empreinte()[:12]}}


ETAPES: list[Callable[[Monde], dict]] = [_t1_demande, _t2_plan, _t3_sollicitations, _t4_contributions, _t5_confirmation,
                                         _t6_memoire, _t7_manque, _t8_bilan]


def rejouer_jusqu_a(tax: Taxonomie, n: int) -> Monde:
    w = Monde(tax)
    for i in range(max(0, min(n, len(ETAPES)))):
        w.traces.append(ETAPES[i](w) | {"etape": i, "le": w.jour.isoformat()})
        w.etape = i + 1
    return w


def vue(w: Monde) -> dict:
    return {"etape": w.etape, "total": len(ETAPES), "le": w.jour.isoformat(), "horloge": "SIMULEE", "traces": w.traces,
            "avertissement": "Réseau de scène FICTIF : personnes et entreprises inventées, aucune donnée du Club."}


# ------------------------------------------------------------------ mode jury : calcul pur
class Essai(BaseModel):
    texte: str = Field(min_length=3, max_length=600)
    demandeur: str = Field(default=SOPHIE, max_length=16)


def essayer(w: Monde, texte: str, demandeur: str) -> dict:
    if demandeur not in w.par_id:
        raise HTTPException(422, "Demandeur inconnu dans le réseau de scène.")
    b, pl = w.plan(texte, demandeur)
    q = db.question_decisive(b, w.par_id[demandeur], w.profils, w.tax)
    memo = db.chercher_en_memoire(w.m, b, w.par_id[demandeur])
    sens_non_couverts = [a.terme for a in b.ambiguites] if (b.ambiguites and not q and not pl["etapes"]) else []
    if not pl["etapes"]:
        verdict = "QUESTION" if q else "MANQUE" if sens_non_couverts else "PRECISER"
    elif all(e["principal"] for e in pl["etapes"]):
        verdict = "PLAN"
    elif any(e["principal"] for e in pl["etapes"]):
        verdict = "PLAN_PARTIEL"
    else:
        verdict = "MANQUE" if any(e["manque"]["certain"] for e in pl["etapes"]) else "PRECISER"
    return {"verdict": verdict, "etapes": [_ligne_plan(e) for e in pl["etapes"]], "ecartees": pl["ecartees"],
            "contraintes": [c["libelle"] for c in pl["contraintes"]], "question": q,
            "sens_non_couverts": sens_non_couverts,
            "memoire": [{"titre": x["titre"], "etape": x["etape_libelle"]} for x in memo],
            "sollicitees": pl["personnes_sollicitees"], "non_derangees": pl["membres_non_derange"],
            "incertain": b.avertissements + b.contexte, "ecrit": False}


def creer_routeur(tax: Taxonomie) -> APIRouter:
    r = APIRouter(prefix="/api/club-repond", tags=["club répond"])
    verrou = threading.Lock()
    etat = {"monde": Monde(tax)}

    @r.get("")
    def lire():
        with verrou:
            return vue(etat["monde"])

    @r.post("/reinitialiser")
    def reinitialiser():
        with verrou:
            etat["monde"] = Monde(tax)
            return vue(etat["monde"])

    @r.post("/suivant")
    def suivant():
        with verrou:
            w = etat["monde"]
            if w.etape >= len(ETAPES):
                raise HTTPException(409, "La démonstration est terminée : réinitialisez ou rejouez.")
            w.traces.append(ETAPES[w.etape](w) | {"etape": w.etape, "le": w.jour.isoformat()})
            w.etape += 1
            return vue(w)

    @r.post("/aller/{n}")
    def aller(n: int):
        if not 0 <= n <= len(ETAPES):
            raise HTTPException(422, "Étape hors limites.")
        with verrou:
            etat["monde"] = rejouer_jusqu_a(tax, n)
            return vue(etat["monde"])

    @r.post("/essayer")
    def essai(e: Essai):
        with verrou:
            return essayer(etat["monde"], e.texte, e.demandeur)

    @r.get("/ressource/{cid}", response_class=PlainTextResponse)
    def ressource(cid: str):
        """Seule une contribution CONFIRMÉE et RÉUTILISABLE par le Club est téléchargeable, avec sa provenance."""
        with verrou:
            w = etat["monde"]
            x = next((x for x in db.memoire_verifiee(w.m) if x["contribution_id"] == cid), None)
            if x is None:
                raise HTTPException(404, "Ressource inconnue, non confirmée ou réservée à son demandeur.")
            statut = next(e.statut.value for e in w.m.evenements("CONTRIBUTION") if e.donnees["contribution_id"] == cid)
            conf = "; ".join(f"{c['verdict']} le {c['le']}" for c in x["confirmations"])
            corps = (f"{x['titre']}\n{'=' * len(x['titre'])}\n\n{x['contenu']}\n\n---\nProvenance : contribution de "
                     f"{w.nom(x['auteur']) if x['auteur'] else 'un membre (anonyme à sa demande)'} ; effet confirmé par "
                     f"le demandeur ({conf}). Le demandeur d'origine n'est pas nommé.\nDONNÉES FICTIVES — scène de "
                     f"démonstration, réseau inventé, dates simulées. Statut : {statut}.\n")
            return PlainTextResponse(corps, headers={"Content-Disposition": f'attachment; filename="fiche-{cid}.txt"'})

    return r
