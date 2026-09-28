"""Moteur de correspondance : contraintes dures (code) → pertinence → explications vérifiées.

Principe : le code décide qui est éligible (consentement, disponibilité, zone,
langue, concurrence). Aucun modèle de langage ne peut rendre éligible un profil exclu.
"""
from __future__ import annotations

import math
import re
import time
from collections import Counter
from typing import Optional

from .models import Besoin, Ecart, Preuve, Profil, ProfilPublic, Resultat, Suggestion
from .taxonomy import Taxonomie, motif, norm

_NEGATION = re.compile(r"\b(?:ne|n'|pas|aucun|aucune|jamais|plus de)\b")
_PHRASES = re.compile(r"[^.!?]+[.!?]?")
_MOTS_VIDES = set(norm(
    "le la les un une des de du d l et ou a au aux en pour par avec sans sur dans qui que quoi "
    "je j nous vous il elle on ils elles me m notre nos votre vos son sa ses ce cet cette ces "
    "est sont suis cherche cherchons recherche besoin faut trouver quelqu idealement si possible "
    "pas plus tres bien aussi mais donc car comme fois semaine mois jour"
).split())


def _public(p: Profil) -> ProfilPublic:
    return ProfilPublic(**p.model_dump(include=set(ProfilPublic.model_fields)))


def couverture(p: Profil, concept: str, tax: Taxonomie) -> Optional[Preuve]:
    """Preuve qu'un profil couvre un concept : déclarée (offre) ou déduite (présentation)."""
    lib = tax.libelle(concept)
    for o in p.offre:
        if tax.couvre(o.concept, concept):
            return Preuve(critere=lib, champ="offre", extrait=o.texte, nature="declare")
    # Déduction depuis la présentation libre, phrase par phrase, en ignorant les phrases négatives
    # (« nous réparons les groupes froid, nous ne livrons pas »).
    for m in _PHRASES.finditer(p.presentation):
        phrase = m.group(0).strip()
        np_ = norm(phrase)
        if _NEGATION.search(np_):
            continue
        if any(motif(e).search(np_) for e in tax.expressions_de(concept)):
            return Preuve(critere=lib, champ="presentation", extrait=phrase, nature="deduit")
    return None


def couverture_parent(p: Profil, concept: str, tax: Taxonomie) -> Optional[tuple[Preuve, int]]:
    """Le profil couvre seulement une catégorie plus large (piste à vérifier).

    Retourne aussi la distance dans la taxonomie (1 = parent direct) pour classer les pistes.
    """
    for distance, anc in enumerate(tax.ancetres(concept), start=1):
        for o in p.offre:
            if o.concept == anc:
                return Preuve(critere=tax.libelle(anc), champ="offre", extrait=o.texte, nature="declare"), distance
    return None


def preuve_valide(p: Profil, pr: Preuve) -> bool:
    """Garde-fou : l'extrait cité doit exister tel quel dans le champ du profil."""
    if pr.champ == "offre":
        return any(pr.extrait == o.texte for o in p.offre)
    if pr.champ == "recherche":
        return any(pr.extrait == o.texte for o in p.recherche)
    if pr.champ == "presentation":
        return bool(pr.extrait) and pr.extrait in p.presentation
    if pr.champ == "langues":
        return pr.extrait in p.langues
    if pr.champ == "zones_service":
        return pr.extrait in p.zones_service
    return False


def _tokens(texte: str) -> list[str]:
    return [t.rstrip("s") for t in re.findall(r"[a-z0-9]+", norm(texte)) if len(t) > 2 and t not in _MOTS_VIDES]


def texte_profil(p: Profil) -> str:
    return " ".join([p.fonction, p.entreprise, p.presentation] + [o.texte for o in p.offre])


class _Tfidf:
    def __init__(self, docs: dict[str, str]):
        self.tf = {k: Counter(_tokens(v)) for k, v in docs.items()}
        n = len(docs)
        df = Counter(t for c in self.tf.values() for t in c)
        self.idf = {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}

    def sim(self, requete: str, doc_id: str) -> float:
        q = Counter(_tokens(requete))
        d = self.tf.get(doc_id, Counter())
        num = sum(q[t] * d[t] * self.idf.get(t, 1) ** 2 for t in q)
        nq = math.sqrt(sum((q[t] * self.idf.get(t, 1)) ** 2 for t in q))
        nd = math.sqrt(sum((d[t] * self.idf.get(t, 1)) ** 2 for t in d))
        return num / (nq * nd) if nq and nd else 0.0


def filtres_durs(
    besoin: Besoin, demandeur: Profil, p: Profil, tax: Taxonomie
) -> Optional[str]:
    """Retourne la raison d'exclusion, ou None si le profil est éligible.

    Partagé avec la référence « mots-clés » pour que la comparaison porte
    uniquement sur la qualité du classement.
    """
    if p.id == demandeur.id or p.entreprise == demandeur.entreprise:
        return "vous-même"
    if p.type == "visiteur":
        return "hors communauté (visiteur)"
    if p.type == "exposant" and not besoin.inclure_exposants:
        return "exposant (non inclus dans la recherche)"
    if not p.accepte_introductions:
        return "ne souhaite pas recevoir d'introductions"
    if not p.disponible:
        return "indisponible actuellement"
    for c in besoin.criteres:
        if not c.obligatoire:
            continue
        if c.type == "zone":
            if not p.zones_service:
                return "zone desservie non renseignée"
            if c.valeur not in p.zones_service:
                return f"ne dessert pas : {c.libelle}"
        elif c.type == "langue":
            if not p.langues:
                return "langues non renseignées"
            if c.valeur not in p.langues:
                return f"ne parle pas {c.libelle}"
    if besoin.exclure_concurrents and any(
        tax.meme_famille(a, b) for a in p.secteurs for b in demandeur.secteurs
    ):
        return "concurrent potentiel (même secteur que vous)"
    return None


# Raisons non affichées au demandeur (pas d'information utile ou risque de révéler un refus nominatif).
_RAISONS_SILENCIEUSES = {"vous-même", "hors communauté (visiteur)"}


def rechercher(
    besoin: Besoin, demandeur: Profil, profils: list[Profil], tax: Taxonomie,
    mode: str = "demo", limite: int = 5,
) -> Resultat:
    t0 = time.perf_counter()
    expertises = [c for c in besoin.criteres if c.type == "expertise"]
    if not expertises:
        return Resultat(
            mode=mode, suggestions=[], abstention=True,
            message="Précisez la compétence recherchée : aucune n'a été reconnue ou choisie.",
            nb_profils_examines=0, duree_ms=(time.perf_counter() - t0) * 1000,
        )
    principale = next((c for c in expertises if c.obligatoire), expertises[0])
    tfidf = _Tfidf({p.id: texte_profil(p) for p in profils})

    suggestions: list[Suggestion] = []
    pistes: list[Suggestion] = []
    ecarts: Counter = Counter()
    examines = 0

    for p in profils:
        if p.id == demandeur.id:
            continue
        examines += 1
        pr_princ = couverture(p, principale.valeur, tax)
        pr_parent = None if pr_princ else couverture_parent(p, principale.valeur, tax)
        if pr_parent and pr_parent[1] > 1:
            pr_parent = None  # au-delà du parent direct, la piste devient du bruit
        if not pr_princ and not pr_parent:
            continue  # pas pertinent : on ne compte pas comme « écarté »

        raison = filtres_durs(besoin, demandeur, p, tax)
        if raison is None:
            for c in expertises:
                if c is principale or not c.obligatoire:
                    continue
                if not couverture(p, c.valeur, tax):
                    raison = f"ne couvre pas : {c.libelle}"
                    break
        if raison:
            if raison not in _RAISONS_SILENCIEUSES and pr_princ:
                ecarts[raison] += 1
            continue

        preuves: list[Preuve] = []
        a_verifier: list[str] = []
        score = 0.0
        if pr_princ:
            preuves.append(pr_princ)
            score += 1.0 if pr_princ.nature == "declare" else 0.5
            if pr_princ.nature == "deduit":
                a_verifier.append(f"{principale.libelle} : déduit de sa présentation, pas déclaré comme offre")
        else:
            preuves.append(pr_parent[0])
            score += 0.5 / pr_parent[1]
        toutes_declarees = pr_princ is not None and pr_princ.nature == "declare"

        for c in besoin.criteres:
            if c is principale:
                continue
            if c.type == "expertise":
                pr = couverture(p, c.valeur, tax)
                if pr:
                    preuves.append(pr)
                    score += 0.3 if pr.nature == "declare" else 0.15
                    toutes_declarees &= pr.nature == "declare" or not c.obligatoire
                elif not c.obligatoire:
                    a_verifier.append(f"{c.libelle} : non mentionné dans le profil")
            elif c.type == "zone":
                if c.valeur in p.zones_service:
                    preuves.append(Preuve(critere=f"Dessert : {c.libelle}", champ="zones_service", extrait=c.valeur, nature="declare"))
                    score += 0.1
                elif not c.obligatoire:
                    a_verifier.append(f"Zone {c.libelle} : " + ("non renseignée" if not p.zones_service else "non desservie selon le profil"))
            elif c.type == "langue":
                if c.valeur in p.langues:
                    preuves.append(Preuve(critere=f"Parle {c.libelle}", champ="langues", extrait=c.valeur, nature="declare"))
                    score += 0.1
                elif not c.obligatoire:
                    a_verifier.append(f"{c.libelle.capitalize()} : " + ("langues non renseignées" if not p.langues else "non indiqué dans le profil"))

        reciprocite = None
        for r in p.recherche:
            if any(tax.meme_famille(r.concept, s) for s in demandeur.secteurs):
                reciprocite = Preuve(critere="Cherche elle-même / lui-même votre type d'activité", champ="recherche", extrait=r.texte, nature="declare")
                score += 0.1
                break

        score += 0.2 * tfidf.sim(besoin.texte, p.id)

        # Garde-fou : on retire toute preuve qui ne se retrouve pas mot pour mot dans le profil.
        preuves = [x for x in preuves if preuve_valide(p, x)]
        if reciprocite and not preuve_valide(p, reciprocite):
            reciprocite = None

        s = Suggestion(
            profil=_public(p), niveau="forte" if toutes_declarees else "partielle",
            preuves=preuves, a_verifier=a_verifier, reciprocite=reciprocite, score=round(score, 4),
        )
        (suggestions if pr_princ else pistes).append(s)

    suggestions.sort(key=lambda s: (-s.score, s.profil.nom))
    pistes.sort(key=lambda s: (-s.score, s.profil.nom))
    abstention = not suggestions
    if abstention:
        message = f"Aucune correspondance fiable pour « {principale.libelle} » parmi les profils disponibles."
        if pistes:
            message += " Des pistes plus larges existent, sans garantie qu'elles couvrent votre besoin précis."
    else:
        message = ""
    return Resultat(
        mode=mode, suggestions=suggestions[:limite], abstention=abstention, message=message,
        pistes_elargies=pistes[:3] if abstention else [],
        ecartes=[Ecart(raison=r, nombre=n) for r, n in ecarts.most_common()],
        nb_profils_examines=examines, duree_ms=round((time.perf_counter() - t0) * 1000, 2),
    )
