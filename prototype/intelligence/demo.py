"""Contrôleur de DÉMONSTRATION : une ACTION COLLECTIVE, faite d'appels RÉELS au service (aucun résultat écrit d'avance).

    BESOIN (les mots de Sophie) → EXIGENCES confirmées → PROPOSITION (le seul créneau où les offres se recouvrent)
    → ACCORDS (chacun sur son téléphone) → PERTURBATION (une disponibilité change, valeur choisie par le jury)
    → ADAPTATION (ce qui tombe, ce qui tient, qui reconfirme) → ACTION ENGAGÉE → FICHE transmise → RÉCEPTION confirmée
    → après l'événement : ce qui reste (horloge de démonstration, signalée)

Chaque étape appelle `ClubPulse` et le banc comme le feraient les membres ; les gestes humains sont JOUÉS par la
présentation et marqués `joue=True` (en direct, les téléphones les font). `rejouer(n)` reconstruit l'état depuis zéro :
mêmes données, même résultat. Monde FICTIF (données préparées, étiquetées) ; dates simulées.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Callable, Optional

from app.taxonomy import Taxonomie

from plateforme.affirmations import Statut

from . import monde_demo as md
from .club_pulse import CRITERE_ACTION, ClubPulse
from .essai import Plage
from .ia import Intelligence

CLAUDIA, STEFAN, NICOLAS = "s15", "s16", md.NICOLAS
BESOIN_SOPHIE = ("Je voudrais présenter nos tisanes à des acheteurs germanophones pendant la Foire, jeudi après-midi. Je n'ai ni "
                 "stand ni personne qui parle allemand, et j'aimerais leur laisser une fiche en allemand.")
FICHE_DE = ("Kräutertees aus dem Val d'Entremont — Bio-Kräuter aus 1 200 m Höhe, von Hand geerntet.\n"
            "Sorten: Alpenminze, Melisse, Thymian-Zitrone. 20 Beutel à 1,5 g.\n"
            "Ideal für Bioläden und Hofläden. Muster auf Anfrage am Stand.")
OBSERVATION = "Trois acheteurs présents, une demande d'échantillons pour un magasin bio de Munich. Rien n'est commandé."
LIMITES = "une présentation de 45 min, une gamme (tisanes), trois personnes ; aucune commande à ce stade"
HEURE_JURY = ("17:00", "19:00")          # la valeur par défaut du rejeu ; en direct, le jury la choisit


def jour_foire(club: ClubPulse):
    """Le jeudi de la Foire du Valais 2026 (08.10) ; le monde fictif commence au mardi 06.10, pendant la Foire."""
    return md.JOUR_SCENE


def offres_scene(club: ClubPulse) -> list[tuple]:
    """DONNÉES PRÉPARÉES (fictives) : ce que des membres ont publié AVANT la scène, avec LEURS horaires. Dont des pièges
    réels : une traductrice le matin seulement, une offre sans horaire, une personne qui refuse les sollicitations."""
    j = jour_foire(club)
    return [  # (auteur, nature, quoi, durée max, capacité, conditions, capacité déclarée, plages)
        (md.LEA, "competence", "Présenter un produit en allemand et en rédiger une fiche courte", 60, 2, "sur place, à la Foire", "traduction",
         [Plage(jour=j, debut="16:00", fin="18:00")]),
        (md.ANNA, "competence", "Traduction et interprétariat français–allemand", 60, 2, "", "traduction", [Plage(jour=j, debut="09:00", fin="12:00")]),
        (md.PAULINE, "lieu", "Présentoir éclairé sur mon stand (halle 2)", None, 1, "stand B12", None, [Plage(jour=j, debut="14:00", fin="17:30")]),
        (NICOLAS, "lieu", "Coin dégustation du stand de la distillerie (halle 3)", None, 1, "stand C4", None, [Plage(jour=j, debut="16:30", fin="19:00")]),
        (md.MARKUS, "competence", "Amener deux ou trois acheteurs germanophones à un stand", 60, 1, "acheteurs de magasins bio", "export_allemagne",
         [Plage(jour=j, debut="15:00", fin="18:30")]),
        (STEFAN, "competence", "Présenter des distributeurs allemands", 60, 1, "", "export_allemagne", [Plage(jour=j, debut="14:00", fin="18:00")]),
    ]


OFFRES_PIVOT = [   # la tranche précédente (banc d'essai sans horaire) : conservée, jamais retenue pour une action à créneau
    (CLAUDIA, "competence", "Conseil pour lancer un produit sur le marché allemand", 60, 2, 0, 30, "en visio ou à Sierre", "export_allemagne"),
    (md.MARKUS, "temps", "Regard neuf de distributeur sur un emballage ou une étiquette", 15, 2, 0, 20, "pendant la Foire, sur un stand", None),
    (md.LEA, "temps", "Quelques minutes de regard neuf sur un support imprimé (français ou allemand)", 15, 2, 0, 20, "à distance", None),
    (md.PAULINE, "lieu", "Un présentoir éclairé sur mon stand pendant la Foire", 20, 1, 0, 10, "hors heures d'affluence", None),
    ("s12", "competence", "Photographier un produit sur fond neutre", 30, 1, -60, -5, "offre ancienne", "developpement_web"),
]


def semer_offres(club: ClubPulse) -> None:
    j = club.jour
    for auteur, nature, quoi, duree, capacite, du, au, conditions, concept in OFFRES_PIVOT:
        club.banc.publier_offre(auteur, nature, quoi, capacite, j + timedelta(days=du), j + timedelta(days=au),
                                duree_max_min=duree, conditions=conditions, concept=concept)
    for auteur, nature, quoi, duree, capacite, conditions, concept, plages in offres_scene(club):
        club.banc.publier_offre(auteur, nature, quoi, capacite, j, jour_foire(club), duree_max_min=duree, conditions=conditions,
                                concept=concept, plages=plages)


def semer_capacites(club: ClubPulse) -> None:
    """DONNÉES PRÉPARÉES (fictives) du scénario A : pour « Accueillir une délégation d'acheteurs germanophones » (vendredi
    09.10), une salle et une interprète ont DÉJÀ déclaré leur disponibilité et consenti à cette finalité. Il manque UNE
    pièce — un minibus de 12 places ou plus : c'est l'Ask. Rien n'est posé le jeudi 08.10 (l'action collective)."""
    j, v = club.jour, md.JOUR_SCENE + timedelta(days=1)
    p = club.capacites.patron("delegation_acheteurs")
    for auteur, emplacement, nature, quoi, concept, attributs, plage in (
            (NICOLAS, "salle", "lieu", "Salle de dégustation de la distillerie, 24 places", None, {"places": 24}, ("13:00", "18:00")),
            (md.ANNA, "interp", "competence", "Interprétation français–allemand, une demi-journée", "traduction", {}, ("13:30", "17:30"))):
        oid = club.banc.publier_offre(auteur, nature, quoi, 1, j, v, concept=concept, attributs=attributs,
                                      plages=[Plage(jour=v, debut=plage[0], fin=plage[1])])
        club.banc.consentir_finalite(auteur, p.id, emplacement, oid, p.portee(emplacement), p.fenetre.jour)


class Demo:
    PERSONAS = (md.SOPHIE, md.LEA, md.PAULINE, md.MARKUS, NICOLAS, md.ANNA, CLAUDIA)

    def __init__(self, tax: Taxonomie, ia: Optional[Intelligence] = None, reprendre: bool = False):
        """`reprendre=True` (démarrage du serveur) : l'état est REPRIS du journal existant (HACKVS_ESSAIS_DB) au lieu
        d'être effacé ; le scénario guidé ne peut alors pas continuer (son contexte n'est pas dans le journal)."""
        self.tax, self._ia = tax, ia
        self.reinitialiser(reprendre)

    def reinitialiser(self, reprendre: bool = False) -> None:
        # nouvelle démonstration : un journal VIDE (aucun essai d'une démonstration précédente)
        self.club = ClubPulse(self.tax, ia=Intelligence(self.tax, self._ia.f if self._ia else None) if self._ia else None,
                              neuf=not reprendre)
        repris = len(self.club.journal.evenements()) > 1          # au-delà du seul semis : un monde déjà vécu
        if not repris:
            with self.club.banc.origine(Statut.SYNTHETIQUE):  # données PRÉPARÉES : jamais présentées comme déclarées
                semer_offres(self.club)
                semer_capacites(self.club)
        self.etape = len(self.ETAPES) if repris else 0
        self.ctx: dict = {}
        self.traces: list[dict] = [{"acte": "reprise", "legende": "état repris du journal ; « Nouvelle démonstration » pour "
                                                                  "rejouer le scénario"}] if repris else []

    # --------------------------------------------------------------- utilitaires
    def _essai(self) -> tuple[str, int]:
        return self.ctx["essai"], self.club.banc.version(self.ctx["essai"])

    def offre_de_lea(self) -> str:
        c = self.club
        return next(o.id for o in c.banc.offres(publiques=True) if o.auteur == md.LEA and o.plages)

    def perturber_disponibilite(self, debut: str, fin: str) -> list[str]:
        """La personne germanophone change SA disponibilité (sur son téléphone en direct ; jouée ici, et dite telle)."""
        c = self.club
        return c.banc.modifier_offre(md.LEA, self.offre_de_lea(), plages=[Plage(jour=jour_foire(c), debut=debut, fin=fin)])

    # --------------------------------------------------------------- les étapes (acte, légende, geste joué ?)
    def _e1_besoin(self) -> dict:
        c = self.club
        acces = c.activer_compte(c.coffre.code_invitation(md.SOPHIE))
        self.ctx["session_sophie"] = acces["session"]
        aide = c.proposer("tisanes de plantes alpines bio", "aide")
        c.onboarding(md.SOPHIE, aide=[aide[0]], cherche=[], visible=True)
        prop = c.preparer_action(md.SOPHIE, BESOIN_SOPHIE)
        self.ctx["comprehension"] = prop
        eid = c.creer_action(md.SOPHIE, {"question": "Présenter nos tisanes à des acheteurs germanophones", "objet": prop["objet"],
                                          "critere": CRITERE_ACTION, "exigences": prop["exigences"], "fenetre": prop["fenetre"],
                                          "duree_min_acceptable": 30})
        self.ctx["essai"] = eid
        c.banc.autoriser_projection(md.SOPHIE, eid, True)
        return {"acte": "Besoin", "legende": f"Sophie écrit avec ses mots : « {BESOIN_SOPHIE} » Elle a le produit ; il lui manque "
                "une voix allemande (avec la fiche), un lieu et un public. Elle confirme ces trois exigences et sa fenêtre (jeudi 14 h–18 h), "
                "et accepte de montrer son action sur l'écran commun (en rôles, sans noms).",
                "joue": True, "ia": prop["ia"], "ecran": {"app": md.SOPHIE, "vue": "essai", "cible": eid}}

    def _e2_proposition(self) -> dict:
        c = self.club
        eid, _ = self._essai()
        a = c.banc.assembler(md.SOPHIE, eid)
        cr = a["solution"]["creneau"]
        return {"acte": "Proposition", "legende": f"Aucune offre ne suffit seule. Le serveur cherche le moment où les disponibilités "
                f"DÉCLARÉES se recouvrent : {cr.texte()}. La traductrice du matin, l'offre sans horaire et la personne qui refuse les "
                "sollicitations sont écartées — et c'est dit.", "joue": False, "creneau": cr.texte(),
                "ecran": {"projection": True}}

    def _e3_publication(self) -> dict:
        c = self.club
        eid, v = self._essai()
        c.publier_action(md.SOPHIE, eid, v)
        return {"acte": "Invitation", "legende": "Sophie publie. Chaque personne reçoit, sur SON téléphone, sa seule part : le geste, "
                "le créneau, ce qui sera partagé. Rien n'est décidé à sa place.", "joue": True,
                "ecran": {"app": md.LEA, "vue": "essai", "cible": eid}}

    def _e4_accords(self) -> dict:
        c = self.club
        eid, v = self._essai()
        for pid in (md.LEA, md.PAULINE, md.MARKUS):
            c.banc.decider(pid, eid, v, True)
        return {"acte": "Accords", "legende": "Léa, Pauline et Markus acceptent, chacun depuis son espace. La coopération est prête : "
                "tous les accords couvrent CETTE version — pas encore une réalisation.", "joue": True, "etat": c.banc.etat(eid),
                "ecran": {"projection": True}}

    def _e5_perturbation(self) -> dict:
        eid, _ = self._essai()
        self.perturber_disponibilite(*HEURE_JURY)
        c = self.club
        return {"acte": "Perturbation", "legende": f"Le jury change une condition : Léa n'est disponible qu'à partir de {HEURE_JURY[0]}. "
                "Elle le déclare sur son téléphone. Son accord ne couvre plus le créneau ; le lieu et le public restent valables "
                "— pour ce créneau-là.", "joue": True, "etat": c.banc.etat(eid), "ecran": {"projection": True}}

    def _e6_adaptation(self) -> dict:
        c = self.club
        eid, v = self._essai()
        alts = c.banc.alternatives(eid)
        choix = next((a for a in alts if a["type"] == "decaler" and not a["plus_court"]), alts[0])
        c.banc.choisir_alternative(md.SOPHIE, eid, v, choix["id"])
        return {"acte": "Adaptation", "legende": f"{len(alts)} adaptation(s) admissible(s), calculées par le serveur. Sophie garde 45 min : "
                f"{choix['texte']} Personne n'est reconfirmé à sa place.", "joue": True,
                "alternatives": [a["texte"] for a in alts], "ecran": {"projection": True}}

    def _e7_reconfirmations(self) -> dict:
        c = self.club
        eid, v = self._essai()
        for e in c.banc.protocole(eid).etapes:
            if c.banc.couverture(eid).get(e.contributeur or "") is not None:
                c.banc.decider(e.contributeur or "", eid, v, True)
        c.banc.lancer(md.SOPHIE, eid, c.banc.version(eid))
        return {"acte": "Engagé", "legende": "Chacun reconfirme sur la nouvelle version ; Sophie engage l'action. Réalisation engagée "
                "— pas encore réalisée.", "joue": True, "etat": c.banc.etat(eid), "ecran": {"projection": True}}

    def _e8_fiche(self) -> dict:
        c = self.club
        eid, _ = self._essai()
        e = next(x for x in c.banc.protocole(eid).etapes if x.livrable)
        c.banc.livrer(e.contributeur or "", eid, e.id, FICHE_DE)
        c.banc.recevoir(md.SOPHIE, eid, e.id)                 # la FICHE est reçue ; la présentation reste à tenir
        return {"acte": "Résultat", "legende": "Léa écrit la fiche en allemand et la transmet. Elle apparaît sur le téléphone de Sophie, "
                "qui en confirme la réception. Transmise, puis reçue : deux faits distincts.", "joue": True,
                "ecran": {"app": md.SOPHIE, "vue": "essai", "cible": eid}}

    def _e9_apres(self) -> dict:
        c = self.club
        eid, _ = self._essai()
        c.avancer((jour_foire(c) - c.jour).days)
        for e in c.banc.protocole(eid).etapes:
            if not any(x.donnees["etape"] == e.id for x in c.banc._evs(eid, "CONTRIBUTION")):
                c.banc.constater(md.SOPHIE, eid, e.id)
        rev = c.banc.observer(md.SOPHIE, eid, OBSERVATION, "positif", LIMITES)
        for pid in sorted(c.banc.participants(eid) - {md.SOPHIE}):
            c.banc.aviser(pid, eid, rev, "confirme")
        c.banc.reutilisation(md.SOPHIE, eid, "club", "nom")
        for pid in sorted(c.banc.participants(eid) - {md.SOPHIE}):
            c.banc.reutilisation(pid, eid, "club", "nom")
        c.avancer(30)
        return {"acte": "Entre les événements", "legende": "Horloge de démonstration : +30 jours. Il reste ce qui a été déclaré et "
                "confirmé — la fiche reçue, la présentation DÉCLARÉE tenue par Sophie, ce qu'elle a observé, qui l'a confirmé, qui peut le réutiliser. Les "
                "disponibilités ont expiré : rien n'est reconduit.", "joue": True, "horloge": "démonstration (+30 jours, simulé)",
                "ecran": {"app": md.SOPHIE, "vue": "souvenirs"}}

    ETAPES: list[Callable[["Demo"], dict]] = [_e1_besoin, _e2_proposition, _e3_publication, _e4_accords, _e5_perturbation, _e6_adaptation,
                                              _e7_reconfirmations, _e8_fiche, _e9_apres]

    def suivant(self) -> dict:
        if self.etape >= len(self.ETAPES):
            raise IndexError("démonstration terminée")
        with self.club.banc.origine(Statut.JOUE):         # le contrôleur de démonstration JOUE tous les personnages
            t = self.ETAPES[self.etape](self) | {"etape": self.etape + 1, "total": len(self.ETAPES), "date": self.club.jour.isoformat()}
        self.traces.append(t)
        self.etape += 1
        return t

    def rejouer(self, n: int) -> None:
        self.reinitialiser()
        for _ in range(max(0, min(n, len(self.ETAPES)))):
            self.suivant()

    def personas(self) -> list[dict]:
        """DÉMO SEULEMENT : les membres fictifs que l'équipe peut incarner (code d'invitation, session si compte actif).
        En production, chacun n'a que son propre téléphone : cette route n'existe pas."""
        c = self.club
        res = []
        for p in self.PERSONAS:
            per = c.coffre.identite(p)
            res.append({"id": p, "nom": per.nom if per else p, "code": c.coffre.code_invitation(p),
                        "session": c.session(p) if p in c.coffre.actives else None,
                        "capacite": next((self.tax.libelle(o.concept) for o in c.profil(p).offre if o.concept), None)})
        return res
