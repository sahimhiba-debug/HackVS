"""Routes FOIRE 2026 (interrupteur HACKVS_FOIRE) : Suivi, clôture de reçu, visibilité, passe découverte, « le Club
cherche ». Un adaptateur mince, comme capacites_api : valider, authentifier, appeler le service, traduire l'erreur.
Interrupteur éteint : chaque route répond 404 « désactivé » — le produit d'hier, à l'identique."""
from __future__ import annotations

import json
import os

from typing import Callable, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .urls import base_publique
from intelligence import (annonces, assembler, associe, carte, club_cherche, distance, metiers, partenariats, piliers, recu_27560, suivi,
                          tableau_bord)


class Cloture(BaseModel):
    resultat: Literal["signé", "test sans suite", "contact établi", "abandonné"]
    note: Optional[str] = Field(default=None, max_length=partenariats.NOTE_MAX)


class Visibilite(BaseModel):
    visible: bool


class Emission(BaseModel):
    origine: Literal["stand", "demande", "startup"] = "stand"
    demande: Optional[str] = Field(default=None, max_length=120)


class Activation(BaseModel):
    jeton: str = Field(max_length=120)


class Declaration(BaseModel):
    entreprise: str = Field(min_length=2, max_length=80)
    metier: str = Field(max_length=40)
    zone: str = Field(max_length=40)


class Aide(BaseModel):
    aide: bool


class Distance(BaseModel):
    zone: str = Field(max_length=40)
    langue: Literal["fr", "de"]


class Carte(BaseModel):
    image: str = Field(max_length=1_000_000)              # data:image/…;base64,… — jamais conservée


class Profil(BaseModel):
    entreprise: str = Field(min_length=2, max_length=80)
    metier: str = Field(max_length=40)
    zone: str = Field(max_length=40)
    langue: Literal["fr", "de"]
    proposition: dict[str, str] = Field(default_factory=dict, max_length=4)


class Lien(BaseModel):
    jeton: str = Field(max_length=300)
    attributs: dict[str, int] = Field(default_factory=dict, max_length=4)


class Annonce(BaseModel):
    texte: str = Field(min_length=1, max_length=400)


class Pilier(BaseModel):
    actif: bool


class Associe(BaseModel):
    membre: str = Field(min_length=1, max_length=40)


def ajouter_routes(r: APIRouter, au_monde: Callable, membre: Callable, console: Callable, *, limiter: Callable,
                   nouveau_limiteur: Callable, qr: Callable[[str], str], hors_verrou: Optional[Callable] = None) -> None:
    # PASSE DÉCOUVERTE : jamais par adresse IP (une salle partage la même) — par CODE tenté, par SESSION d'invité, et un
    # plafond global doux ; l'émission (console) est plafonnée aussi
    limite_emission = nouveau_limiteur(30, 60.0)
    limite_activation_global = nouveau_limiteur(300, 60.0)
    limite_activation_code = nouveau_limiteur(5, 60.0)
    limite_invite = nouveau_limiteur(60, 60.0)
    limite_lien_global = nouveau_limiteur(300, 60.0)       # liens d'e-mail : par lien tenté, et un plafond global doux
    limite_lien = nouveau_limiteur(10, 60.0)
    limite_annonce = nouveau_limiteur(5, 60.0)            # annonces sous chiffre : 5 par minute et par membre

    def foire(f: Callable) -> Callable:
        def g(c):
            if not c.reglages.foire:
                raise HTTPException(404, "Fonction désactivée (HACKVS_FOIRE=0).")
            return f(c)
        return g

    # L'ÉTAT de l'interrupteur, toujours 200 : les écrans le lisent avant d'appeler une route de la Foire — éteint, aucun
    # 404 dans la console du navigateur (le produit d'hier, à l'identique, jusque dans ses journaux)
    @r.get("/console/foire", dependencies=[Depends(console)])
    def etat_foire_console() -> dict:
        return au_monde(lambda c: {"actif": c.reglages.foire})

    @r.get("/moi/foire")
    def etat_foire_membre(pid: str = Depends(membre)) -> dict:
        return au_monde(lambda c: {"actif": c.reglages.foire})

    @r.get("/console/suivi", dependencies=[Depends(console)])
    def lire_suivi(periode: str = "demo") -> dict:
        return au_monde(foire(lambda c: suivi.calculer(c, periode[:12])))

    @r.get("/console/recus", dependencies=[Depends(console)])
    def recus_console() -> list[dict]:
        """Les reçus du Club pour la clôture : référence, capacité, pièce, étape — JAMAIS le membre (sauf double accord,
        dans Suivi)."""
        return au_monde(foire(lambda c: [{"reference": x["reference"], "titre": x["titre"], "piece": x["piece"],
                                          "etape": x["etape"], "resultat": (x["cloture"] or {}).get("resultat"),
                                          "visible_club": partenariats.CLUB in x["visible"], "visible_membre": "membre" in x["visible"],
                                          "fictif": True}
                                         for x in partenariats.recus_du_club(c)]))

    @r.post("/console/recus/{reference}/cloture", dependencies=[Depends(console)])
    def cloturer(reference: str, x: Cloture) -> dict:
        return au_monde(foire(lambda c: partenariats.cloturer(c, reference[:40], x.resultat, x.note)))

    @r.post("/console/recus/{reference}/visible", dependencies=[Depends(console)])
    def visible_club(reference: str, x: Visibilite) -> dict:
        return au_monde(foire(lambda c: partenariats.rendre_visible(c, reference[:40], partenariats.CLUB, x.visible)))

    @r.post("/moi/recus/{reference}/visible")
    def visible_membre(reference: str, x: Visibilite, pid: str = Depends(membre)) -> dict:
        return au_monde(foire(lambda c: partenariats.rendre_visible(c, reference[:40], "membre", x.visible, membre=pid)))

    # ------------------------------------------------------------------ D · passe découverte
    def invite(x_pulse_invite: Optional[str] = Header(None)) -> str:
        """La session d'un INVITÉ (passe découverte activé) : vérifiée à chaque requête (signature, révocation, terme)."""
        limiter(limite_invite, "invite|" + (x_pulse_invite or "")[:60])
        au_monde(foire(lambda c: c.decouverte.invite(x_pulse_invite or "")))
        return x_pulse_invite or ""

    @r.post("/console/decouverte", dependencies=[Depends(console)])
    def emettre_decouverte(x: Emission, request: Request) -> dict:
        limiter(limite_emission, "decouverte-emission")
        res = au_monde(foire(lambda c: c.decouverte.emettre(x.origine, x.demande)))
        base = base_publique(request)
        res |= {"url": base + res["chemin"], "qr": qr(base + res["chemin"])}
        if x.origine == "demande":                    # « Inviter un contact » : le texte FR / DE, prêt à envoyer (par la personne)
            d = au_monde(lambda c: next((d | {"metier": g["metier"]} for g in club_cherche.calculer(c)["metiers"]
                                         for d in g["demandes"] if d["id"] == x.demande), None))
            if d is not None:
                res["invitation"] = club_cherche.invitation(d["piece"], d["metier"], res["url"], res["jours"])
        return res

    @r.get("/console/club-cherche", dependencies=[Depends(console)])
    def le_club_cherche() -> dict:
        return au_monde(foire(club_cherche.calculer))

    @r.get("/moi/recus/27560")
    def recus_27560(pid: str = Depends(membre)):
        """Mes reçus, alignés sur ISO/IEC TS 27560 (JSON-LD, DPV) — interrupteur HACKVS_RECU_27560 (allumé par défaut)."""
        if os.environ.get("HACKVS_RECU_27560", "1") != "1":
            raise HTTPException(404, "Export ISO/IEC TS 27560 désactivé (HACKVS_RECU_27560=0).")
        doc = au_monde(lambda c: recu_27560.export(c, pid))
        return Response(json.dumps(doc, ensure_ascii=False), media_type="application/ld+json")

    # ---- annonces sous chiffre (P3 n°9)
    @r.post("/moi/annonces")
    def publier_annonce(x: Annonce, pid: str = Depends(membre)) -> dict:
        limiter(limite_annonce, "annonce|" + pid)
        return au_monde(foire(lambda c: annonces.publier(c, pid, x.texte)))

    @r.get("/moi/annonces")
    def mes_annonces(pid: str = Depends(membre)) -> list[dict]:
        return au_monde(foire(lambda c: annonces.mes_annonces(c, pid)))

    @r.get("/annonces")
    def lire_annonces(pid: str = Depends(membre)) -> list[dict]:
        return au_monde(foire(lambda c: annonces.pour_membre(c, pid)))

    @r.post("/moi/annonces/{chiffre}/interet")
    def interet_annonce(chiffre: str, pid: str = Depends(membre)) -> dict:
        return au_monde(foire(lambda c: annonces.interet(c, pid, chiffre[:12])))

    @r.post("/moi/annonces/{chiffre}/accepter/{n}")
    def accepter_annonce(chiffre: str, n: int, pid: str = Depends(membre)) -> dict:
        return au_monde(foire(lambda c: annonces.accepter(c, pid, chiffre[:12], n)))

    @r.post("/moi/pilier")
    def declarer_pilier(x: Pilier, pid: str = Depends(membre)) -> dict:
        return au_monde(foire(lambda c: piliers.declarer(c, pid, x.actif)))

    @r.get("/moi/escalades")
    def mes_escalades(pid: str = Depends(membre)) -> list[dict]:
        return au_monde(foire(lambda c: piliers.escalades(c, pid)))

    @r.get("/console/piliers", dependencies=[Depends(console)])
    def lire_piliers() -> dict:
        return au_monde(foire(piliers.agregats))

    @r.get("/console/tableau", dependencies=[Depends(console)])
    def tableau() -> dict:
        return au_monde(foire(tableau_bord.calculer))

    @r.get("/console/annonces", dependencies=[Depends(console)])
    def agregats_annonces() -> dict:
        return au_monde(foire(annonces.agregats))

    @r.get("/console/associes", dependencies=[Depends(console)])
    def lire_associes() -> dict:
        return au_monde(foire(associe.agregats))

    @r.post("/console/associes", dependencies=[Depends(console)])
    def declarer_associe(x: Associe) -> dict:
        return au_monde(foire(lambda c: associe.declarer(c, x.membre)))

    @r.post("/console/associes/retirer", dependencies=[Depends(console)])
    def retirer_associe(x: Associe) -> dict:
        return au_monde(foire(lambda c: associe.retirer(c, x.membre)))

    @r.get("/moi/associe")
    def mon_statut_associe(pid: str = Depends(membre)) -> dict:
        return au_monde(foire(lambda c: associe.statut(c, pid)))

    @r.get("/console/club/assembler", dependencies=[Depends(console)])
    def club_assembler() -> dict:
        """Liste du Club : « Ce que votre Club pourrait assembler », « le Club cherche » d'après la liste, chiffres."""
        def f(c):
            liste = club_cherche.entreprises_par_metier()
            pm = liste["par_metier"] if liste else None
            k = c.reglages.k_anonymat
            return {"assembler": assembler.calculer(pm, k), "cherche": assembler.absents_et_rares(pm, k),
                    "chiffres": assembler.chiffres(liste)}
        return au_monde(foire(f))

    @r.get("/console/decouverte", dependencies=[Depends(console)])
    def passes_decouverte() -> list[dict]:
        return au_monde(foire(lambda c: c.decouverte.liste()))

    @r.post("/console/decouverte/{nonce}/revoquer", dependencies=[Depends(console)])
    def revoquer_decouverte(nonce: str) -> dict:
        return au_monde(foire(lambda c: c.decouverte.revoquer(nonce[:40])))

    @r.post("/decouverte/activer")
    def activer_decouverte(a: Activation) -> dict:
        limiter(limite_activation_global, "decouverte")
        limiter(limite_activation_code, "decouverte-code|" + a.jeton.split(".")[1][:40] if a.jeton.count(".") == 2 else "decouverte-code|?")
        return au_monde(foire(lambda c: c.decouverte.activer(a.jeton)))

    @r.get("/decouverte/moi")
    def moi_invite(session: str = Depends(invite)) -> dict:
        return au_monde(foire(lambda c: c.decouverte.demandes(session)))

    @r.post("/decouverte/declaration")
    def declarer(x: Declaration, session: str = Depends(invite)) -> dict:
        return au_monde(foire(lambda c: c.decouverte.declarer(session, x.entreprise, x.metier, x.zone)))

    @r.post("/decouverte/demandes/{ask_id}/reponse")
    def repondre_invite(ask_id: str, x: Aide, session: str = Depends(invite)) -> dict:
        return au_monde(foire(lambda c: c.decouverte.repondre(session, ask_id[:120], x.aide)))

    @r.post("/decouverte/rejoindre")
    def rejoindre(session: str = Depends(invite)) -> dict:
        return au_monde(foire(lambda c: c.decouverte.rejoindre(session)))

    @r.get("/decouverte/referentiel")
    def referentiel(session: str = Depends(invite)) -> dict:
        return {"metiers": [{"id": m["id"], "fr": m["fr"], "de": m["de"]} for m in metiers.metiers()], "zones": list(metiers.ZONES)}

    # ------------------------------------------------------------------ F · membre à distance, réponse depuis l'e-mail
    @r.get("/moi/distance")
    def ma_distance(pid: str = Depends(membre)) -> dict:
        return au_monde(foire(lambda c: {"profil": distance.profil(c, pid), "zones": list(metiers.ZONES), "langues": list(distance.LANGUES),
                                         "recus": [{"reference": x["reference"], "titre": x["titre"], "visible_par_le_club": "membre" in x["visible"]}
                                                   for x in partenariats.recus_du_club(c) if x["membre"] == pid and x["etape"] != "retire"]}))

    @r.post("/moi/distance")
    def declarer_distance(x: Distance, pid: str = Depends(membre)) -> dict:
        return au_monde(foire(lambda c: distance.declarer(c, pid, x.zone, x.langue)))

    @r.get("/console/boite", dependencies=[Depends(console)])
    def boite_de_sortie(request: Request) -> dict:
        base = base_publique(request)
        return au_monde(foire(lambda c: distance.boite(c, base)))

    def _limiter_lien(jeton: str) -> None:
        limiter(limite_lien_global, "courriel")
        limiter(limite_lien, "courriel|" + jeton[-32:])

    @r.post("/courriel/lire")
    def lire_courriel(x: Lien) -> dict:
        _limiter_lien(x.jeton)
        return au_monde(foire(lambda c: distance.lire_lien(c, x.jeton)))

    @r.post("/courriel/repondre")
    def repondre_courriel(x: Lien) -> dict:
        _limiter_lien(x.jeton)
        return au_monde(foire(lambda c: distance.repondre_lien(c, x.jeton, x.attributs or None)))

    # ------------------------------------------------------------------ « la carte devient le profil »
    @r.post("/moi/carte/proposer")
    def proposer_carte(x: Carte, pid: str = Depends(membre)) -> dict:
        """L'image est lue par Apertus (vision) puis OUBLIÉE ; rien n'est écrit avant la confirmation du membre."""
        limiter(limite_lien, "carte|" + pid)                    # 10 propositions par minute et par membre
        # HORS DU VERROU du monde : l'appel au modèle dure des secondes ; il ne lit que l'interrupteur IA (rien n'est écrit)
        return (hors_verrou or au_monde)(foire(lambda c: carte.proposer(c, x.image)))

    @r.get("/moi/carte/referentiel")
    def referentiel_carte(pid: str = Depends(membre)) -> dict:
        return au_monde(foire(lambda c: carte.referentiel()))

    @r.post("/moi/carte/confirmer")
    def confirmer_carte(x: Profil, pid: str = Depends(membre)) -> dict:
        return au_monde(foire(lambda c: carte.confirmer(c, pid, x.entreprise, x.metier, x.zone, x.langue, x.proposition)))
