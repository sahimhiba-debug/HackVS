"""API Club Pulse (mode démo) : une plateforme, deux expériences — l'application du MEMBRE et la TOUR DE CONTRÔLE du Club.

- Membre : session signée issue d'un code d'invitation (QR) ; chaque réponse est rendue POUR ce membre par la politique
  de visibilité (aucun identifiant d'une autre personne n'y figure).
- Console : rôle « animatrice ». En démonstration elle n'exige pas de connexion (monde fictif, mode démo seulement) ;
  en production elle exigerait un compte du personnel du Club (non construit ici).
- Démonstration : réinitialiser / étape suivante / rejouer jusqu'à n — appels réels, résultats non écrits d'avance.
Toutes les écritures passent par un verrou : deux clics simultanés ne produisent jamais deux gestes.
"""
from __future__ import annotations

import threading
from typing import Callable, Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from intelligence import monde_demo as md
from intelligence.activation import ErreurActivation
from intelligence.club_pulse import ErreurPulse
from intelligence.demo import Demo
from intelligence.politique import Spectateur

from .taxonomy import Taxonomie

PERSONAS = [md.SOPHIE, md.ANNA, md.LEA, md.MARKUS, md.PAULINE]


class Acces(BaseModel):
    code: str = Field(min_length=4, max_length=12)


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
    visibilite: Optional[dict[str, str]] = None


class Note(BaseModel):
    texte: str = Field(min_length=3, max_length=2000)
    evenement: Optional[str] = Field(default=None, max_length=120)


class Demande(BaseModel):
    texte: str = Field(min_length=3, max_length=600)


class Activer(BaseModel):
    anonyme: bool = False
    langue: Optional[Literal["fr", "de", "en", "it"]] = None


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


def creer_routeur(tax: Taxonomie) -> APIRouter:
    r = APIRouter(prefix="/api/pulse", tags=["club pulse"])
    etat = {"demo": Demo(tax)}
    remplacement = threading.Lock()          # réinitialiser / rejouer / avancer : une seule opération à la fois

    def club():
        return etat["demo"].club

    def verrouille(f: Callable):
        with club().verrou:
            try:
                return f()
            except (ErreurPulse, ErreurActivation) as e:
                raise HTTPException(409 if isinstance(e, ErreurActivation) else 422, str(e)) from None

    def membre(jeton: Optional[str]) -> str:
        try:
            return club().verifier_session(jeton or "")
        except ErreurPulse:
            raise HTTPException(401, "Session invalide : scannez à nouveau votre code d'invitation.") from None

    # ------------------------------------------------------------------ démonstration
    @r.get("/etat")
    def lire_etat():
        d = etat["demo"]
        return {"etape": d.etape, "total": len(d.ETAPES), "traces": d.traces, "date": d.club.jour.isoformat(),
                "monde": d.club.r.nom, "ia": d.club.ia.etat(), "fictif": True}

    @r.post("/demo/reinitialiser")
    def reinitialiser():
        with remplacement:
            etat["demo"] = Demo(tax)
            return lire_etat()

    @r.post("/demo/suivant")
    def suivant():
        with remplacement:                   # double clic : la seconde requête attend, puis avance d'UNE étape
            d = etat["demo"]
            with d.club.verrou:
                if d.etape >= len(d.ETAPES):
                    raise HTTPException(409, "Démonstration terminée : réinitialisez ou rejouez.")
                t = d.suivant()
            return lire_etat() | {"derniere": t}

    @r.post("/demo/aller/{n}")
    def aller(n: int):
        if not 0 <= n <= len(Demo.ETAPES):
            raise HTTPException(422, "Étape hors limites.")
        with remplacement:
            d = Demo(tax)
            d.rejouer(n)
            etat["demo"] = d
            return lire_etat()

    # ------------------------------------------------------------------ accès
    @r.post("/acces")
    def acces(a: Acces):
        return verrouille(lambda: club().activer_compte(a.code))

    # ------------------------------------------------------------------ application du membre
    @r.get("/moi/pouls")
    def pouls(x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().pouls_membre(pid))

    @r.get("/moi/profil")
    def profil(x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().vue_profil(pid))

    @r.post("/moi/profil/proposer")
    def proposer(p: Proposer, x_pulse_session: Optional[str] = Header(None)):
        membre(x_pulse_session)
        return verrouille(lambda: club().proposer(p.texte, p.sens))

    @r.post("/moi/accueil")
    def accueil(a: Accueil, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().onboarding(pid, [i.model_dump() for i in a.aide], [i.model_dump() for i in a.cherche], a.visible))

    @r.patch("/moi/profil")
    def modifier(m: ModifProfil, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().modifier_profil(pid, retirer_capacite=m.retirer_capacite, ajouter_recherche=m.ajouter_recherche,
                                                         disponible=m.disponible, accepte=m.sollicitable, visibilite=m.visibilite))

    @r.get("/moi/notes")
    def notes(x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().notes_de(pid))

    @r.post("/moi/notes")
    def noter(n: Note, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().capturer(pid, n.texte, n.evenement))

    @r.post("/moi/notes/{note_id}/partager/{index}")
    def partager(note_id: str, index: int, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().partager(pid, note_id, index))

    @r.post("/moi/demandes")
    def demander(d: Demande, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().demander(pid, d.texte))

    @r.get("/moi/opportunites/{oid}")
    def opportunite(oid: str, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().vue_opportunite(club().opportunite(oid), Spectateur("membre", pid)))

    @r.get("/moi/opportunites/{oid}/pourquoi")
    def pourquoi(oid: str, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)

        def f():
            club().vue_opportunite(club().opportunite(oid), Spectateur("membre", pid))    # contrôle d'accès
            return club().expliquer(oid, Spectateur("membre", pid))
        return verrouille(f)

    @r.post("/moi/opportunites/{oid}/activer")
    def activer(oid: str, a: Activer, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: {"activation": club().activer(oid, Spectateur("membre", pid), anonyme=a.anonyme)})

    @r.get("/moi/sollicitations")
    def sollicitations(x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().demandes_pour(pid))

    @r.post("/moi/sollicitations/{aid}")
    def repondre(aid: str, rep: Reponse, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: (club().repondre(aid, pid, rep.accepte), {"ok": True})[1])

    @r.get("/moi/activations")
    def activations(x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().activations_de(pid))

    @r.get("/moi/activations/{aid}")
    def activation(aid: str, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().vue_activation(aid, Spectateur("membre", pid)))

    @r.post("/moi/activations/{aid}/contribuer")
    def contribuer(aid: str, c: Contribution, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: (club().contribuer(aid, pid, c.nature, c.titre, c.contenu, c.reutilisable, c.attribution), {"ok": True})[1])

    @r.post("/moi/activations/{aid}/confirmer")
    def confirmer(aid: str, c: Confirmation, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().confirmer(aid, pid, c.verdict, c.etape_suivante, c.pourquoi))

    @r.post("/moi/activations/{aid}/retirer")
    def retirer(aid: str, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: (club().moteur.retirer_consentement(aid, club().jour, pid), {"ok": True})[1])

    @r.post("/moi/activations/{aid}/reutiliser")
    def reutiliser(aid: str, x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)

        def f():
            if club().moteur.opportunite(aid).beneficiaire != pid:
                raise ErreurPulse("seul le bénéficiaire reçoit la ressource vérifiée")
            club().reutiliser(aid)
            return {"ok": True}
        return verrouille(f)

    @r.get("/moi/evenements")
    def evenements(x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)

        def f():
            c = club()
            scan = c.scanner()
            res = []
            for ev in sorted(c.r.evenements, key=lambda e: e.le):
                if (ev.le - c.jour).days < 0:
                    continue
                inscrit = pid in ev.participants
                a_preparer = [c.vue_opportunite(o, Spectateur("membre", pid)) for o in scan["opportunites"]
                              if o.evenement == ev.id and o.beneficiaire == pid] if inscrit else []
                res.append({"id": ev.id, "nom": ev.nom, "le": ev.le.isoformat(), "dans_jours": (ev.le - c.jour).days,
                            "inscrit": inscrit, "participants": len(ev.participants),
                            "avant": a_preparer, "pendant": "Notez vos rencontres : la note reste privée.",
                            "apres": "Les suites utiles apparaîtront dans votre pouls."})
            return res
        return verrouille(f)

    @r.get("/memoire")
    def memoire(x_pulse_session: Optional[str] = Header(None)):
        pid = membre(x_pulse_session)
        return verrouille(lambda: club().memoire_club(Spectateur("membre", pid)))

    @r.get("/memoire/{motif_id}/fiche", response_class=PlainTextResponse)
    def fiche(motif_id: str):
        texte = verrouille(lambda: club().fiche(motif_id))
        return PlainTextResponse(texte, headers={"Content-Disposition": f'attachment; filename="fiche-{motif_id}.txt"'})

    # ------------------------------------------------------------------ tour de contrôle du Club
    anim = Spectateur("animatrice")

    @r.get("/console")
    def console():
        return verrouille(lambda: club().tour())

    @r.post("/console/scan")
    def scan():
        def f():
            club().scanner(force=True)
            return club().tour()
        return verrouille(f)

    @r.get("/console/opportunites/{oid}")
    def c_opportunite(oid: str):
        return verrouille(lambda: club().vue_opportunite(club().opportunite(oid), anim) | {"explication": club().expliquer(oid, anim)})

    @r.post("/console/opportunites/{oid}/activer")
    def c_activer(oid: str, a: Activer):
        return verrouille(lambda: {"activation": club().activer(oid, anim, anonyme=a.anonyme, langue=a.langue)})

    @r.post("/console/opportunites/{oid}/ecarter")
    def c_ecarter(oid: str):
        def f():
            club().opportunite(oid)
            club().ecartees.add(oid)
            club()._scan = None
            return {"ok": True}
        return verrouille(f)

    @r.get("/console/activations/{aid}")
    def c_activation(aid: str):
        return verrouille(lambda: club().vue_activation(aid, anim))

    @r.post("/console/activations/{aid}/{action}")
    def c_action(aid: str, action: Literal["lancer", "pause", "reprendre", "annuler"]):
        def f():
            c, m = club(), club().moteur
            {"lancer": lambda: m.lancer(aid, c.jour), "pause": lambda: m.mettre_en_pause(aid, c.jour),
             "reprendre": lambda: m.reprendre(aid, c.jour), "annuler": lambda: m.annuler(aid, c.jour)}[action]()
            return c.vue_activation(aid, anim)
        return verrouille(f)

    @r.post("/console/activations/{aid}/contraintes")
    def c_contraintes(aid: str, k: Contraintes):
        def f():
            club().moteur.changer_contraintes(aid, club().jour, langue=k.langue, anonyme=k.anonyme)
            return club().vue_activation(aid, anim)
        return verrouille(f)

    @r.post("/console/temps")
    def c_temps(t: Temps):
        return verrouille(lambda: {"echeances": club().avancer(t.jours), "date": club().jour.isoformat()})

    @r.get("/console/personas")
    def personas():
        """DÉMO SEULEMENT : incarner un membre fictif (le jury joue un rôle). En production : chacun son téléphone."""
        def f():
            c = club()
            return [{"id": p, "nom": c.coffre.identite(p).nom, "code": c.coffre.code_invitation(p),  # type: ignore[union-attr]
                     "session": c.session(p) if p in c.coffre.actives else None,
                     "capacite": next((tax.libelle(o.concept) for o in c.profil(p).offre if o.concept), None)} for p in PERSONAS]
        return verrouille(f)

    return r
