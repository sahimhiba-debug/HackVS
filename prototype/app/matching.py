"""Moteur de correspondance : contraintes dures (code) → pertinence → explications vérifiées.

Principe : le code décide qui est éligible (consentement, disponibilité, zone, implantation,
langue, concurrence, exclusions). Aucun modèle de langage ne peut rendre éligible un profil exclu.

Hiérarchie des preuves de compétence :
1. « declare »  : offre structurée du profil (le membre l'a déclarée) → peut donner « forte » ;
2. « deduit »   : phrase de présentation qui AFFIRME une offre (« nous assurons… »), sans négation,
                  sans formulation de besoin ni de clientèle → « partielle » ;
3. « textuel »  : besoin hors catalogue, mots retrouvés dans une offre déclarée → « partielle ».
"""
from __future__ import annotations

import math
import re
import time
from collections import Counter
from typing import Optional

from .models import Besoin, Critere, Ecart, Explication, LigneExplication, Preuve, Profil, ProfilPublic, Resultat, Suggestion
from .taxonomy import Taxonomie, norm

_NEGATION = re.compile(r"\b(?:ne|n'|pas|aucun|aucune|jamais|plus de)\b")
# Une phrase de présentation ne prouve une compétence que si elle affirme une offre…
_AFFIRME_OFFRE = re.compile(
    r"\b(?:nous|on|je)\s+(?:assurons|proposons|offrons|livrons|realisons|effectuons|faisons|installons|"
    r"accompagnons|transportons|fournissons|louons|organisons|assure|propose|offre|livre|realise|installe)\b"
    r"|\bspecialis|\bservice(?:s)? de\b|\bnous sommes (?:un|une|des)\b"
)
# …et ne décrit ni un besoin du membre ni sa clientèle.
_BESOIN_OU_CLIENTELE = re.compile(
    r"\b(?:cherchons|recherchons|cherche|recherche|besoin|nos clients|clients\s*:|clientele|nos fournisseurs)\b"
)
_PHRASES = re.compile(r"[^.!?]+[.!?]?")
_MOTS_VIDES = set(norm(
    "le la les un une des de du d l et ou a au aux en pour par avec sans sur dans qui que quoi "
    "je j nous vous il elle on ils elles me m notre nos votre vos son sa ses ce cet cette ces "
    "est sont suis cherche cherchons recherche besoin faut trouver quelqu idealement si possible "
    "pas plus tres bien aussi mais donc car comme fois semaine mois jour"
).split())


def _public(p: Profil) -> ProfilPublic:
    return ProfilPublic(**p.model_dump(include=set(ProfilPublic.model_fields)))


def _racine(mot: str) -> str:
    """Racinisation grossière (6 premiers caractères) : pollinisation ≈ polliniser."""
    return mot[:6]


def _mots(texte: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", norm(texte)) if len(t) >= 3 and t not in _MOTS_VIDES]


def _exclu(concept: Optional[str], besoin: Besoin, tax: Taxonomie) -> bool:
    return concept is not None and any(tax.couvre(concept, e.valeur) for e in besoin.exclusions)


def couverture(p: Profil, concept: str, tax: Taxonomie, besoin: Optional[Besoin] = None) -> Optional[Preuve]:
    """Preuve qu'un profil couvre un concept : déclarée (offre) ou déduite (présentation affirmative)."""
    lib = tax.libelle(concept)
    for o in p.offre:
        if o.concept and tax.couvre(o.concept, concept) and not (besoin and _exclu(o.concept, besoin, tax)):
            return Preuve(critere=lib, champ="offre", extrait=o.texte, nature="declare")
    for m in _PHRASES.finditer(p.presentation):
        phrase = m.group(0).strip()
        np_ = norm(phrase)
        if _NEGATION.search(np_) or _BESOIN_OU_CLIENTELE.search(np_) or not _AFFIRME_OFFRE.search(np_):
            continue
        presents = tax.concepts_dans(np_)
        if any(c in presents for c in tax.descendants(concept) if not (besoin and _exclu(c, besoin, tax))):
            return Preuve(critere=lib, champ="presentation", extrait=phrase, nature="deduit")
    return None


def couverture_textuelle(p: Profil, critere: Critere, besoin: Besoin, tax: Taxonomie) -> Optional[Preuve]:
    """Besoin hors catalogue : une MÊME offre déclarée doit contenir assez de mots du besoin.

    Seuil : au moins 2 racines communes ET au moins la moitié des racines du besoin.
    Volontairement strict : « droit maritime » ne doit pas trouver « droit des sociétés ».
    """
    requete = {_racine(m) for m in _mots(critere.valeur)}
    if not requete:
        return None
    seuil = max(2, math.ceil(len(requete) / 2))
    meilleur = None
    for o in p.offre:
        if _exclu(o.concept, besoin, tax):
            continue
        communs = requete & {_racine(m) for m in _mots(o.texte)}
        if len(communs) >= seuil and (meilleur is None or len(communs) > meilleur[0]):
            meilleur = (len(communs), o.texte)
    if meilleur:
        return Preuve(critere="Mots de votre besoin dans son offre", champ="offre", extrait=meilleur[1], nature="textuel")
    return None


def couverture_parent(p: Profil, concept: str, tax: Taxonomie) -> Optional[tuple[Preuve, int]]:
    """Le profil couvre seulement la catégorie parente directe (piste à vérifier)."""
    ancetres = tax.ancetres(concept)[:1]
    for anc in ancetres:
        for o in p.offre:
            if o.concept == anc:
                return Preuve(critere=tax.libelle(anc), champ="offre", extrait=o.texte, nature="declare"), 1
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
    if pr.champ == "commune":
        return pr.extrait == p.commune
    return False


def _tokens(texte: str) -> list[str]:
    return [t.rstrip("s") for t in _mots(texte)]


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


def filtres_durs(besoin: Besoin, demandeur: Profil, p: Profil, tax: Taxonomie) -> Optional[str]:
    """Raison d'exclusion, ou None si le profil est éligible.

    Partagé avec la référence « mots-clés » et avec la Bourse : les trois vues appliquent
    exactement les mêmes règles.
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
                return "zone d'intervention non renseignée"
            if c.valeur not in p.zones_service:
                return f"n'intervient pas en : {c.libelle}"
        elif c.type == "implantation":
            z = tax.zone_de_commune(p.commune)
            if z is None:
                return "implantation inconnue"
            if z != c.valeur:
                return f"pas implanté·e en : {c.libelle}"
        elif c.type == "langue":
            if not p.langues:
                return "langues non renseignées"
            if c.valeur not in p.langues:
                return f"ne parle pas {c.libelle}"
    if besoin.exclure_concurrents and any(tax.meme_famille(a, b) for a in p.secteurs for b in demandeur.secteurs):
        return "concurrent potentiel (même secteur que vous)"
    return None


# Raisons non affichées au demandeur (pas utiles, ou risque de révéler un refus nominatif).
_RAISONS_SILENCIEUSES = {"vous-même", "hors communauté (visiteur)"}


def rechercher(
    besoin: Besoin, demandeur: Profil, profils: list[Profil], tax: Taxonomie,
    mode: str = "demo", limite: int = 5, texte_libre: bool = True,
) -> Resultat:
    t0 = time.perf_counter()
    expertises = [c for c in besoin.criteres if c.type == "expertise"]
    libre = next((c for c in besoin.criteres if c.type == "texte_libre"), None) if texte_libre else None
    if not expertises and not libre:
        return Resultat(mode=mode, suggestions=[], abstention=True,
                        message="Précisez la compétence recherchée : aucune n'a été reconnue ou choisie.",
                        duree_ms=round((time.perf_counter() - t0) * 1000, 2))
    principale = next((c for c in expertises if c.obligatoire), expertises[0]) if expertises else libre
    tfidf = _Tfidf({p.id: texte_profil(p) for p in profils})

    suggestions: list[Suggestion] = []
    pistes: list[Suggestion] = []
    ecarts: Counter = Counter()
    examines = 0

    for p in profils:
        if p.id == demandeur.id:
            continue
        examines += 1
        if principale.type == "texte_libre":
            pr_princ, pr_parent = couverture_textuelle(p, principale, besoin, tax), None
        else:
            pr_princ = couverture(p, principale.valeur, tax, besoin)
            pr_parent = None if pr_princ else couverture_parent(p, principale.valeur, tax)
        if not pr_princ and not pr_parent:
            continue  # pas pertinent : non compté comme « écarté »

        raison = filtres_durs(besoin, demandeur, p, tax)
        if raison is None:
            for c in expertises:
                if c is not principale and c.obligatoire and not couverture(p, c.valeur, tax, besoin):
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
            score += {"declare": 1.0, "deduit": 0.5, "textuel": 0.6}[pr_princ.nature]
            if pr_princ.nature == "deduit":
                a_verifier.append(f"{principale.libelle} : mentionné dans sa présentation, pas déclaré comme offre")
            if pr_princ.nature == "textuel":
                a_verifier.append("Compétence hors catalogue : correspondance par mots, à confirmer avec la personne")
        else:
            preuves.append(pr_parent[0])
            score += 0.5 / pr_parent[1]
        toutes_declarees = pr_princ is not None and pr_princ.nature == "declare"

        for c in besoin.criteres:
            if c is principale or c.type == "texte_libre":
                continue
            if c.type == "expertise":
                pr = couverture(p, c.valeur, tax, besoin)
                if pr:
                    preuves.append(pr)
                    score += 0.3 if pr.nature == "declare" else 0.15
                else:
                    a_verifier.append(f"{c.libelle} (souhaité) : non mentionné dans le profil")
            elif c.type == "zone":
                if c.valeur in p.zones_service:
                    preuves.append(Preuve(critere=f"Intervient en : {c.libelle}", champ="zones_service", extrait=c.valeur, nature="declare"))
                    score += 0.1
                elif not c.obligatoire:
                    a_verifier.append(f"Intervention en {c.libelle} (souhaité) : " + ("non renseignée" if not p.zones_service else "non indiquée"))
            elif c.type == "implantation":
                if tax.zone_de_commune(p.commune) == c.valeur:
                    preuves.append(Preuve(critere=f"Implanté·e en : {c.libelle}", champ="commune", extrait=p.commune, nature="declare"))
                    score += 0.1
                elif not c.obligatoire:
                    a_verifier.append(f"Implantation en {c.libelle} (souhaité) : implanté·e à {p.commune}")
            elif c.type == "langue":
                if c.valeur in p.langues:
                    preuves.append(Preuve(critere=f"Parle {c.libelle}", champ="langues", extrait=c.valeur, nature="declare"))
                    score += 0.1
                elif not c.obligatoire:
                    a_verifier.append(f"{c.libelle.capitalize()} (souhaité) : " + ("langues non renseignées" if not p.langues else "non indiqué"))

        reciprocite = None
        for r in p.recherche:
            if r.concept and any(tax.meme_famille(r.concept, s) for s in demandeur.secteurs):
                reciprocite = Preuve(critere="Réciprocité", champ="recherche", extrait=r.texte, nature="declare")
                score += 0.1
                break

        score += 0.2 * tfidf.sim(besoin.texte, p.id)

        # Garde-fou : on retire toute preuve qui ne se retrouve pas mot pour mot dans le profil.
        preuves = [x for x in preuves if preuve_valide(p, x)]
        if reciprocite and not preuve_valide(p, reciprocite):
            reciprocite = None

        s = Suggestion(profil=_public(p), niveau="forte" if toutes_declarees else "partielle",
                       preuves=preuves, a_verifier=a_verifier, reciprocite=reciprocite, score=round(score, 4))
        (suggestions if pr_princ else pistes).append(s)

    suggestions.sort(key=lambda s: (-s.score, s.profil.nom))
    pistes.sort(key=lambda s: (-s.score, s.profil.nom))
    abstention = not suggestions
    message = ""
    if abstention:
        cible = principale.libelle if principale.type != "texte_libre" else f"« {principale.valeur} »"
        message = f"Aucune correspondance fiable pour {cible} parmi les membres disponibles."
        if pistes:
            message += " Des pistes plus larges existent, sans garantie qu'elles couvrent votre besoin précis."
    return Resultat(
        mode=mode, suggestions=suggestions[:limite], abstention=abstention, message=message,
        pistes_elargies=pistes[:3] if abstention else [],
        ecartes=[Ecart(raison=r, nombre=n) for r, n in ecarts.most_common()],
        nb_profils_examines=examines, duree_ms=round((time.perf_counter() - t0) * 1000, 2),
    )


# Raisons d'exclusion qui touchent au consentement ou à la situation personnelle : jamais divulguées nominativement.
_RAISONS_OPAQUES = {"ne souhaite pas recevoir d'introductions", "indisponible actuellement"}


def expliquer(besoin: Besoin, demandeur: Profil, p: Profil, tax: Taxonomie, mode: str = "demo") -> Explication:
    """Explique, critère par critère, pourquoi `p` est (ou n'est pas) proposé pour `besoin`.

    Le VERDICT vient du même appel à `rechercher` que la liste de résultats (cohérence garantie) ;
    le tableau détaille les preuves. Si la raison relève du consentement ou de la disponibilité de la
    personne, on ne détaille rien (on ne révèle pas qu'un membre a refusé les introductions).
    """
    res = rechercher(besoin, demandeur, [demandeur, p], tax, mode=mode)
    if any(s.profil.id == p.id for s in res.suggestions):
        verdict = "propose"
    elif any(s.profil.id == p.id for s in res.pistes_elargies):
        verdict = "piste"
    else:
        verdict = "non_propose"
    pub = _public(p)
    raison = filtres_durs(besoin, demandeur, p, tax)
    if raison in _RAISONS_OPAQUES or raison in _RAISONS_SILENCIEUSES:
        return Explication(membre=pub, verdict="non_propose", opaque=True,
                           resume="Cette personne ne peut pas être proposée actuellement. Par respect de ses choix, "
                                  "le détail n'est pas communiqué.")
    lignes: list[LigneExplication] = []

    def ligne(c: Critere, statut: str, detail: str, preuve: Optional[Preuve] = None) -> None:
        if preuve is not None and not preuve_valide(p, preuve):
            preuve, statut, detail = None, "a_verifier", "preuve non retrouvée telle quelle dans le profil"
        lignes.append(LigneExplication(critere=c.libelle, type=c.type, obligatoire=c.obligatoire, statut=statut,
                                       detail=detail, preuve=preuve))

    for c in besoin.criteres:
        if c.type == "expertise":
            pr = couverture(p, c.valeur, tax, besoin)
            if pr and pr.nature == "declare":
                ligne(c, "verifie", "offre déclarée dans son profil", pr)
            elif pr:
                ligne(c, "a_verifier", "mentionné dans sa présentation, pas déclaré comme offre", pr)
            elif (par := couverture_parent(p, c.valeur, tax)):
                ligne(c, "a_verifier", f"couvre la catégorie plus large « {par[0].critere} », pas forcément votre besoin précis", par[0])
            else:
                ligne(c, "non_satisfait", "aucune offre ni présentation ne le mentionne")
        elif c.type == "texte_libre":
            pr = couverture_textuelle(p, c, besoin, tax)
            ligne(c, "a_verifier", "mots de votre besoin retrouvés dans une offre (hors catalogue)", pr) if pr else \
                ligne(c, "non_satisfait", "mots de votre besoin absents de ses offres")
        elif c.type == "zone":
            if c.valeur in p.zones_service:
                ligne(c, "verifie", "zone d'intervention déclarée",
                      Preuve(critere=f"Intervient en : {c.libelle}", champ="zones_service", extrait=c.valeur, nature="declare"))
            else:
                ligne(c, "non_satisfait" if c.obligatoire else "a_verifier",
                      "zone d'intervention non renseignée" if not p.zones_service else "n'intervient pas dans cette zone")
        elif c.type == "implantation":
            z = tax.zone_de_commune(p.commune)
            if z == c.valeur:
                ligne(c, "verifie", f"implanté·e à {p.commune}",
                      Preuve(critere=f"Implanté·e en : {c.libelle}", champ="commune", extrait=p.commune, nature="declare"))
            else:
                ligne(c, "non_satisfait" if c.obligatoire else "a_verifier", f"implanté·e à {p.commune}")
        elif c.type == "langue":
            if c.valeur in p.langues:
                ligne(c, "verifie", "langue déclarée",
                      Preuve(critere=f"Parle {c.libelle}", champ="langues", extrait=c.valeur, nature="declare"))
            else:
                ligne(c, "non_satisfait" if c.obligatoire else "a_verifier",
                      "langues non renseignées" if not p.langues else "langue non indiquée")
    for e in besoin.exclusions:
        if any(o.concept and tax.couvre(o.concept, e.valeur) for o in p.offre):
            lignes.append(LigneExplication(critere=f"Sans : {e.libelle}", type="exclusion", obligatoire=True,
                                           statut="a_verifier", detail="propose aussi ce que vous avez écarté ; seules ses autres offres comptent"))
    if besoin.exclure_concurrents:
        conc = any(tax.meme_famille(a, b) for a in p.secteurs for b in demandeur.secteurs)
        lignes.append(LigneExplication(critere="Pas un concurrent", type="concurrence", obligatoire=True,
                                       statut="non_satisfait" if conc else "verifie",
                                       detail="même secteur que vous" if conc else "secteur différent du vôtre"))
    if p.type == "exposant" and not besoin.inclure_exposants:
        lignes.append(LigneExplication(critere="Membre du Club", type="communaute", obligatoire=True, statut="non_satisfait",
                                       detail="exposant de la Foire, non inclus dans votre recherche"))

    n = Counter(l.statut for l in lignes)
    bilan = f"{n['verifie']} vérifié(s), {n['a_verifier']} à vérifier, {n['non_satisfait']} non satisfait(s)"
    if verdict == "propose":
        resume = f"Proposé·e : {bilan}."
    elif verdict == "piste":
        resume = f"Piste plus large seulement : {bilan}."
    else:
        bloquant = next((l for l in lignes if l.statut == "non_satisfait" and l.obligatoire), None)
        resume = f"Non proposé·e : {bloquant.critere.lower()} — {bloquant.detail}." if bloquant else f"Non proposé·e : {bilan}."
        if not bloquant and res.abstention and not besoin.criteres:
            resume = "Non proposé·e : aucune compétence reconnue dans le besoin."
    return Explication(membre=pub, verdict=verdict, resume=resume, lignes=lignes)
