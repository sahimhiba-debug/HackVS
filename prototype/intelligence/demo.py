"""Contrôleur de DÉMONSTRATION : la boucle Club Pulse en 11 étapes, faites d'appels RÉELS au service (aucun résultat
écrit d'avance). Chaque étape appelle `ClubPulse` et le banc d'essai comme le feraient les membres ; les gestes humains
(déclarer, proposer, accepter, réduire sa disponibilité, choisir, observer, confirmer, partager) sont JOUÉS par la
présentation et marqués `joue=True`. `rejouer(n)` reconstruit l'état depuis zéro : mêmes données, même résultat.

    BESOIN → DÉCOUVERTE → POURQUOI → INVITATION → ACCORD → PERTURBATION → ADAPTATION → ACTION → RÉSULTAT → MÉMOIRE
    → DÉCOUVERTE SUIVANTE (qui n'existait pas avant)

Monde FICTIF (données synthétiques étiquetées) ; dates simulées.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Callable, Optional

from app.taxonomy import Taxonomie

from . import memoire_club
from . import monde_demo as md
from .club_pulse import CRITERE_SUGGERE, ClubPulse
from .ia import Intelligence

CLAUDIA = "s15"
BESOIN_SOPHIE = "Trouver un distributeur pour entrer sur le marché allemand avec nos tisanes"
OBSERVATION = ("Deux distributeurs bio présentés, à contacter ; un rendez-vous pris avec l'un d'eux au salon de Munich. "
               "Rien n'est signé.")
LIMITES = "un échange de 20 minutes, une seule gamme (tisanes), avant le salon ; aucun contrat à ce stade"

OFFRES_PREPAREES = [   # DONNÉES PRÉPARÉES (fictives) : ce que des membres ont publié AVANT la scène — (auteur, nature, quoi,
    # durée max, capacité, du, au, conditions, capacité déclarée)
    (CLAUDIA, "competence", "Conseil pour lancer un produit sur le marché allemand", 60, 2, 0, 30, "en visio ou à Sierre", "export_allemagne"),
    # une offre « temps » de Markus (le banc d'essai de la tranche pivot) : elle ne dit RIEN de sa disponibilité pour
    # une heure de conseil export — la découverte l'ignore (autre capacité), l'essai sur invitation aussi
    (md.MARKUS, "temps", "Regard neuf de distributeur sur un emballage ou une étiquette", 15, 2, 0, 20, "pendant la Foire, sur un stand", None),
    (md.LEA, "temps", "Quelques minutes de regard neuf sur un support imprimé (français ou allemand)", 15, 2, 0, 20, "à distance", None),
    (md.PAULINE, "lieu", "Un présentoir éclairé sur mon stand pendant la Foire", None, 1, 0, 10, "hors heures d'affluence", None),
    ("s12", "competence", "Photographier un produit sur fond neutre", 30, 1, -60, -5, "offre ancienne", "developpement_web"),
]


def semer_offres(club: ClubPulse) -> None:
    """Offres volontaires DÉCLARÉES par des membres fictifs (données préparées, étiquetées). Aucune n'est déduite d'un
    profil : une compétence déclarée n'est pas une disponibilité présente."""
    j = club.jour
    for auteur, nature, quoi, duree, capacite, du, au, conditions, concept in OFFRES_PREPAREES:
        club.banc.publier_offre(auteur, nature, quoi, capacite, j + timedelta(days=du), j + timedelta(days=au),
                                duree_max_min=duree, conditions=conditions, concept=concept)


class Demo:
    PERSONAS = (md.SOPHIE, md.MARKUS, CLAUDIA, md.NICOLAS, md.PAULINE, md.LEA, md.ANNA)

    def __init__(self, tax: Taxonomie, ia: Optional[Intelligence] = None):
        self.tax, self._ia = tax, ia
        self.reinitialiser()

    def reinitialiser(self) -> None:
        self.club = ClubPulse(self.tax, ia=Intelligence(self.tax, self._ia.f if self._ia else None) if self._ia else None)
        self.club.banc.m.vider()                         # nouvelle démonstration : aucun essai d'une démonstration précédente
        semer_offres(self.club)
        self.etape = 0
        self.ctx: dict = {}
        self.traces: list[dict] = []

    # --------------------------------------------------------------- utilitaires
    def _decouverte(self, pid: str) -> Optional[dict]:
        d = self.club.vues.decouvertes_de(pid)
        return next((x for x in d if any(p["capacite"] == self.tax.libelle("export_allemagne") for p in x["personnes"])), None)

    def _essai(self) -> tuple[str, int]:
        return self.ctx["essai"], self.club.banc.version(self.ctx["essai"])

    # --------------------------------------------------------------- les étapes (acte, légende, geste joué ?)
    def _e1_besoin(self) -> dict:
        c = self.club
        acces = c.activer_compte(c.coffre.code_invitation(md.SOPHIE))
        self.ctx["session_sophie"] = acces["session"]
        aide = c.proposer("tisanes de plantes alpines bio", "aide")
        cherche = c.proposer(BESOIN_SOPHIE, "cherche")
        c.onboarding(md.SOPHIE, aide=[aide[0]], cherche=[next(x for x in cherche if x["concept"] == "export_allemagne")], visible=True)
        self.ctx["avant_nicolas"] = len(c.vues.decouvertes_de(md.NICOLAS))
        return {"acte": "Besoin", "legende": "Sophie produit des tisanes en Valais. Elle rejoint l'application du Club et dit ce qu'elle "
                f"cherche : « {BESOIN_SOPHIE} ». Elle accepte d'être sollicitée ; rien d'autre n'est partagé.", "joue": True,
                "ecran": {"app": md.SOPHIE, "vue": "profil"}}

    def _e2_decouverte(self) -> dict:
        d = self._decouverte(md.SOPHIE)
        assert d is not None, "la découverte attendue n'existe pas"
        self.ctx["decouverte"] = d["id"]
        return {"acte": "Découverte", "legende": f"Personne n'a rien demandé à personne. Club Pulse détecte une possibilité : {d['titre']}. "
                "Ce n'est pas un score, ni une décision : une inférence, avec ses preuves.", "joue": False,
                "ecran": {"app": md.SOPHIE, "vue": "decouverte", "cible": d["id"]}}

    def _e3_pourquoi(self) -> dict:
        d = self.club.vues.decouverte_de(md.SOPHIE, self.ctx["decouverte"])
        p = d["pourquoi"]
        return {"acte": "Pourquoi", "legende": "Pourquoi lui, pourquoi maintenant : le besoin (déclaré), sa capacité (déclarée), leur "
                "rencontre à la Foire (observée), le salon de Munich (agenda). Ce qui reste inconnu est dit : sa disponibilité. "
                "Et le risque : aucune contribution de sa part n'a encore été confirmée dans le Club.", "joue": False,
                "ecran": {"app": md.SOPHIE, "vue": "decouverte", "cible": self.ctx["decouverte"]},
                "inconnues": [x["texte"] for x in p["inconnues"]], "risques": p["risques"]}

    def _e4_invitation(self) -> dict:
        c = self.club
        eid = c.proposer_essai(md.SOPHIE, self.ctx["decouverte"])
        p = c.banc.protocole(eid)
        v = c.banc.modifier_brouillon(md.SOPHIE, eid, 0, p.model_copy(update={"critere": CRITERE_SUGGERE}))   # adopté EXPLICITEMENT
        c.banc.proposer(md.SOPHIE, eid, v)
        self.ctx["essai"] = eid
        return {"acte": "Invitation", "legende": "Sophie décide. Le brouillon d'essai est prêt : un échange d'une heure avec Markus avant "
                "le salon. Le critère n'est pas écrit à sa place : elle adopte la suggestion. Markus est invité en privé.",
                "joue": True, "ecran": {"app": md.MARKUS, "vue": "essai", "cible": eid}}

    def _e5_accord(self) -> dict:
        eid, v = self._essai()
        self.club.banc.decider(md.MARKUS, eid, v, True)
        return {"acte": "Accord", "legende": "Markus accepte. En acceptant, il DÉCLARE sa disponibilité : une heure, pour cet essai seulement. "
                "Son nom n'est révélé qu'à présent, et seulement à Sophie.", "joue": True,
                "ecran": {"app": md.SOPHIE, "vue": "essai", "cible": eid}}

    def _e6_perturbation(self) -> dict:
        c = self.club
        eid, _ = self._essai()
        o = c.banc.offre_de(eid, c.banc.protocole(eid).etapes[0])
        assert o is not None
        c.banc.modifier_offre(md.MARKUS, o.id, duree_max_min=20)
        return {"acte": "Perturbation", "legende": "La réalité : Markus n'a plus que 20 minutes au lieu de 60. Son accord ne couvre plus "
                "l'essai. Le système ne remplace personne en silence : il dit ce qui est invalidé et ce qui reste valable.",
                "joue": True, "ecran": {"app": md.SOPHIE, "vue": "essai", "cible": eid}}

    def _e7_adaptation(self) -> dict:
        c = self.club
        eid, v = self._essai()
        alts = c.banc.alternatives(eid)
        choix = next(a for a in alts if a["type"] == "raccourcir")
        c.banc.choisir_alternative(md.SOPHIE, eid, v, choix["id"])
        c.banc.decider(md.MARKUS, eid, c.banc.version(eid), True)
        return {"acte": "Adaptation", "legende": f"{len(alts)} adaptations valables : raccourcir à 20 minutes avec Markus, ou demander à "
                "une autre personne qui offre une heure sur le marché allemand. Sophie garde Markus ; lui seul redonne son accord, "
                "sur la nouvelle version.", "joue": True, "alternatives": [a["type"] for a in alts],
                "ecran": {"app": md.SOPHIE, "vue": "essai", "cible": eid}}

    def _e8_action(self) -> dict:
        c = self.club
        eid, v = self._essai()
        c.banc.lancer(md.SOPHIE, eid, v)
        c.avancer((c.banc.protocole(eid).echeance - c.jour).days or 1)
        c.banc.constater(md.SOPHIE, eid, "e1")
        return {"acte": "Action", "legende": "Au salon de Munich, l'échange a lieu. Sophie le constate : une contribution reçue — ce n'est "
                "pas encore un résultat.", "joue": True, "ecran": {"app": md.SOPHIE, "vue": "essai", "cible": eid}}

    def _e9_resultat(self) -> dict:
        c = self.club
        eid, _ = self._essai()
        c.avancer(2)
        rev = c.banc.observer(md.SOPHIE, eid, OBSERVATION, "positif", LIMITES)
        c.banc.aviser(md.MARKUS, eid, rev, "confirme")
        return {"acte": "Résultat", "legende": "Deux jours plus tard, Sophie déclare ce qui s'est passé, avec ses limites : deux contacts, "
                "un rendez-vous, rien de signé. Markus confirme. Déclaré et confirmé par deux personnes : pas une vérité, pas une note.",
                "joue": True, "ecran": {"app": md.SOPHIE, "vue": "essai", "cible": eid}}

    def _e10_memoire(self) -> dict:
        c = self.club
        eid, _ = self._essai()
        c.banc.reutilisation(md.SOPHIE, eid, "club", "nom")
        c.banc.reutilisation(md.MARKUS, eid, "club", "nom")
        s = next(x for x in memoire_club.souvenirs(c.banc) if x["essai"] == eid)
        return {"acte": "Mémoire", "legende": "Chacun choisit ce que le Club peut en réutiliser : les deux acceptent, avec leur nom. La "
                f"mémoire dit « dans ce contexte, cette contribution a aidé, avec ces limites » — statut : {s['statut']}, "
                f"partage : {s['niveau']}. Jamais « Markus est fiable ».", "joue": True,
                "ecran": {"app": md.SOPHIE, "vue": "souvenirs"}}

    def _e11_suivante(self) -> dict:
        d = self._decouverte(md.NICOLAS)
        assert d is not None, "la découverte suivante n'existe pas"
        self.ctx["decouverte_nicolas"] = d["id"]
        preuve = next((x["texte"] for x in d["pourquoi"]["preuves"] if x["statut"] == "CONFIRMÉ"), None)
        return {"acte": "Découverte suivante", "legende": "Nicolas, distillateur, cherche lui aussi à se faire connaître en Allemagne. Hier, "
                "rien ne se passait. Aujourd'hui, une possibilité apparaît — parce que le Club a appris. Il ne voit pas le nom de "
                "Markus : seulement qu'une personne du Club a déjà aidé sur ce sujet.", "joue": False,
                "avant": self.ctx.get("avant_nicolas"), "preuve": preuve,
                "ecran": {"app": md.NICOLAS, "vue": "decouverte", "cible": d["id"]}}

    ETAPES: list[Callable[["Demo"], dict]] = [_e1_besoin, _e2_decouverte, _e3_pourquoi, _e4_invitation, _e5_accord, _e6_perturbation,
                                              _e7_adaptation, _e8_action, _e9_resultat, _e10_memoire, _e11_suivante]

    def suivant(self) -> dict:
        if self.etape >= len(self.ETAPES):
            raise IndexError("démonstration terminée")
        t = self.ETAPES[self.etape](self) | {"etape": self.etape + 1, "total": len(self.ETAPES), "date": self.club.jour.isoformat()}
        self.traces.append(t)
        self.etape += 1
        return t

    def rejouer(self, n: int) -> None:
        self.reinitialiser()
        for _ in range(max(0, min(n, len(self.ETAPES)))):
            self.suivant()

    def personas(self) -> list[dict]:
        """DÉMO SEULEMENT : les membres fictifs que le jury peut incarner (code d'invitation, session si compte actif).
        En production, chacun n'a que son propre téléphone : cette route n'existe pas."""
        c = self.club
        res = []
        for p in self.PERSONAS:
            per = c.coffre.identite(p)
            res.append({"id": p, "nom": per.nom if per else p, "code": c.coffre.code_invitation(p),
                        "session": c.session(p) if p in c.coffre.actives else None,
                        "capacite": next((self.tax.libelle(o.concept) for o in c.profil(p).offre if o.concept), None)})
        return res

