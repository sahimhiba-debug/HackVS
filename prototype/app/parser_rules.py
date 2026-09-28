"""Analyse d'un besoin en texte libre par règles (hors ligne, déterministe).

Ce n'est PAS de l'IA générative : correspondance d'expressions de la taxonomie,
désambiguïsation par indices de contexte, portée des marqueurs limitée à la clause.
Intérêt : reproductible, sans réseau, explicable. Limite : vocabulaire et tournures fermés.

Règles principales (chacune couverte par le jeu adversarial) :
- seules les phrases qui expriment une recherche comptent (« je cherche », « il me faut »…) ;
- « idéalement », « si possible »… rendent SOUHAITÉ le critère de la même clause ;
  « impérativement », « uniquement »… le rendent OBLIGATOIRE ;
- une compétence niée (« pas de cybersécurité ») devient une EXCLUSION ;
- « basé / implanté à X » = implantation du prestataire ; « livrer / intervenir à X » = zone
  d'intervention ; « nous sommes basés à X » = contexte sur le demandeur, pas un critère ;
- sans compétence reconnue, les mots significatifs restants forment un critère « hors catalogue ».
"""
from __future__ import annotations

import re

from .models import Ambiguite, Besoin, Critere, Exclusion, OptionAmbiguite
from .taxonomy import Taxonomie, motif, normaliser

_SEPARATEURS_CLAUSE = re.compile(r"[,.;:!?()\n]|\bmais\b")
_CONTEXTE = [
    re.compile(r"\b(?:\d+|une|deux|trois|quatre|cinq)\s+fois\s+par\s+(?:jour|semaine|mois|an)\b"),
    re.compile(r"\bd'ici\s+[\w']+(?:\s+[\w']+){0,2}"),
    re.compile(r"\bavant\s+(?:le\s+|la\s+|l')?(?:\w+\s+){0,2}\d{4}\b"),
    re.compile(r"\bbudget\s+(?:de\s+)?[\w\s'.]{0,20}?(?:chf|francs|fr\.)"),
    re.compile(r"\b\d+\s+(?:personnes|colis|palettes|bouteilles|m2)\b"),
]
_RECHERCHE = re.compile(
    r"\b(?:cherche|cherchons|recherche|recherchons|besoin|il me faut|il nous faut|trouver|"
    r"aimerais|aimerions|voudrais|voudrions|souhaite|souhaitons|qui peut|qui pourrait|qui fait|quelqu'un|recrute|recrutons|"
    r"dois|devons|faudrait|suche|suchen|brauche|brauchen|benotige|benotigen)\b"
)
_PHRASE = re.compile(r"[^.!?\n]+[.!?\n]?")
_NEGATION_AVANT = re.compile(
    r"(?:\bpas\b|\bne\b|\bn'|\bsans\b|\bsauf\b|\bhors\b|\bni\b|\bnon\b|\bplutot que\b|\bautre que\b)"
    r"(?:\s+[\w'-]+){0,4}\s*$"
)
_IMPL = (r"(?:base|basee|bases|basees|implante|implantee|implantes|implantees|installe|installee|installes|"
         r"installees|situe|situee|situes|situees|localise|localisee|localises|localisees)")
_PREP = r"(?:a|en|au|aux|dans|pres de|du|dans la region de|dans le|dans la|sur)"
_SOI = re.compile(
    r"(?:nous sommes|je suis|nous nous trouvons|on est|notre (?:entreprise|societe|siege|atelier|cave|domaine|bureau) est)"
    rf"\s+(?:{_IMPL}\s+)?{_PREP}\s+(?:la\s+|le\s+|l')?$"
)
_IMPLANTATION = re.compile(rf"{_IMPL}\s+{_PREP}\s+(?:la\s+|le\s+|l')?$")
_TOKEN = re.compile(r"[a-z0-9][a-z0-9-]*")


def _clause(n: str, p: int) -> tuple[int, int]:
    debut = 0
    for m in _SEPARATEURS_CLAUSE.finditer(n):
        if m.end() <= p:
            debut = m.end()
        elif m.start() > p:
            return debut, m.start()
    return debut, len(n)


def _chevauche(debut: int, fin: int, pris: list[tuple[int, int]]) -> bool:
    return any(debut < f and d < fin for d, f in pris)


def analyser(texte: str, tax: Taxonomie) -> Besoin:
    n, pos = normaliser(texte)

    def extrait(debut: int, fin: int) -> str:
        return texte[pos[debut]: pos[fin - 1] + 1] if fin > debut else ""

    phrases = [(m.start(), m.end()) for m in _PHRASE.finditer(n)]
    zones_utiles = [(d, f) for d, f in phrases if _RECHERCHE.search(n[d:f])] or [(0, len(n))]

    def dans_recherche(p: int) -> bool:
        return any(d <= p < f for d, f in zones_utiles)

    def force(p: int) -> bool | None:
        """True = obligatoire explicite, False = souhaité explicite, None = aucun marqueur dans la clause."""
        d, f = _clause(n, p)
        cl = n[d:f]
        if any(motif(m).search(cl) for m in tax.marqueurs_souples):
            return False
        if any(motif(m).search(cl) for m in tax.marqueurs_forts):
            return True
        return None

    def nie(p: int) -> bool:
        d, _ = _clause(n, p)
        return bool(_NEGATION_AVANT.search(n[d:p]))

    pris: list[tuple[int, int]] = []
    trouves: list[tuple[int, Critere]] = []
    exclusions: list[tuple[str, str]] = []
    hors_recherche: list[str] = []
    contexte: list[str] = []

    # 0. Composés trompeurs (« comptabilité carbone », « assurance maladie ») : consommés, jamais une compétence.
    trompeurs: list[str] = []
    for expr in tax.composes_trompeurs:
        for m in motif(expr).finditer(n):
            if not _chevauche(m.start(), m.end(), pris):
                pris.append((m.start(), m.end()))
                trompeurs.append(extrait(m.start(), m.end()))

    # 1. Compétences, expressions les plus longues d'abord.
    candidats = sorted(((e, c.id) for c in tax.concepts.values() for e in c.expressions), key=lambda x: -len(x[0]))
    for expr, cid in candidats:
        for m in motif(expr).finditer(n):
            if _chevauche(m.start(), m.end(), pris):
                continue
            pris.append((m.start(), m.end()))
            ex = extrait(m.start(), m.end())
            d_cl, f_cl = _clause(n, m.start())
            piege = next((t for t in tax.contextes_trompeurs.get(cid, ()) if motif(t).search(n[d_cl:f_cl])), None)
            if piege:  # « avocat … divorce » : même mot, autre domaine → pas cette compétence
                trompeurs += [ex, piege]
                continue
            if not dans_recherche(m.start()):
                hors_recherche.append(ex)
            elif nie(m.start()):
                exclusions.append((cid, ex))
            else:
                trouves.append((m.start(), Critere(type="expertise", valeur=cid, libelle=tax.libelle(cid),
                                                   obligatoire=force(m.start()) is True, extrait=ex)))

    # 2. Termes ambigus restants : résolus seulement si un seul sens a des indices dans le texte.
    ambiguites: list[Ambiguite] = []
    for spec_terme, spec in tax.ambigus.items():
        for m in motif(spec_terme).finditer(n):
            if _chevauche(m.start(), m.end(), pris) or not dans_recherche(m.start()):
                continue
            pris.append((m.start(), m.end()))
            options = spec["options"]
            indices = {cid: [i for i in hints if motif(normaliser(i)[0]).search(n)] for cid, hints in options.items()}
            gagnants = [cid for cid, t in indices.items() if t]
            ex = extrait(m.start(), m.end())
            if nie(m.start()):
                if len(gagnants) == 1:
                    exclusions.append((gagnants[0], ex))
                continue
            if len(gagnants) == 1:
                cid = gagnants[0]
                trouves.append((m.start(), Critere(
                    type="expertise", valeur=cid, libelle=tax.libelle(cid), obligatoire=force(m.start()) is True,
                    extrait=ex, note=f"« {spec['libelle']} » compris comme « {tax.libelle(cid)} » (indice : {indices[cid][0]})")))
            else:
                ambiguites.append(Ambiguite(terme=spec["libelle"], extrait=ex,
                                            options=[OptionAmbiguite(valeur=c, libelle=tax.libelle(c)) for c in options]))

    # 3. Langues : obligatoires par défaut, souhaitées si un marqueur souple est dans la clause.
    for code, spec in tax.langues.items():
        for expr in spec["expressions"]:
            m = next((x for x in motif(normaliser(expr)[0]).finditer(n) if dans_recherche(x.start())), None)
            if m and not _chevauche(m.start(), m.end(), pris):
                pris.append((m.start(), m.end()))
                if not nie(m.start()):
                    trouves.append((m.start(), Critere(type="langue", valeur=code, libelle=spec["libelle"],
                                                       obligatoire=force(m.start()) is not False,
                                                       extrait=extrait(m.start(), m.end()))))
                break

    # 4. Lieux : implantation du prestataire, zone d'intervention, ou localisation du demandeur.
    for zone, exprs in tax.zones.items():
        for expr in sorted(exprs, key=len, reverse=True):
            for m in motif(expr).finditer(n):
                if _chevauche(m.start(), m.end(), pris):
                    continue
                pris.append((m.start(), m.end()))
                ex = extrait(m.start(), m.end())
                d, _ = _clause(n, m.start())
                avant = n[d:m.start()]
                if not dans_recherche(m.start()):
                    hors_recherche.append(ex)
                    continue
                if _SOI.search(avant):
                    contexte.append(f"Votre localisation : {ex} (pas un critère)")
                    continue
                type_ = "implantation" if _IMPLANTATION.search(avant) else "zone"
                trouves.append((m.start(), Critere(type=type_, valeur=zone, libelle=zone,
                                                   obligatoire=force(m.start()) is not False, extrait=ex)))

    # Ordre d'apparition + dédoublonnage.
    trouves.sort(key=lambda x: x[0])
    criteres: list[Critere] = []
    vus: set[tuple[str, str]] = set()
    for _, c in trouves:
        if (c.type, c.valeur) not in vus:
            vus.add((c.type, c.valeur))
            criteres.append(c)

    # Le plus précis l'emporte (« avocat » + « droit du travail » → droit du travail).
    presents = {c.valeur for c in criteres if c.type == "expertise"}
    criteres = [c for c in criteres if c.type != "expertise"
                or not any(c.valeur in tax.ancetres(autre) for autre in presents)]

    # Une exclusion contredite par une recherche positive du même concept est ignorée
    # (« marketing, mais pas pour les réseaux sociaux » : on garde le marketing).
    presents = {c.valeur for c in criteres if c.type == "expertise"}
    excl: list[Exclusion] = []
    for cid, ex in exclusions:
        if cid in presents:
            contexte.append(f"À éviter : {ex}")
        elif not any(e.valeur == cid for e in excl):
            excl.append(Exclusion(valeur=cid, libelle=tax.libelle(cid), extrait=ex))

    # Besoin principal = première compétence, toujours obligatoire ; les suivantes restent
    # souhaitées sauf marqueur fort (calculé plus haut).
    principale = next((c for c in criteres if c.type == "expertise"), None)
    if principale:
        principale.obligatoire = True

    # Hors catalogue : sans compétence reconnue, on garde les mots significatifs restants.
    if principale is None and not ambiguites:
        libres = list(trompeurs)  # le composé trompeur EST le besoin (hors catalogue)
        for d, f in zones_utiles:
            for m in _TOKEN.finditer(n, d, f):
                mot = m.group(0).strip("-")
                if (len(mot) >= 3 and mot not in tax.mots_generiques and not mot.isdigit()
                        and not _chevauche(m.start(), m.end(), pris)):
                    libres.append(extrait(m.start(), m.end()))
        libres = list(dict.fromkeys(libres))
        if libres:
            criteres.insert(0, Critere(type="texte_libre", valeur=" ".join(libres), libelle="Compétence hors catalogue",
                                       obligatoire=True, extrait=None,
                                       note="Aucune catégorie du Club reconnue : recherche par mots dans les offres déclarées."))

    for rx in _CONTEXTE:
        for m in rx.finditer(n):
            contexte.append(extrait(m.start(), m.end()))
    if hors_recherche:
        contexte.append("À propos de vous : " + ", ".join(dict.fromkeys(hors_recherche)))

    avertissements = []
    if not any(c.type in ("expertise", "texte_libre") for c in criteres) and not ambiguites:
        avertissements.append("Je n'ai pas compris quelle compétence vous cherchez. Précisez-la en une phrase "
                              "ou choisissez-la dans la liste.")

    return Besoin(
        texte=texte, criteres=criteres, exclusions=excl,
        exclure_concurrents=any(motif(mc).search(n) for mc in tax.marqueurs_concurrents),
        ambiguites=ambiguites, contexte=list(dict.fromkeys(contexte)), analyseur="regles",
        avertissements=avertissements,
    )


# ---------------------------------------------------------------------------- profil en 30 secondes
# Verbes de production : « nous produisons des tisanes à Orsières » est une offre, même si la phrase cite un lieu.
_PRODUCTION = re.compile(r"\b(?:nous|on|je)\s+(?:produisons|fabriquons|vendons|proposons|offrons|cultivons|elevons|distillons|brassons)\b")
_OFFRE_PROFIL = re.compile(
    r"\b(?:nous|on|je)\s+(?:assurons|proposons|offrons|livrons|realisons|effectuons|faisons|installons|accompagnons|"
    r"transportons|fournissons|louons|organisons|vendons|produisons|fabriquons|conseillons|intervenons|travaillons|"
    r"sommes specialis\w*|sommes)\b|\bspecialis|\bservice(?:s)? de\b|\bnotre (?:offre|metier|specialite)\b"
)
_CHERCHE_PROFIL = re.compile(r"\b(?:cherchons|recherchons|cherche|recherche|aimerions trouver|avons besoin|besoin de)\b")


def extraire_profil(texte: str, tax: Taxonomie) -> dict:
    """Description libre d'une entreprise → offres, recherches, zones d'intervention, langues PROPOSÉES.

    Chaque offre garde la phrase d'origine comme texte : c'est elle qui servira de preuve, mot pour mot.
    Rien n'est enregistré sans validation du membre.
    """
    offres, recherches, zones, langues, ignorees = [], [], [], [], []
    for m in _PHRASE.finditer(texte):
        phrase = m.group(0).strip().rstrip(".!?").strip()
        if len(phrase) < 4:
            continue
        n, _ = normaliser(phrase)
        cible = recherches if _CHERCHE_PROFIL.search(n) else offres
        trouves: list[tuple[int, str]] = []
        pris: list[tuple[int, int]] = []
        for expr, cid in sorted(((e, c.id) for c in tax.concepts.values() for e in c.expressions), key=lambda x: -len(x[0])):
            for mm in motif(expr).finditer(n):
                if _chevauche(mm.start(), mm.end(), pris):
                    continue
                pris.append((mm.start(), mm.end()))
                d, _f = _clause(n, mm.start())
                if not _NEGATION_AVANT.search(n[d:mm.start()]):
                    trouves.append((mm.start(), cid))
        concepts = list(dict.fromkeys(cid for _, cid in sorted(trouves)))
        # garder le plus précis quand un concept et sa sous-catégorie sont présents
        concepts = [c for c in concepts if not any(c in tax.ancetres(o) for o in concepts)]
        for cid in concepts:
            cible.append({"concept": cid, "libelle": tax.libelle(cid), "texte": phrase})
        lieu_ou_langue = any(motif(e).search(n) for ex in tax.zones.values() for e in ex) or any(
            motif(normaliser(e)[0]).search(n) for spec in tax.langues.values() for e in spec["expressions"])
        if not concepts:
            if lieu_ou_langue and cible is offres and not _PRODUCTION.search(n):
                pass  # phrase de contexte (« nous intervenons en Valais ») : renseigne zones et langues, pas une offre
            elif cible is offres and _OFFRE_PROFIL.search(n):
                offres.append({"concept": None, "libelle": "Hors catalogue (recherche par mots)", "texte": phrase})
            elif cible is recherches:
                recherches.append({"concept": None, "libelle": "Hors catalogue", "texte": phrase})
            else:
                ignorees.append(phrase)
        for zone, exprs in tax.zones.items():
            if zone not in zones and any(motif(e).search(n) for e in exprs) and cible is offres:
                zones.append(zone)
        for code, spec in tax.langues.items():
            if code not in langues and any(motif(normaliser(e)[0]).search(n) for e in spec["expressions"]):
                langues.append(code)
    return {"offre": offres, "recherche": recherches, "zones_service": zones, "langues": langues,
            "phrases_ignorees": ignorees}
