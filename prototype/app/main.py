"""API du prototype « Le Fil du Club » (prototype exploratoire préparé avant Hack VS).

Modes (séparation explicite) :
- HACKVS_MODE=demo (défaut) : profils FICTIFS. L'identité du membre est choisie par l'en-tête
  X-Membre (ou ?membre=) : c'est la SIMULATION des autres humains (on incarne tour à tour
  Sophie, Julien…). Rien n'est envoyé à personne.
- HACKVS_MODE=reel : uniquement HACKVS_PROFILS (fichier autorisé). Sans fichier → 503.
  Aucune identité simulée : sans authentification (non implémentée) → 501.
Analyse du besoin : règles locales par défaut ; Claude si HACKVS_LLM=claude + clé API.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import date
import time
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import threading

from . import agenda, analyse, club, parser_llm, parser_rules, securite, semantique, soiree
from .baseline import rechercher_mots_cles
from .matching import expliquer, rechercher
from .models import Besoin, Profil
from .store import ErreurMetier, Interdit, Magasin
from .taxonomy import DATA_DIR, charger_taxonomie
from adaptateurs.club import cycle as cycle_club
from adaptateurs.club import reseau
from plateforme.memoire import Memoire

RACINE = Path(__file__).resolve().parent.parent
MODE = os.environ.get("HACKVS_MODE", "demo")
TAX = charger_taxonomie()


def _charger_profils() -> tuple[list[Profil], Optional[str]]:
    if MODE == "demo":
        chemin = DATA_DIR / "profils_demo.json"
    else:
        src = os.environ.get("HACKVS_PROFILS")
        if not src:
            return [], None
        chemin = Path(src)
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    return [Profil(**p) for p in brut["profils"]], brut.get("utilisateur_demo")


PROFILS, UTILISATEUR_DEFAUT = _charger_profils()
PAR_ID = {p.id: p for p in PROFILS}
MAGASIN = Magasin(os.environ.get("HACKVS_DB", str(RACINE / "var" / f"fil_{MODE}.db")))
# Mémoire du réseau : journal d'événements temporel. Le magasin y est PROJETÉ (source unique par fait, cf. adaptateurs/club/reseau.py).
CHEMIN_MEMOIRE = os.environ.get("HACKVS_CYCLE_DB", str(RACINE / "var" / f"reseau_{MODE}.db"))
MEMOIRE = Memoire(CHEMIN_MEMOIRE)


def projeter_reseau() -> None:
    reseau.projeter(MEMOIRE, MAGASIN.relations())


def aujourdhui_reseau() -> date:
    projeter_reseau()
    return MEMOIRE.maintenant(date.today())

app = FastAPI(title="Le Fil du Club (prototype exploratoire)", version="0.2.0")


# ---------------------------------------------------------------- identité et données effectives
def profils_effectifs() -> list[Profil]:
    """Profils de référence + modifications faites dans l'application (profil, consentement)."""
    consent, modifs = MAGASIN.consentements(), MAGASIN.profils_modifies()
    res = []
    for p in PROFILS:
        maj = dict(modifs.get(p.id, {}))
        if p.id in consent:
            maj["accepte_introductions"] = consent[p.id]
        res.append(Profil(**(p.model_dump() | maj)) if maj else p)
    return res


def profil(membre_id: str) -> Profil:
    for p in profils_effectifs():
        if p.id == membre_id:
            return p
    raise HTTPException(404, "Membre inconnu.")


def moi(x_membre: Optional[str], membre_q: Optional[str] = None) -> Profil:
    if not PROFILS:
        raise HTTPException(503, "Mode réel non configuré : aucune source de profils autorisée n'est branchée.")
    if MODE != "demo":
        raise HTTPException(501, "Mode réel : authentification des membres non implémentée. Aucune identité simulée n'est acceptée.")
    mid = x_membre or membre_q or UTILISATEUR_DEFAUT
    p = profil(mid)
    if p.type == "visiteur":
        raise HTTPException(403, "Les visiteurs n'ont pas accès à l'espace du Club.")
    return p


def _pub(p: Profil) -> dict:
    return p.model_dump(include={"id", "nom", "fonction", "entreprise", "commune", "type"})


def _erreurs(fn):
    try:
        return fn()
    except KeyError:
        raise HTTPException(404, "Élément introuvable.") from None
    except Interdit as e:
        raise HTTPException(403, str(e)) from e
    except ErreurMetier as e:
        raise HTTPException(409, str(e)) from e


# ---------------------------------------------------------------- schémas d'entrée
class EntreeAnalyse(BaseModel):
    texte: str
    analyseur: Literal["auto", "regles", "claude"] = "auto"


class EntreeRecherche(BaseModel):
    besoin: Besoin


class EntreeBesoin(BaseModel):
    besoin: Besoin
    publier: bool = False
    anonyme: bool = False


class EntreeModif(BaseModel):
    besoin: Besoin
    anonyme: Optional[bool] = None


class EntreeActionBesoin(BaseModel):
    resolu_par: Optional[str] = None
    note: str = ""


class EntreeRelation(BaseModel):
    besoin_id: str
    cible_id: Optional[str] = None  # requis pour une demande (auteur → aidant), ignoré pour une offre
    message: str


class EntreeTransition(BaseModel):
    date_rencontre: Optional[str] = None
    resultat: Optional[str] = None


class EntreeConsentement(BaseModel):
    accepte: bool


# ---------------------------------------------------------------- état et membres
@app.get("/api/etat")
def etat():
    return {
        "mode": MODE,
        "donnees_fictives": MODE == "demo",
        "analyseur_claude_disponible": parser_llm.llm_configure(),
        "fournisseur_llm": parser_llm.fournisseur(),
        "semantique_locale": semantique.disponible(),
        "nb_profils": len(PROFILS),
        "utilisateur_defaut": UTILISATEUR_DEFAUT,
        "concepts": [{"valeur": c.id, "libelle": c.libelle} for c in sorted(TAX.concepts.values(), key=lambda c: c.libelle)],
        "zones": list(TAX.zones),
        "langues": [{"valeur": k, "libelle": v["libelle"]} for k, v in TAX.langues.items()],
        "seq": MAGASIN.dernier_seq(),
    }


@app.get("/api/membres")
def membres():
    """Personnages incarnables en démo (jamais en mode réel)."""
    if MODE != "demo":
        raise HTTPException(501, "Pas de changement d'identité en mode réel.")
    return [_pub(p) | {"accepte_introductions": p.accepte_introductions}
            for p in profils_effectifs() if p.type != "visiteur"]


@app.get("/api/moi")
def api_moi(x_membre: Optional[str] = Header(None)):
    p = moi(x_membre)
    return p.model_dump() | {"zone_implantation": TAX.zone_de_commune(p.commune)}


@app.post("/api/moi/consentement")
def api_consentement(e: EntreeConsentement, x_membre: Optional[str] = Header(None)):
    p = moi(x_membre)
    annulees = MAGASIN.changer_consentement(p.id, e.accepte)
    return {"accepte_introductions": e.accepte, "relations_annulees": annulees}


class EntreeTexte(BaseModel):
    texte: str


class OffreSaisie(BaseModel):
    concept: Optional[str] = None
    texte: str


class EntreeProfil(BaseModel):
    offre: list[OffreSaisie]
    recherche: list[OffreSaisie] = []
    zones_service: list[str] = []
    langues: list[str] = []
    presentation: Optional[str] = None
    creneaux: Optional[list[str]] = None


@app.post("/api/profil/analyser")
def analyser_profil(e: EntreeTexte):
    """Profil en 30 secondes : description libre → proposition (rien n'est enregistré)."""
    texte = e.texte.strip()
    if not texte:
        raise HTTPException(422, "Décrivez votre entreprise en quelques phrases.")
    if len(texte) > 3000:
        raise HTTPException(422, "Texte trop long (3 000 caractères maximum).")
    return parser_rules.extraire_profil(texte, TAX) | {"analyseur": "regles"}


@app.put("/api/moi/profil")
def modifier_profil(e: EntreeProfil, x_membre: Optional[str] = Header(None)):
    """Enregistre le profil VALIDÉ par le membre. Vocabulaire fermé vérifié côté serveur."""
    m = moi(x_membre)
    for o in e.offre + e.recherche:
        if o.concept is not None and o.concept not in TAX.concepts:
            raise HTTPException(422, f"Compétence inconnue : {o.concept}")
        if not o.texte.strip() or len(o.texte) > 300:
            raise HTTPException(422, "Chaque offre doit avoir un texte (300 caractères maximum).")
    if any(z not in TAX.zones for z in e.zones_service) or any(l not in TAX.langues for l in e.langues):
        raise HTTPException(422, "Zone ou langue inconnue.")
    if not e.offre:
        raise HTTPException(422, "Gardez au moins une offre : c'est ce qui permet aux autres membres de vous trouver.")
    champs = {"offre": [o.model_dump() for o in e.offre], "recherche": [o.model_dump() for o in e.recherche],
              "zones_service": list(dict.fromkeys(e.zones_service)), "langues": list(dict.fromkeys(e.langues))}
    if e.presentation is not None:
        champs["presentation"] = e.presentation.strip()[:600]
    if e.creneaux is not None:
        if any(c not in agenda.CRENEAUX for c in e.creneaux):
            raise HTTPException(422, "Créneau inconnu (attendu : lun-matin … ven-apres-midi).")
        champs["creneaux"] = agenda.valides(e.creneaux)
    MAGASIN.modifier_profil(m.id, champs)
    nouveau = profil(m.id)
    return nouveau.model_dump() | {"alertes_contenu": securite.signaux_profil(nouveau)}


# ---------------------------------------------------------------- analyse du besoin
def _analyse_regles(texte: str) -> tuple[Besoin, dict]:
    """Règles + IA sémantique locale (si le modèle est présent) : aucune donnée ne quitte la machine."""
    t0 = time.perf_counter()
    b, info = analyse.analyser_hybride(texte, TAX)
    return b, {"analyseur": b.analyseur, "semantique": info, "latence_ms": round((time.perf_counter() - t0) * 1000, 2)}


def _prechauffer() -> None:
    try:
        semantique.prototypes()
        semantique.inferer_concept("préchauffage", TAX)
    except Exception:  # le produit fonctionne sans la couche sémantique
        pass


if semantique.disponible():
    threading.Thread(target=_prechauffer, daemon=True).start()


def _verifier_texte(texte: str) -> str:
    texte = texte.strip()
    if not texte:
        raise HTTPException(422, "Décrivez votre besoin en une ou deux phrases.")
    if len(texte) > 1500:
        raise HTTPException(422, "Texte trop long (1 500 caractères maximum).")
    return texte


def _veut_claude(analyseur: str) -> bool:
    if analyseur == "claude" and not parser_llm.llm_configure():
        raise HTTPException(409, "Analyse par Claude non configurée (HACKVS_LLM=claude et clé API requises).")
    return analyseur == "claude" or (analyseur == "auto" and parser_llm.llm_configure())


@app.post("/api/analyser")
def analyser(e: EntreeAnalyse):
    texte = _verifier_texte(e.texte)
    besoin, tele = parser_llm.analyser(texte, TAX) if _veut_claude(e.analyseur) else _analyse_regles(texte)
    return {"besoin": besoin, "telemetrie": tele}


@app.get("/api/analyser/flux")
def analyser_flux(texte: str = Query(...), analyseur: str = "auto"):
    """Server-Sent Events : critères provisoires (Claude uniquement) puis résultat final validé."""
    texte = _verifier_texte(texte)

    def evenements():
        if _veut_claude(analyseur):
            for ev in parser_llm.analyser_flux(texte, TAX):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        else:
            b, tele = _analyse_regles(texte)
            yield f"data: {json.dumps({'type': 'final', 'besoin': b.model_dump(), 'telemetrie': tele}, ensure_ascii=False)}\n\n"
    return StreamingResponse(evenements(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def besoin_valide(b: Besoin) -> Besoin:
    """Le client peut modifier les critères : le serveur n'accepte que le vocabulaire fermé
    et recalcule les libellés (on ne fait jamais confiance au libellé envoyé)."""
    propres = []
    for c in b.criteres:
        if c.type == "expertise" and c.valeur in TAX.concepts:
            propres.append(c.model_copy(update={"libelle": TAX.libelle(c.valeur)}))
        elif c.type in ("zone", "implantation") and c.valeur in TAX.zones:
            propres.append(c.model_copy(update={"libelle": c.valeur}))
        elif c.type == "langue" and c.valeur in TAX.langues:
            propres.append(c.model_copy(update={"libelle": TAX.langues[c.valeur]["libelle"]}))
        elif c.type == "texte_libre" and 0 < len(c.valeur.strip()) <= 200:
            propres.append(c.model_copy(update={"libelle": "Compétence hors catalogue"}))
        else:
            raise HTTPException(422, f"Critère non reconnu : {c.type} « {c.valeur[:40]} ».")
    excl = [e.model_copy(update={"libelle": TAX.libelle(e.valeur)}) for e in b.exclusions if e.valeur in TAX.concepts]
    if len(excl) != len(b.exclusions):
        raise HTTPException(422, "Exclusion non reconnue.")
    return b.model_copy(update={"criteres": propres, "exclusions": excl})


# ---------------------------------------------------------------- recherche (aperçu avant enregistrement)
@app.post("/api/rechercher")
def api_rechercher(e: EntreeRecherche, x_membre: Optional[str] = Header(None)):
    return rechercher(besoin_valide(e.besoin), moi(x_membre), profils_effectifs(), TAX, mode=MODE)


class EntreeExplication(BaseModel):
    besoin: Besoin
    membre_id: str


@app.post("/api/expliquer")
def api_expliquer(e: EntreeExplication, x_membre: Optional[str] = Header(None)):
    """« Pourquoi cette personne ? » / « Pourquoi pas elle ? » : critère par critère, verdict identique à la recherche."""
    m = moi(x_membre)
    cible = next((p for p in profils_effectifs() if p.id == e.membre_id), None)
    if cible is None:
        raise HTTPException(404, "Membre inconnu.")
    return expliquer(besoin_valide(e.besoin), m, cible, TAX, mode=MODE)


@app.post("/api/comparer")
def comparer(e: EntreeRecherche, x_membre: Optional[str] = Header(None)):
    m, b = moi(x_membre), besoin_valide(e.besoin)
    return {"moteur": rechercher(b, m, profils_effectifs(), TAX, mode=MODE),
            "reference": rechercher_mots_cles(b, m, profils_effectifs(), TAX)}


# ---------------------------------------------------------------- besoins
def _vue_besoin(b, pour: Profil) -> dict:
    """Vue d'un besoin pour un membre donné : l'anonymat de l'auteur est levé seulement
    pour lui-même ou après une mise en relation acceptée."""
    d = b.model_dump()
    auteur = PAR_ID.get(b.auteur_id)
    partage = pour.id == b.auteur_id or any(
        r.besoin_id == b.id and pour.id in (r.auteur_id, r.aidant_id) and r.coordonnees_partagees
        for r in MAGASIN.relations(pour.id))
    if b.anonyme and not partage:
        secteur = TAX.libelle(auteur.secteurs[0]) if auteur and auteur.secteurs else "secteur non précisé"
        d["auteur"] = {"id": None, "nom": "Un membre du Club", "entreprise": f"Secteur : {secteur}",
                       "commune": TAX.zone_de_commune(auteur.commune) if auteur else "", "fonction": "", "anonyme": True}
        d["auteur_id"] = None
    else:
        d["auteur"] = _pub(auteur) if auteur else None
    return d


@app.post("/api/besoins")
def creer_besoin(e: EntreeBesoin, x_membre: Optional[str] = Header(None)):
    m = moi(x_membre)
    b = besoin_valide(e.besoin)
    return _erreurs(lambda: _vue_besoin(MAGASIN.creer_besoin(m.id, b, e.publier, e.anonyme), m))


@app.get("/api/besoins")
def mes_besoins(x_membre: Optional[str] = Header(None)):
    m = moi(x_membre)
    return [_vue_besoin(b, m) for b in MAGASIN.besoins() if b.auteur_id == m.id]


@app.put("/api/besoins/{besoin_id}")
def modifier_besoin(besoin_id: str, e: EntreeModif, x_membre: Optional[str] = Header(None)):
    m = moi(x_membre)
    b = besoin_valide(e.besoin)
    return _erreurs(lambda: _vue_besoin(MAGASIN.modifier_besoin(besoin_id, m.id, b, e.anonyme), m))


@app.post("/api/besoins/{besoin_id}/{action}")
def action_besoin(besoin_id: str, action: Literal["publier", "depublier", "cloturer"], e: EntreeActionBesoin,
                  x_membre: Optional[str] = Header(None)):
    m = moi(x_membre)
    return _erreurs(lambda: _vue_besoin(MAGASIN.action_besoin(besoin_id, m.id, action, e.resolu_par, e.note), m))


@app.get("/api/besoins/{besoin_id}/correspondances")
def correspondances(besoin_id: str, x_membre: Optional[str] = Header(None)):
    """Pour l'auteur : membres pertinents + état de la mise en relation éventuelle avec chacun."""
    m = moi(x_membre)
    b = _erreurs(lambda: MAGASIN.besoin(besoin_id))
    if b.auteur_id != m.id:
        raise HTTPException(403, "Seul·e l'auteur·e voit les correspondances de son besoin.")
    res = rechercher(b.besoin, m, profils_effectifs(), TAX, mode=MODE)
    res.besoin_id, res.besoin_version = b.id, b.version
    rels = {r.aidant_id: r for r in MAGASIN.relations(m.id) if r.besoin_id == b.id and r.etat != "retiree"}
    d = res.model_dump()
    t = aujourdhui_reseau()
    g = reseau.graphe_de_confiance(MEMOIRE, t)
    par_id = {p.id: p for p in profils_effectifs()}
    publie = next((date.fromisoformat(e.horodatage[:10]) for e in b.historique if e.action.startswith("creer")), None)
    for s in d["suggestions"]:
        r = rels.get(s["profil"]["id"])
        s["relation"] = r.model_dump() if r else None
        s["dimensions"] = reseau.dimensions(MEMOIRE, m, s, par_id, t, publie, g)
    return d


# ---------------------------------------------------------------- Bourse (sens inverse)
@app.get("/api/bourse")
def bourse(x_membre: Optional[str] = Header(None)):
    """Besoins publiés par d'autres membres auxquels JE peux répondre, avec la raison.

    Même moteur, mêmes filtres que la recherche de l'auteur : si je vois un besoin ici,
    l'auteur me voit dans ses correspondances, et inversement.
    """
    m = moi(x_membre)
    eff = profils_effectifs()
    eff_moi = next(p for p in eff if p.id == m.id)
    sortie = []
    for b in MAGASIN.besoins():
        if b.auteur_id == m.id or b.statut not in ("publie", "en_cours"):
            continue
        auteur = next((p for p in eff if p.id == b.auteur_id), None)
        if auteur is None:
            continue
        res = rechercher(b.besoin, auteur, [auteur, eff_moi], TAX, mode=MODE)
        ma = next((s for s in res.suggestions if s.profil.id == m.id), None)
        # Une relation terminée (annulée, déclinée, retirée) ne maintient pas un besoin dans la Bourse.
        rel = next((r for r in MAGASIN.relations(m.id) if r.besoin_id == b.id and r.aidant_id == m.id
                    and r.etat not in ("retiree", "annulee", "declinee")), None)
        if ma is None and rel is None:
            continue
        sortie.append({"besoin": _vue_besoin(b, m), "correspondance": ma.model_dump() if ma else None,
                       "relation": rel.model_dump() if rel else None})
    return sortie


# ---------------------------------------------------------------- mises en relation
@app.get("/api/relations/brouillon")
def brouillon(besoin_id: str, cible_id: Optional[str] = None, x_membre: Optional[str] = Header(None)):
    """Message pré-rédigé de façon déterministe à partir des preuves vérifiées (aucune invention)."""
    m = moi(x_membre)
    b = _erreurs(lambda: MAGASIN.besoin(besoin_id))
    auteur = profil(b.auteur_id)
    if m.id == b.auteur_id and not cible_id:
        raise HTTPException(422, "Indiquez le membre à solliciter.")
    aidant = profil(cible_id) if m.id == b.auteur_id else m
    res = rechercher(b.besoin, auteur, [auteur, aidant], TAX, mode=MODE)
    preuve = next((p.extrait for s in res.suggestions for p in s.preuves if p.champ in ("offre", "presentation")), None)
    resume = _resume_besoin(b.besoin)
    if m.id == b.auteur_id:
        txt = (f"Bonjour {aidant.nom.split(' ')[0]},\n\nJe suis {m.nom}, {m.fonction.lower()} de {m.entreprise} à {m.commune}. "
               f"{resume}\n\n" + (f"Votre profil du Club mentionne « {preuve} », c'est pourquoi je me permets de vous solliciter. " if preuve else "")
               + f"Seriez-vous d'accord pour un échange de 20 minutes ?\n\nBelle journée,\n{m.nom}")
    else:
        txt = (f"Bonjour,\n\nJ'ai vu votre besoin dans la Bourse du Club ({_quoi(b.besoin)}).\n\n"
               + (f"Chez {m.entreprise}, nous proposons « {preuve} ». " if preuve else "")
               + f"Je serais ravi·e d'en parler lors d'un court échange.\n\n{m.nom}, {m.fonction} · {m.entreprise}")
    return {"message": txt}


def _quoi(b: Besoin) -> str:
    princ = next((c for c in b.criteres if c.type in ("expertise", "texte_libre")), None)
    if not princ:
        return "besoin"
    quoi = princ.libelle.lower() if princ.type == "expertise" else f"« {princ.valeur} »"
    zones = [c.libelle for c in b.criteres if c.type == "zone"]
    return quoi + (f", {', '.join(zones)}" if zones else "")


def _resume_besoin(b: Besoin) -> str:
    """Reformule à partir des critères validés (le texte brut peut contenir « pas un concurrent »…)."""
    princ = next((c for c in b.criteres if c.type in ("expertise", "texte_libre")), None)
    if not princ:
        return ""
    quoi = princ.libelle.lower() if princ.type == "expertise" else f"« {princ.valeur} »"
    zones = [c.libelle for c in b.criteres if c.type == "zone"]
    autres = [c.libelle.lower() for c in b.criteres if c.type == "expertise" and c is not princ]
    phrase = f"Je recherche un partenaire pour : {quoi}" + (f" ({', '.join(zones)})" if zones else "")
    if autres:
        phrase += f", et si possible : {', '.join(autres)}"
    return phrase + "."


@app.post("/api/relations")
def creer_relation(e: EntreeRelation, x_membre: Optional[str] = Header(None)):
    """Crée une demande (auteur → aidant) ou une offre (aidant → auteur).

    Le moteur revérifie la correspondance CÔTÉ SERVEUR : on ne peut solliciter que quelqu'un
    que le moteur propose (demande) ou répondre qu'à un besoin qui nous correspond (offre).
    """
    m = moi(x_membre)
    b = _erreurs(lambda: MAGASIN.besoin(e.besoin_id))
    auteur = profil(b.auteur_id)
    # Demande : l'auteur choisit la cible. Offre : la cible est TOUJOURS l'auteur (déterminé ici,
    # l'aidant ne connaît pas forcément son identité si le besoin est anonyme).
    cible = profil(e.cible_id) if m.id == b.auteur_id else auteur
    aidant = cible if m.id == b.auteur_id else m
    res = rechercher(b.besoin, auteur, [auteur, aidant], TAX, mode=MODE)
    if cible.type != "visiteur" and cible.accepte_introductions and not any(s.profil.id == aidant.id for s in res.suggestions):
        raise HTTPException(409, "Ce membre ne correspond pas (ou plus) aux critères de ce besoin.")
    return _erreurs(lambda: MAGASIN.creer_relation(b.id, m.id, cible.id, e.message,
                                                   # publier un besoin = accepter les offres pour CE besoin
                                                   autre_accepte=cible.accepte_introductions or cible.id == b.auteur_id,
                                                   autre_eligible=cible.type != "visiteur"))


def _vue_relation(r, pour: Profil) -> dict:
    d = r.model_dump()
    b = MAGASIN.besoin(r.besoin_id)
    d["besoin"] = _vue_besoin(b, pour)
    d["besoin_modifie_depuis"] = b.version != r.besoin_version
    autre_id = r.aidant_id if pour.id == r.auteur_id else r.auteur_id
    autre = PAR_ID.get(autre_id)
    masque = b.anonyme and pour.id == r.aidant_id and not r.coordonnees_partagees
    d["autre"] = ({"nom": "Un membre du Club", "entreprise": d["besoin"]["auteur"]["entreprise"], "anonyme": True}
                  if masque else (_pub(autre) if autre else None))
    d["mon_role"] = "auteur" if pour.id == r.auteur_id else "aidant"
    d["je_suis_destinataire"] = pour.id == r.destinataire_id()
    if masque:
        d["auteur_id"] = None
    return d


@app.get("/api/relations")
def mes_relations(x_membre: Optional[str] = Header(None)):
    m = moi(x_membre)
    return [_vue_relation(r, m) for r in MAGASIN.relations(m.id)]


@app.get("/api/relations/{relation_id}/creneaux")
def creneaux_communs(relation_id: str, x_membre: Optional[str] = Header(None)):
    """Prochaines demi-journées communes aux DEUX personnes, visibles d'elles seules et après acceptation."""
    m = moi(x_membre)
    r = _erreurs(lambda: MAGASIN.relation(relation_id))
    if m.id not in (r.auteur_id, r.aidant_id):
        raise HTTPException(403, "Seules les deux personnes de la mise en relation voient leurs créneaux communs.")
    if r.etat not in ("acceptee", "rencontre_planifiee"):
        raise HTTPException(409, "Les créneaux communs ne sont calculés qu'après acceptation.")
    a, b = profil(r.auteur_id), profil(r.aidant_id)
    props = agenda.communs(a.creneaux, b.creneaux, date.today())
    return {"creneaux": props, "message": "" if props else
            "Aucun créneau commun déclaré dans les deux prochaines semaines : proposez une date dans votre message."}


@app.post("/api/relations/{relation_id}/{action}")
def transition(relation_id: str, action: str, e: EntreeTransition, x_membre: Optional[str] = Header(None)):
    m = moi(x_membre)
    r = _erreurs(lambda: MAGASIN.transition(relation_id, action, m.id, e.date_rencontre, e.resultat))
    return _vue_relation(r, m)


# ---------------------------------------------------------------- journal et flux temps réel
def _journal_autorise() -> None:
    # Le journal contient l'identité des acteurs (y compris l'auteur d'un besoin anonyme) :
    # c'est un instrument de DÉMONSTRATION (vue scène). En mode réel, il faudrait un flux filtré par membre authentifié.
    if MODE != "demo":
        raise HTTPException(501, "Journal réservé au mode démo : flux filtré par membre non implémenté.")


@app.get("/api/journal")
def journal(depuis: int = 0):
    _journal_autorise()
    return MAGASIN.journal(depuis)


@app.get("/api/flux")
async def flux(request: Request, depuis: int = 0):
    """SSE : pousse chaque nouvel événement du journal (utilisé par la vue « scène » et le rafraîchissement)."""
    _journal_autorise()

    async def generateur():
        seq = depuis
        yield "retry: 1500\n\n"
        while not await request.is_disconnected():
            for ev in MAGASIN.journal(seq):
                seq = ev["seq"]
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.4)
    return StreamingResponse(generateur(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


# ---------------------------------------------------------------- vue du Club (animation)
@app.get("/api/club/tableau")
def tableau_club():
    if MODE != "demo":
        raise HTTPException(501, "Vue du Club : rôle d'animateur·rice authentifié non implémenté.")
    return club.tableau(MAGASIN, profils_effectifs(), TAX) | {"donnees_fictives": True}


@app.get("/api/soiree/plan")
def plan_soiree(donnees: Literal["club", "synthetique"] = "club", tours: int = Query(3, ge=1, le=5)):
    """Plan de rencontres optimisé (MILP) pour une soirée du Club. Démo : tous les membres sont supposés présents."""
    return _plan(donnees, tours)


def _plan(donnees: str, tours: int) -> dict:
    if MODE != "demo":
        raise HTTPException(501, "Liste des inscrits à une soirée non disponible en mode réel.")
    if donnees == "synthetique":
        brut = json.loads((DATA_DIR / "profils_synthetiques.json").read_text(encoding="utf-8"))
        participants, besoins = [Profil(**p) for p in brut["profils"]], []
        deja = frozenset()
    else:
        participants, besoins = profils_effectifs(), MAGASIN.besoins()
        deja = frozenset(frozenset((r.auteur_id, r.aidant_id)) for r in MAGASIN.relations()
                         if r.etat in ("acceptee", "rencontre_planifiee", "rencontre_faite", "cloturee"))
    return soiree.planifier(participants, besoins, TAX, tours=tours, deja_en_relation=deja) | {"donnees": donnees, "donnees_fictives": True}


@app.get("/api/soiree/programme.ics")
def programme_soiree(membre: str, donnees: Literal["club", "synthetique"] = "club", tours: int = Query(3, ge=1, le=5)):
    """Programme individuel (iCalendar). Date de soirée FICTIVE (HACKVS_SOIREE_DEBUT), démo uniquement."""
    plan = _plan(donnees, tours)
    if not any(membre in (m["a"]["id"], m["b"]["id"]) for m in plan["rencontres"]):
        raise HTTPException(404, "Aucune rencontre ciblée pour ce membre dans ce plan.")
    ics = soiree.programme_ics(plan, membre, os.environ.get("HACKVS_SOIREE_DEBUT", "2026-10-03T18:30"))
    return Response(ics, media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="soiree-{membre}.ics"'})


@app.post("/api/demo/historique")
def charger_historique():
    if MODE != "demo":
        raise HTTPException(403, "Historique fictif réservé au mode démo.")
    MAGASIN.reinitialiser()
    MEMOIRE.vider()  # la mémoire est dérivée du magasin (+ scénarios) : pas de faits orphelins
    n = club.charger_historique(MAGASIN, profils_effectifs(), TAX)
    return {"besoins_charges": n}


@app.post("/api/demo/reinitialiser")
def reinitialiser():
    if MODE != "demo":
        raise HTTPException(403, "Réinitialisation réservée au mode démo.")
    MAGASIN.reinitialiser()
    MEMOIRE.vider()
    return {"ok": True}


# ---------------------------------------------------------------- pages
WEB = RACINE / "web"
app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(WEB / "favicon.svg", media_type="image/svg+xml")


CAPTURES = RACINE.parent / "docs" / "captures"
if CAPTURES.exists():
    app.mount("/captures", StaticFiles(directory=CAPTURES), name="captures")


def _url_publique(request: Request) -> str:
    return os.environ.get("HACKVS_URL_PUBLIQUE") or str(request.base_url).rstrip("/")


@app.get("/api/qr.svg")
def qr(request: Request, chemin: str = "/"):
    """QR code généré localement (aucun service externe) vers l'URL publique de l'application."""
    import io

    import qrcode
    import qrcode.image.svg
    if not chemin.startswith("/"):
        raise HTTPException(422, "Chemin relatif attendu.")
    img = qrcode.make(_url_publique(request) + chemin, image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=2)
    tampon = io.BytesIO()
    img.save(tampon)
    return Response(tampon.getvalue(), media_type="image/svg+xml")


@app.get("/rejoindre", response_class=HTMLResponse)
def rejoindre(request: Request):
    url = _url_publique(request)
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Essayer · Le Fil du Club</title><link rel="icon" href="/favicon.ico" type="image/svg+xml"><link rel="stylesheet" href="/static/app.css">
<style>.qr{{display:grid;place-items:center;gap:16px;text-align:center;padding:32px 16px}}
.qr img{{width:min(70vw,420px);background:#fff;padding:12px;border:2px solid var(--encre);border-radius:6px}}</style>
</head><body><main class="qr"><p class="surtitre">Le Fil du Club · démonstration</p><h1>Essayez-le<br>sur votre téléphone</h1>
<img src="/api/qr.svg?chemin=/" alt="QR code vers {url}"><p class="sous">{url}</p>
<p>Vous incarnez un membre <strong>fictif</strong> (choix en haut de l'écran). Aucune donnée réelle, aucun message envoyé.</p></main></body></html>"""


@app.get("/presentation")
def presentation():
    return FileResponse(WEB / "presentation.html")


if MODE == "demo":  # expérience isolée « intentions scellées » (docs/STRATEGIC_RESEARCH.md) : jamais en mode réel
    from experiences.scelle_api import creer_routeur as _routeur_scelle
    app.include_router(_routeur_scelle(profils_effectifs, TAX))


if MODE == "demo":  # espace de décision (plateforme + adaptateur Club) : instantanés de profils, jamais exposés en mode réel
    from .decisions_api import creer_routeur as _routeur_decisions
    app.include_router(_routeur_decisions(profils_effectifs, MAGASIN, TAX,
                                          os.environ.get("HACKVS_DECISIONS_DB", str(RACINE / "var" / "decisions_demo.db"))))


if MODE == "demo":  # cycle de vie des relations : horloge simulée, membres fictifs
    from .cycle_api import creer_routeur as _routeur_cycle
    app.include_router(_routeur_cycle(profils_effectifs, TAX, MEMOIRE, ":memory:" if CHEMIN_MEMOIRE == ":memory:" else CHEMIN_MEMOIRE + ".runs",
                                      avant_lecture=projeter_reseau))


@app.get("/api/reseau/boite")
def boite_reseau(x_membre: Optional[str] = Header(None)):
    """Boîte réseau : les prochains mouvements utiles du membre (pas un fil d'actualité)."""
    m = moi(x_membre)
    t = aujourdhui_reseau()
    rel = cycle_club.relances(MEMOIRE, profils_effectifs(), TAX, t)
    return reseau.boite(MEMOIRE, m, profils_effectifs(), MAGASIN.relations(m.id), rel, t)


@app.get("/api/reseau/relation/{autre_id}")
def memoire_relation(autre_id: str, x_membre: Optional[str] = Header(None)):
    """Où nous sommes-nous rencontrés ? Que s'est-il passé ensuite ? — uniquement pour une relation dont je fais partie."""
    m = moi(x_membre)
    if autre_id not in PAR_ID:
        raise HTTPException(404, "Membre inconnu.")
    return reseau.memoire_relation(MEMOIRE, m.id, autre_id, aujourdhui_reseau())


@app.get("/cycle")
def page_cycle():
    if MODE != "demo":
        raise HTTPException(501, "Cycle des relations réservé au mode démo.")
    return FileResponse(WEB / "cycle.html")


@app.get("/api/modeles")
def registre_modeles():
    """Passerelle de modèles : capacités ANNONCÉES vs état CONSTATÉ (configuré, vérifié). Aucune valeur de clé."""
    from plateforme import modeles
    return modeles.registre()


@app.get("/decision")
def page_decision():
    if MODE != "demo":
        raise HTTPException(501, "Espace de décision réservé au mode démo.")
    return FileResponse(WEB / "decision.html")


@app.get("/scelle")
def page_scelle():
    if MODE != "demo":
        raise HTTPException(501, "Expérience réservée au mode démo.")
    return FileResponse(WEB / "scelle.html")


@app.get("/soiree")
def page_soiree():
    return FileResponse(WEB / "soiree.html")


@app.get("/club")
def page_club():
    return FileResponse(WEB / "club.html")


@app.get("/scene")
def scene():
    return FileResponse(WEB / "scene.html")
