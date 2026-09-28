"""Couche sémantique LOCALE : multilingual-e5-large (ONNX), sans réseau ni clé.

Rôle strictement limité : quand les règles ne reconnaissent aucune compétence, proposer LE concept de la
taxonomie le plus proche, seulement si la proposition est assez sûre. Ensuite, le pipeline habituel
s'applique (filtres du code, preuves citées mot pour mot, abstention). Le modèle ne voit pas les profils
pour décider ; il ne crée ni preuve ni éligibilité.

Décision calibrée (voir `calibrer`) : on accepte le concept le plus proche si
  score ≥ τ  ET  score − score du 2e concept ≥ δ,
avec (τ, δ) choisis sur un jeu de calibration indépendant des jeux d'évaluation, pour contenir le taux
de fausses acceptations sur des besoins hors catalogue.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

from .taxonomy import DATA_DIR, Taxonomie

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_MODELE = Path(os.environ.get("HACKVS_MODELE_SEMANTIQUE", RACINE / "var" / "modeles" / "fast-multilingual-e5-large"))
CACHE = RACINE / "var" / "cache_semantique"
CALIBRATION = DATA_DIR / "calibration_semantique.json"


class Encodeur:
    """e5 : préfixes « query: » / « passage: », moyenne des états cachés, normalisation L2."""

    def __init__(self, dossier: Path):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = max(1, (os.cpu_count() or 2) - 1)
        self.session = ort.InferenceSession(str(dossier / "model.onnx"), opts, providers=["CPUExecutionProvider"])
        self.entrees = {i.name for i in self.session.get_inputs()}
        self.tok = Tokenizer.from_file(str(dossier / "tokenizer.json"))
        self.tok.enable_truncation(256)
        self.tok.enable_padding()

    def encoder(self, textes: list[str], lot: int = 32) -> np.ndarray:
        sorties = []
        for i in range(0, len(textes), lot):
            enc = self.tok.encode_batch(textes[i:i + lot])
            ids = np.array([e.ids for e in enc], dtype=np.int64)
            masque = np.array([e.attention_mask for e in enc], dtype=np.int64)
            flux = {"input_ids": ids, "attention_mask": masque}
            if "token_type_ids" in self.entrees:
                flux["token_type_ids"] = np.zeros_like(ids)
            h = self.session.run(None, flux)[0]
            v = (h * masque[..., None]).sum(1) / masque.sum(1, keepdims=True)
            sorties.append(v / np.linalg.norm(v, axis=1, keepdims=True))
        return np.vstack(sorties).astype(np.float32)


def disponible() -> bool:
    return (DOSSIER_MODELE / "model.onnx").exists() and os.environ.get("HACKVS_SEMANTIQUE", "1") != "0"


@lru_cache(maxsize=1)
def encodeur() -> Encodeur:
    return Encodeur(DOSSIER_MODELE)


def _passages_concept(tax: Taxonomie, cid: str, sauf: Optional[str] = None) -> list[str]:
    c = tax.concepts[cid]
    # expressions « de base » (sans les variantes pluriel générées) pour des prototypes lisibles
    return [f"passage: {c.libelle}"] + [f"passage: {e}" for e in sorted(set(c.expressions)) if e != sauf and not e.endswith("s")]


class Prototypes:
    """Un vecteur par concept = moyenne des passages (libellé + expressions), mise en cache sur disque."""

    def __init__(self, tax: Taxonomie):
        self.tax = tax
        self.ids = list(tax.concepts)
        cle = hashlib.sha1(json.dumps({c: _passages_concept(tax, c) for c in self.ids}, sort_keys=True).encode()).hexdigest()[:12]
        fichier = CACHE / f"passages_{cle}.npz"
        self.passages = {c: _passages_concept(tax, c) for c in self.ids}
        if fichier.exists():
            d = np.load(fichier)
            self.vecteurs_passages = {c: d[c] for c in self.ids}
        else:
            tous = [p for c in self.ids for p in self.passages[c]]
            v = encodeur().encoder(tous)
            self.vecteurs_passages, k = {}, 0
            for c in self.ids:
                n = len(self.passages[c])
                self.vecteurs_passages[c] = v[k:k + n]
                k += n
            CACHE.mkdir(parents=True, exist_ok=True)
            np.savez(fichier, **self.vecteurs_passages)
        self.matrice = np.vstack([self._proto(c) for c in self.ids])

    def _proto(self, cid: str, sauf_indice: Optional[int] = None) -> np.ndarray:
        v = self.vecteurs_passages[cid]
        if sauf_indice is not None and len(v) > 1:
            v = np.delete(v, sauf_indice, axis=0)
        m = v.mean(0)
        return m / np.linalg.norm(m)

    def scores(self, vecteur_requete: np.ndarray) -> list[tuple[str, float]]:
        s = self.matrice @ vecteur_requete
        ordre = np.argsort(-s)
        return [(self.ids[i], float(s[i])) for i in ordre]


@lru_cache(maxsize=1)
def prototypes(tax_id: int = 0) -> Prototypes:
    from .taxonomy import charger_taxonomie
    return Prototypes(charger_taxonomie())


def seuils() -> dict:
    if CALIBRATION.exists():
        return json.loads(CALIBRATION.read_text(encoding="utf-8"))["seuils"]
    return {"tau": 1.0, "delta": 1.0}  # non calibré : n'accepte rien


def inferer_concept(texte: str, tax: Taxonomie) -> Optional[dict]:
    """Concept le plus proche du besoin, s'il passe les seuils calibrés ; sinon None (abstention)."""
    if not disponible():
        return None
    t0 = time.perf_counter()
    q = encodeur().encoder([f"query: {texte}"])[0]
    classement = prototypes().scores(q)
    (c1, s1), (c2, s2) = classement[0], classement[1]
    s = seuils()
    accepte = s1 >= s["tau"] and (s1 - s2) >= s["delta"]
    return {"concept": c1, "score": round(s1, 4), "second": c2, "marge": round(s1 - s2, 4), "accepte": accepte,
            "top": [(c, round(x, 4)) for c, x in classement[:5]],
            "latence_ms": round((time.perf_counter() - t0) * 1000, 1), "tau": s["tau"], "delta": s["delta"]}


# ---------------------------------------------------------------------------- recherche dans les offres
class IndexOffres:
    """Offres déclarées des membres, encodées (« passage: »), cache par texte sur disque."""

    def __init__(self, profils):
        self.entrees = [(p.id, o.concept, o.texte) for p in profils if p.type == "membre_club" for o in p.offre]
        textes = sorted({t for *_, t in self.entrees})
        cache = CACHE / "offres.npz"
        connus: dict[str, np.ndarray] = {}
        if cache.exists():
            d = np.load(cache, allow_pickle=False)
            connus = {k: d[k] for k in d.files}
        cle = lambda t: hashlib.sha1(t.encode()).hexdigest()
        manquants = [t for t in textes if cle(t) not in connus]
        if manquants:
            v = encodeur().encoder([f"passage: {t}" for t in manquants])
            for t, x in zip(manquants, v, strict=True):
                connus[cle(t)] = x
            CACHE.mkdir(parents=True, exist_ok=True)
            np.savez(cache, **connus)
        self.matrice = np.vstack([connus[cle(t)] for *_, t in self.entrees]) if self.entrees else np.zeros((0, 1024), np.float32)

    def classer(self, vecteur: np.ndarray) -> list[tuple[float, float, str, Optional[str], str]]:
        """(z, score, membre, concept, texte) triés par z décroissant. z = écart au bruit de fond de CETTE requête."""
        s = self.matrice @ vecteur
        mu, sigma = float(s.mean()), float(s.std() or 1e-6)
        ordre = np.argsort(-s)
        return [(float((s[i] - mu) / sigma), float(s[i]), *self.entrees[i]) for i in ordre]


_index_cache: dict[str, IndexOffres] = {}


def index_offres(profils) -> IndexOffres:
    cle = hashlib.sha1(json.dumps([(p.id, [o.texte for o in p.offre]) for p in profils]).encode()).hexdigest()
    if cle not in _index_cache:
        _index_cache.clear()
        _index_cache[cle] = IndexOffres(profils)
    return _index_cache[cle]


def seuils_offres() -> dict:
    if CALIBRATION.exists():
        d = json.loads(CALIBRATION.read_text(encoding="utf-8"))
        if "seuils_offres" in d:
            return d["seuils_offres"]
    return {"z": 99.0, "marge_z": 99.0}


def inferer_par_offres(texte: str, profils, tax: Taxonomie) -> Optional[dict]:
    """Concept déduit de l'offre de membre la plus proche, si elle se détache assez du bruit de fond."""
    if not disponible():
        return None
    t0 = time.perf_counter()
    idx = index_offres(profils)
    if not idx.entrees:
        return None
    classement = idx.classer(encodeur().encoder([f"query: {texte}"])[0])
    z1, s1, membre, concept, offre = classement[0]
    # marge : écart avec la meilleure offre d'une AUTRE famille de concepts
    autre = next((c for c in classement[1:] if not (c[3] and concept and tax.meme_famille(c[3], concept))), None)
    marge = z1 - (autre[0] if autre else 0.0)
    s = seuils_offres()
    accepte = concept is not None and z1 >= s["z"] and marge >= s["marge_z"]
    return {"concept": concept, "offre": offre, "membre": membre, "score": round(s1, 4), "z": round(z1, 3),
            "marge_z": round(marge, 3), "accepte": accepte, "seuil_z": s["z"], "seuil_marge": s["marge_z"],
            "latence_ms": round((time.perf_counter() - t0) * 1000, 1)}


# ---------------------------------------------------------------------------- suggestions hybrides
# Idées reprises (voir docs/OPEN_SOURCE_RECON.md) : score hybride pondéré dense + lexical (BGE-M3 : w·dense + w'·sparse),
# score « max » par expression (multi-vecteur). La fusion par rangs réciproques k = 61 (Haystack) a été MESURÉE et
# écartée : sur la calibration, hit@3 0,870 contre 0,948 pour la somme pondérée. Aucune dépendance ajoutée.
POIDS_LEXICAL = 0.3  # choisi sur la calibration (0 / 0,3 / 0,5 / 1 testés), pas sur les jeux d'évaluation


class IndexLexical:
    """Lexical « sparse » : préfixes de 5 lettres des mots du libellé et des expressions, pondérés par IDF."""

    def __init__(self, tax: Taxonomie):
        from .taxonomy import norm
        self.norm = norm
        self.vides = set(tax.mots_generiques) | _MOTS_VIDES_SUGG
        self.termes: dict[str, set[str]] = {}
        for cid, c in tax.concepts.items():
            self.termes[cid] = {self._p(m) for t in [c.libelle, *c.expressions] for m in self._mots(t)}
        import math
        df: dict[str, int] = {}
        for ts in self.termes.values():
            for t in ts:
                df[t] = df.get(t, 0) + 1
        n = len(self.termes)
        self.idf = {t: math.log(1 + n / d) for t, d in df.items()}

    def _mots(self, texte: str) -> list[str]:
        import re
        return [m for m in re.findall(r"[a-z0-9]+", self.norm(texte)) if len(m) >= 4 and m not in self.vides]

    @staticmethod
    def _p(m: str) -> str:
        return m[:5]

    def scores(self, texte: str) -> dict[str, float]:
        q = {self._p(m) for m in self._mots(texte)}
        return {cid: sum(self.idf[t] for t in q & ts) for cid, ts in self.termes.items()}


_MOTS_VIDES_SUGG = {"cherche", "cherchons", "recherche", "besoin", "quelqu", "quelqun", "personne", "aurais", "voudrais",
                    "pourrait", "faudrait", "notre", "votre", "nous", "avec", "pour", "dans", "sont", "that", "with",
                    "someone", "looking", "need", "want", "help", "brauchen", "suchen", "jemanden", "unsere", "unser",
                    "wir", "eine", "einen", "aider", "aide", "rencontrer", "travaille", "connait", "bien", "capable"}


@lru_cache(maxsize=1)
def index_lexical() -> IndexLexical:
    from .taxonomy import charger_taxonomie
    return IndexLexical(charger_taxonomie())


def suggerer(texte: str, tax: Taxonomie, methode: str = "hybride") -> dict:
    """Classement des compétences pour un besoin, et OPTIONS à montrer au membre (à confirmer, jamais imposées).

    dense   : comportement historique (prototypes e5, 3 options dès que le score frôle τ).
    hybride : z-score dense (max par expression + prototype) + 0,3 × lexical IDF ; options adaptatives
              (écart Δ calibré pour montrer la bonne compétence dans ≥ 90 % des cas de calibration).
    Aucun seuil ne sait reconnaître un besoin hors catalogue (mesuré) : le membre garde toujours « Aucune ».
    """
    t0 = time.perf_counter()
    q = encodeur().encoder([f"query: {texte}"])[0]
    P = prototypes()
    moy = P.scores(q)
    s = seuils()
    if methode == "dense":
        opts = [c for c, _ in moy[:3]] if moy[0][1] >= s["tau"] - 0.05 else []
        return {"classement": [{"concept": c, "score": round(x, 4)} for c, x in moy], "options": opts,
                "latence_ms": round((time.perf_counter() - t0) * 1000, 1)}
    mx = np.array([float((P.vecteurs_passages[c] @ q).max()) for c in P.ids])
    mo = np.array([x for _, x in sorted(moy, key=lambda t: P.ids.index(t[0]))])
    # z-score dans la distribution de la requête : e5 donne des scores « plats » (0,80–0,87 pour tout)
    zsum = (mx - mx.mean()) / mx.std() + (mo - mo.mean()) / mo.std()
    lex = index_lexical().scores(texte)
    lx = np.array([lex[c] for c in P.ids])
    score = zsum + POIDS_LEXICAL * lx
    classement = [P.ids[i] for i in np.argsort(-score)]
    fus = {c: float(score[P.ids.index(c)]) for c in P.ids}
    delta = s.get("hybride", {}).get("delta_z", 0.0)
    z = {c: float(zsum[P.ids.index(c)]) for c in P.ids}
    top3 = classement[:3]
    # Nombre d'options ADAPTATIF : on ne montre que les compétences proches de la meilleure (≥ 1 option).
    options = [c for c in top3 if fus[c] >= fus[top3[0]] - delta]
    return {"classement": [{"concept": c, "score": round(fus[c], 3), "z": round(z[c], 3),
                            "dense_max": round(float(mx[P.ids.index(c)]), 4), "lexical": round(lex[c], 3)} for c in classement],
            "options": options, "latence_ms": round((time.perf_counter() - t0) * 1000, 1)}
