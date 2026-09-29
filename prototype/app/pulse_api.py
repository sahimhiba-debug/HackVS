"""API HTTP de Club Pulse — un ADAPTATEUR mince : valider l'entrée, authentifier, appeler le service, traduire l'erreur.

Aucune règle métier ici (elles sont dans `intelligence/`). Trois garanties par requête :
- UN monde, UN verrou : `au_monde(...)` capture le monde courant une seule fois et exécute la requête entière sous son
  verrou (pas de lecture-vérification-écriture entrelacée ; une réinitialisation concurrente ne mélange pas deux mondes) ;
- erreurs typées → statut HTTP à UN seul endroit (401 qui êtes-vous ; 403 pas le droit ; 404 inconnu ; 409 état
  incompatible ; 422 entrée invalide ; 429 trop de demandes). Tout le reste est une vraie panne : 500 journalisé ;
- la console (rôle animatrice) exige l'en-tête `X-Pulse-Console` (bloque les requêtes intersites sans pré-vol CORS) et,
  si `HACKVS_CONSOLE_JETON` est défini, sa valeur exacte. En démonstration, la console n'a pas de compte : c'est dit.
Mode DÉMO seulement : monde fictif, gestes humains joués, résultats calculés à chaque appel.
"""
from __future__ import annotations

import hmac
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Literal, Optional, TypeVar

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from intelligence.club_pulse import ClubPulse
from intelligence.demo import Demo
from intelligence.erreurs import ErreurMetier, Limite
from intelligence.politique import Spectateur

from .taxonomy import Taxonomie

T = TypeVar("T")
ANIMATRICE = Spectateur("animatrice")


# ---------------------------------------------------------------------- contrats d'entrée (tout est borné)
class Acces(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class Session(BaseModel):
    session: str
    nom: str
    organisation: Optional[str]
    role: str
    profil_complet: bool


class Proposer(BaseModel):
    texte: str = Field(min_length=2, max_length=300)
    sens: Literal["aide", "cherche"]


class Item(BaseModel):
    texte: str = Field(min_length=2, max_length=200)
    concept: Optional[str] = Field(default=None, max_length=64)


class Accueil(BaseModel):
    aide: list[Item] = Field(default_factory=list, max_length=5)
    cherche: list[Item] = Field(default_factory=list, max_length=5)
    visible: bool = False


class ModifProfil(BaseModel):
    retirer_capacite: Optional[str] = Field(default=None, max_length=64)
    ajouter_recherche: Optional[str] = Field(default=None, max_length=200)
    disponible: Optional[bool] = None
    sollicitable: Optional[bool] = None
    visibilite: Optional[dict[Literal["nom", "organisation", "capacites", "interets"], str]] = None


class Note(BaseModel):
    texte: str = Field(min_length=3, max_length=2000)
    evenement: Optional[str] = Field(default=None, max_length=120)


class Demande(BaseModel):
    texte: str = Field(min_length=3, max_length=600)


class Activer(BaseModel):
    anonyme: bool = False
    langue: Optional[Literal["fr", "de", "en", "it"]] = None


class ActivationCreee(BaseModel):
    activation: str


class Reponse(BaseModel):
    accepte: bool


class Contribution(BaseModel):
    nature: Literal["ressource", "rencontre", "conseil", "validation", "introduction", "document", "seance"]
    titre: str = Field(min_length=2, max_length=120)
    contenu: str = Field(default="", max_length=4000)
    reutilisable: bool = False
    attribution: bool = False


class Confirmation(BaseModel):
    verdict: Literal["debloque", "partiel", "non"]
    etape_suivante: bool
    pourquoi: str = Field(default="", max_length=300)


class Temps(BaseModel):
    jours: int = Field(ge=1, le=60)


class Contraintes(BaseModel):
    langue: Optional[Literal["fr", "de", "en", "it"]] = None
    anonyme: Optional[bool] = None


class Ok(BaseModel):
    ok: bool = True


ERREURS = {401: {"description": "Session absente, expirée ou falsifiée"}, 403: {"description": "Geste non autorisé pour ce membre"},
           404: {"description": "Inconnu (ou invisible pour vous)"}, 409: {"description": "État incompatible (déjà fait, transition interdite)"},
           422: {"description": "Entrée invalide"}, 429: {"description": "Trop de demandes"}}


# ---------------------------------------------------------------------- limitation de fréquence
class Limiteur:
    """Fenêtre glissante par clé (ex. adresse IP + route). En mémoire : suffit pour un processus de démonstration ;
    en production, derrière plusieurs instances, elle vivrait dans le proxy ou un magasin partagé."""

    def __init__(self, maximum: int, fenetre_s: float, horloge: Callable[[], float] = time.monotonic):
        self.maximum, self.fenetre_s, self._horloge = maximum, fenetre_s, horloge
        self._traces: dict[str, deque] = defaultdict(deque)
        self._v = threading.Lock()

    def verifier(self, cle: str) -> None:
        with self._v:
            t = self._horloge()
            q = self._traces[cle]
            while q and q[0] <= t - self.fenetre_s:
                q.popleft()
            if len(q) >= self.maximum:
                raise Limite("trop de demandes : réessayez dans une minute")
            q.append(t)


def creer_routeur(tax: Taxonomie, console_jeton: Optional[str] = None) -> APIRouter:
    r = APIRouter(prefix="/api/pulse", tags=["club pulse"], responses=ERREURS)  # type: ignore[arg-type]
    etat = {"demo": Demo(tax)}
    remplacement = threading.Lock()                   # réinitialiser / avancer la démo : une opération à la fois
    limite_acces = Limiteur(10, 60.0)                 # deviner un code d'invitation : 10 essais par minute et par client
    limite_ia = Limiteur(30, 60.0)                    # appels de langage (notes, demandes) : 30 par minute et par membre

    def traduire(e: ErreurMetier) -> HTTPException:
        return HTTPException(e.statut_http, str(e))

    def au_monde(f: Callable[[ClubPulse], T]) -> T:
        c = etat["demo"].club                         # capturé UNE fois pour toute la requête
        with c.verrou:
            try:
                return f(c)
            except ErreurMetier as e:
                raise traduire(e) from None

    def membre(x_pulse_session: Optional[str] = Header(None)) -> str:
        return au_monde(lambda c: c.verifier_session(x_pulse_session or ""))

    def console(x_pulse_console: Optional[str] = Header(None)) -> None:
        if not x_pulse_console:
            raise HTTPException(403, "Console du Club : en-tête X-Pulse-Console requis.")
        if console_jeton and not hmac.compare_digest(x_pulse_console, console_jeton):
            raise HTTPException(403, "Console du Club : jeton invalide.")

    def limiter(lim: Limiteur, cle: str) -> None:
        try:
            lim.verifier(cle)
        except Limite as e:
            raise traduire(e) from None

    # ------------------------------------------------------------------ démonstration (console)
    @r.get("/etat")
    def lire_etat() -> dict:
        d = etat["demo"]
        return {"etape": d.etape, "total": len(d.ETAPES), "traces": d.traces, "date": d.club.jour.isoformat(),
                "monde": d.club.r.nom, "ia": d.club.ia.etat(), "fictif": True}

    @r.post("/demo/reinitialiser", dependencies=[Depends(console)])
    def reinitialiser() -> dict:
        with remplacement:
            etat["demo"] = Demo(tax)
            return lire_etat()

    @r.post("/demo/suivant", dependencies=[Depends(console)])
    def suivant() -> dict:
        with remplacement:                            # double clic : la seconde requête attend, puis avance d'UNE étape
            d = etat["demo"]
            with d.club.verrou:
                if d.etape >= len(d.ETAPES):
                    raise HTTPException(409, "Démonstration terminée : réinitialisez ou rejouez.")
                t = d.suivant()
            return lire_etat() | {"derniere": t}

    @r.post("/demo/aller/{n}", dependencies=[Depends(console)])
    def aller(n: int) -> dict:
        if not 0 <= n <= len(Demo.ETAPES):
            raise HTTPException(422, "Étape hors limites.")
        with remplacement:
            d = Demo(tax)
            d.rejouer(n)
            etat["demo"] = d
            return lire_etat()

    # ------------------------------------------------------------------ accès
    @r.post("/acces", response_model=Session)
    def acces(a: Acces, request: Request) -> dict:
        limiter(limite_acces, f"acces|{request.client.host if request.client else '?'}")
        return au_monde(lambda c: c.activer_compte(a.code))

    # ------------------------------------------------------------------ application du membre
    @r.get("/moi/pouls")
    def pouls(pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.vues.pouls_membre(pid))

    @r.get("/moi/profil")
    def profil(pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.vues.vue_profil(pid))

    @r.post("/moi/profil/proposer")
    def proposer(p: Proposer, pid: str = Depends(membre)) -> list[dict]:
        return au_monde(lambda c: c.proposer(p.texte, p.sens))

    @r.post("/moi/accueil")
    def accueil(a: Accueil, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.onboarding(pid, [i.model_dump() for i in a.aide], [i.model_dump() for i in a.cherche], a.visible))

    @r.patch("/moi/profil")
    def modifier(m: ModifProfil, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.modifier_profil(pid, retirer_capacite=m.retirer_capacite, ajouter_recherche=m.ajouter_recherche,
                                                    disponible=m.disponible, accepte=m.sollicitable,
                                                    visibilite={str(k): v for k, v in m.visibilite.items()} if m.visibilite else None))

    @r.get("/moi/notes")
    def notes(pid: str = Depends(membre)) -> list[dict]:
        return au_monde(lambda c: c.vues.notes_de(pid))

    @r.post("/moi/notes")
    def noter(n: Note, pid: str = Depends(membre)) -> dict:
        limiter(limite_ia, f"ia|{pid}")
        return au_monde(lambda c: c.capturer(pid, n.texte, n.evenement))

    @r.post("/moi/notes/{note_id}/partager/{index}")
    def partager(note_id: str, index: int, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.partager(pid, note_id, index))

    @r.post("/moi/demandes")
    def demander(d: Demande, pid: str = Depends(membre)) -> dict:
        limiter(limite_ia, f"ia|{pid}")
        return au_monde(lambda c: c.demander(pid, d.texte))

    @r.get("/moi/opportunites/{oid}")
    def opportunite(oid: str, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.vues.vue_opportunite(c.opportunite(oid), Spectateur("membre", pid)))

    @r.get("/moi/opportunites/{oid}/pourquoi")
    def pourquoi(oid: str, pid: str = Depends(membre)) -> dict:
        def f(c: ClubPulse) -> dict:
            c.vues.vue_opportunite(c.opportunite(oid), Spectateur("membre", pid))    # contrôle d'accès avant l'IA
            return c.expliquer(oid, Spectateur("membre", pid))
        return au_monde(f)

    @r.post("/moi/opportunites/{oid}/activer", response_model=ActivationCreee)
    def activer(oid: str, a: Activer, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: {"activation": c.activer(oid, Spectateur("membre", pid), anonyme=a.anonyme)})

    @r.get("/moi/sollicitations")
    def sollicitations(pid: str = Depends(membre)) -> list[dict]:
        return au_monde(lambda c: c.vues.demandes_pour(pid))

    @r.post("/moi/sollicitations/{aid}", response_model=Ok)
    def repondre(aid: str, rep: Reponse, pid: str = Depends(membre)) -> Ok:
        au_monde(lambda c: c.repondre(aid, pid, rep.accepte))
        return Ok()

    @r.get("/moi/activations")
    def activations(pid: str = Depends(membre)) -> list[dict]:
        return au_monde(lambda c: c.vues.activations_de(pid))

    @r.get("/moi/activations/{aid}")
    def activation(aid: str, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.vues.vue_activation(aid, Spectateur("membre", pid)))

    @r.post("/moi/activations/{aid}/contribuer", response_model=Ok)
    def contribuer(aid: str, k: Contribution, pid: str = Depends(membre)) -> Ok:
        au_monde(lambda c: c.contribuer(aid, pid, k.nature, k.titre, k.contenu, k.reutilisable, k.attribution))
        return Ok()

    @r.post("/moi/activations/{aid}/confirmer")
    def confirmer(aid: str, k: Confirmation, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.confirmer(aid, pid, k.verdict, k.etape_suivante, k.pourquoi))

    @r.post("/moi/activations/{aid}/retirer", response_model=Ok)
    def retirer(aid: str, pid: str = Depends(membre)) -> Ok:
        au_monde(lambda c: c.retirer_consentement(aid, pid))
        return Ok()

    @r.post("/moi/activations/{aid}/reutiliser", response_model=Ok)
    def reutiliser(aid: str, pid: str = Depends(membre)) -> Ok:
        au_monde(lambda c: c.reutiliser(aid, pid))
        return Ok()

    @r.get("/moi/evenements")
    def evenements(pid: str = Depends(membre)) -> list[dict]:
        return au_monde(lambda c: c.vues.evenements_de(pid))

    @r.get("/memoire")
    def memoire(pid: str = Depends(membre)) -> list[dict]:
        return au_monde(lambda c: c.vues.memoire_club(Spectateur("membre", pid)))

    @r.get("/memoire/{motif_id}/fiche", response_class=PlainTextResponse)
    def fiche(motif_id: str, pid: str = Depends(membre)) -> PlainTextResponse:
        texte = au_monde(lambda c: c.vues.fiche(motif_id))
        return PlainTextResponse(texte, headers={"Content-Disposition": f'attachment; filename="fiche-{motif_id[:16]}.txt"'})

    # ------------------------------------------------------------------ tour de contrôle du Club (rôle animatrice)
    @r.get("/console", dependencies=[Depends(console)])
    def tour() -> dict:
        return au_monde(lambda c: c.vues.tour())

    @r.post("/console/scan", dependencies=[Depends(console)])
    def scan() -> dict:
        def f(c: ClubPulse) -> dict:
            c.scanner(force=True)
            return c.vues.tour()
        return au_monde(f)

    @r.get("/console/opportunites/{oid}", dependencies=[Depends(console)])
    def c_opportunite(oid: str) -> dict:
        return au_monde(lambda c: c.vues.vue_opportunite(c.opportunite(oid), ANIMATRICE) | {"explication": c.expliquer(oid, ANIMATRICE)})

    @r.post("/console/opportunites/{oid}/activer", dependencies=[Depends(console)], response_model=ActivationCreee)
    def c_activer(oid: str, a: Activer) -> dict:
        return au_monde(lambda c: {"activation": c.activer(oid, ANIMATRICE, anonyme=a.anonyme, langue=a.langue)})

    @r.post("/console/opportunites/{oid}/ecarter", dependencies=[Depends(console)], response_model=Ok)
    def c_ecarter(oid: str) -> Ok:
        au_monde(lambda c: c.ecarter(oid))
        return Ok()

    @r.get("/console/activations/{aid}", dependencies=[Depends(console)])
    def c_activation(aid: str) -> dict:
        return au_monde(lambda c: c.vues.vue_activation(aid, ANIMATRICE))

    @r.post("/console/activations/{aid}/contraintes", dependencies=[Depends(console)])
    def c_contraintes(aid: str, k: Contraintes) -> dict:
        def f(c: ClubPulse) -> dict:
            c.changer_contraintes(aid, k.langue, k.anonyme)
            return c.vues.vue_activation(aid, ANIMATRICE)
        return au_monde(f)

    @r.post("/console/activations/{aid}/{action}", dependencies=[Depends(console)])
    def c_action(aid: str, action: Literal["lancer", "pause", "reprendre", "annuler"]) -> dict:
        def f(c: ClubPulse) -> dict:
            c.piloter(aid, action)
            return c.vues.vue_activation(aid, ANIMATRICE)
        return au_monde(f)

    @r.post("/console/temps", dependencies=[Depends(console)])
    def c_temps(t: Temps) -> dict:
        return au_monde(lambda c: {"echeances": c.avancer(t.jours), "date": c.jour.isoformat()})

    @r.get("/console/personas", dependencies=[Depends(console)])
    def personas() -> list[dict]:
        d = etat["demo"]
        with d.club.verrou:
            return d.personas()

    return r
