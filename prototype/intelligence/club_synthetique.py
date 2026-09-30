"""Club SYNTHÉTIQUE, reproductible par graine : pour démontrer et mesurer, jamais pour prétendre.

Deux couches :
1. un FOND aléatoire réaliste (organisations, métiers, besoins publiés en phrases, langues, créneaux, disponibilité,
   profils anciens, refus d'introduction, rencontres sur 400 jours, événements à venir) ;
2. des SITUATIONS PLANTÉES, chacune sur une capacité RÉSERVÉE que le fond n'offre ni ne demande jamais :
   - vraies opportunités (complémentarité, latente + événement, composition, convergence, lacune, et « mémoire du
     Club » : une contribution confirmée — fournie dans `verite["souvenirs"]` — fait choisir la personne qui a déjà aidé) ;
   - pièges (concurrent, refus d'introduction, profil obsolète, même organisation, aucune langue commune,
     introduction déjà déclinée, indisponible, déjà en relation, simple ressemblance).
La vérité terrain (`verite`) décrit ce qu'un moteur honnête DOIT trouver et ce qu'il ne doit JAMAIS proposer.
Limite déclarée : générateur et détecteur partagent la même taxonomie ; le banc mesure le respect des règles et la
robustesse aux pièges, pas la pertinence humaine.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from functools import lru_cache

from app.models import Offre, Profil
from app.parser_rules import analyser
from app.taxonomy import DATA_DIR, Taxonomie, charger_taxonomie
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

from .modele import BesoinActif, Evenement, Reseau

AUJOURD_HUI = date(2026, 11, 3)
FOND = ["transport_frigorifique", "logistique", "fiduciaire", "droit_affaires", "cybersecurite", "informatique",
        "developpement_web", "marketing", "traduction", "energie_solaire", "efficacite_energetique", "emballage",
        "export_suisse_alemanique", "export_allemagne", "sante_securite_travail"]
PRODUITS = ["boissons", "vins"]      # secteurs de production (clients, jamais offerts comme service par le fond)
RESERVES = ["photo_video", "traiteur", "menuiserie", "construction_metallique", "assurance", "immobilier_commercial",
            "location_machines", "transmission_entreprise", "tourisme", "recrutement", "financement",
            "installation_froid", "formation", "mentorat", "ia_donnees", "evenementiel", "securite_evenement"]
PRENOMS = ["Aline", "Bastien", "Céline", "Damien", "Estelle", "Fabien", "Gaëlle", "Hugo", "Isabelle", "Julien", "Karine",
           "Lionel", "Mélanie", "Noé", "Océane", "Pascal", "Quentin", "Romane", "Sébastien", "Tania", "Ursula", "Valentin",
           "Wendy", "Xavier", "Yasmine", "Zoé", "Beat", "Corinne", "Reto", "Sabine"]
NOMS = ["Rey", "Favre", "Crettaz", "Luisier", "Moret", "Bonvin", "Roduit", "Gay", "Michellod", "Carron", "Fournier",
        "Mayor", "Theytaz", "Pitteloud", "Zufferey", "Salamin", "Métrailler", "Dorsaz", "Vouilloz", "Rossier",
        "Imboden", "Schmid", "Furrer", "Andenmatten", "Clausen"]
COMMUNES = ["Sion", "Martigny", "Monthey", "Sierre", "Fully", "Conthey", "Saxon", "Brigue", "Viège", "Orsières"]


@lru_cache(maxsize=1)
def _brut() -> dict:
    return json.loads((DATA_DIR / "taxonomie.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def phrase_besoin(concept: str) -> str:
    """Une phrase de besoin que l'ANALYSEUR RÉEL comprend comme ce concept (vérifié, sinon erreur)."""
    tax = charger_taxonomie()
    for expr in _brut()["concepts"][concept]["expressions"]:
        t = f"Nous cherchons de l'aide : {expr}."
        if concept in {c.valeur for c in analyser(t, tax).criteres if c.type == "expertise"}:
            return t
    raise ValueError(f"aucune expression analysable pour {concept}")


def _offre(tax: Taxonomie, c: str) -> Offre:
    return Offre(concept=c, texte=f"{tax.libelle(c)} pour les PME de la région")


def _membre(rnd: random.Random, tax: Taxonomie, i: int, org: str, offres: list[str], recherche: list[str],
            secteurs: list[str], **kw) -> Profil:
    langues = kw.pop("langues", None) or (["fr", "de"] if rnd.random() < 0.3 else ["de"] if rnd.random() < 0.08 else ["fr"])
    d = dict(id=kw.pop("id", f"c{i:05d}"), nom=kw.pop("nom", f"{rnd.choice(PRENOMS)} {rnd.choice(NOMS)}"),
             fonction=kw.pop("fonction", "Dirigeant·e"), entreprise=org, commune=rnd.choice(COMMUNES), type="membre_club",
             secteurs=secteurs, offre=[_offre(tax, c) for c in offres],
             recherche=[Offre(concept=c, texte=f"Nous cherchons : {tax.libelle(c)}") for c in recherche],
             langues=langues, zones_service=["Valais"], accepte_introductions=rnd.random() > 0.08,
             disponible=rnd.random() > 0.06, creneaux=rnd.sample(["lun-matin", "mar-matin", "mar-apres-midi", "mer-matin",
                                                                   "jeu-matin", "jeu-apres-midi", "ven-matin"], 3),
             maj=(AUJOURD_HUI - timedelta(days=rnd.choice([20, 60, 120, 200, 300, 700]))).isoformat())
    d.update(kw)
    return Profil(**d)


def generer(n: int = 150, graine: int = 2026, plantes: bool = True) -> tuple[Reseau, dict]:
    """Un Club de n membres (fond + situations plantées). Déterministe pour une graine donnée."""
    tax = charger_taxonomie()
    rnd = random.Random(graine)
    m = Memoire()
    profils: list[Profil] = []
    besoins: list[BesoinActif] = []
    n_orgs = max(3, n * 2 // 3)
    orgs = [f"Entreprise {k:04d} (fictive)" for k in range(n_orgs)]
    verite: dict = {"vraies": [], "pieges": [], "souvenirs": [], "graine": graine, "membres": n}

    n_fond = n - (40 if plantes else 0)
    for i in range(max(0, n_fond)):
        produit = rnd.random() < 0.3
        offres = rnd.sample(PRODUITS, 1) if produit else rnd.sample(FOND, rnd.choice([1, 1, 2]))
        secteurs = offres[:1]
        recherche = rnd.sample(FOND + PRODUITS, 1) if rnd.random() < 0.35 else []
        recherche = [c for c in recherche if c not in offres]
        profils.append(_membre(rnd, tax, i, rnd.choice(orgs), offres, recherche, secteurs))
    ids = [p.id for p in profils]
    for k, p in enumerate(profils):                        # ~12 % publient un besoin (sur le fond seulement)
        if rnd.random() < 0.12:
            c = rnd.choice([x for x in FOND if x not in {o.concept for o in p.offre}])
            t = phrase_besoin(c)
            besoins.append(BesoinActif(id=f"b{k:05d}", auteur=p.id, texte=t, le=AUJOURD_HUI - timedelta(days=rnd.randint(1, 60)),
                                       besoin=analyser(t, tax)))
    for _ in range(int(1.5 * len(ids))):                  # ~3 rencontres par membre sur 400 jours
        if len(ids) < 2:
            break
        a, b = rnd.sample(ids, 2)
        m.ajouter(Evt(type="RENCONTRE", le=AUJOURD_HUI - timedelta(days=rnd.randint(1, 400)), acteurs=sorted([a, b]),
                      statut=Statut.SYNTHETIQUE, donnees={"evenement": "soirée du Club"}))
    evenements = [Evenement(id=f"ev{k}", nom=nom, le=AUJOURD_HUI + timedelta(days=j), themes=tuple(th),
                            participants=tuple(sorted(rnd.sample(ids, min(len(ids), max(2, n // 6))))) if ids else ())
                  for k, (nom, j, th) in enumerate([("Foire du Valais — journée PME (fictive)", 9, ["export_suisse_alemanique"]),
                                                    ("Soirée énergie du Club (fictive)", 16, ["energie_solaire"]),
                                                    ("Petit-déjeuner numérique (fictif)", 23, ["cybersecurite"])])]
    if plantes:
        _planter(rnd, tax, n_fond, profils, besoins, evenements, m, verite)
    reseau = Reseau(profils=profils, besoins=besoins, evenements=evenements, memoire=m, aujourd_hui=AUJOURD_HUI,
                    nom=f"Club synthétique ({n} membres, graine {graine})")
    return reseau, verite


def _planter(rnd, tax, base, profils, besoins, evenements, m, verite) -> None:
    compteur = [base]
    res = list(RESERVES)

    def membre(offres=(), recherche=(), secteurs=None, **kw) -> Profil:
        i = compteur[0]
        compteur[0] += 1
        kw.setdefault("accepte_introductions", True)
        kw.setdefault("disponible", True)
        kw.setdefault("maj", (AUJOURD_HUI - timedelta(days=30)).isoformat())
        kw.setdefault("langues", ["fr"])
        kw.setdefault("creneaux", ["mar-matin", "jeu-matin"])
        p = _membre(rnd, tax, i, kw.pop("org", f"Entreprise plantée {i:05d} (fictive)"), list(offres), list(recherche),
                    secteurs or (list(offres[:1]) if offres else ["boissons"]), **kw)
        profils.append(p)
        return p

    def besoin(p: Profil, concepts: list[str], texte: str | None = None, jours: int = 5) -> BesoinActif:
        t = texte or " ".join(phrase_besoin(c) for c in concepts)
        b = BesoinActif(id=f"bp{len(besoins):05d}", auteur=p.id, texte=t, le=AUJOURD_HUI - timedelta(days=jours),
                        besoin=analyser(t, tax))
        besoins.append(b)
        return b

    # --- vraies opportunités
    for _ in range(2):                                           # complémentarité directe
        c = res.pop()
        a, b = membre(secteurs=["boissons"]), membre(offres=[c])
        besoin(a, [c])
        verite["vraies"].append({"type": "COMPLEMENTARITE", "membres": [a.id, b.id], "concepts": [c]})
    for k in range(2):                                           # latente : personne n'a publié de besoin
        c = res.pop()
        a = membre(offres=["vins"], recherche=[c], secteurs=["vins"])
        b = membre(offres=[c], recherche=["vins"])
        ev = evenements[k]
        evenements[k] = Evenement(id=ev.id, nom=ev.nom, le=ev.le, themes=ev.themes,
                                  participants=tuple(sorted(set(ev.participants) | {a.id, b.id})))
        verite["vraies"].append({"type": "LATENTE", "membres": [a.id, b.id], "concepts": [c], "evenement": ev.id})
    c1, c2 = res.pop(), res.pop()                                # composition : deux capacités, deux personnes
    a, b, x = membre(secteurs=["boissons"]), membre(offres=[c1]), membre(offres=[c2])
    besoin(a, [c1, c2])
    verite["vraies"].append({"type": "COMPOSITION", "membres": [a.id, b.id, x.id], "concepts": [c1, c2]})
    cz = res.pop()                                               # convergence : trois besoins, une experte
    demandeurs = [membre(secteurs=["boissons"]) for _ in range(3)]
    for j, d in enumerate(demandeurs):
        besoin(d, [cz], jours=3 + j * 7)
    experte = membre(offres=[cz])
    verite["vraies"].append({"type": "CONVERGENCE", "membres": sorted([d.id for d in demandeurs]) + [experte.id],
                             "concepts": [cz]})
    cw = res.pop()                                               # lacune : deux besoins, personne n'offre
    lac = [membre(secteurs=["vins"]) for _ in range(2)]
    for d in lac:
        besoin(d, [cw])
    verite["vraies"].append({"type": "LACUNE", "membres": sorted(d.id for d in lac), "concepts": [cw]})
    cm = res.pop()                                               # mémoire : une contribution confirmée CHANGE le choix
    ancien = membre(offres=[cm], maj=(AUJOURD_HUI - timedelta(days=200)).isoformat())
    membre(offres=[cm], maj=(AUJOURD_HUI - timedelta(days=20)).isoformat())       # sans mémoire, ce profil plus récent passerait devant
    nouveau = membre(secteurs=["boissons"])
    besoin(nouveau, [cm])
    verite["souvenirs"].append({                                 # forme de `memoire_club.souvenirs` : confirmée, partagée « club »
        "essai": "es-historique-1", "question": f"Nous cherchons : {tax.libelle(cm)}", "porteur": membre(secteurs=["boissons"]).id,
        "contributeurs": [ancien.id], "concepts": [cm], "qualification": "positif", "statut": "confirmee", "niveau": "club",
        "limites": "un essai, un seul bénéficiaire", "le": (AUJOURD_HUI - timedelta(days=90)).isoformat()})
    verite["vraies"].append({"type": "mémoire du Club", "membres": [nouveau.id, ancien.id], "concepts": [cm]})

    # --- pièges : la paire (a, b) ne doit JAMAIS être proposée
    def piege(nom: str, prop_a: dict, prop_b: dict, texte: str | None = None, avant=None) -> None:
        c = res.pop()
        a = membre(secteurs=prop_a.pop("secteurs", ["boissons"]), **prop_a)
        b = membre(offres=[c], **prop_b)
        if avant:
            avant(a, b)
        besoin(a, [c], texte=texte and texte.format(phrase=phrase_besoin(c)))
        verite["pieges"].append({"type": nom, "membres": [a.id, b.id], "concepts": [c]})

    piege("CONCURRENT", {}, {"secteurs": ["boissons"]}, texte="{phrase} Pas un concurrent direct.")
    piege("REFUS_INTRODUCTIONS", {}, {"accepte_introductions": False})
    piege("PROFIL_OBSOLETE", {}, {"maj": (AUJOURD_HUI - timedelta(days=800)).isoformat()})
    piege("MEME_ORGANISATION", {"org": "Maison commune (fictive)"}, {"org": "Maison commune (fictive)"})
    piege("AUCUNE_LANGUE_COMMUNE", {"langues": ["de"]}, {"langues": ["fr"]})
    piege("INTRODUCTION_DECLINEE", {}, {}, avant=lambda a, b: m.ajouter(Evt(
        type="INTRO_DECLINEE", le=AUJOURD_HUI - timedelta(days=40), acteurs=[a.id, b.id], statut=Statut.SYNTHETIQUE,
        donnees={"t": 1})))
    piege("INDISPONIBLE", {}, {"disponible": False})
    piege("DEJA_EN_RELATION", {}, {}, avant=lambda a, b: m.ajouter(Evt(
        type="RENCONTRE", le=AUJOURD_HUI - timedelta(days=12), acteurs=sorted([a.id, b.id]), statut=Statut.SYNTHETIQUE,
        donnees={"evenement": "soirée du Club"})))
    a = membre(offres=["vins"], secteurs=["vins"])               # ressemblance : même métier, même événement, rien à s'apporter
    b = membre(offres=["vins"], secteurs=["vins"])
    ev = evenements[2]
    evenements[2] = Evenement(id=ev.id, nom=ev.nom, le=ev.le, themes=ev.themes,
                              participants=tuple(sorted(set(ev.participants) | {a.id, b.id})))
    verite["pieges"].append({"type": "RESSEMBLANCE", "membres": [a.id, b.id], "concepts": []})
    while len(profils) < base + 40:                               # compléter à n exactement (membres sans rôle planté)
        membre(offres=[rnd.choice(FOND)])
