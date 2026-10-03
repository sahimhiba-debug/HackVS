"""API HTTP de Club Pulse — un ADAPTATEUR mince : valider l'entrée, authentifier, appeler le service, traduire l'erreur.

Aucune règle métier ici (elles sont dans `intelligence/`). Trois garanties par requête :
- UN monde, UN verrou : `au_monde(...)` capture le monde courant une seule fois et exécute la requête entière sous son
  verrou (pas de lecture-vérification-écriture entrelacée ; une réinitialisation concurrente ne mélange pas deux mondes) ;
- erreurs typées → statut HTTP à UN seul endroit (401 qui êtes-vous ; 403 pas le droit ; 404 inconnu ; 409 état
  incompatible ; 422 entrée invalide ; 429 trop de demandes). Tout le reste est une vraie panne : 500 journalisé ;
- la console (rôle animatrice) exige l'en-tête `X-Pulse-Console` (bloque les requêtes intersites sans pré-vol CORS) et,
  si `HACKVS_CONSOLE_JETON` est défini, sa valeur exacte. En démonstration, la console n'a pas de compte : c'est dit.
Mode DÉMO seulement : monde fictif, gestes humains joués, résultats calculés à chaque appel. Les routes du banc
d'essai (`essai_api`) partagent ces sessions, ce verrou et ces erreurs.
"""
from __future__ import annotations

import hmac
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Iterator, Literal, Optional, TypeVar

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from intelligence.club_pulse import ClubPulse
from intelligence.demo import Demo
from intelligence.erreurs import ErreurMetier, Limite
from intelligence.politique import Spectateur

from .capacites_api import ajouter_routes as ajouter_routes_capacites
from .essai_api import ajouter_routes as ajouter_routes_essai
from .foire_api import ajouter_routes as ajouter_routes_foire
from .protections import LOCALES
from .taxonomy import Taxonomie

T = TypeVar("T")
ANIMATRICE = Spectateur("animatrice")


# ---------------------------------------------------------------------- contrats d'entrée (tout est borné)
class Acces(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class PassJure(BaseModel):
    persona: str = Field(min_length=1, max_length=40)
    minutes: int = Field(default=15, ge=1, le=60)


class ActivationJure(BaseModel):
    jeton: str = Field(min_length=10, max_length=160)


def qr_svg(url: str) -> str:
    """QR code produit ICI (bibliothèque locale, aucun service externe), en data: URI (la CSP l'autorise pour img)."""
    import base64
    import io

    import qrcode
    import qrcode.image.svg
    tampon = io.BytesIO()
    qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2).save(tampon)
    return "data:image/svg+xml;base64," + base64.b64encode(tampon.getvalue()).decode()


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


class Effacement(BaseModel):
    confirme: Literal[True]                            # « Tout effacer » : jamais sans une confirmation explicite


class Temps(BaseModel):
    jours: int = Field(ge=1, le=60)


class EssaiCree(BaseModel):
    essai: str


class Ok(BaseModel):
    ok: bool = True


ERREURS = {401: {"description": "Session absente, expirée ou falsifiée"}, 403: {"description": "Geste non autorisé pour ce membre"},
           404: {"description": "Inconnu (ou invisible pour vous)"}, 409: {"description": "État incompatible (déjà fait, transition interdite)"},
           422: {"description": "Entrée invalide"}, 429: {"description": "Trop de demandes"}}


# ---------------------------------------------------------------------- limitation de fréquence
class Limiteur:
    """Fenêtre glissante par clé (ex. adresse IP + route). En mémoire : suffit pour un processus de démonstration ;
    en production, derrière plusieurs instances, elle vivrait dans le proxy ou un magasin partagé."""

    def __init__(self, maximum: int, fenetre_s: float, horloge: Callable[[], float] = time.monotonic,
                 message: str = "trop de demandes : réessayez dans une minute"):
        self.maximum, self.fenetre_s, self._horloge, self.message = maximum, fenetre_s, horloge, message
        self._traces: dict[str, deque] = defaultdict(deque)
        self._v = threading.Lock()
        self._purge = horloge()

    def verifier(self, cle: str) -> None:
        with self._v:
            t = self._horloge()
            if t - self._purge >= self.fenetre_s:
                # une fois par fenêtre : oublier les clés dont TOUTES les traces en sont sorties (sinon chaque clé jamais
                # vue — un code inventé — resterait en mémoire pour toujours : revue publique R-02)
                for k in [k for k, q in self._traces.items() if not q or q[-1] <= t - self.fenetre_s]:
                    del self._traces[k]
                self._purge = t
            q = self._traces[cle]
            while q and q[0] <= t - self.fenetre_s:
                q.popleft()
            if len(q) >= self.maximum:
                raise Limite(self.message)
            q.append(t)


class Passage:
    """Verrou lecteurs / rédacteur, indépendant des fils (F28). Chaque requête est un LECTEUR du monde courant pour
    toute sa durée ; remplacer le monde (réinitialiser, aller à une étape) est le RÉDACTEUR : il attend que les requêtes
    en vol se terminent, et les nouvelles attendent qu'il ait fini. Aucune requête ne voit deux mondes."""

    def __init__(self) -> None:
        self._c = threading.Condition()
        self._lecteurs, self._redacteur, self._en_attente = 0, False, 0

    def entrer(self, rediger: bool) -> None:
        with self._c:
            if rediger:
                self._en_attente += 1
                self._c.wait_for(lambda: not self._redacteur and self._lecteurs == 0)
                self._en_attente -= 1
                self._redacteur = True
            else:                                      # priorité au rédacteur : pas de famine de la réinitialisation
                self._c.wait_for(lambda: not self._redacteur and self._en_attente == 0)
                self._lecteurs += 1

    def sortir(self, rediger: bool) -> None:
        with self._c:
            if rediger:
                self._redacteur = False
            else:
                self._lecteurs -= 1
            self._c.notify_all()


REMPLACER_LE_MONDE = ("/api/pulse/demo/reinitialiser", "/api/pulse/demo/aller/")


def creer_routeur(tax: Taxonomie, console_jeton: Optional[str] = None) -> APIRouter:
    passage = Passage()

    def garde(request: Request) -> Iterator[None]:
        rediger = request.url.path.startswith(REMPLACER_LE_MONDE)
        passage.entrer(rediger)
        try:
            yield
        finally:
            passage.sortir(rediger)

    r = APIRouter(prefix="/api/pulse", tags=["club pulse"], responses=ERREURS,  # type: ignore[arg-type]
                  dependencies=[Depends(garde)])
    etat = {"demo": Demo(tax, reprendre=True)}        # démarrage : l'état est repris du journal (jamais effacé)

    def remplacer(nouveau: Demo) -> None:
        """Sous le passage RÉDACTEUR seulement : le monde neuf prend la place, l'ancien journal est fermé."""
        ancien, etat["demo"] = etat["demo"], nouveau
        if ancien is not nouveau:
            ancien.club.journal.fermer()
    remplacement = threading.Lock()                   # réinitialiser / avancer la démo : une opération à la fois
    # ACCÈS PAR CODE D'INVITATION : jamais par adresse IP (F09 — une salle entière sort par la même adresse, comme pour le
    # QR juré). Par CODE tenté (deviner UN code : 5 essais par minute) et un plafond GLOBAL doux (balayer beaucoup de
    # codes : 300 essais par minute pour tout le serveur, de quoi activer une salle entière en une minute)
    limite_acces_code = Limiteur(5, 60.0)
    limite_acces_global = Limiteur(300, 60.0)
    limite_ia = Limiteur(30, 60.0)                    # appels de langage (notes, demandes) : 30 par minute et par membre
    # ÉCRITURES qui font grandir le journal (offres, essais, notes) : 30 par minute et par MEMBRE — un passe juré est une
    # session de membre, il a donc le même plafond (décision D2 ; sans plafond, des centaines d'offres ou de brouillons
    # alourdissaient chaque recalcul de l'Établi, voir durcissement H2)
    limite_ecritures = Limiteur(30, 60.0, message="trop de publications en une minute : attendez un instant avant de publier "
                                                  "de nouveau")
    # QR JURÉ : jamais par adresse IP (dans la salle, tout le public partage la même) — par CODE et par SESSION
    limite_jure_global = Limiteur(300, 60.0)          # plafond GLOBAL doux, comme `/acces` (R-02 : sans lui, des passes
    #                                                   inventés à la chaîne n'étaient freinés par rien)
    limite_jure_code = Limiteur(5, 60.0)              # activations tentées sur un même passe
    limite_jure_session = Limiteur(90, 60.0)          # requêtes d'une session de juré

    def traduire(e: ErreurMetier) -> HTTPException:
        return HTTPException(e.statut_http, str(e))

    def au_monde(f: Callable[[ClubPulse], T]) -> T:
        c = etat["demo"].club                         # capturé UNE fois pour toute la requête
        with c.verrou:
            try:
                return f(c)
            except ErreurMetier as e:
                raise traduire(e) from None

    def hors_verrou(f: Callable[[ClubPulse], T]) -> T:
        """Comme `au_monde`, SANS le verrou du monde : pour un appel au modèle de langage (secondes) qui n'écrit rien —
        la méthode prend elle-même le verrou pour ce qu'elle lit et pour la trace. La requête reste LECTRICE du monde
        courant (passage) : une réinitialisation attend qu'elle se termine."""
        c = etat["demo"].club
        try:
            return f(c)
        except ErreurMetier as e:
            raise traduire(e) from None

    def membre(x_pulse_session: Optional[str] = Header(None)) -> str:
        pid = au_monde(lambda c: c.verifier_session(x_pulse_session or ""))
        if au_monde(lambda c: c.passes_jure.est_session_de_jure(x_pulse_session or "")):
            limiter(limite_jure_session, f"jure-session|{x_pulse_session}")
        return pid

    def console(request: Request, x_pulse_console: Optional[str] = Header(None)) -> None:
        if not x_pulse_console:
            raise HTTPException(403, "Console du Club : en-tête X-Pulse-Console requis.")
        if console_jeton:
            if not hmac.compare_digest(x_pulse_console, console_jeton):
                raise HTTPException(403, "Console du Club : jeton invalide.")
        elif (request.client.host if request.client else "") not in LOCALES:
            # sans jeton configuré, la console (qui peut incarner chaque membre) ne répond qu'à CETTE machine :
            # un déploiement accessible depuis le réseau doit définir HACKVS_CONSOLE_JETON
            raise HTTPException(403, "Console du Club : hors de cette machine, définissez HACKVS_CONSOLE_JETON.")

    def limiter(lim: Limiteur, cle: str) -> None:
        try:
            lim.verifier(cle)
        except Limite as e:
            raise traduire(e) from None

    # ------------------------------------------------------------------ démonstration (console)
    @r.get("/etat", dependencies=[Depends(console)])     # le récit de la démonstration nomme des personnes : console seulement
    def lire_etat() -> dict:
        d = etat["demo"]
        return {"etape": d.etape, "total": len(d.ETAPES), "traces": d.traces, "date": d.club.jour.isoformat(),
                "actes": [f.__name__.split("_", 2)[-1] for f in d.ETAPES],
                "monde": d.club.r.nom, "ia": d.club.ia.etat(), "fictif": True}

    @r.post("/demo/reinitialiser", dependencies=[Depends(console)])
    def reinitialiser() -> dict:
        with remplacement:
            remplacer(Demo(tax))
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
            remplacer(d)
            return lire_etat()

    # ------------------------------------------------------------------ accès
    @r.post("/acces", response_model=Session)
    def acces(a: Acces) -> dict:
        limiter(limite_acces_global, "acces")
        limiter(limite_acces_code, "acces-code|" + a.code.strip().upper())
        return au_monde(lambda c: c.activer_compte(a.code))

    # ------------------------------------------------------------------ QR juré
    @r.post("/console/jure", dependencies=[Depends(console)])
    def passe_jure(p: PassJure, request: Request) -> dict:
        res = au_monde(lambda c: c.emettre_pass_jure(p.persona, p.minutes))
        import os
        base = os.environ.get("HACKVS_URL_PUBLIQUE") or str(request.base_url).rstrip("/")
        return {k: v for k, v in res.items() if k != "jeton"} | {"url": base + res["chemin"], "qr": qr_svg(base + res["chemin"])}

    @r.post("/jure", response_model=None)
    def activer_jure(a: ActivationJure) -> dict:
        limiter(limite_jure_global, "jure")
        limiter(limite_jure_code, "jure-code|" + au_monde(lambda c: c.passes_jure.nonce(a.jeton)))
        return au_monde(lambda c: c.utiliser_pass_jure(a.jeton))

    # ------------------------------------------------------------------ application du membre
    @r.get("/moi/date")
    def date_du_club(pid: str = Depends(membre)) -> dict:
        """La date du monde (simulée en démonstration) : chaque écran du téléphone l'affiche."""
        return au_monde(lambda c: {"date": c.jour.isoformat(), "simulee": True})

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

    @r.post("/moi/effacer")
    def effacer(x: Effacement, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.effacer(pid))

    @r.get("/moi/notes")
    def notes(pid: str = Depends(membre)) -> list[dict]:
        return au_monde(lambda c: c.vues.notes_de(pid))

    @r.post("/moi/notes")
    def noter(n: Note, pid: str = Depends(membre)) -> dict:
        limiter(limite_ecritures, f"ecrit|{pid}")
        limiter(limite_ia, f"ia|{pid}")
        return au_monde(lambda c: c.capturer(pid, n.texte, n.evenement))

    @r.post("/moi/notes/{note_id}/partager/{index}")
    def partager(note_id: str, index: int, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.partager(pid, note_id, index))

    @r.post("/moi/demandes")
    def demander(d: Demande, pid: str = Depends(membre)) -> dict:
        limiter(limite_ia, f"ia|{pid}")
        return au_monde(lambda c: c.demander(pid, d.texte))                 # une INTERPRÉTATION : rien n'est publié

    @r.post("/moi/demandes/{proposition}/confirmer")
    def confirmer_demande(proposition: str, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.confirmer_demande(pid, proposition[:16]))

    # ------------------------------------------------------------------ découvertes (Network Intelligence → la personne aidée)
    @r.get("/moi/decouvertes")
    def decouvertes(pid: str = Depends(membre)) -> list[dict]:
        return au_monde(lambda c: c.vues.decouvertes_de(pid))

    @r.get("/moi/decouvertes/{oid}")
    def decouverte(oid: str, pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: c.vues.decouverte_de(pid, oid))

    @r.post("/moi/decouvertes/{oid}/en-clair")
    def narrer(oid: str, pid: str = Depends(membre)) -> dict:
        """COMMANDE : demander la reformulation (IA contrôlée si configurée) ; la lecture GET la relit sans appel."""
        limiter(limite_ia, f"ia|{pid}")
        return au_monde(lambda c: c.narrer_decouverte(oid, Spectateur("membre", pid)))

    @r.get("/moi/decouvertes/{oid}/en-clair")
    def en_clair(oid: str, pid: str = Depends(membre)) -> dict:
        limiter(limite_ia, f"ia|{pid}")
        return au_monde(lambda c: c.en_clair(oid, Spectateur("membre", pid)))

    @r.post("/moi/decouvertes/{oid}/essai", response_model=EssaiCree)
    def proposer_essai(oid: str, pid: str = Depends(membre)) -> dict:
        limiter(limite_ecritures, f"ecrit|{pid}")
        return au_monde(lambda c: {"essai": c.proposer_essai(pid, oid)})    # un BROUILLON, visible de la personne seule

    # ------------------------------------------------------------------ salle de contrôle du Club (rôle animatrice)
    @r.get("/console/intelligence", dependencies=[Depends(console)])
    def c_intelligence() -> dict:
        return au_monde(lambda c: c.vues.panneau())

    @r.get("/console/decouvertes/{oid}", dependencies=[Depends(console)])
    def c_decouverte(oid: str) -> dict:
        return au_monde(lambda c: c.vues.opportunite_console(oid))

    @r.post("/console/temps", dependencies=[Depends(console)])
    def c_temps(t: Temps) -> dict:
        return au_monde(lambda c: {"echeances": c.avancer(t.jours), "date": c.jour.isoformat()})

    ajouter_routes_essai(r, au_monde, membre, console, lambda pid: limiter(limite_ia, f"ia|{pid}"),
                         lambda pid: limiter(limite_ecritures, f"ecrit|{pid}"), hors_verrou)
    ajouter_routes_capacites(r, au_monde, membre, console)
    ajouter_routes_foire(r, au_monde, membre, console)

    @r.get("/console/personas", dependencies=[Depends(console)])
    def personas() -> list[dict]:
        d = etat["demo"]
        with d.club.verrou:
            return d.personas()

    return r
