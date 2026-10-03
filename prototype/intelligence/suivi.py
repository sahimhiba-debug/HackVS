"""SUIVI (Foire 2026, A) — ce que le Club ne savait jamais : où en sont les partenariats entre membres.

Calculé à la lecture, DEPUIS LE JOURNAL (rien n'est écrit en lisant), pour une période : toute la démonstration, les
7 derniers jours ou le trimestre (90 jours) — de l'horloge du monde (simulée en démonstration).

Règles de confidentialité, testées :
- AGRÉGATS seulement : la charge utile ne contient ni nom, ni identifiant de membre, ni texte d'offre, ni note — sauf
  une ligne nominative pour un partenariat dont LES DEUX parties ont activé « visible par le Club » ;
- k = 3 : tout décompte de PERSONNES inférieur à k (Reglages.k_anonymat) s'affiche « < 3 » — un total comme une
  catégorie. Les décomptes de DEMANDES (une pièce qui manque, un métier) ne désignent personne et sont dits tels quels.
- Ce qu'on ne suit JAMAIS : vues, inscrits inactifs, « matchs » proposés par une IA."""
from __future__ import annotations

import statistics
from collections import Counter
from datetime import date, timedelta
from typing import TYPE_CHECKING, Optional, Union

from .erreurs import Invalide
from .partenariats import CLUB, ETAPES, RESULTATS, demandes_repondues, recus_du_club

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

PERIODES = {"demo": None, "7j": 7, "trimestre": 90}
LIBELLES_PERIODE = {"demo": "toute la démonstration", "7j": "7 derniers jours", "trimestre": "trimestre (90 jours)"}
Nombre = Union[int, str]


def _k(n: int, k: int) -> Nombre:
    """Un décompte de personnes sous le seuil n'est jamais dit : « < 3 » (0 reste 0 : personne n'est désigné)."""
    return f"< {k}" if 0 < n < k else n


def _pct(n: int, total: int) -> Optional[int]:
    return round(100 * n / total) if total else None


def calculer(c: "ClubPulse", periode: str = "demo") -> dict:
    if periode not in PERIODES:
        raise Invalide("période inconnue : demo, 7j ou trimestre")
    k, jour = c.reglages.k_anonymat, c.jour
    n = PERIODES[periode]
    debut: Optional[date] = None if n is None else jour - timedelta(days=n)
    dans = (lambda e: True) if debut is None else (lambda e: e.le >= debut)   # noqa: E731

    reponses = [e for e in c.journal.evenements("ASK_REPONSE") if dans(e)]
    nuances = {(e.acteurs[0], e.donnees["ask"]) for e in c.journal.evenements("REPONSE_NUANCE")
               if e.donnees.get("choix") == "pas cette fois"}
    oui = [e for e in reponses if e.donnees["oui"]]
    pas_cette_fois = [e for e in reponses if not e.donnees["oui"] and (e.acteurs[0], e.donnees["ask"]) in nuances]
    non = [e for e in reponses if not e.donnees["oui"] and (e.acteurs[0], e.donnees["ask"]) not in nuances]
    ouvertes = [i for i in c.projection_capacites() if i.ask is not None]
    encore = demandes_repondues(c)                  # un retrait rouvre la demande : sa réponse d'avant ne compte plus
    sans_reponse = [i for i in ouvertes if i.ask and i.ask.id not in encore]
    # demandes adressées : chaque réponse de la période en est une, et chaque demande encore sans réponse aussi
    adressees = len(reponses) + len(sans_reponse)
    total_rep = len(reponses) + len(sans_reponse)

    # délai avant le premier oui (jours de l'horloge du monde) : de la naissance de la demande — le début du monde, ou le
    # dernier retrait sur cette capacité qui l'a rouverte — au premier oui qui la comble
    semis = c.journal.evenements("SEMIS")[0].le
    delais = []
    for e in oui:
        f = e.donnees["ask"].split(":", 1)[0]
        avant = [x.le for x in c.journal.evenements("RETRAIT") if x.donnees.get("finalite") == f and x.seq < e.seq]
        delais.append((e.le - max([semis, *avant])).days)
    delai = statistics.median(delais) if len(delais) >= k else None

    recus = recus_du_club(c)
    recus_p = [r for r in recus if debut is None or date.fromisoformat(r["donne_le"]) >= debut]
    par_etape = Counter(r["etape"] for r in recus_p)
    clotures = [e for e in c.journal.evenements("CLOTURE") if dans(e)]
    par_resultat = {res: _k(len({e.acteurs[0] for e in clotures if e.donnees["resultat"] == res}), k) for res in RESULTATS}

    # métiers manquants : les demandes restées sans réponse, par rôle (une pièce, jamais une personne)
    manquants = Counter(next(e.role for e in c.capacites.patron(i.finalite).emplacements if e.id == i.ask.emplacement)  # type: ignore[union-attr]
                        for i in sans_reponse)

    actifs = {e.acteurs[0] for e in reponses} | {e.acteurs[0] for e in c.journal.evenements("ACCORD") if dans(e) and e.acteurs}
    invites = getattr(c, "decouverte", None)
    zones = getattr(c, "zones_membres", None)
    nominatif = [{"titre": r["titre"], "piece": r["piece"], "etape": r["etape"],
                  "resultat": (r["cloture"] or {}).get("resultat"), "note": (r["cloture"] or {}).get("note"),
                  "membre": (c.coffre.identite(r["membre"]).nom if c.coffre.identite(r["membre"]) else "—")}  # type: ignore[union-attr]
                 for r in recus_p if {"membre", CLUB} <= set(r["visible"])]
    return {
        "periode": periode, "periode_libelle": LIBELLES_PERIODE[periode], "du": debut.isoformat() if debut else semis.isoformat(),
        "au": jour.isoformat(), "k": k, "monde": "monde de démonstration", "fictif": True,
        "demandes": {"adressees": adressees, "ouvertes": len(ouvertes), "sans_reponse": len(sans_reponse)},
        "reponses": {"oui": _k(len(oui), k), "non": _k(len(non), k), "pas_cette_fois": _k(len(pas_cette_fois), k),
                     "sans_reponse": len(sans_reponse),
                     "pourcentages": {"oui": _pct(len(oui), total_rep) if len(oui) >= k or not oui else None,
                                      "sans_reponse": _pct(len(sans_reponse), total_rep)}},
        "delai_premier_oui_jours": delai,
        "delai_note": None if delai is not None else f"moins de {k} oui dans la période : non affiché",
        # une demande ouverte ne désigne personne : dite telle quelle ; les étapes suivantes sont des personnes (k)
        "partenariats_par_etape": {"demande": len(sans_reponse)}
                                  | {et: _k(par_etape.get(et, 0), k) for et in (*ETAPES[1:], "retire")},
        "resultats": par_resultat,
        "metiers_manquants": [{"metier": m, "demandes": n} for m, n in manquants.most_common()],
        "membres_actifs": _k(len(actifs), k),
        "hors_valais": zones(debut, k) if callable(zones) else "zone non renseignée",
        "invites": invites.statistiques(debut, k) if invites is not None else {"actifs": 0, "ont_contribue": 0, "intentions_adhesion": 0},
        "nominatif": nominatif,
        "regles": f"Agrégats seulement. Tout décompte de personnes sous {k} s'affiche « < {k} ». Une ligne nominative "
                  "n'apparaît que si les deux parties l'ont permis. Jamais suivi : vues, inscrits inactifs, « matchs » IA.",
    }
