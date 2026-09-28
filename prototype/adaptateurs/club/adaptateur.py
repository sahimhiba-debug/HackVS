"""Adaptateur du Club des Affaires : données du Club → modèle canonique de la plateforme.

Tout ce qui est propre au Club est ICI (vocabulaire, grammaire française, règles de consentement) ; la plateforme
n'en connaît rien. Statuts HONNÊTES :
- profils de démonstration et Club généré : SYNTHETIQUE (personnes fictives) ;
- mode réel : DECLARE (le membre l'a déclaré, rien n'est vérifié) ;
- ce que le moteur DÉDUIT d'une phrase de présentation : INFERE ;
- une relation acceptée dans l'application : OBSERVE (constatée par le système).
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable, Optional

from pydantic import BaseModel

from app.models import Profil
from app.soiree import _recherches, calculer_aides, langues_communes
from app.taxonomy import Taxonomie
from plateforme.affirmations import Affirmation, Registre, Statut
from plateforme.compilateur import Grammaire, Regle
from plateforme.critique import Objection
from plateforme.optimisation import Probleme, Solution, cle
from plateforme.specification import Domaine, SpecDecision, Terme
from plateforme.validation import Verdict

DOMAINE = Domaine(
    nom="club_affaires_valais",
    objectifs={
        "valeur_aide": Terme(nom="valeur_aide", description="aides prouvées couvertes (1 si offre déclarée, 0,5 si partielle), dans les deux sens"),
        "couverture": Terme(nom="couverture", description="participants ayant au moins une rencontre utile"),
        "diversite": Terme(nom="diversite", description="rencontres entre secteurs différents"),
        "reciprocite": Terme(nom="reciprocite", description="rencontres où chacun peut aider l'autre"),
        "opportunite": Terme(nom="opportunite", description="présentations ouvertes par la mémoire du réseau (ami d'un ami qui peut aider)"),
    },
    contraintes={
        "une_rencontre_par_tour": Terme(nom="une_rencontre_par_tour", description="au plus une rencontre par personne et par tour"),
        "paire_unique": Terme(nom="paire_unique", description="jamais deux fois la même paire"),
        "consentement": Terme(nom="consentement", description="seuls les membres qui acceptent les introductions"),
        "disponibilite": Terme(nom="disponibilite", description="seuls les membres disponibles"),
        "langue_commune": Terme(nom="langue_commune", description="jamais deux personnes sans langue commune déclarée"),
        "pas_deja_en_relation": Terme(nom="pas_deja_en_relation", description="pas de table pour deux membres déjà en relation"),
    },
    contraintes_obligatoires=["une_rencontre_par_tour", "paire_unique", "consentement"],
    parametres={"tours": (1, 6)},
)

GRAMMAIRE = Grammaire(
    domaine=DOMAINE.nom,
    contraintes_par_defaut=list(DOMAINE.contraintes),
    parametres_par_defaut={"tours": 3},
    statuts_admis=[Statut.VERIFIE, Statut.DECLARE, Statut.OBSERVE, Statut.INFERE, Statut.SYNTHETIQUE],
    regles=[
        Regle(motif=r"rencontres? utiles?|s.entraider|aider|aides?\b|valeur", effet="objectif:valeur_aide", libelle="valeur des aides"),
        Regle(motif=r"tout le monde|chacun|personne ne (reste|soit)|au moins une (rencontre|interaction)|equit|couverture|inclu",
              effet="objectif:couverture:2", libelle="couverture (chacun au moins une rencontre)"),
        Regle(motif=r"entre secteurs|inter.?sector|croiser|diversit|decloisonn|autres? secteurs?|transversal",
              effet="objectif:diversite", libelle="diversité sectorielle"),
        Regle(motif=r"reciproq|donnant.donnant|deux sens|mutuel", effet="objectif:reciprocite", libelle="réciprocité"),
        Regle(motif=r"opportunit|presentations? (ouvertes?|proposees?)|ami[es]* d.(un|une) ami|suites? de la derniere",
              effet="objectif:opportunite:2", libelle="opportunités ouvertes par le réseau"),
        Regle(motif=r"\d+ tours?", effet="parametre:tours", libelle="nombre de tours"),
        Regle(motif=r"(sans|ignorer|ignorant|peu importe|quelle que soit|sans tenir compte de|sans regarder)( la)? langues?|toutes langues",
              effet="retirer_contrainte:langue_commune", libelle="lever la contrainte de langue"),
        Regle(motif=r"deja en (relation|contact)", effet="retirer_contrainte:pas_deja_en_relation", libelle="autoriser les paires déjà en relation"),
        Regle(motif=r"(sans|ignorer|ignorant|meme sans|outrepasser|passer outre)( au| le)? consentement", effet="retirer_contrainte:consentement",
              libelle="lever le consentement (refusé par la politique)"),
        Regle(motif=r"meme (les )?indisponibles?", effet="retirer_contrainte:disponibilite", libelle="inclure les indisponibles"),
    ],
)


class Instantane(BaseModel):
    """Tout ce qu'une exécution consomme : sérialisable, haché, rejouable sans les données vivantes."""
    source: str
    participants: dict[str, dict]
    affirmations: list[dict]
    aides: dict[str, dict]            # « i→j » → aide prouvée que j apporte à i (+ ids d'affirmations)
    deja_en_relation: list[str]       # clés « a|b »
    opportunites: dict[str, dict] = {}  # « a|c » → {via, raison, affirmation} (mémoire du réseau)

    def empreinte(self) -> str:
        return hashlib.sha256(json.dumps(self.model_dump(), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _statut_source(source: str) -> Statut:
    return Statut.DECLARE if source == "reel" else Statut.SYNTHETIQUE


def instantane(profils: list[Profil], besoins_publies: list, tax: Taxonomie, source: str,
               relations_observees: Optional[list[tuple[str, str]]] = None,
               opportunites: Optional[list[dict]] = None) -> Instantane:
    base = _statut_source(source)
    reg = Registre()
    membres = [p for p in profils if p.type == "membre_club"]
    par_id = {p.id: p for p in membres}
    ids_offre: dict[tuple[str, str], str] = {}
    for p in membres:
        src = f"profil:{p.id}"
        for i, o in enumerate(p.offre):
            a = Affirmation(sujet=p.id, predicat="propose", objet=o.concept or "texte_libre", extrait=o.texte,
                            source=f"{src}#offre[{i}]", type_source="profil", statut=base)
            ids_offre[(p.id, o.texte)] = reg.ajouter(a)
        for i, o in enumerate(p.recherche):
            reg.ajouter(Affirmation(sujet=p.id, predicat="recherche", objet=o.concept or "texte_libre", extrait=o.texte,
                                    source=f"{src}#recherche[{i}]", type_source="profil", statut=base))
        for s in p.secteurs:
            reg.ajouter(Affirmation(sujet=p.id, predicat="secteur", objet=s, source=f"{src}#secteurs", type_source="profil", statut=base))
        reg.ajouter(Affirmation(sujet=p.id, predicat="accepte_introductions", objet=str(p.accepte_introductions).lower(),
                                source=f"{src}#consentement", type_source="profil", statut=base))
    aides_brutes = calculer_aides(membres, besoins_publies, tax)
    aides = {}
    for (i, j), aide in aides_brutes.items():
        besoin_id = next((a.id for a in reg.chercher(sujet=i, predicat="recherche") if a.extrait and a.extrait in aide["besoin"]), None)
        if aide.get("champ_preuve") == "offre" and (j, aide["preuve"]) in ids_offre:
            preuve_id = ids_offre[(j, aide["preuve"])]
        else:  # déduit d'une phrase de présentation, ou autre champ : c'est NOTRE inférence
            preuve_id = reg.ajouter(Affirmation(sujet=j, predicat="peut_aider_sur", objet=aide["besoin"][:80], extrait=aide["preuve"],
                                                source=f"moteur:matching({i}→{j})", type_source="deduction", statut=Statut.INFERE))
        if besoin_id is None:  # besoin publié dans l'application (pas dans le profil) ; SIMULE s'il vient d'un scénario
            st = next((getattr(b, "statut_affirmation", None) for b in besoins_publies
                       if b.auteur_id == i and f"besoin publié : {b.besoin.texte}" == aide["besoin"]), None) or Statut.OBSERVE
            besoin_id = reg.ajouter(Affirmation(sujet=i, predicat="besoin_publie", objet=aide["besoin"][:80],
                                                source=f"application:bourse({i})", type_source="application", statut=st))
        aides[f"{i}→{j}"] = aide | {"affirmations": [besoin_id, preuve_id]}
    for a, b in relations_observees or []:
        reg.ajouter(Affirmation(sujet=cle(a, b), predicat="deja_en_relation", objet="true", source="application:relations",
                                type_source="application", statut=Statut.OBSERVE))
    opps = {}
    for o in opportunites or []:  # déduites par la mémoire (fermeture de triade) : INFÉRÉES, jamais plus
        k = cle(o["a"], o["c"])
        aid = reg.ajouter(Affirmation(sujet=k, predicat="opportunite_ouverte", objet=o["via"], extrait=o.get("raison", ""),
                                      source=f"memoire:fermeture({o['a']},{o['via']},{o['c']})", type_source="deduction",
                                      statut=Statut.INFERE))
        opps[k] = {"via": o["via"], "raison": o.get("raison", ""), "affirmation": aid}
    parts = {p.id: {"secteurs": p.secteurs, "langues": p.langues, "consentement": p.accepte_introductions,
                    "disponible": p.disponible, "nom": p.nom} for p in par_id.values()}
    return Instantane(source=source, participants=parts, affirmations=reg.exporter(), aides=aides,
                      deja_en_relation=sorted({cle(a, b) for a, b in relations_observees or []}), opportunites=opps)


def probleme(inst: Instantane, spec: SpecDecision, tax: Taxonomie) -> tuple[Probleme, dict[str, str], dict[str, list[str]]]:
    """Applique les contraintes dures de la SPEC. Retourne le problème, les participants écartés (raison) et,
    pour chaque arête, les affirmations qui la fondent."""
    cd = set(spec.contraintes_dures)
    ecartes: dict[str, str] = {}
    for pid, p in inst.participants.items():
        if "consentement" in cd and not p["consentement"]:
            ecartes[pid] = "n'accepte pas les introductions"
        elif "disponibilite" in cd and not p["disponible"]:
            ecartes[pid] = "indisponible"
    eligibles = sorted(pid for pid in inst.participants if pid not in ecartes)
    aretes, exclues, preuves = {}, {}, {}
    paires = {cle(*k.split("→")) for k in inst.aides}
    for k in sorted(paires):
        a, b = k.split("|")
        if a not in eligibles or b not in eligibles:
            continue
        pa, pb = inst.participants[a], inst.participants[b]
        if "langue_commune" in cd and not set(pa["langues"]) & set(pb["langues"]):
            exclues[k] = "aucune langue commune déclarée"
            continue
        if "pas_deja_en_relation" in cd and k in inst.deja_en_relation:
            exclues[k] = "déjà en relation"
            continue
        ab, ba = inst.aides.get(f"{a}→{b}"), inst.aides.get(f"{b}→{a}")
        valeur = (ab["valeur"] if ab else 0) + (ba["valeur"] if ba else 0)
        diverse = not any(tax.meme_famille(x, y) for x in pa["secteurs"] for y in pb["secteurs"])
        aretes[k] = {"valeur_aide": valeur, "reciprocite": float(bool(ab and ba)), "diversite": float(diverse),
                     "opportunite": float(k in inst.opportunites)}
        preuves[k] = [aid for x in (ab, ba) if x for aid in x["affirmations"]] + (
            [inst.opportunites[k]["affirmation"]] if k in inst.opportunites else [])
    return (Probleme(participants=eligibles, aretes=aretes, exclues=exclues, tours=spec.parametres.get("tours", 3)),
            ecartes, preuves)


# --------------------------------------------------------------- validateurs INDÉPENDANTS et règles du gardien
# Ils relisent l'instantané brut (participants), pas le problème construit : une erreur dans `probleme()` serait vue.
def validateurs(inst: dict, spec: SpecDecision) -> list[Callable[[Solution], Verdict]]:
    parts, cd = inst["participants"], set(spec.contraintes_dures)

    def consentement(sol: Solution) -> Verdict:
        d = [f"{p} (tour {t}) n'accepte pas les introductions" for t, a, b in sol.rencontres for p in (a, b)
             if not parts.get(p, {}).get("consentement", False)]
        return Verdict(niveau="L5", nom="consentement (recalculé)", etat="FAIL" if d else "PASS", details=d)

    def langue(sol: Solution) -> Verdict:
        if "langue_commune" not in cd:
            return Verdict(niveau="L5", nom="langue commune (recalculée)", etat="SKIP", details=["contrainte levée par la spécification"])
        d = [f"{a}–{b} (tour {t}) : aucune langue commune" for t, a, b in sol.rencontres
             if not set(parts[a]["langues"]) & set(parts[b]["langues"])]
        return Verdict(niveau="L5", nom="langue commune (recalculée)", etat="FAIL" if d else "PASS", details=d)

    def disponibilite(sol: Solution) -> Verdict:
        if "disponibilite" not in cd:
            return Verdict(niveau="L5", nom="disponibilité (recalculée)", etat="SKIP", details=["contrainte levée par la spécification"])
        d = [f"{p} (tour {t}) indisponible" for t, a, b in sol.rencontres for p in (a, b) if not parts[p]["disponible"]]
        return Verdict(niveau="L5", nom="disponibilité (recalculée)", etat="FAIL" if d else "PASS", details=d)

    def relations(sol: Solution) -> Verdict:
        if "pas_deja_en_relation" not in cd:
            return Verdict(niveau="L5", nom="pas déjà en relation (recalculé)", etat="SKIP", details=["contrainte levée par la spécification"])
        deja = set(inst["deja_en_relation"])
        d = [f"{cle(a, b)} déjà en relation" for _, a, b in sol.rencontres if cle(a, b) in deja]
        return Verdict(niveau="L5", nom="pas déjà en relation (recalculé)", etat="FAIL" if d else "PASS", details=d)

    return [consentement, langue, disponibilite, relations]


def regles_gardien(inst: dict, spec: SpecDecision) -> list[Callable[[Solution], list[Objection]]]:
    parts = inst["participants"]

    def jamais_sans_consentement(sol: Solution) -> list[Objection]:
        return [Objection(code="consentement", gravite="bloquante", message=f"{p} n'a pas consenti aux introductions")
                for _, a, b in sol.rencontres for p in (a, b) if not parts.get(p, {}).get("consentement", False)]

    def consentement_non_levable(sol: Solution) -> list[Objection]:
        if "consentement" not in spec.contraintes_dures:
            return [Objection(code="politique", gravite="bloquante", message="la spécification lève le consentement : interdit")]
        return []

    def donnees_fictives(sol: Solution) -> list[Objection]:
        if inst["source"] != "reel":
            return [Objection(code="donnees_fictives", gravite="info", ouverte=False,
                              message=f"données « {inst['source']} » : personnes et besoins FICTIFS, aucune action réelle possible")]
        return []

    return [jamais_sans_consentement, consentement_non_levable, donnees_fictives]


class AdaptateurClub:
    """Implémente le protocole `plateforme.pipeline.Adaptateur`. `fournisseur` rend les données vivantes :
    (profils, besoins publiés, relations observées, source)."""
    domaine = DOMAINE
    grammaire = GRAMMAIRE

    def __init__(self, fournisseur: Callable[[], tuple], tax: Taxonomie):
        """fournisseur() → (profils, besoins, relations, source) ou (…, source, opportunites)."""
        self.fournisseur, self.tax = fournisseur, tax

    def instantane_courant(self) -> dict:
        profils, besoins, relations, source, *reste = self.fournisseur()
        return instantane(profils, besoins, self.tax, source, relations, reste[0] if reste else None).model_dump()

    def probleme(self, inst: dict, spec: SpecDecision):
        return probleme(Instantane(**inst), spec, self.tax)

    def validateurs(self, inst: dict, spec: SpecDecision, pb: Probleme):
        return validateurs(inst, spec)

    def regles_gardien(self, inst: dict, spec: SpecDecision):
        return regles_gardien(inst, spec)


def recherches_du_membre(p: Profil, tax: Taxonomie) -> list:
    return _recherches(p, [], tax)


__all__ = ["AdaptateurClub", "DOMAINE", "GRAMMAIRE", "Instantane", "instantane", "probleme", "langues_communes"]
