"""Analyse d'un besoin en texte libre par règles (hors ligne, déterministe).

Ce n'est PAS de l'IA générative : correspondance d'expressions de la taxonomie,
désambiguïsation par indices de contexte, marqueurs « idéalement / si possible ».
Son intérêt : reproductible, sans réseau, explicable. Sa limite : vocabulaire fermé.
"""
from __future__ import annotations

import re

from .models import Ambiguite, Besoin, Critere, OptionAmbiguite
from .taxonomy import Taxonomie, motif, normaliser

_SEPARATEURS_CLAUSE = re.compile(r"[,.;!?\n]|\bmais\b")
_CONTEXTE = [
    re.compile(r"\b(?:\d+|une|deux|trois|quatre|cinq)\s+fois\s+par\s+(?:jour|semaine|mois|an)\b"),
    re.compile(r"\bd'ici\s+[\w']+(?:\s+[\w']+){0,2}"),
    re.compile(r"\bavant\s+(?:le\s+|la\s+|l')?(?:\w+\s+){0,2}\d{4}\b"),
    re.compile(r"\bbudget\s+(?:de\s+)?[\w\s'.]{0,20}?(?:chf|francs|fr\.)"),
]


def _clause(norm: str, pos: int) -> str:
    debut = 0
    for m in _SEPARATEURS_CLAUSE.finditer(norm):
        if m.end() <= pos:
            debut = m.end()
        elif m.start() > pos:
            return norm[debut:m.start()]
    return norm[debut:]


def _chevauche(debut: int, fin: int, pris: list[tuple[int, int]]) -> bool:
    return any(debut < f and d < fin for d, f in pris)


_RECHERCHE = re.compile(
    r"\b(?:cherche|cherchons|recherche|recherchons|besoin|il me faut|il nous faut|trouver|"
    r"aimerais|aimerions|voudrais|voudrions|souhaite|souhaitons|qui peut|quelqu'un)\b"
)
_PHRASE = re.compile(r"[^.!?\n]+[.!?\n]?")


def _zones_recherche(n: str) -> list[tuple[int, int]]:
    """Phrases qui expriment la recherche. Si aucune, tout le texte compte.

    Évite de prendre « nous produisons des jus » pour le besoin : on ne garde que
    les phrases contenant un verbe de recherche (« je cherche », « il me faut »…).
    """
    phrases = [(m.start(), m.end()) for m in _PHRASE.finditer(n)]
    cibles = [(d, f) for d, f in phrases if _RECHERCHE.search(n[d:f])]
    return cibles or [(0, len(n))]


def analyser(texte: str, tax: Taxonomie) -> Besoin:
    n, pos = normaliser(texte)
    zones_utiles = _zones_recherche(n)

    def dans_recherche(debut: int) -> bool:
        return any(d <= debut < f for d, f in zones_utiles)

    def extrait(debut: int, fin: int) -> str:
        return texte[pos[debut]: pos[fin - 1] + 1] if fin > debut else ""

    def souple(debut: int) -> bool:
        cl = _clause(n, debut)
        return any(motif(m).search(cl) for m in tax.marqueurs_souples)

    pris: list[tuple[int, int]] = []
    trouves: list[tuple[int, Critere]] = []
    hors_recherche: list[str] = []

    # 1. Expressions de compétences, les plus longues d'abord (évite « transporteur » seul
    #    quand « transporteur frigorifique » est présent).
    candidats = sorted(
        ((e, c.id) for c in tax.concepts.values() for e in c.expressions),
        key=lambda x: -len(x[0]),
    )
    for expr, cid in candidats:
        for m in motif(expr).finditer(n):
            if _chevauche(m.start(), m.end(), pris):
                continue
            pris.append((m.start(), m.end()))
            if not dans_recherche(m.start()):
                hors_recherche.append(extrait(m.start(), m.end()))
                continue
            trouves.append((m.start(), Critere(
                type="expertise", valeur=cid, libelle=tax.libelle(cid),
                obligatoire=not souple(m.start()), extrait=extrait(m.start(), m.end()),
            )))

    # 2. Termes ambigus restants : résolus seulement si un seul sens a des indices dans le texte.
    ambiguites: list[Ambiguite] = []
    for terme, spec in tax.ambigus.items():
        for m in motif(terme).finditer(n):
            if _chevauche(m.start(), m.end(), pris) or not dans_recherche(m.start()):
                continue
            pris.append((m.start(), m.end()))
            options = spec["options"]
            indices = {
                cid: [i for i in hints if motif(normaliser(i)[0]).search(n)]
                for cid, hints in options.items()
            }
            gagnants = [cid for cid, trouves_i in indices.items() if trouves_i]
            ex = extrait(m.start(), m.end())
            if len(gagnants) == 1:
                cid = gagnants[0]
                trouves.append((m.start(), Critere(
                    type="expertise", valeur=cid, libelle=tax.libelle(cid),
                    obligatoire=not souple(m.start()), extrait=ex,
                    note=f"« {spec['libelle']} » compris comme « {tax.libelle(cid)} » (indice : {indices[cid][0]})",
                )))
            else:
                ambiguites.append(Ambiguite(
                    terme=spec["libelle"], extrait=ex,
                    options=[OptionAmbiguite(valeur=c, libelle=tax.libelle(c)) for c in options],
                ))

    # 3. Langues.
    for code, spec in tax.langues.items():
        for expr in spec["expressions"]:
            m = next((x for x in motif(normaliser(expr)[0]).finditer(n) if dans_recherche(x.start())), None)
            if m and not _chevauche(m.start(), m.end(), pris):
                pris.append((m.start(), m.end()))
                trouves.append((m.start(), Critere(
                    type="langue", valeur=code, libelle=spec["libelle"],
                    obligatoire=not souple(m.start()), extrait=extrait(m.start(), m.end()),
                )))
                break

    # 4. Zones desservies.
    for zone, exprs in tax.zones.items():
        for expr in sorted(exprs, key=len, reverse=True):
            m = next((x for x in motif(expr).finditer(n) if dans_recherche(x.start())), None)
            if m and not _chevauche(m.start(), m.end(), pris):
                pris.append((m.start(), m.end()))
                trouves.append((m.start(), Critere(
                    type="zone", valeur=zone, libelle=zone,
                    obligatoire=not souple(m.start()), extrait=extrait(m.start(), m.end()),
                )))
                break

    # Dédoublonnage (même type + valeur), ordre d'apparition dans le texte.
    trouves.sort(key=lambda x: x[0])
    criteres: list[Critere] = []
    vus: set[tuple[str, str]] = set()
    for _, c in trouves:
        if (c.type, c.valeur) not in vus:
            vus.add((c.type, c.valeur))
            criteres.append(c)

    # Si une compétence et l'une de ses sous-catégories sont présentes (« avocat » + « droit du
    # travail »), on retire la plus générale : le besoin réel est le plus précis.
    presents = {c.valeur for c in criteres if c.type == "expertise"}
    criteres = [c for c in criteres if c.type != "expertise"
                or not any(c.valeur in tax.ancetres(autre) for autre in presents)]

    # La première compétence est le besoin principal (obligatoire) ; les suivantes sont
    # « souhaitées » par défaut, l'utilisateur peut les rendre obligatoires.
    premiere = True
    for c in criteres:
        if c.type == "expertise":
            if premiere:
                c.obligatoire = True
                premiere = False
            else:
                c.obligatoire = False

    contexte = []
    for rx in _CONTEXTE:
        for m in rx.finditer(n):
            contexte.append(extrait(m.start(), m.end()))

    if hors_recherche:
        contexte.append("À propos de vous : " + ", ".join(dict.fromkeys(hors_recherche)))

    exclure = any(motif(mc).search(n) for mc in tax.marqueurs_concurrents)

    avertissements = []
    if not any(c.type == "expertise" for c in criteres) and not ambiguites:
        avertissements.append("Aucune compétence reconnue dans le texte. Choisissez-en une dans la liste ou reformulez.")

    return Besoin(
        texte=texte, criteres=criteres, exclure_concurrents=exclure,
        ambiguites=ambiguites, contexte=contexte, analyseur="regles",
        avertissements=avertissements,
    )
