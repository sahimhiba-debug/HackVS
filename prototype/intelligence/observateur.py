"""OBSERVER : lire l'état du réseau à une date, une fois, en index utilisables par la détection.

Entrée : `Reseau` (profils, besoins actifs, événements, journal). Sortie : `Etat` — qui offre quoi (sur preuve
DÉCLARÉE ou DÉDUITE d'une phrase affirmative), qui cherche quoi, qui est sollicitable, quelles paires sont déjà en
relation ou ont décliné, quels événements ouvrent une fenêtre, quels motifs vérifiés sont frais.
Aucune écriture. Coût linéaire en membres + besoins + événements du journal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from app.matching import couverture, filtres_durs, meme_organisation
from app.models import Besoin, Profil
from app.taxonomy import Taxonomie, norm

from . import apprentissage
from .modele import BesoinActif, Evenement, Reseau

PROFIL_OBSOLETE_JOURS = 540      # hypothèse de produit : 18 mois sans mise à jour ⇒ capacité non garantie
RELATION_JOURS = 365             # une rencontre de moins d'un an = « déjà en relation » (pas d'introduction à faire)
DORMANT_JOURS = 180              # aucune rencontre depuis 6 mois ⇒ capacité dormante
FENETRE_EVENEMENT_JOURS = 30     # un événement dans les 30 jours ⇒ « pourquoi maintenant »
CONVERGENCE_MIN = 3              # 3 demandes sur la même capacité ⇒ une action collective


@dataclass
class Etat:
    reseau: Reseau
    tax: Taxonomie
    offreurs: dict[str, list[tuple[str, str, str]]] = field(default_factory=dict)   # concept → (membre, extrait, nature)
    recherches: dict[str, list[tuple[str, str]]] = field(default_factory=dict)      # concept → (membre, extrait)
    relies: set[frozenset] = field(default_factory=set)
    declinees: set[frozenset] = field(default_factory=set)
    derniere_rencontre: dict[str, date] = field(default_factory=dict)
    evenements_proches: list[Evenement] = field(default_factory=list)
    motifs: list[dict] = field(default_factory=list)
    mesures: dict[str, float] = field(default_factory=dict)

    @property
    def aujourd_hui(self) -> date:
        return self.reseau.aujourd_hui

    def age_profil(self, p: Profil) -> Optional[int]:
        try:
            return (self.aujourd_hui - date.fromisoformat(p.maj[:10])).days
        except ValueError:
            return None

    def dormant(self, pid: str) -> bool:
        d = self.derniere_rencontre.get(pid)
        return d is None or (self.aujourd_hui - d).days > DORMANT_JOURS

    def evenement_commun(self, a: str, b: str) -> Optional[Evenement]:
        return next((e for e in self.evenements_proches if a in e.participants and b in e.participants), None)

    def exclusion(self, beneficiaire: Profil, candidat: Profil, besoin: Optional[Besoin] = None) -> Optional[str]:
        """Pourquoi `candidat` ne peut pas être proposé à `beneficiaire` (None : il peut l'être). Règles DURES."""
        if besoin is not None:
            r = filtres_durs(besoin, beneficiaire, candidat, self.tax)
            if r:
                return r
        else:
            if candidat.id == beneficiaire.id:
                return "vous-même"
            if meme_organisation(candidat, beneficiaire):
                return "même organisation"
            if not candidat.accepte_introductions:
                return "ne souhaite pas recevoir d'introductions"
            if not candidat.disponible:
                return "indisponible actuellement"
        age = self.age_profil(candidat)
        if age is None or age > PROFIL_OBSOLETE_JOURS:
            return "profil non mis à jour depuis plus de 18 mois"
        langues_imposees = [c.valeur for c in besoin.criteres if c.type == "langue" and c.obligatoire] if besoin else []
        if not langues_imposees and not set(beneficiaire.langues) & set(candidat.langues):
            return "aucune langue commune déclarée"
        paire = frozenset((beneficiaire.id, candidat.id))
        if paire in self.declinees:
            return "introduction déjà déclinée"
        if paire in self.relies:
            return "déjà en relation"
        return None


def observer(reseau: Reseau, tax: Taxonomie) -> Etat:
    import time
    t0 = time.perf_counter()
    e = Etat(reseau=reseau, tax=tax)
    for p in reseau.profils:
        vus: set[str] = set()
        for o in p.offre:
            if o.concept:
                for c in [o.concept, *tax.ancetres(o.concept)]:
                    if c not in vus:
                        vus.add(c)
                        e.offreurs.setdefault(c, []).append((p.id, o.texte, "declare"))
        if p.presentation:
            for c in sorted(tax.concepts_dans(norm(p.presentation)) - vus):
                pr = couverture(p, c, tax)
                if pr and pr.nature == "deduit":
                    vus.add(c)
                    e.offreurs.setdefault(c, []).append((p.id, pr.extrait, "deduit"))
        for r in p.recherche:
            if r.concept:
                e.recherches.setdefault(r.concept, []).append((p.id, r.texte))
    e.mesures["membres_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    t1 = time.perf_counter()
    m = reseau.memoire
    limite = reseau.aujourd_hui - timedelta(days=RELATION_JOURS)
    for ev in m.evenements("RENCONTRE", "INTRO_DECLINEE", jusqu_au=reseau.aujourd_hui):
        if len(ev.acteurs) < 2:
            continue
        paire = frozenset(ev.acteurs[:2])
        if ev.type == "INTRO_DECLINEE":
            e.declinees.add(paire)
            continue
        if ev.le >= limite:
            e.relies.add(paire)
        for x in ev.acteurs[:2]:
            if x not in e.derniere_rencontre or e.derniere_rencontre[x] < ev.le:
                e.derniere_rencontre[x] = ev.le
    e.evenements_proches = sorted((ev for ev in reseau.evenements
                                   if 0 <= (ev.le - reseau.aujourd_hui).days <= FENETRE_EVENEMENT_JOURS), key=lambda x: (x.le, x.id))
    e.motifs = apprentissage.motifs(m, reseau.aujourd_hui)
    e.mesures["relations_ms"] = round((time.perf_counter() - t1) * 1000, 1)
    return e


def pouls(e: Etat, besoins: list[BesoinActif]) -> dict:
    """Ce que l'on peut dire de l'état du réseau, chaque chiffre avec sa définition (pas de score)."""
    r = e.reseau
    sollicitables = [p for p in r.profils if p.accepte_introductions and p.disponible
                     and (e.age_profil(p) or 10**6) <= PROFIL_OBSOLETE_JOURS]
    offerts = {c for c, lst in e.offreurs.items() if lst}
    demandes = {c.valeur for b in besoins for c in b.besoin.criteres if c.type == "expertise"}
    return {
        "membres": {"valeur": len(r.profils), "definition": "membres du Club (fictif)"},
        "sollicitables": {"valeur": len(sollicitables), "definition": "acceptent d'être sollicités, disponibles, profil de moins de 18 mois"},
        "besoins_actifs": {"valeur": len(besoins), "definition": "demandes publiées et non closes"},
        "capacites": {"valeur": len(offerts), "definition": "capacités distinctes déclarées ou affirmées dans un profil"},
        "capacites_dormantes": {"valeur": sum(1 for p in sollicitables if p.offre and e.dormant(p.id)),
                                "definition": "membres sollicitables qui offrent une capacité et n'ont eu aucune rencontre depuis 6 mois"},
        "demandes_sans_offre": {"valeur": len(demandes - offerts), "definition": "capacités demandées que personne ne déclare"},
        "evenements_proches": {"valeur": len(e.evenements_proches), "definition": "événements dans les 30 prochains jours"},
        "motifs_verifies": {"valeur": sum(1 for x in e.motifs if x["frais"]), "definition": "résultats confirmés par un bénéficiaire, de moins d'un an"},
    }
