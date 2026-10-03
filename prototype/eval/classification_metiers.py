"""CLASSIFICATION DES DEMANDES DANS LA TAXONOMIE DES MÉTIERS (Foire 2026 · H) — le harnais commun à
`scripts/ingest_tally.py` et `scripts/eval_classification.py`.

- LANGUE RÉELLE de chaque phrase, détectée sur le texte (mots-outils), jamais déduite de la page choisie : une réponse
  anglaise passée par la page française est « en ».
- CLASSIFICATION CONTRAINTE : le modèle répond par un objet JSON {metier, abstention} ; le CODE valide — métier de la
  taxonomie (`data/taxonomie_metiers.yaml`) ou abstention explicite ; toute autre sortie est REJETÉE (comptée, jamais
  corrigée). S'abstenir est une bonne réponse pour une phrase qui n'est pas une demande pour le Club.
- CONSENTEMENT (formulaire Tally : « votre phrase sert seulement à tester une IA suisse ») : les phrases de source
  `foire-2026-qr` ne partent QUE vers Apertus (ou le fournisseur factice, sans réseau) — jamais vers un modèle frontière
  du banc. Imposé ici, par le code, et testé.
- AUCUNE EXACTITUDE revendiquée sans étiquettes humaines : le rapport donne des AGRÉGATS (nombre de phrases, langues,
  distribution par métier, taux d'abstention, sorties rejetées) et une FEUILLE D'ANNOTATION pour l'équipe (colonnes
  `metier_attendu` et `domaine` = club | hors_club à remplir à la main)."""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from typing import Optional

from intelligence import metiers

SOURCE_FOIRE = "foire-2026-qr"
PERMIS_FOIRE = frozenset({"apertus", "factice"})

MOTS = {
    "fr": {"le", "la", "les", "de", "des", "du", "un", "une", "et", "pour", "avec", "nous", "je", "vous", "est", "pas", "qui",
           "que", "sur", "dans", "il", "on", "au", "aux", "chercher", "cherche", "besoin", "notre", "mon", "ma", "quelqu'un"},
    "de": {"der", "die", "das", "und", "ich", "wir", "für", "mit", "ein", "eine", "einen", "ist", "nicht", "zu", "auf", "im",
           "suche", "suchen", "brauchen", "brauche", "unser", "unsere", "jemand", "den", "dem", "von", "bei", "oder"},
    "en": {"the", "and", "for", "with", "we", "i", "a", "an", "is", "not", "to", "on", "in", "looking", "need", "our", "my",
           "someone", "of", "or", "who", "can", "help", "you"},
    "it": {"il", "lo", "la", "gli", "di", "che", "per", "con", "un", "una", "e", "cerco", "cerchiamo", "abbiamo", "nostro",
           "nostra", "qualcuno", "bisogno", "della", "del"},
}


def detecter_langue(texte: str) -> str:
    """fr | de | en | it | inconnue — par les mots-outils, sur le texte seul (jamais la page choisie)."""
    mots = re.findall(r"[a-zàâäçéèêëîïôöùûüß']+", texte.lower())
    if not mots:
        return "inconnue"
    scores = {lg: sum(m in liste for m in mots) for lg, liste in MOTS.items()}
    if any(c in texte.lower() for c in "äöüß"):
        scores["de"] += 2
    if any(c in texte.lower() for c in "éèêàç"):
        scores["fr"] += 1
    meilleur = max(scores, key=lambda lg: scores[lg])
    second = sorted(scores.values())[-2]
    return meilleur if scores[meilleur] >= 1 and scores[meilleur] > second else "inconnue"


COURRIEL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
TELEPHONE = re.compile(r"(?:\+|00)\d[\d\s./-]{7,}\d|\b0\d{2}[\s./-]?\d{3}[\s./-]?\d{2}[\s./-]?\d{2}\b")


def contient_contact(texte: str) -> bool:
    return bool(COURRIEL.search(texte) or TELEPHONE.search(texte))


def normaliser(texte: str) -> str:
    t = unicodedata.normalize("NFKC", texte).strip().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", t)).strip()


def verifier_fournisseur(source: str, fournisseur: str) -> None:
    if source == SOURCE_FOIRE and fournisseur not in PERMIS_FOIRE:
        raise PermissionError(f"consentement : les phrases « {SOURCE_FOIRE} » ne passent que par Apertus — pas par « {fournisseur} »")


SCHEMA = {"type": "object", "additionalProperties": False, "required": ["metier", "abstention"],
          "properties": {"metier": {"type": ["string", "null"]}, "abstention": {"type": "boolean"}}}


def systeme() -> str:
    liste = "\n".join(f"- {m['id']} : {m['fr']} / {m['de']}" for m in metiers.metiers())
    return ("Tu classes UNE phrase écrite par une personne à la Foire du Valais : quel MÉTIER pourrait répondre à ce dont "
            "elle parle ? Réponds par un objet JSON {\"metier\": <id ou null>, \"abstention\": <bool>}. Choisis un id de "
            "la liste, ou abstention=true et metier=null si la phrase n'est pas une demande qu'un club d'entrepreneurs "
            "peut relayer, ou si elle est trop vague. N'invente jamais d'id.\nMétiers :\n" + liste)


def valider(brut: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    """(sortie validée, motif de rejet). Validée : {"metier": id, "abstention": False} ou {"metier": None, "abstention": True}."""
    if brut is None:
        return None, "pas de réponse"
    try:
        m = re.search(r"\{.*\}", brut, re.S)
        d = json.loads(m.group(0) if m else brut)
    except (ValueError, TypeError):
        return None, "JSON illisible"
    if not isinstance(d, dict) or set(d) - {"metier", "abstention"} or not isinstance(d.get("abstention"), bool):
        return None, "hors schéma"
    if d["abstention"]:
        return ({"metier": None, "abstention": True}, None) if d.get("metier") in (None, "") else (None, "abstention avec métier")
    if d.get("metier") not in metiers.ids():
        return None, "métier hors taxonomie"
    return {"metier": d["metier"], "abstention": False}, None


def classer(fournisseur, nom: str, source: str, texte: str) -> dict:
    verifier_fournisseur(source, nom)
    try:
        brut: Optional[str] = fournisseur.completer(systeme(), texte, SCHEMA)
        erreur = None
    except Exception as e:                                          # une panne est comptée, jamais maquillée
        brut, erreur = None, type(e).__name__
    sortie, rejet = valider(brut)
    return {"sortie": sortie, "rejet": rejet or (f"panne ({erreur})" if erreur else None)}


def rapport(phrases: list[dict], resultats: list[dict], source: str, fournisseur: str, modele: str, quand: str) -> str:
    """AGRÉGATS SEULEMENT : aucune phrase individuelle (règle Tally n° 4)."""
    n = len(phrases)
    langues = Counter(p["langue"] for p in phrases)
    acceptees = [r["sortie"] for r in resultats if r["sortie"]]
    abst = sum(s["abstention"] for s in acceptees)
    rejets = Counter(r["rejet"] for r in resultats if r["rejet"])
    dist = Counter(s["metier"] for s in acceptees if not s["abstention"])
    pct = lambda x: f"{round(100 * x / n)} %" if n else "—"  # noqa: E731
    L = [f"# Classification dans la taxonomie des métiers — {source} · {fournisseur}", "",
         f"> Exécuté le {quand} · modèle « {modele} » · {n} phrase(s). **Agrégats seulement** : aucune phrase individuelle "
         "n'est reproduite. **Aucune exactitude n'est revendiquée** : sans étiquettes humaines, on ne sait pas si le "
         "métier proposé est juste — la feuille d'annotation (hors dépôt) sert à le mesurer ensuite.", "",
         "| Mesure | Valeur |", "|---|---|", f"| Phrases | {n} |",
         *[f"| Langue détectée — {lg} | {c} ({pct(c)}) |" for lg, c in sorted(langues.items())],
         f"| Sorties acceptées par la validation | {len(acceptees)} ({pct(len(acceptees))}) |",
         f"| dont abstentions | {abst} ({pct(abst)}) |",
         *[f"| Sorties rejetées — {k} | {c} |" for k, c in sorted(rejets.items())], "",
         "## Distribution des métiers proposés (sorties acceptées, hors abstention)", "",
         *([f"- {metiers.libelle(m)} : {c}" for m, c in dist.most_common()] or ["- aucune"]), "",
         "Part de demandes implicites ou vagues : **non mesurée** — elle exige la colonne `domaine` et le jugement humain de "
         "la feuille d'annotation ; le taux d'abstention ci-dessus n'en est qu'un indice.", ""]
    return "\n".join(L)
