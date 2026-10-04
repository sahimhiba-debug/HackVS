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
import os
import threading
import time
from collections import defaultdict, deque
from datetime import date
from pathlib import Path
from typing import Callable, Iterator, Literal, Optional, TypeVar

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from intelligence.club_pulse import ClubPulse
from intelligence.demo import Demo
from intelligence.erreurs import ErreurMetier, Limite
from intelligence.politique import Spectateur

from .urls import base_publique
from .capacites_api import ajouter_routes as ajouter_routes_capacites
from .essai_api import ajouter_routes as ajouter_routes_essai
from .foire_api import ajouter_routes as ajouter_routes_foire
from .salle_api import ajouter_routes as ajouter_routes_salle
from .visite_api import ajouter_routes as ajouter_routes_visite
from .visite_api import visite
from .protections import est_local
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


class Pause(BaseModel):
    jusqu_au: date


class Preferences(BaseModel):
    langue: Literal["fr", "de", "en", "it"]
    region: str = Field(default="", max_length=60)
    canaux: list[Literal["app", "email", "sms"]] = Field(min_length=1, max_length=3)


class MetierConfirme(BaseModel):
    valeur: str = Field(min_length=1, max_length=200)
    metier: str = Field(min_length=1, max_length=40)


class Campagne(BaseModel):
    metier: str = Field(min_length=1, max_length=40)
    nombre: int = Field(ge=1, le=20)


class InvitationConsole(BaseModel):
    role: Literal["membre", "invite", "secretariat", "administration"]
    etiquette: str = Field(min_length=1, max_length=60)
    duree_s: int = Field(default=7 * 24 * 3600, ge=60, le=30 * 24 * 3600)


def _imprimer_pdf(html_doc: str) -> bytes:
    """ANNÉE 1 · LOT 4 : le PDF du bilan est l'IMPRESSION de son HTML par Chromium (Playwright). Sans Playwright : 501."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise HTTPException(501, "PDF indisponible sur ce serveur (Playwright absent) : téléchargez le Markdown") from None
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:                                 # navigateur hors de l'emplacement par défaut
            b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"))
        try:
            pg = b.new_page()
            pg.set_content(html_doc, wait_until="load")
            return pg.pdf(format="A4", print_background=True)
        finally:
            b.close()


class ADistance(BaseModel):
    oui: bool


class ClubExemple(BaseModel):
    id: str = Field(min_length=2, max_length=40)
    nom: str = Field(min_length=3, max_length=80)
    region: str = Field(default="", max_length=60)
    pays: str = Field(default="CH", min_length=2, max_length=2)
    fictif: bool


class LotPasses(BaseModel):
    nombre: int = Field(ge=1, le=500)


class ImportExposants(BaseModel):
    csv: str = Field(min_length=5, max_length=60_000)    # sous le plafond de 64 Kio du corps (M3)


class Adhesion(BaseModel):
    reference: str = Field(min_length=3, max_length=20)


class AVerifier(BaseModel):
    sd_jwt: str = Field(min_length=20, max_length=20_000)


class Desinscription(BaseModel):
    jeton: str = Field(min_length=8, max_length=200)


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
    limite_desinscription = Limiteur(5, 60.0)         # ANNÉE 1 · lot 5 : par lien de désinscription valide
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
        elif visite():
            pass                                      # monde « visite » : bac à sable fictif, conteneur à part (docs/DEPLOIEMENT.md)
        elif not est_local(request.client.host if request.client else "", request.headers.raw):
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

    def jamais_en_production() -> None:
        """AUDIT I6 : une nouvelle démonstration VIDE le journal. Sur PostgreSQL (la production, lot 1), refusé."""
        if (os.environ.get("HACKVS_ESSAIS_DB") or "").startswith(("postgresql://", "postgres://")):
            raise HTTPException(409, "Journal de production (PostgreSQL) : une nouvelle démonstration l'effacerait — refusé.")

    @r.post("/demo/reinitialiser", dependencies=[Depends(console), Depends(jamais_en_production)])
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

    @r.post("/demo/aller/{n}", dependencies=[Depends(console), Depends(jamais_en_production)])
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
        base = base_publique(request)
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

    # ANNÉE 1 · LOT 3 — l'espace membre (pause, préférences, mes demandes, export, effacement définitif) : construit sur
    # la branche annee-1, éteint par défaut (HACKVS_ESPACE_MEMBRE=1) — la démo n'en dépend pas
    def espace_allume() -> None:
        if os.environ.get("HACKVS_ESPACE_MEMBRE") != "1":
            raise HTTPException(404, "Not Found")

    @r.get("/moi/espace", dependencies=[Depends(espace_allume)])
    def espace(pid: str = Depends(membre)) -> dict:
        from intelligence import espace_membre as em, reciprocite
        return au_monde(lambda c: {"pause": em.etat_pause(c, pid), "preferences": em.preferences(c, pid),
                                   "demandes": em.mes_demandes(c, pid), "solde": reciprocite.balance(c, pid),
                                   "pause_max_jours": em.PAUSE_MAX_JOURS})

    @r.post("/moi/pause", dependencies=[Depends(espace_allume)])
    def pause(x: Pause, pid: str = Depends(membre)) -> dict:
        from intelligence import espace_membre as em
        limiter(limite_ecritures, f"ecrit|{pid}")
        return au_monde(lambda c: em.mettre_en_pause(c, pid, x.jusqu_au))

    @r.post("/moi/pause/fin", dependencies=[Depends(espace_allume)])
    def pause_fin(pid: str = Depends(membre)) -> dict:
        from intelligence import espace_membre as em
        limiter(limite_ecritures, f"ecrit|{pid}")
        return au_monde(lambda c: em.reprendre(c, pid))

    @r.post("/moi/preferences", dependencies=[Depends(espace_allume)])
    def regler_preferences(x: Preferences, pid: str = Depends(membre)) -> dict:
        from intelligence import espace_membre as em
        limiter(limite_ecritures, f"ecrit|{pid}")
        return au_monde(lambda c: em.regler_preferences(c, pid, langue=x.langue, region=x.region, canaux=list(x.canaux)))

    @r.get("/moi/export", dependencies=[Depends(espace_allume)])
    def exporter(pid: str = Depends(membre)) -> JSONResponse:
        from intelligence import espace_membre as em
        return JSONResponse(au_monde(lambda c: em.exporter(c, pid)), headers={
            "Content-Disposition": 'attachment; filename="club-pulse-mes-donnees.json"', "Cache-Control": "no-store"})

    @r.post("/moi/effacer-definitivement", dependencies=[Depends(espace_allume)])
    def effacer_definitivement(x: Effacement, pid: str = Depends(membre)) -> dict:
        from intelligence import espace_membre as em
        return au_monde(lambda c: em.effacer_definitivement(c, pid))

    # ANNÉE 1 · LOT 8 — plusieurs clubs (exemples fictifs), adhésion croisée choisie par le membre, membre à distance
    def multiclub_allume() -> None:
        if os.environ.get("HACKVS_MULTICLUB") != "1":
            raise HTTPException(404, "Not Found")

    @r.get("/langues", dependencies=[Depends(multiclub_allume)])
    def langues() -> dict:
        """PUBLIQUE : les langues de l'interface au-delà du français et de l'allemand (audit des lots 6-8, I4 : l'anglais
        suit l'interrupteur — éteint, la route n'existe pas et le téléphone reste en français)."""
        return {"en": True, "a_relire": "traduction à relire par un natif"}

    @r.get("/moi/clubs", dependencies=[Depends(multiclub_allume)])
    def mes_clubs(pid: str = Depends(membre)) -> dict:
        from intelligence import clubs
        return au_monde(lambda c: {"clubs": clubs.liste(c), "moi": clubs.clubs_de(c, pid)})

    @r.post("/moi/clubs/{cid}", dependencies=[Depends(multiclub_allume)])
    def rejoindre_club(cid: str, pid: str = Depends(membre)) -> dict:
        from intelligence import clubs
        limiter(limite_ecritures, f"ecrit|{pid}")
        return au_monde(lambda c: clubs.rejoindre(c, pid, cid[:40]))

    @r.post("/moi/clubs/{cid}/quitter", dependencies=[Depends(multiclub_allume)])
    def quitter_club(cid: str, pid: str = Depends(membre)) -> dict:
        from intelligence import clubs
        limiter(limite_ecritures, f"ecrit|{pid}")
        return au_monde(lambda c: clubs.quitter(c, pid, cid[:40]))

    @r.post("/moi/a-distance", dependencies=[Depends(multiclub_allume)])
    def membre_a_distance(x: ADistance, pid: str = Depends(membre)) -> dict:
        from intelligence import clubs
        limiter(limite_ecritures, f"ecrit|{pid}")
        return au_monde(lambda c: clubs.a_distance(c, pid, x.oui))

    # ANNÉE 1 · LOT 10 — prototype e-ID : reçus émis comme attestations SD-JWT VC (« prototype, non connecté à swiyu »)
    def eid_allume() -> None:
        if os.environ.get("HACKVS_EID") != "1":
            raise HTTPException(404, "Not Found")

    def emetteur():
        from intelligence import attestations as at
        return at.Emetteur(etat["demo"].club.reglages.secret)

    @r.get("/moi/attestations", dependencies=[Depends(eid_allume)])
    def mes_attestations(pid: str = Depends(membre)) -> dict:
        from intelligence import attestations as at
        e = emetteur()
        return au_monde(lambda c: {"mention": at.MENTION, "emetteur": e.did,
                                   "attestations": [{"reference": r["reference"], "sd_jwt": e.emettre(c, pid, r)}
                                                    for r in c.capacites.recus(pid)]})

    @r.post("/attestations/verifier", dependencies=[Depends(eid_allume)])
    def verifier_attestation(x: AVerifier) -> dict:
        """PUBLIQUE : le vérificateur LOCAL de démonstration (lecture seule, aucun état)."""
        from intelligence import attestations as at
        limiter(limite_acces_global, "attestations")
        return at.verifier(x.sd_jwt, emetteurs={emetteur().did})       # seul l'émetteur de CE serveur (B1)

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
    ajouter_routes_foire(r, au_monde, membre, console, limiter=limiter, nouveau_limiteur=Limiteur, qr=qr_svg,
                         hors_verrou=hors_verrou)
    ajouter_routes_visite(r, qr_svg)
    r.journal = lambda: etat["demo"].club.journal  # type: ignore[attr-defined]   # ANNÉE 1 : /sante/pret, /metriques
    _comptes: dict = {"club": None, "c": None}

    def comptes():
        """ANNÉE 1 · LOT 2 : les comptes vivent dans le journal du Club (et le suivent s'il est remplacé). Clé propre,
        dérivée du secret du serveur : une signature de session de membre ne vaut jamais pour un compte."""
        import hashlib
        import hmac as _hmac

        from intelligence.comptes import Comptes
        club = etat["demo"].club
        if _comptes["club"] is not club:
            cle = _hmac.new(club.reglages.secret, b"comptes|annee-1", hashlib.sha256).digest()
            _comptes["club"], _comptes["c"] = club, Comptes(club.journal, cle)
        return _comptes["c"]
    r.comptes = comptes  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ ANNÉE 1 · LOT 4 : console du secrétariat
    # Éteinte par défaut (HACKVS_SECRETARIAT=1, avec HACKVS_COMPTES=1). Jamais le jeton « console » de la démo : un compte
    # NOMINATIF du secrétariat ou de l'administration, double authentification active, session élevée par un code.
    from .comptes_api import _origine_sure

    def secretariat(request: Request, x_pulse_compte: Optional[str] = Header(None)) -> str:
        if os.environ.get("HACKVS_SECRETARIAT") != "1" or os.environ.get("HACKVS_COMPTES") != "1":
            raise HTTPException(404, "Not Found")
        _origine_sure(request)
        if not x_pulse_compte:
            raise HTTPException(401, "session de compte requise (X-Pulse-Compte)")
        route = request.scope.get("route")                 # ANNÉE 1 · lot 6 : journal des accès (la route, jamais
        nom = f"{request.method} {getattr(route, 'path', request.url.path)}"   # les données)
        try:
            comptes().exiger_console(x_pulse_compte)
            if request.method != "GET":
                comptes().compter_ecriture(x_pulse_compte)
            comptes().tracer_acces(x_pulse_compte, nom)
        except ErreurMetier as e:
            try:                                           # audit des lots 6-8, I2 : un REFUS d'une session valide est
                comptes().tracer_acces(x_pulse_compte, nom + " (refusé)")   # tracé aussi
            except ErreurMetier:
                pass                                       # session invalide : il n'y a personne à qui l'attribuer
            raise traduire(e) from None
        return x_pulse_compte

    def criteres() -> Path:
        from intelligence import secretariat as sec
        return Path(os.environ.get("HACKVS_CRITERES_PILOTE") or sec.CRITERES_DEFAUT)

    @r.get("/secretariat/metiers")
    def sec_metiers(s: str = Depends(secretariat)) -> dict:
        from intelligence import secretariat as sec
        return au_monde(sec.metiers_a_verifier)

    @r.post("/secretariat/metiers")
    def sec_confirmer(x: MetierConfirme, s: str = Depends(secretariat)) -> dict:
        from intelligence import secretariat as sec
        par = comptes().verifier(s)["etiquette"]
        return au_monde(lambda c: sec.confirmer_metier(c, x.valeur, x.metier, par=par))

    @r.get("/secretariat/pilote")
    def sec_pilote(s: str = Depends(secretariat)) -> dict:
        from intelligence import secretariat as sec
        return au_monde(lambda c: sec.tableau_pilote(c, criteres()))

    @r.post("/secretariat/pilote/geler")
    def sec_geler(s: str = Depends(secretariat)) -> dict:
        from intelligence import secretariat as sec
        par = comptes().verifier(s)["etiquette"]
        return au_monde(lambda c: sec.geler_criteres(c, criteres(), par=par))

    @r.get("/secretariat/campagnes")
    def sec_campagnes(s: str = Depends(secretariat)) -> dict:
        from intelligence import club_cherche, secretariat as sec
        return au_monde(lambda c: {"campagnes": sec.campagnes(c), "metiers_cherches": [
            {"metier": g["metier"], "libelle": g["libelle"], "demandes": g["nombre"], "age_max_jours": g["age_max_jours"]}
            for g in club_cherche.calculer(c)["metiers"]]})

    @r.post("/secretariat/campagnes")
    def sec_lancer(x: Campagne, request: Request, s: str = Depends(secretariat)) -> dict:
        from intelligence import secretariat as sec
        base = base_publique(request)
        return au_monde(lambda c: sec.lancer_campagne(c, x.metier, x.nombre, base=base))

    @r.get("/secretariat/ia")
    def sec_ia(s: str = Depends(secretariat)) -> dict:
        from intelligence import suivi_ia
        return au_monde(suivi_ia.taux) | {"allume": suivi_ia.allume()}

    @r.get("/secretariat/clubs", dependencies=[Depends(multiclub_allume)])
    def sec_clubs(s: str = Depends(secretariat)) -> dict:
        from intelligence import clubs
        return au_monde(clubs.vue_console)

    @r.post("/secretariat/clubs", dependencies=[Depends(multiclub_allume)])
    def sec_declarer_club(x: ClubExemple, s: str = Depends(secretariat)) -> dict:
        from intelligence import clubs
        return au_monde(lambda c: clubs.declarer(c, x.id, x.nom, region=x.region, pays=x.pays, fictif=x.fictif))

    # ------------------------------------------------------------------ ANNÉE 1 · LOT 9 : allumage Foire
    def foire_allumee() -> None:
        if os.environ.get("HACKVS_FOIRE_ALLUMAGE") != "1":
            raise HTTPException(404, "Not Found")

    def secret_bornes() -> bytes:
        import hashlib
        return hmac.new(etat["demo"].club.reglages.secret, b"bornes|annee-1", hashlib.sha256).digest()
    bornes: dict = {}

    def borne():
        from intelligence import foire_allumage as fa
        cle = secret_bornes()
        if bornes.get("cle") != cle:
            bornes["cle"], bornes["b"] = cle, fa.Borne(cle)
        return bornes["b"]

    @r.get("/secretariat/foire", dependencies=[Depends(foire_allumee)])
    def sec_foire(s: str = Depends(secretariat)) -> dict:
        from intelligence import foire_allumage as fa
        # l'entonnoir seul (audit des lots 9-10, I2) : la liste des intentions, avec métier et région par ligne, aurait
        # contourné le seuil « < 3 » de ce même entonnoir ; le secrétariat saisit la référence que l'invité montre
        return au_monde(fa.entonnoir)

    @r.post("/secretariat/foire/passes", dependencies=[Depends(foire_allumee)])
    def sec_foire_passes(x: LotPasses, request: Request, s: str = Depends(secretariat)) -> dict:
        from intelligence import foire_allumage as fa
        base = base_publique(request)
        lot = au_monde(lambda c: fa.emettre_lot(c, x.nombre, origine="stand"))
        return {"liens": [base + p["chemin"] for p in lot], "nombre": len(lot)}

    @r.post("/secretariat/foire/exposants", dependencies=[Depends(foire_allumee)])
    def sec_foire_exposants(x: ImportExposants, request: Request, s: str = Depends(secretariat)) -> dict:
        from intelligence import foire_allumage as fa
        base = base_publique(request)
        return au_monde(lambda c: fa.importer_exposants(c, x.csv, base=base))

    @r.post("/secretariat/foire/adhesions", dependencies=[Depends(foire_allumee)])
    def sec_foire_adhesion(x: Adhesion, s: str = Depends(secretariat)) -> dict:
        from intelligence import foire_allumage as fa
        par = comptes().verifier(s)["etiquette"]
        return au_monde(lambda c: fa.confirmer_adhesion(c, x.reference, par=par))

    @r.post("/secretariat/foire/bornes", dependencies=[Depends(foire_allumee)])
    def sec_foire_borne(request: Request, s: str = Depends(secretariat)) -> dict:
        from intelligence import foire_allumage as fa
        jeton = fa.jeton_borne(secret_bornes(), fa.nouveau_nom_borne())
        return {"jeton": jeton, "lien": base_publique(request) + f"/borne#b={jeton}",
                "note": "ouvrez ce lien UNE fois sur la borne : elle le garde ; ne le partagez pas"}

    @r.post("/borne/passe", dependencies=[Depends(foire_allumee)])
    def borne_passe(request: Request, x_pulse_borne: Optional[str] = Header(None)) -> dict:
        """PUBLIQUE pour la borne seulement : son jeton signé (émis par le secrétariat), un visiteur à la fois."""
        base = base_publique(request)
        b = borne()
        p = au_monde(lambda c: b.passe(c, x_pulse_borne or ""))
        url = base + p["chemin"]
        return {"url": url, "qr": qr_svg(url), "reference": p["reference"], "jusqu_au": p["jusqu_au"]}

    @r.get("/secretariat/acces")
    def sec_acces(s: str = Depends(secretariat)) -> list:
        return au_monde(lambda c: comptes().journal_acces(s))

    @r.get("/secretariat/comptes")
    def sec_comptes(s: str = Depends(secretariat)) -> list:
        return au_monde(lambda c: comptes().lister(s))

    @r.post("/secretariat/comptes/{compte}/revoquer")
    def sec_revoquer(compte: str, s: str = Depends(secretariat)) -> dict:
        au_monde(lambda c: comptes().revoquer(s, compte))
        return {"ok": True}

    @r.post("/secretariat/invitations")
    def sec_inviter(x: InvitationConsole, s: str = Depends(secretariat)) -> dict:
        return au_monde(lambda c: comptes().inviter(s, role=x.role, etiquette=x.etiquette, duree_s=x.duree_s))

    # ------------------------------------------------------------------ ANNÉE 1 · LOT 5 : notifications
    def notifications_allumees() -> None:
        if os.environ.get("HACKVS_NOTIFICATIONS") != "1":
            raise HTTPException(404, "Not Found")

    def notifications(request: Request):
        from intelligence import notifications as nt
        return nt.depuis_env(etat["demo"].club, base_publique(request))

    @r.get("/secretariat/notifications", dependencies=[Depends(notifications_allumees)])
    def sec_notifications(request: Request, s: str = Depends(secretariat)) -> dict:
        n = notifications(request)
        return au_monde(lambda c: n.suivi())

    @r.post("/secretariat/notifications/relance", dependencies=[Depends(notifications_allumees)])
    def sec_relance(request: Request, s: str = Depends(secretariat)) -> dict:
        from intelligence import notifications as nt
        n = notifications(request)
        envois = au_monde(lambda c: nt.preparer_relance(n))      # sous le verrou : lire le monde
        n.expedier(envois)                                       # HORS du verrou : le réseau (audit des lots 4-5, B1)
        au_monde(lambda c: n.tracer(envois))                     # sous le verrou : écrire le suivi
        return nt.bilan_relance(envois)

    @r.post("/notifications/desinscrire", dependencies=[Depends(notifications_allumees)])
    def desinscrire(x: Desinscription, request: Request) -> dict:
        """PUBLIQUE : le lien signé de chaque message (aucune session : on se désinscrit sans se connecter)."""
        n = notifications(request)
        if not n.signature_valide(x.jeton):                      # audit I4 : seuls les liens FAUX partagent un plafond
            limiter(limite_acces_global, "desinscription-invalide")
            raise HTTPException(401, "lien de désinscription invalide")
        limiter(limite_desinscription, f"desinscription|{x.jeton[-32:]}")
        return au_monde(lambda c: n.desinscrire(x.jeton))

    @r.get("/secretariat/bilan.{fmt}")
    def sec_bilan(fmt: str, s: str = Depends(secretariat)) -> Response:
        from intelligence import secretariat as sec
        types = {"md": "text/markdown; charset=utf-8", "csv": "text/csv; charset=utf-8", "pdf": "application/pdf"}
        if fmt not in types:
            raise HTTPException(404, "Not Found")
        texte = au_monde(lambda c: sec.bilan_trimestriel(c, "html" if fmt == "pdf" else fmt))
        corps = _imprimer_pdf(texte) if fmt == "pdf" else texte.encode("utf-8")
        return Response(corps, media_type=types[fmt], headers={
            "Content-Disposition": f'attachment; filename="bilan-trimestriel.{fmt}"', "Cache-Control": "no-store"})
    r.lien_salle, r.apercu_salle = ajouter_routes_salle(r, console,  # type: ignore[attr-defined]
                                                         lambda: etat["demo"].club.reglages.secret, limiter=limiter,
                                                         nouveau_limiteur=Limiteur, qr=qr_svg)

    @r.get("/console/personas", dependencies=[Depends(console)])
    def personas() -> list[dict]:
        d = etat["demo"]
        with d.club.verrou:
            return d.personas()

    return r
