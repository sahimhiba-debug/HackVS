"""Le monde de DÉMONSTRATION : un Club fictif de 150 membres, reproductible.

= le Club synthétique (graine 2026, situations plantées comprises) + les personnages lisibles de la scène
(`data/stage_reseau.json` : Sophie, Anna, Markus, Pauline, Stefan…) + un événement proche (salon de Munich, fictif).
Rien n'est réel : personnes, entreprises, besoins, rencontres et dates sont inventés, et l'interface le dit.

Ce que le monde CONTIENT (données) et ce que le moteur en DÉDUIT (calcul) sont séparés : aucune opportunité n'est
écrite ici ; elles sont toutes trouvées par `intelligence.detection` à chaque analyse.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from app.models import Offre, Profil
from app.taxonomy import DATA_DIR
from plateforme.affirmations import Statut
from plateforme.memoire import Evt

from .club_synthetique import AUJOURD_HUI, generer
from .modele import Evenement, Reseau

SOPHIE, ANNA, MARKUS, PAULINE, LEA = "n01", "s10", "s14", "s01", "d01"
SALON = "ev_munich"
TAILLE = 150
GRAINE = 2026


FOIRE = "Foire du Valais 2026 (fictive)"
RECHERCHES_SOPHIE = [Offre(concept="traduction", texte="Traduire nos étiquettes en allemand"),
                     Offre(concept=None, texte="Faire valider la conformité de nos étiquettes pour le marché allemand")]
# scène de la boucle complète : UN besoin, déclaré dans le profil de Sophie (fictif)
BESOIN_ALLEMAGNE = [Offre(concept="export_allemagne", texte="Trouver un distributeur pour entrer sur le marché allemand avec nos tisanes")]


def construire(sophie_profilee: bool = True, recherches: list[Offre] | None = None) -> Reseau:
    """`sophie_profilee=False` : Sophie vient d'activer son compte — ni capacités, ni intérêts, invisible par défaut.
    `recherches` : ce que Sophie déclare chercher (par défaut, la scène historique des étiquettes)."""
    d = json.loads((DATA_DIR / "stage_reseau.json").read_text(encoding="utf-8"))
    scene = [Profil(**p) for p in d["profils"]]
    s = d["sophie"]
    sophie = Profil(
        id=SOPHIE, nom=s["nom"], fonction=s["fonction"], entreprise=s["entreprise"], commune=s["commune"],
        type="membre_club", secteurs=["boissons"], offre=[Offre(**o) for o in s["offre"]],
        recherche=list(recherches if recherches is not None else RECHERCHES_SOPHIE) if sophie_profilee else [],
        langues=s["langues"], zones_service=s["zones_service"], creneaux=s["creneaux"], accepte_introductions=sophie_profilee,
        maj=d["debut"])
    if not sophie_profilee:
        sophie = sophie.model_copy(update={"offre": [], "secteurs": []})
    # une seconde traductrice : l'alternative si Anna décline — éligible, mais disponible seulement la semaine suivante
    lea = Profil(id=LEA, nom="Léa Imhof", fonction="Traductrice indépendante", entreprise="Imhof Übersetzungen (fictive)",
                 commune="Viège", type="membre_club", secteurs=["traduction"],
                 offre=[Offre(concept="traduction", texte="Traduction et relecture français–allemand, étiquettes et emballages")],
                 langues=["de", "fr"], zones_service=["Valais"], accepte_introductions=True,
                 creneaux=["jeu-apres-midi", "ven-matin"], maj=(AUJOURD_HUI - timedelta(days=45)).isoformat(),
                 note_disponibilite="disponible à partir du 12 novembre")
    fond, _ = generer(TAILLE - len(scene) - 2, GRAINE)
    profils = fond.profils + scene + [sophie, lea]
    m = fond.memoire
    for r in d["rencontres_passees"]:
        m.ajouter(Evt(type="RENCONTRE", le=date.fromisoformat(r["le"]), acteurs=sorted([r["a"], r["b"]]),
                      statut=Statut.SIMULE, donnees={"evenement": r["evenement"], "raisons": []}))
    m.ajouter(Evt(type="RENCONTRE", le=AUJOURD_HUI - timedelta(days=31), acteurs=sorted([SOPHIE, MARKUS]),
                  statut=Statut.SIMULE, donnees={"evenement": FOIRE, "raisons": []}))
    salon = Evenement(id=SALON, nom="Salon Bio de Munich (fictif)", le=AUJOURD_HUI + timedelta(days=12),
                      themes=("export_allemagne",), participants=tuple(sorted({SOPHIE, MARKUS, "s02", "s03"})))
    return Reseau(profils=profils, besoins=list(fond.besoins), evenements=[salon, *fond.evenements], memoire=m,
                  aujourd_hui=AUJOURD_HUI, nom=f"Club des Affaires — monde de démonstration FICTIF ({len(profils)} membres)")
