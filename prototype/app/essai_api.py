"""Routes du banc d'essai partagé : un ADAPTATEUR mince, branché sur le routeur Club Pulse (mêmes sessions, même
verrou par monde, mêmes erreurs typées). Chaque commande qui engage une décision porte la VERSION que la personne a
vue : si le protocole a changé entre-temps, 409 — rien n'est appliqué à une version qu'elle n'a pas lue."""
from __future__ import annotations

from datetime import date
from typing import Callable, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from intelligence.club_pulse import ClubPulse
from intelligence.erreurs import Interdit

Nature = Literal["temps", "lieu", "objet", "competence"]


class Formulation(BaseModel):
    texte: str = Field(min_length=3, max_length=600)


class GesteEntree(BaseModel):
    nature: Nature
    geste: str = Field(min_length=3, max_length=200)
    duree_min: int = Field(ge=1, le=120)


class Brouillon(BaseModel):
    question: str = Field(min_length=3, max_length=300)
    objet: str = Field(default="", max_length=120)
    pourquoi: str = Field(default="", max_length=300)
    critere: str = Field(default="", max_length=300)
    echeance: date
    etapes: list[GesteEntree] = Field(default_factory=list, max_length=4)


class Version(BaseModel):
    version: int = Field(ge=0)


class Publication(Version):
    choix: dict[str, str] = Field(default_factory=dict, max_length=4)       # geste → offre choisie par le porteur


class Decision(Version):
    accepte: bool


class Modification(Version):
    question: Optional[str] = Field(default=None, min_length=3, max_length=300)
    pourquoi: Optional[str] = Field(default=None, max_length=300)
    critere: Optional[str] = Field(default=None, min_length=3, max_length=300)
    echeance: Optional[date] = None


class Choix(Version):
    alternative: str = Field(min_length=3, max_length=80)


class OffreEntree(BaseModel):
    nature: Nature
    quoi: str = Field(min_length=3, max_length=200)
    duree_max_min: Optional[int] = Field(default=None, ge=1, le=240)
    capacite: int = Field(default=1, ge=1, le=20)
    du: Optional[date] = None                          # absent : la date du monde (simulée en démonstration)
    au: date
    conditions: str = Field(default="", max_length=300)


class OffreModif(BaseModel):
    duree_max_min: Optional[int] = Field(default=None, ge=1, le=240)
    capacite: Optional[int] = Field(default=None, ge=1, le=20)
    au: Optional[date] = None
    conditions: Optional[str] = Field(default=None, max_length=300)


class Observation(BaseModel):
    texte: str = Field(min_length=3, max_length=1000)
    qualification: Literal["positif", "negatif", "mitige", "non_concluant"]
    limites: str = Field(min_length=3, max_length=300)


class Avis(BaseModel):
    revision: int = Field(ge=1)
    avis: Literal["confirme", "conteste"]
    raison: str = Field(default="", max_length=300)


class Reutilisation(BaseModel):
    niveau: Literal["moi", "participants", "club"]
    mention: Literal["nom", "anonyme"]


JOUABLES = {"s01", "d01"}                  # Pauline, Léa : jamais Sophie ni Markus, qui ont chacun leur téléphone


class GesteJoue(BaseModel):
    membre: str = Field(max_length=8)
    version: int = Field(ge=0)
    accepte: bool


class Annulation(BaseModel):
    raison: str = Field(default="annulé", min_length=3, max_length=200)


def ajouter_routes(r: APIRouter, au_monde: Callable, membre: Callable, console: Callable, limiter_ia: Callable) -> None:
    def vue(c: ClubPulse, eid: str, pid: str) -> dict:
        return c.vues_essai.essai(eid, pid)

    # ------------------------------------------------------------------ A. mes actions / C. souvenirs et accords
    @r.get("/moi/actions")
    def actions(pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.vues_essai.actions(pid))

    @r.get("/moi/souvenirs")
    def souvenirs(pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.vues_essai.souvenirs(pid))

    # ------------------------------------------------------------------ offres volontaires (les siennes)
    @r.post("/moi/offres")
    def publier_offre(o: OffreEntree, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: {"offre": c.banc.publier_offre(pid, o.nature, o.quoi, o.capacite, o.du or c.jour, o.au, o.duree_max_min,
                                                                o.conditions)})

    @r.patch("/moi/offres/{oid}")
    def modifier_offre(oid: str, m: OffreModif, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: {"essais_a_adapter": c.banc.modifier_offre(pid, oid, **m.model_dump())})

    @r.post("/moi/offres/{oid}/retirer")
    def retirer_offre(oid: str, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: {"essais_a_adapter": c.banc.retirer_offre(pid, oid)})

    # ------------------------------------------------------------------ B. un essai
    @r.post("/moi/essais/preparer")
    def preparer(f: Formulation, pid: str = Depends(membre)) -> dict:
        limiter_ia(pid)
        return au_monde(lambda c: c.preparer_essai(pid, f.texte))           # rien n'est écrit : un brouillon à corriger

    @r.post("/moi/essais")
    def creer(b: Brouillon, pid: str = Depends(membre)) -> dict:
        def f(c: ClubPulse) -> dict:
            eid = c.creer_essai(pid, b.model_dump(mode="json"))
            return vue(c, eid, pid)
        return au_monde(f)

    @r.get("/moi/essais/{eid}")
    def lire(eid: str, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: vue(c, eid, pid))

    def commande(eid: str, pid: str, action: Callable[[ClubPulse], object]) -> dict:
        def f(c: ClubPulse) -> dict:
            retour = action(c)
            return vue(c, eid, pid) | ({"effet": retour} if isinstance(retour, dict) else {})
        return au_monde(f)

    @r.put("/moi/essais/{eid}/brouillon")
    def corriger(eid: str, b: Brouillon, version: int, pid: str = Depends(membre)) -> dict:
        return commande(eid, pid, lambda c: c.corriger_essai(pid, eid, version, b.model_dump(mode="json")))

    @r.post("/moi/essais/{eid}/publier")
    def publier(eid: str, v: Publication, pid: str = Depends(membre)) -> dict:
        return commande(eid, pid, lambda c: c.banc.proposer(pid, eid, v.version, v.choix))

    @r.post("/moi/essais/{eid}/decision")
    def decider(eid: str, d: Decision, pid: str = Depends(membre)) -> dict:
        return commande(eid, pid, lambda c: c.banc.decider(pid, eid, d.version, d.accepte))

    @r.post("/moi/essais/{eid}/modifier")
    def modifier(eid: str, m: Modification, pid: str = Depends(membre)) -> dict:
        return commande(eid, pid, lambda c: c.banc.modifier(pid, eid, m.version, **m.model_dump(exclude={"version"})))

    @r.post("/moi/essais/{eid}/adapter")
    def adapter(eid: str, ch: Choix, pid: str = Depends(membre)) -> dict:
        return commande(eid, pid, lambda c: c.banc.choisir_alternative(pid, eid, ch.version, ch.alternative))

    @r.post("/moi/essais/{eid}/lancer")
    def lancer(eid: str, v: Version, pid: str = Depends(membre)) -> dict:
        return commande(eid, pid, lambda c: c.banc.lancer(pid, eid, v.version))

    @r.post("/moi/essais/{eid}/contributions/{etape}")
    def constater(eid: str, etape: str, pid: str = Depends(membre)) -> dict:
        return commande(eid, pid, lambda c: c.banc.constater(pid, eid, etape))

    @r.post("/moi/essais/{eid}/observation")
    def observer(eid: str, o: Observation, pid: str = Depends(membre)) -> dict:
        return commande(eid, pid, lambda c: c.banc.observer(pid, eid, o.texte, o.qualification, o.limites))

    @r.post("/moi/essais/{eid}/avis")
    def aviser(eid: str, a: Avis, pid: str = Depends(membre)) -> dict:
        return commande(eid, pid, lambda c: c.banc.aviser(pid, eid, a.revision, a.avis, a.raison))

    @r.post("/moi/essais/{eid}/reutilisation")
    def reutiliser(eid: str, x: Reutilisation, pid: str = Depends(membre)) -> dict:
        return commande(eid, pid, lambda c: c.banc.reutilisation(pid, eid, x.niveau, x.mention))

    @r.post("/moi/essais/{eid}/retirer")
    def retirer(eid: str, pid: str = Depends(membre)) -> dict:
        return commande(eid, pid, lambda c: c.banc.retirer(pid, eid))

    @r.post("/moi/essais/{eid}/annuler")
    def annuler(eid: str, a: Annulation, pid: str = Depends(membre)) -> dict:
        return commande(eid, pid, lambda c: c.banc.annuler(pid, eid, a.raison))

    # ------------------------------------------------------------------ D. console légère (mêmes objets)
    @r.get("/console/essais", dependencies=[Depends(console)])
    def c_essais() -> dict:
        return au_monde(lambda c: c.vues_essai.console())

    @r.get("/console/essais/{eid}", dependencies=[Depends(console)])
    def c_essai(eid: str) -> dict:
        return au_monde(lambda c: c.vues_essai.essai(eid, None, console=True))

    @r.post("/console/essais/{eid}/annuler", dependencies=[Depends(console)])
    def c_annuler(eid: str, a: Annulation) -> dict:
        def f(c: ClubPulse) -> dict:
            c.banc.annuler("", eid, "annulé par l'animation du Club : " + a.raison, console=True)
            return c.vues_essai.essai(eid, None, console=True)
        return au_monde(f)

    @r.post("/console/essais/{eid}/geste", dependencies=[Depends(console)])
    def c_geste(eid: str, g: GesteJoue) -> dict:
        """DÉMONSTRATION SEULEMENT : un geste d'un membre fictif absent de la scène (ex. Pauline), JOUÉ par l'animation
        et journalisé comme tel. Les deux personnes de la scène agissent depuis leur propre téléphone."""
        def f(c: ClubPulse) -> dict:
            if g.membre not in JOUABLES:
                raise Interdit("seuls les membres absents de la scène peuvent être joués")
            c.banc.decider(g.membre, eid, g.version, g.accepte)
            return c.vues_essai.essai(eid, None, console=True) | {"joue": True}
        return au_monde(f)

