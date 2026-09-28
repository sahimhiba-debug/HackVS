"""API du prototype « Le Fil du Club » (prototype exploratoire préparé avant Hack VS).

Modes :
- HACKVS_MODE=demo (défaut) : profils FICTIFS, réponses des personnes sollicitées simulées.
- HACKVS_MODE=reel : n'utilise que HACKVS_PROFILS (fichier autorisé). Sans fichier → 503.
  Pas de simulation de réponse en mode réel.
Analyse du besoin : règles locales par défaut ; Claude si HACKVS_LLM=claude + clé API.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import parser_llm, parser_rules
from .baseline import rechercher_mots_cles
from .intros import ErreurTransition, Registre
from .matching import rechercher
from .models import Besoin, Profil
from .taxonomy import DATA_DIR, charger_taxonomie

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
    with open(chemin, encoding="utf-8") as f:
        brut = json.load(f)
    return [Profil(**p) for p in brut["profils"]], brut.get("utilisateur_demo")


PROFILS, UTILISATEUR_ID = _charger_profils()
PAR_ID = {p.id: p for p in PROFILS}
REGISTRE = Registre(os.environ.get("HACKVS_DB", str(RACINE / "var" / f"intros_{MODE}.db")))

app = FastAPI(title="Le Fil du Club — prototype exploratoire", version="0.1.0")


def _demandeur() -> Profil:
    if not PROFILS or UTILISATEUR_ID not in PAR_ID:
        raise HTTPException(503, "Mode réel non configuré : aucune source de profils autorisée n'est branchée.")
    return PAR_ID[UTILISATEUR_ID]


class EntreeAnalyse(BaseModel):
    texte: str
    analyseur: Literal["auto", "regles", "claude"] = "auto"


class EntreeRecherche(BaseModel):
    besoin: Besoin


class EntreeIntro(BaseModel):
    cible_id: str
    besoin: Besoin
    message: str


class EntreeTransition(BaseModel):
    acteur: Literal["demandeur", "cible"]
    date_rencontre: Optional[str] = None
    resultat: Optional[str] = None


@app.get("/api/etat")
def etat():
    moi = PAR_ID.get(UTILISATEUR_ID) if UTILISATEUR_ID else None
    return {
        "mode": MODE,
        "donnees_fictives": MODE == "demo",
        "analyseur_claude_disponible": parser_llm.llm_configure(),
        "nb_profils": len(PROFILS),
        "utilisateur": moi.model_dump(include={"id", "nom", "fonction", "entreprise", "commune"}) if moi else None,
        "concepts": [{"valeur": c.id, "libelle": c.libelle} for c in sorted(TAX.concepts.values(), key=lambda c: c.libelle)],
        "zones": list(TAX.zones),
        "langues": [{"valeur": k, "libelle": v["libelle"]} for k, v in TAX.langues.items()],
    }


@app.post("/api/analyser")
def analyser(e: EntreeAnalyse):
    texte = e.texte.strip()
    if not texte:
        raise HTTPException(422, "Décrivez votre besoin en une ou deux phrases.")
    if len(texte) > 1500:
        raise HTTPException(422, "Texte trop long (1 500 caractères maximum).")
    veut_claude = e.analyseur == "claude" or (e.analyseur == "auto" and parser_llm.llm_configure())
    if veut_claude:
        if not parser_llm.llm_configure():
            raise HTTPException(409, "Analyse par Claude non configurée (HACKVS_LLM=claude et clé API requises).")
        besoin, tele = parser_llm.analyser(texte, TAX)
    else:
        import time
        t0 = time.perf_counter()
        besoin = parser_rules.analyser(texte, TAX)
        tele = {"analyseur": "regles", "latence_ms": round((time.perf_counter() - t0) * 1000, 2)}
    return {"besoin": besoin, "telemetrie": tele}


@app.post("/api/rechercher")
def api_rechercher(e: EntreeRecherche):
    return rechercher(e.besoin, _demandeur(), PROFILS, TAX, mode=MODE)


@app.post("/api/comparer")
def comparer(e: EntreeRecherche):
    moi = _demandeur()
    return {
        "moteur": rechercher(e.besoin, moi, PROFILS, TAX, mode=MODE),
        "reference": rechercher_mots_cles(e.besoin, moi, PROFILS, TAX),
    }


def _resume_besoin(b: Besoin) -> str:
    """Reformule le besoin à partir des critères validés (le texte brut peut contenir
    des éléments à ne pas transmettre tels quels, ex. « pas un concurrent »)."""
    exp = [c.libelle.lower() for c in b.criteres if c.type == "expertise"]
    zones = [c.libelle for c in b.criteres if c.type == "zone"]
    if not exp:
        return ""
    phrase = f"Je recherche un partenaire pour : {exp[0]}"
    if zones:
        phrase += f" ({', '.join(zones)})"
    if len(exp) > 1:
        phrase += f", et si possible : {', '.join(exp[1:])}"
    return phrase + "."


@app.post("/api/introductions/brouillon")
def brouillon(e: EntreeRecherche, cible_id: str):
    """Brouillon déterministe à partir des preuves vérifiées (aucune invention)."""
    moi, cible = _demandeur(), PAR_ID.get(cible_id)
    if not cible:
        raise HTTPException(404, "Profil inconnu.")
    res = rechercher(e.besoin, moi, [p for p in PROFILS if p.id in {moi.id, cible_id}], TAX, mode=MODE)
    raisons = [f"« {p.extrait} »" for s in res.suggestions for p in s.preuves if p.champ in {"offre", "presentation"}]
    prenom = cible.nom.split(" ")[0]
    message = (
        f"Bonjour {prenom},\n\n"
        f"Je suis {moi.nom}, {moi.fonction.lower()} de {moi.entreprise} à {moi.commune}. "
        f"{_resume_besoin(e.besoin)}\n\n"
        + (f"Votre profil du Club mentionne {raisons[0]}, c'est pourquoi je me permets de vous solliciter. " if raisons else "")
        + "Seriez-vous d'accord pour un échange de 20 minutes ?\n\n"
        f"Belle journée,\n{moi.nom}"
    )
    return {"message": message}


@app.post("/api/introductions")
def creer_intro(e: EntreeIntro):
    moi, cible = _demandeur(), PAR_ID.get(e.cible_id)
    if not cible:
        raise HTTPException(404, "Profil inconnu.")
    try:
        intro = REGISTRE.creer(
            moi.id, cible.id, e.besoin.texte, [c.model_dump() for c in e.besoin.criteres], e.message,
            cible_accepte=cible.accepte_introductions, cible_eligible=cible.type != "visiteur",
        )
    except ErreurTransition as err:
        raise HTTPException(409, str(err))
    return _enrichir(intro)


def _enrichir(intro):
    d = intro.model_dump()
    c = PAR_ID.get(intro.cible_id)
    d["cible"] = c.model_dump(include={"id", "nom", "fonction", "entreprise", "commune"}) if c else None
    d["simulation"] = MODE == "demo"
    return d


@app.get("/api/introductions")
def lister_intros():
    return [_enrichir(i) for i in REGISTRE.lister(_demandeur().id)]


@app.post("/api/introductions/{intro_id}/{action}")
def transition(intro_id: str, action: str, e: EntreeTransition):
    if e.acteur == "cible" and MODE != "demo":
        raise HTTPException(403, "En mode réel, seule la personne sollicitée peut répondre (authentification requise).")
    try:
        return _enrichir(REGISTRE.transition(intro_id, action, e.acteur, e.date_rencontre, e.resultat))
    except KeyError:
        raise HTTPException(404, "Introduction inconnue.")
    except ErreurTransition as err:
        raise HTTPException(409, str(err))


@app.post("/api/demo/reinitialiser")
def reinitialiser():
    if MODE != "demo":
        raise HTTPException(403, "Réinitialisation réservée au mode démo.")
    REGISTRE.reinitialiser()
    return {"ok": True}


WEB = RACINE / "web"
app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
