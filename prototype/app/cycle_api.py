"""Cycle de vie des relations (mode démo) : soirée → rencontres → +10 jours → pourquoi reprendre contact ? → suivi →
opportunité → soirée suivante. Horloge SIMULÉE (avancée à la main) ; membres fictifs ; rien n'est envoyé."""
from __future__ import annotations

from datetime import date
from typing import Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from adaptateurs.club import cycle as cy
from adaptateurs.club import reseau
from adaptateurs.club.adaptateur import AdaptateurClub
from plateforme import action as ac
from plateforme import memoire as me
from plateforme import pipeline as pl
from plateforme.affirmations import Statut
from plateforme.certificat import certificat
from plateforme.execution import Journal

from .models import Profil
from .taxonomy import Taxonomie


class Soiree(BaseModel):
    demande: str = Field("Je veux que tout le monde ait au moins une rencontre utile, et les opportunités ouvertes, 3 tours",
                         min_length=1, max_length=500)


class Approbation(BaseModel):
    par: str = Field("organisatrice (démo)", min_length=1, max_length=80)


class Avance(BaseModel):
    jours: int = Field(ge=1, le=60)


class NouveauBesoin(BaseModel):
    auteur: str = Field(max_length=64)
    texte: str = Field(min_length=5, max_length=500)


class Reponse(BaseModel):
    accepte: bool
    par: str = Field(max_length=64)


class Confirmation(BaseModel):
    a: str = Field(max_length=64)
    b: str = Field(max_length=64)
    par: str = Field(max_length=64)


def creer_routeur(profils_effectifs: Callable[[], list[Profil]], tax: Taxonomie, m: me.Memoire,
                  chemin_journal: str = ":memory:", avant_lecture: Callable[[], None] = lambda: None,
                  retraits: Callable[[], set[str]] = set) -> APIRouter:
    """`m` : LA mémoire du réseau (partagée avec l'application) ; `avant_lecture` y projette le magasin ;
    `retraits` : membres ayant EXPLICITEMENT retiré leur consentement (aucune relance ne les sollicite)."""
    r = APIRouter(prefix="/api/cycle", tags=["cycle"])
    journal = Journal(chemin_journal)
    debut = date.today()  # même origine que le reste du réseau ; ensuite seule l'horloge SIMULÉE avance

    def jour() -> date:
        avant_lecture()
        return m.maintenant(debut)

    def fournisseur():
        t = jour()
        return (profils_effectifs(), cy.besoins_publies(m, t), cy.relations(m, t), "demo", cy.opportunites(m, profils_effectifs(), tax, t),
                reseau.paires_declinees(m, t))

    ad = AdaptateurClub(fournisseur, tax)

    def erreur(e: Exception):
        raise HTTPException(409, str(e)) from None

    @r.get("/etat")
    def etat():
        t = jour()
        g = me.graphe(m, t)
        noms = {p.id: p.nom for p in profils_effectifs()}
        soirees = m.evenements("EVENEMENT_TENU")
        return {"aujourdhui": t.isoformat(), "horloge": "SIMULEE", "soirees": [e.donnees | {"le": e.le.isoformat()} for e in soirees],
                "croissance": me.croissance(m), "maintenant": me.indicateurs(g, t),
                "liens": [{"a": a, "b": b, "noms": [noms.get(a, a), noms.get(b, b)], "statut": d["statut"].value,
                           "derniere": d["derniere"].isoformat(), "force": me.force(d["derniere"], t), "types": sorted(d["types"])}
                          for a, b, d in sorted(g.edges(data=True))],
                "opportunites": [o | {"noms": [noms.get(o["a"]), noms.get(o["c"]), noms.get(o["via"])]}
                                 for o in cy.opportunites(m, profils_effectifs(), tax, t)],
                "evenements": len(m.evenements()), "empreinte": m.empreinte()[:16]}

    @r.get("/journal")
    def evenements():
        return [e.model_dump(mode="json") | {"id": e.id} for e in m.evenements()]

    @r.post("/soiree")
    def preparer(s: Soiree):
        run = pl.executer(ad, s.demande, journal)
        return {"run": run.model_dump(), "certificat": certificat(run)}

    @r.post("/soiree/{run_id}/approuver")
    def approuver(run_id: str, a: Approbation):
        try:
            ac.decider(journal, run_id, ac.DecisionHumaine(verdict="APPROUVER", par=a.par))
            n = len(m.evenements("EVENEMENT_TENU")) + 1
            return cy.enregistrer_soiree(m, journal, run_id, f"Soirée {n}", jour())
        except KeyError:
            raise HTTPException(404, "Plan inconnu.") from None
        except (ac.ErreurAction, cy.ErreurCycle) as e:
            erreur(e)

    @r.post("/avancer")
    def avancer(a: Avance):
        return {"aujourdhui": m.avancer(a.jours, debut).isoformat(), "horloge": "SIMULEE"}

    @r.post("/besoin")
    def besoin(b: NouveauBesoin):
        if b.auteur not in {p.id for p in profils_effectifs()}:
            raise HTTPException(404, "Membre inconnu.")
        e = cy.publier_besoin(m, b.auteur, b.texte, jour(), tax, Statut.SIMULE)
        return {"publie_le": e.le.isoformat(), "statut": e.statut.value,
                "criteres": [c["libelle"] for c in e.donnees["besoin"]["criteres"]]}

    @r.get("/relances")
    def relances():
        return cy.relances(m, profils_effectifs(), tax, jour(), retraits=retraits())

    @r.post("/relances/{relance_id}")
    def repondre(relance_id: str, rep: Reponse):
        try:
            return cy.repondre(m, profils_effectifs(), tax, jour(), relance_id, rep.accepte, rep.par, retraits())
        except cy.ErreurCycle as e:
            erreur(e)

    @r.post("/confirmer")
    def confirmer(c: Confirmation):
        try:
            return cy.confirmer_rencontre(m, c.a, c.b, c.par, jour()).model_dump(mode="json")
        except cy.ErreurCycle as e:
            erreur(e)

    @r.post("/reinitialiser")
    def reinitialiser():
        m.vider()
        return {"ok": True}

    return r
