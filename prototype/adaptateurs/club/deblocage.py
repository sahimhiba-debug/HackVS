"""Débloquer une demande : l'unité de valeur est une demande DÉBLOQUÉE, pas une recommandation.

demande (texte + prochaine étape définie par le demandeur)
  → étapes (une par compétence comprise, chacune avec l'extrait qui la justifie)
  → plan de contributions (le plus petit nombre de personnes qui couvre les étapes ; une réserve silencieuse par étape)
  → sollicitations PRIVÉES (chaque personne ne voit que son étape, sans savoir qui demande)
  → accord → contribution (une ressource, une introduction, un conseil)
  → le DEMANDEUR confirme l'effet (débloqué / partiel / non) — seule cette confirmation compte
  → mémoire vérifiée : une contribution confirmée et réutilisable répond à la prochaine demande semblable, sans
    redéranger personne.

Garde-fous : une question n'est posée que si ses réponses changent le plan (valeur de l'information) ; une étape
non couverte dit QUELLE contrainte l'empêche et la plus petite levée qui la débloquerait ; un refus n'est jamais
révélé au demandeur ; le consentement, les preuves et les filtres viennent du moteur existant (`app.matching`).
Tout est dérivé d'événements immuables (`plateforme.memoire`) : rien n'est stocké deux fois.
"""
from __future__ import annotations

import hashlib
from datetime import date
from typing import Optional

from app.matching import rechercher
from app.models import Besoin, Critere, Profil
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

TYPES = ("DEMANDE_OUVERTE", "SOLLICITATION", "SOLLICITATION_ACCEPTEE", "SOLLICITATION_DECLINEE", "CONTRIBUTION",
         "EFFET_CONFIRME", "REUTILISATION")
VERDICTS = ("debloque", "partiel", "non")
NATURES = ("ressource", "introduction", "conseil")
REUTILISATIONS = ("club", "non")          # « club » : réutilisable par d'autres membres ; « non » : pour ce demandeur seul
MAX_SOLLICITATIONS_OUVERTES = 2           # budget d'attention par membre (hypothèse de produit)


class ErreurDeblocage(ValueError):
    pass


def _id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:10]


# ------------------------------------------------------------------ comprendre : étapes et contraintes partagées
def etapes(besoin: Besoin) -> list[dict]:
    """Une étape par compétence comprise (dédoublonnée), avec l'extrait de la phrase qui la justifie."""
    vues: set[str] = set()
    res: list[dict] = []
    for c in besoin.criteres:
        if c.type in ("expertise", "texte_libre") and c.valeur not in vues:
            vues.add(c.valeur)
            res.append({"id": f"e{len(res) + 1}", "type": c.type, "concept": c.valeur, "libelle": c.libelle,
                        "extrait": c.extrait})
    return res


def contraintes(besoin: Besoin) -> list[dict]:
    """Contraintes appliquées à TOUTES les étapes (limite déclarée : une langue ne peut pas encore viser une seule étape)."""
    res = [{"cle": f"{c.type}:{c.valeur}", "libelle": f"{c.type} : {c.libelle}", "extrait": c.extrait}
           for c in besoin.criteres if c.type in ("langue", "zone", "implantation")]
    if besoin.exclure_concurrents:
        res.append({"cle": "concurrents", "libelle": "pas un concurrent direct", "extrait": None})
    return res


def _besoin_etape(besoin: Besoin, etape: dict, sans: Optional[str] = None) -> Besoin:
    principal = next(c for c in besoin.criteres if c.type == etape["type"] and c.valeur == etape["concept"])
    autres = [c for c in besoin.criteres if c.type in ("langue", "zone", "implantation") and f"{c.type}:{c.valeur}" != sans]
    return Besoin(texte=besoin.texte, criteres=[principal.model_copy(update={"obligatoire": True}), *autres],
                  exclusions=besoin.exclusions, exclure_concurrents=besoin.exclure_concurrents and sans != "concurrents")


def candidats(besoin: Besoin, etape: dict, demandeur: Profil, profils: list[Profil], tax, sans: Optional[str] = None) -> list[dict]:
    r = rechercher(_besoin_etape(besoin, etape, sans), demandeur, profils, tax, limite=len(profils))
    return [{"id": s.profil.id, "nom": s.profil.nom, "niveau": s.niveau, "score": s.score,
             "preuve": s.preuves[0].extrait if s.preuves else "", "nature": s.preuves[0].nature if s.preuves else ""}
            for s in r.suggestions]


def levee_minimale(besoin: Besoin, etape: dict, demandeur: Profil, profils: list[Profil], tax) -> dict:
    """Étape non couverte : quelle contrainte l'empêche, et la plus petite levée qui la débloquerait.
    Des COMPTES seulement (jamais de nom avant accord) ; qui refuse les introductions n'est jamais compté."""
    levees = []
    for c in contraintes(besoin):
        n = len(candidats(besoin, etape, demandeur, profils, tax, sans=c["cle"]))
        if n:
            levees.append({"sans": c["libelle"], "personnes": n})
    if levees:
        return {"raison": "une contrainte écarte toutes les personnes qui déclarent cette compétence", "levees": levees}
    return {"raison": "aucun membre disponible ne déclare cette compétence : c'est un manque du Club", "levees": []}


def question_decisive(besoin: Besoin, demandeur: Profil, profils: list[Profil], tax) -> Optional[dict]:
    """Ne pose une question que si ses réponses possibles changent le plan (ensembles de personnes différents).
    Sinon None : aucune question décorative."""
    for a in besoin.ambiguites:
        branches = []
        for o in a.options:
            b = besoin.model_copy(update={"criteres": [Critere(type="expertise", valeur=o.valeur, libelle=o.libelle,
                                                                obligatoire=True, extrait=a.extrait), *besoin.criteres],
                                          "ambiguites": []})
            e = {"type": "expertise", "concept": o.valeur}
            branches.append((o, frozenset(x["id"] for x in candidats(b, e, demandeur, profils, tax))))
        if len({ids for _, ids in branches}) > 1:
            return {"terme": a.terme, "extrait": a.extrait,
                    "options": [{"valeur": o.valeur, "libelle": o.libelle, "personnes": len(ids)} for o, ids in branches],
                    "pourquoi": "selon votre réponse, ce ne sont pas les mêmes personnes qui peuvent vous aider"}
    return None


def charge(m: Memoire) -> dict[str, int]:
    """Sollicitations sans réponse, par membre (budget d'attention)."""
    repondues = {(e.acteurs[0], e.donnees["demande_id"], e.donnees["etape_id"])
                 for e in m.evenements("SOLLICITATION_ACCEPTEE", "SOLLICITATION_DECLINEE")}
    res: dict[str, int] = {}
    for e in m.evenements("SOLLICITATION"):
        if (e.acteurs[0], e.donnees["demande_id"], e.donnees["etape_id"]) not in repondues:
            res[e.acteurs[0]] = res.get(e.acteurs[0], 0) + 1
    return res


def plan(besoin: Besoin, demandeur: Profil, profils: list[Profil], tax, occupes: Optional[dict[str, int]] = None) -> dict:
    """Le plus petit ensemble de personnes qui couvre les étapes (glouton de couverture, déterministe) ; une réserve
    par étape, contactée seulement si la première personne décline ; budget d'attention respecté."""
    occupes = occupes or {}
    etps = etapes(besoin)
    par_etape = {e["id"]: [c for c in candidats(besoin, e, demandeur, profils, tax)
                           if occupes.get(c["id"], 0) < MAX_SOLLICITATIONS_OUVERTES] for e in etps}
    a_couvrir, choix = {e["id"] for e in etps if par_etape[e["id"]]}, {}
    while a_couvrir:
        couverture: dict[str, list[str]] = {}
        for eid in sorted(a_couvrir):
            for c in par_etape[eid]:
                couverture.setdefault(c["id"], []).append(eid)
        meilleur = min(couverture, key=lambda pid: (-len(couverture[pid]),
                                                    -sum(1 for eid in couverture[pid] for c in par_etape[eid]
                                                         if c["id"] == pid and c["niveau"] == "forte"),
                                                    -sum(c["score"] for eid in couverture[pid] for c in par_etape[eid] if c["id"] == pid),
                                                    pid))
        for eid in couverture[meilleur]:
            choix[eid] = meilleur
        a_couvrir -= set(couverture[meilleur])
    lignes = []
    for e in etps:
        cands = par_etape[e["id"]]
        if not cands:
            lignes.append(e | {"principal": None, "reserve": None, "manque": levee_minimale(besoin, e, demandeur, profils, tax)})
            continue
        principal = next(c for c in cands if c["id"] == choix[e["id"]])
        reserve = next((c for c in cands if c["id"] != principal["id"]), None)
        lignes.append(e | {"principal": principal, "reserve": reserve, "manque": None})
    personnes = sorted({x["principal"]["id"] for x in lignes if x["principal"]})
    return {"etapes": lignes, "contraintes": contraintes(besoin), "personnes_sollicitees": len(personnes),
            "personnes": personnes, "membres_non_derange": len([p for p in profils if p.type == "membre_club"
                                                                and p.id not in personnes and p.id != demandeur.id]),
            "couverture": f"{sum(1 for x in lignes if x['principal'])}/{len(lignes)}"}


# ------------------------------------------------------------------ événements : ouvrir, solliciter, contribuer, confirmer
def _dem(m: Memoire, demande_id: str) -> Evt:
    e = next((x for x in m.evenements("DEMANDE_OUVERTE") if x.donnees["demande_id"] == demande_id), None)
    if e is None:
        raise ErreurDeblocage("demande inconnue")
    return e


def ouvrir(m: Memoire, le: date, demandeur: str, texte: str, prochaine_etape: str, besoin: Besoin,
           anonyme: bool = True, secteur: Optional[str] = None, statut: Statut = Statut.SIMULE) -> str:
    if not prochaine_etape.strip():
        raise ErreurDeblocage("indiquez la prochaine étape qui dirait « c'est débloqué »")
    etps = etapes(besoin)
    if not etps:
        raise ErreurDeblocage("aucune étape comprise : précisez ce qui vous manque")
    did = "d" + _id(demandeur, texte, le.isoformat(), str(len(m.evenements("DEMANDE_OUVERTE"))))
    m.ajouter(Evt(type="DEMANDE_OUVERTE", le=le, acteurs=[demandeur], statut=statut,
                  donnees={"demande_id": did, "texte": texte, "prochaine_etape": prochaine_etape.strip(),
                           "besoin": besoin.model_dump(), "anonyme": anonyme, "secteur": secteur,
                           "etapes": etps}))
    return did


def solliciter(m: Memoire, le: date, demande_id: str, etape_id: str, membre: str, candidats_autorises: set[str]) -> None:
    """Seulement une personne que le plan a retenue sur preuve (et qui accepte les introductions) ; budget respecté."""
    dem = _dem(m, demande_id)
    if etape_id not in {e["id"] for e in dem.donnees["etapes"]}:
        raise ErreurDeblocage("étape inconnue")
    if membre == dem.acteurs[0]:
        raise ErreurDeblocage("on ne se sollicite pas soi-même")
    if membre not in candidats_autorises:
        raise ErreurDeblocage("cette personne n'est pas une contributrice prouvée pour cette étape")
    if charge(m).get(membre, 0) >= MAX_SOLLICITATIONS_OUVERTES:
        raise ErreurDeblocage("budget d'attention atteint pour cette personne")
    if any(e.donnees["demande_id"] == demande_id and e.donnees["etape_id"] == etape_id and e.acteurs[0] == membre
           for e in m.evenements("SOLLICITATION")):
        raise ErreurDeblocage("déjà sollicitée pour cette étape")
    m.ajouter(Evt(type="SOLLICITATION", le=le, acteurs=[membre], statut=dem.statut,
                  donnees={"demande_id": demande_id, "etape_id": etape_id}))


def repondre(m: Memoire, le: date, demande_id: str, etape_id: str, membre: str, accepte: bool) -> None:
    dem = _dem(m, demande_id)
    if not any(e.donnees["demande_id"] == demande_id and e.donnees["etape_id"] == etape_id and e.acteurs[0] == membre
               for e in m.evenements("SOLLICITATION")):
        raise ErreurDeblocage("seule une personne sollicitée peut répondre")
    if any(e.donnees["demande_id"] == demande_id and e.donnees["etape_id"] == etape_id and e.acteurs[0] == membre
           for e in m.evenements("SOLLICITATION_ACCEPTEE", "SOLLICITATION_DECLINEE")):
        raise ErreurDeblocage("déjà répondu")
    m.ajouter(Evt(type="SOLLICITATION_ACCEPTEE" if accepte else "SOLLICITATION_DECLINEE", le=le, acteurs=[membre],
                  statut=dem.statut, donnees={"demande_id": demande_id, "etape_id": etape_id}))


def contribuer(m: Memoire, le: date, demande_id: str, etape_id: str, membre: str, nature: str, titre: str,
               contenu: str, reutilisation: str = "non", attribution: bool = False) -> str:
    dem = _dem(m, demande_id)
    if nature not in NATURES or reutilisation not in REUTILISATIONS:
        raise ErreurDeblocage("nature ou portée de réutilisation inconnue")
    if not any(e.donnees["demande_id"] == demande_id and e.donnees["etape_id"] == etape_id and e.acteurs[0] == membre
               for e in m.evenements("SOLLICITATION_ACCEPTEE")):
        raise ErreurDeblocage("contribuer suppose d'avoir accepté la sollicitation")
    if not titre.strip() or not contenu.strip():
        raise ErreurDeblocage("une contribution a un titre et un contenu")
    cid = "c" + _id(demande_id, etape_id, membre)
    m.ajouter(Evt(type="CONTRIBUTION", le=le, acteurs=[membre], statut=dem.statut,
                  donnees={"demande_id": demande_id, "etape_id": etape_id, "contribution_id": cid, "nature": nature,
                           "titre": titre.strip()[:120], "contenu": contenu.strip()[:4000], "reutilisation": reutilisation,
                           "attribution": attribution}))
    return cid


def _contribution(m: Memoire, cid: str) -> Evt:
    e = next((x for x in m.evenements("CONTRIBUTION") if x.donnees["contribution_id"] == cid), None)
    if e is None:
        raise ErreurDeblocage("contribution inconnue")
    return e


def reutiliser(m: Memoire, le: date, demande_id: str, contribution_id: str, demandeur: str) -> None:
    """Réponse depuis la mémoire vérifiée : personne n'est dérangé. Seulement une contribution confirmée ET réutilisable."""
    dem = _dem(m, demande_id)
    if dem.acteurs[0] != demandeur:
        raise ErreurDeblocage("seul le demandeur peut utiliser une réponse pour sa demande")
    if contribution_id not in {x["contribution_id"] for x in memoire_verifiee(m)}:
        raise ErreurDeblocage("seule une contribution confirmée et réutilisable peut répondre à une autre demande")
    m.ajouter(Evt(type="REUTILISATION", le=le, acteurs=[demandeur], statut=dem.statut,
                  donnees={"demande_id": demande_id, "contribution_id": contribution_id}))


def confirmer(m: Memoire, le: date, demande_id: str, contribution_id: str, demandeur: str, verdict: str) -> None:
    """Seul le DEMANDEUR confirme, et seulement une contribution reçue pour SA demande (directe ou réutilisée)."""
    dem = _dem(m, demande_id)
    if dem.acteurs[0] != demandeur:
        raise ErreurDeblocage("seul le demandeur confirme l'effet")
    if verdict not in VERDICTS:
        raise ErreurDeblocage("verdict inconnu")
    c = _contribution(m, contribution_id)
    recue = c.donnees["demande_id"] == demande_id or any(
        e.donnees["demande_id"] == demande_id and e.donnees["contribution_id"] == contribution_id
        for e in m.evenements("REUTILISATION"))
    if not recue:
        raise ErreurDeblocage("cette contribution n'a pas été reçue pour cette demande")
    if any(e.donnees["demande_id"] == demande_id and e.donnees["contribution_id"] == contribution_id
           for e in m.evenements("EFFET_CONFIRME")):
        raise ErreurDeblocage("effet déjà confirmé")
    m.ajouter(Evt(type="EFFET_CONFIRME", le=le, acteurs=[demandeur], statut=dem.statut,
                  donnees={"demande_id": demande_id, "contribution_id": contribution_id, "verdict": verdict}))


# ------------------------------------------------------------------ états (dérivés, jamais stockés)
def etat(m: Memoire, demande_id: str) -> dict:
    dem = _dem(m, demande_id)
    contribs = [e for e in m.evenements("CONTRIBUTION") if e.donnees["demande_id"] == demande_id]
    reutil = [e.donnees["contribution_id"] for e in m.evenements("REUTILISATION") if e.donnees["demande_id"] == demande_id]
    effets = {e.donnees["contribution_id"]: e.donnees["verdict"] for e in m.evenements("EFFET_CONFIRME")
              if e.donnees["demande_id"] == demande_id}
    etapes_res = []
    for e in dem.donnees["etapes"]:
        ids = [c.donnees["contribution_id"] for c in contribs if c.donnees["etape_id"] == e["id"]]
        ids += [cid for cid in reutil if _concept(m, cid) == e["concept"]]
        verdicts = [effets[c] for c in ids if c in effets]
        statut = ("DEBLOQUEE" if "debloque" in verdicts else "PARTIELLE" if "partiel" in verdicts
                  else "NON_DEBLOQUEE" if verdicts else "CONTRIBUTION_RECUE" if ids else "EN_ATTENTE")
        etapes_res.append({"id": e["id"], "libelle": e["libelle"], "statut": statut, "contributions": ids})
    statuts = {x["statut"] for x in etapes_res}
    global_ = ("DEBLOQUEE" if statuts == {"DEBLOQUEE"} else "PARTIELLEMENT_DEBLOQUEE" if statuts & {"DEBLOQUEE", "PARTIELLE"}
               else "EN_COURS" if statuts & {"CONTRIBUTION_RECUE"} or any(x.donnees["demande_id"] == demande_id
                                                                   for x in m.evenements("SOLLICITATION")) else "OUVERTE")
    return {"demande_id": demande_id, "etat": global_, "etapes": etapes_res, "prochaine_etape": dem.donnees["prochaine_etape"],
            "par_memoire": bool(reutil)}


def _concept(m: Memoire, cid: str) -> str:
    c = _contribution(m, cid)
    dem = _dem(m, c.donnees["demande_id"])
    return next(e["concept"] for e in dem.donnees["etapes"] if e["id"] == c.donnees["etape_id"])


# ------------------------------------------------------------------ mémoire vérifiée (apprendre sans entraîner)
def memoire_verifiee(m: Memoire) -> list[dict]:
    """Contributions RÉUTILISABLES dont au moins un demandeur a confirmé un effet (débloqué ou partiel).
    Le demandeur d'origine n'est jamais nommé ; le contributeur seulement s'il l'a accepté."""
    effets: dict[str, list[dict]] = {}
    for e in m.evenements("EFFET_CONFIRME"):
        effets.setdefault(e.donnees["contribution_id"], []).append({"le": e.le.isoformat(), "verdict": e.donnees["verdict"]})
    res = []
    for c in m.evenements("CONTRIBUTION"):
        d = c.donnees
        conf = [x for x in effets.get(d["contribution_id"], []) if x["verdict"] in ("debloque", "partiel")]
        if d["reutilisation"] != "club" or not conf:
            continue
        dem = _dem(m, d["demande_id"])
        res.append({"contribution_id": d["contribution_id"], "concept": _concept(m, d["contribution_id"]),
                    "titre": d["titre"], "contenu": d["contenu"], "nature": d["nature"],
                    "auteur": c.acteurs[0] if d["attribution"] else None, "confirmations": conf,
                    "contexte": {"prochaine_etape": dem.donnees["prochaine_etape"], "demande_le": dem.le.isoformat(),
                                 "secteur": dem.donnees.get("secteur")}})
    return res


def chercher_en_memoire(m: Memoire, besoin: Besoin, secteur_demandeur: Optional[str] = None) -> list[dict]:
    """Pour chaque étape, une contribution vérifiée sur la même compétence — avec ce qui DIFFÈRE du contexte d'origine."""
    memo = memoire_verifiee(m)
    res = []
    for e in etapes(besoin):
        for x in memo:
            if x["concept"] != e["concept"]:
                continue
            sect_origine = x["contexte"]["secteur"]
            differences = []
            if secteur_demandeur and sect_origine and secteur_demandeur != sect_origine:
                differences.append(f"confirmée pour le secteur « {sect_origine} », le vôtre est « {secteur_demandeur} » : à vérifier")
            res.append({"etape": e["id"], "etape_libelle": e["libelle"], **x, "differences": differences})
    return res


# ------------------------------------------------------------------ vues : ce que chacun a le droit de voir
def vue_sollicitation(m: Memoire, demande_id: str, membre: str, profils: list[Profil]) -> dict:
    """Ce que voit une personne sollicitée : SON étape, la prochaine étape visée, jamais les autres étapes ni les
    autres personnes ; le demandeur n'est nommé qu'après son accord, et seulement si la demande n'est pas anonyme."""
    dem = _dem(m, demande_id)
    mes = [e.donnees["etape_id"] for e in m.evenements("SOLLICITATION")
           if e.donnees["demande_id"] == demande_id and e.acteurs[0] == membre]
    if not mes:
        raise ErreurDeblocage("vous n'êtes pas sollicité(e) pour cette demande")
    accepte = any(e.donnees["demande_id"] == demande_id and e.acteurs[0] == membre
                  for e in m.evenements("SOLLICITATION_ACCEPTEE"))
    par_id = {p.id: p for p in profils}
    auteur = par_id.get(dem.acteurs[0])
    secteur = (auteur.secteurs or ["non précisé"])[0] if auteur else "non précisé"
    qui = auteur.nom if (accepte and not dem.donnees["anonyme"] and auteur) else f"Une personne du Club (secteur : {secteur})"
    return {"qui_demande": qui, "prochaine_etape": dem.donnees["prochaine_etape"],
            "vos_etapes": [e for e in dem.donnees["etapes"] if e["id"] in mes], "accepte": accepte}


def vue_demandeur(m: Memoire, demande_id: str, demandeur: str, profils: list[Profil]) -> dict:
    """Ce que voit le demandeur : où en est chaque étape. Une personne n'est nommée qu'après avoir ACCEPTÉ ; un refus
    n'est jamais révélé (« une autre personne a été sollicitée »)."""
    dem = _dem(m, demande_id)
    if dem.acteurs[0] != demandeur:
        raise ErreurDeblocage("seul le demandeur voit le suivi de sa demande")
    par_id = {p.id: p for p in profils}
    res = []
    for e in dem.donnees["etapes"]:
        sol = [x for x in m.evenements("SOLLICITATION") if x.donnees["demande_id"] == demande_id and x.donnees["etape_id"] == e["id"]]
        acc = [x.acteurs[0] for x in m.evenements("SOLLICITATION_ACCEPTEE")
               if x.donnees["demande_id"] == demande_id and x.donnees["etape_id"] == e["id"]]
        res.append({"etape": e["libelle"], "sollicitees": len(sol),
                    "a_accepte": [par_id[x].nom for x in acc if x in par_id],
                    "en_attente": len(sol) > len(acc) and not acc})
    return {"etapes": res, **{k: v for k, v in etat(m, demande_id).items() if k in ("etat", "prochaine_etape")}}
