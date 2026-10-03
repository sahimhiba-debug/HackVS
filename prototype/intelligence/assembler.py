"""« CE QUE VOTRE CLUB POURRAIT ASSEMBLER » (liste du Club, 3 octobre) — neuf capacités types, croisées avec les métiers
PRÉSENTS dans la liste des entreprises du Club (`docs/data/entreprises.csv`, colonne métier seule).

Une capacité est « assemblable » si chacune de ses pièces trouve au moins une entreprise d'un métier qui la tient. C'est
ce que la LISTE dit que le Club pourrait faire — pas ce qu'il peut faire cette semaine (disponibilités, accords) : ça,
c'est Club Pulse. Agrégats seulement : aucun nom ; un décompte d'entreprises sous k s'affiche « < k ». La classification
des métiers vient de l'équipe et reste À CONFIRMER avec le Club."""
from __future__ import annotations

from typing import Optional, Union

from . import metiers

Nombre = Union[int, str]
SOURCE = "d'après la liste du Club, classification à confirmer"
PHRASE = "Votre liste dit ce que le Club pourrait faire. Club Pulse dit ce qu'il peut faire cette semaine."

# (id, libellé, [(pièce, métiers qui la tiennent)])
CAPACITES: list[tuple[str, str, list[tuple[str, tuple[str, ...]]]]] = [
    ("evenement", "Événement d'entreprise", [("lieu", ("hebergement", "tourisme", "salle")), ("repas", ("traiteur",)),
                                             ("organisation", ("evenementiel",)), ("communication", ("communication", "impression"))]),
    ("delegation", "Accueil d'une délégation germanophone", [("transport", ("transport",)), ("lieu", ("hebergement", "salle")),
                                                             ("interprète", ("interprete",))]),
    ("renovation", "Rénovation", [("travaux", ("construction",)), ("bien", ("immobilier",)), ("financement", ("finance",))]),
    ("stand", "Stand à la Foire", [("construction du stand", ("construction",)), ("signalétique", ("impression",)),
                                   ("animation", ("evenementiel", "communication"))]),
    ("creation", "Création d'entreprise", [("statuts", ("juridique",)), ("comptabilité", ("comptabilite",)),
                                           ("financement", ("finance",)), ("accompagnement", ("conseil", "formation"))]),
    ("mondiaux", "Renfort pour les Mondiaux", [("personnel", ("rh",)), ("hébergement", ("hebergement",)),
                                               ("transport", ("transport",)), ("accueil", ("tourisme", "evenementiel"))]),
    ("terroir", "Produit du terroir", [("production", ("agriculture",)), ("vente", ("commerce",)),
                                       ("acheminement", ("logistique", "transport")), ("mise en valeur", ("communication",))]),
    ("sejour", "Séjour premium", [("hébergement", ("hebergement",)), ("table", ("traiteur",)), ("activités", ("tourisme",)),
                                  ("transferts", ("transport",))]),
    ("digital", "Digitalisation d'une PME", [("outils", ("informatique",)), ("formation", ("formation",)),
                                             ("accompagnement", ("conseil",))]),
]


def _k(n: int, k: int) -> Nombre:
    return f"< {k}" if 0 < n < k else n


def calculer(par_metier: Optional[dict[str, int]], k: int = 3) -> dict:
    """`par_metier` : décompte d'ENTREPRISES par métier (club_cherche.entreprises_par_metier) ; None : liste absente."""
    if par_metier is None:
        return {"disponible": False, "note": "liste du Club absente (docs/data/entreprises.csv)", "source": SOURCE}
    libelle = {m["id"]: m["fr"] for m in metiers.metiers()}
    res: list[dict] = []
    for cid, titre, pieces in CAPACITES:
        detail: list[dict] = []
        for piece, ms in pieces:
            n = sum(par_metier.get(m, 0) for m in ms)
            detail.append({"piece": piece, "metiers": [libelle.get(m, m) for m in ms], "entreprises": _k(n, k), "couverte": n > 0})
        manque = [d["piece"] for d in detail if not d["couverte"]]
        res.append({"id": cid, "titre": titre, "assemblable": not manque, "manque": manque, "pieces": detail})
    ok = sum(1 for x in res if x["assemblable"])
    return {"disponible": True, "assemblables": ok, "total": len(res), "capacites": res, "source": SOURCE, "phrase": PHRASE,
            "regle": f"Agrégats seulement, aucun nom. Un décompte d'entreprises sous {k} s'affiche « < {k} »."}


def absents_et_rares(par_metier: Optional[dict[str, int]], k: int = 3) -> dict:
    """« Le Club cherche », d'après la liste : métiers ABSENTS (0 entreprise) et RARES (1 ou 2 : « < 3 »)."""
    if par_metier is None:
        return {"disponible": False}
    libelle = {m["id"]: m["fr"] for m in metiers.metiers() if m["id"] != "autre"}
    absents = [libelle[m] for m in libelle if par_metier.get(m, 0) == 0]
    rares = [libelle[m] for m in libelle if 0 < par_metier.get(m, 0) < k]
    return {"disponible": True, "absents": absents, "rares": rares, "rares_affiche": f"< {k} entreprises", "source": SOURCE}


REPRESENTANTS = 173   # communiqué par le Club avec la liste (3 octobre 2026) ; la liste elle-même ne compte que les entreprises


def chiffres(liste: Optional[dict]) -> Optional[dict]:
    """« Votre Club en chiffres » : entreprises (lignes de la liste) et représentants (chiffre communiqué par le Club)."""
    if not liste:
        return None
    return {"entreprises": liste["lignes"], "representants": REPRESENTANTS, "source": "liste fournie par le Club (3 octobre 2026)"}
