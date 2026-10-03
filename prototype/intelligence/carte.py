"""« LA CARTE DEVIENT LE PROFIL » (Foire 2026, moment de scène) — photo de SA PROPRE carte de visite → Apertus 1.5
(vision) PROPOSE entreprise, métier, région, langue → le membre CONFIRME ou CORRIGE → reçu de consentement.

- L'IMAGE N'EST JAMAIS CONSERVÉE : elle vit le temps de l'appel, en mémoire ; elle n'est ni journalisée, ni écrite sur
  disque, ni tracée (les traces d'appel IA ne portent que des métadonnées).
- La proposition est VALIDÉE PAR LE CODE : métier de la taxonomie, région de la liste des zones, langue fr / de, nom
  d'entreprise borné — sinon le champ reste vide. L'IA propose, le membre décide (rien n'est écrit avant sa confirmation).
- PARITÉ : IA éteinte, aucun modèle, réponse invalide ou délai → FORMULAIRE MANUEL, même écran, même reçu.
- SÉPARATION : le nom d'entreprise va dans le magasin d'IDENTITÉ (hors du journal) ; le journal ne reçoit que métier,
  zone, langue et la provenance (proposé par l'IA et confirmé, ou déclaré)."""
from __future__ import annotations

import base64
import json
import re
from typing import TYPE_CHECKING, Optional

from plateforme.affirmations import Statut

from . import distance, metiers
from .erreurs import Invalide

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

TYPES = {"image/png", "image/jpeg", "image/webp"}
OCTETS_MAX = 900_000
FINALITE = ("Profil du Club : mon entreprise, mon métier, ma région et ma langue servent à m'adresser des demandes du Club. "
            "La photo de ma carte n'est pas conservée. Révocable à tout moment.")
SYSTEME = ("Tu reçois le TEXTE d'une carte de visite. Réponds UNIQUEMENT par un objet JSON {\"entreprise\", \"metier\", \"region\", \"langue\"}. "
           "entreprise : le nom de l'ENTREPRISE (pas celui de la personne), ou null. metier : un id de cette liste, ou null : METIERS. "
           "region : une valeur de cette liste, ou null : ZONES. langue : \"fr\" ou \"de\" (langue principale de la carte), "
           "ou null. N'invente rien : null si la carte ne le dit pas.")
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["entreprise", "metier", "region", "langue"],
          "properties": {k: {"type": ["string", "null"]} for k in ("entreprise", "metier", "region", "langue")}}


def _image(donnees: str) -> tuple[str, bytes]:
    m = re.fullmatch(r"data:(image/[a-z]+);base64,([A-Za-z0-9+/=]+)", donnees or "")
    if not m or m.group(1) not in TYPES:
        raise Invalide("image attendue : PNG, JPEG ou WebP")
    brut = base64.b64decode(m.group(2), validate=True)
    if len(brut) > OCTETS_MAX:
        raise Invalide("image trop lourde : elle est réduite sur le téléphone avant l'envoi")
    return m.group(1), brut


def valider(brut: Optional[str]) -> dict:
    """Chaque champ est gardé seulement s'il passe le code ; sinon vide (le membre le remplit)."""
    try:
        m = re.search(r"\{.*\}", brut or "", re.S)
        d = json.loads(m.group(0) if m else "")
    except (ValueError, TypeError):
        return {}
    if not isinstance(d, dict):
        return {}
    ent = d.get("entreprise")
    sortie = {"entreprise": " ".join(ent.split())[:80] if isinstance(ent, str) and 2 <= len(ent.strip()) <= 80 else None,
              "metier": d.get("metier") if d.get("metier") in metiers.ids() else None,
              "zone": d.get("region") if d.get("region") in metiers.ZONES else None,
              "langue": d.get("langue") if d.get("langue") in distance.LANGUES else None}
    return {k: v for k, v in sortie.items() if v}


def proposer(c: "ClubPulse", donnees_image: str) -> dict:
    """Une PROPOSITION (rien n'est écrit). Sans IA utilisable : formulaire manuel, dit."""
    mime, brut = _image(donnees_image)
    vide = {"proposition": {}, "source": "formulaire", "referentiel": referentiel()}
    f = getattr(c.ia, "f", None)
    if f is None or not c.ia.actif or getattr(f, "nom", "") != "apertus":
        return vide | {"note": "IA éteinte ou indisponible : remplissez le formulaire."}
    # DEUX TEMPS (mesuré le 03.10 : en un seul appel, le modèle lit mal ; en recopiant d'abord, il lit juste) :
    # 1. vision : recopier le texte de la carte ; 2. texte : extraire les quatre champs sous schéma. Ni l'image ni la
    # transcription ne sont conservées.
    contenu = [{"type": "text", "text": "Recopie exactement tout le texte de cette image, ligne par ligne. Rien d'autre."},
               {"type": "image_url", "image_url": {"url": f"data:{mime};base64," + base64.b64encode(brut).decode()}}]
    try:
        texte = f.completer("Tu recopies le texte d'une image.", contenu, None)[:1500]
        systeme = SYSTEME.replace("METIERS", ", ".join(sorted(metiers.ids()))).replace("ZONES", ", ".join(metiers.ZONES))
        sortie = f.completer(systeme, "Texte de la carte :\n" + texte, SCHEMA)
    except Exception:                                               # panne, délai : la parité, pas une erreur
        return vide | {"note": "Le modèle n'a pas répondu : remplissez le formulaire."}
    finally:
        del brut, contenu                                           # l'image ne survit pas à l'appel
    p = valider(sortie)
    return {"proposition": p, "source": "ia" if p else "formulaire", "modele": getattr(f, "modele", "?"), "referentiel": referentiel(),
            "note": "Proposé par le modèle, vérifié par le code : confirmez ou corrigez." if p else
                    "Le modèle n'a rien proposé de valide : remplissez le formulaire."}


def referentiel() -> dict:
    return {"metiers": [{"id": m["id"], "fr": m["fr"], "de": m["de"]} for m in metiers.metiers()], "zones": list(metiers.ZONES),
            "langues": list(distance.LANGUES)}


def confirmer(c: "ClubPulse", pid: str, entreprise: str, metier: str, zone: str, langue: str, proposition: Optional[dict] = None) -> dict:
    entreprise = " ".join((entreprise or "").split())
    if not 2 <= len(entreprise) <= 80:
        raise Invalide("entreprise : 2 à 80 caractères")
    if metier not in metiers.ids():
        raise Invalide("métier hors taxonomie")
    choisi = {"entreprise": entreprise, "metier": metier, "zone": zone, "langue": langue}
    prop = proposition or {}
    ia = bool(prop) and all(prop.get(k) == v for k, v in choisi.items() if k in prop)
    with c.journal.transaction():
        distance.declarer(c, pid, zone, langue)                     # valide zone et langue
        c.banc._ecrire("CARTE_PROFIL", [pid], Statut.DECLARE, membre=pid, metier=metier,
                       provenance="AI_PROPOSED_CONFIRMED" if ia else "SELF_DECLARED")
    c.identites_profil[pid] = {"entreprise": entreprise}            # identité : HORS du journal
    return {"recu": {"reference": f"profil-{pid[:3]}-{len(c.journal.evenements('CARTE_PROFIL'))}", "finalite": FINALITE,
                     "donne_le": c.jour.isoformat(), "revocable": True,
                     "provenance": "proposé par l'IA, confirmé par vous" if ia else "déclaré par vous"},
            "profil": choisi | {"metier_libelle": metiers.libelle(metier)}}
