"""Contrôleur de DÉMONSTRATION : un scénario rejouable, fait d'appels RÉELS au service (aucun résultat écrit d'avance).

Chaque étape appelle `ClubPulse` comme le ferait un membre ou l'animatrice ; les gestes humains (accepter, refuser,
contribuer, confirmer) sont JOUÉS par la présentation et marqués `joue=True`. `rejouer(n)` reconstruit l'état depuis
zéro : même graine, mêmes données, même résultat (vérifié par les tests, empreinte du journal comprise).
"""
from __future__ import annotations

from typing import Callable, Optional

from app.taxonomy import Taxonomie

from . import monde_demo as md
from .club_pulse import ClubPulse
from .ia import Intelligence
from .politique import Spectateur

NOTE_SOPHIE = ("Rencontré Markus à la Foire du Valais : il représente des marques bio en Allemagne et cherche des "
               "producteurs de boissons. Je dois aussi faire traduire mes étiquettes.")
FICHE = """Mentions à traduire (règlement européen sur l'information des consommateurs, dit « INCO ») :
1. Dénomination de vente (Bezeichnung des Lebensmittels).
2. Liste des ingrédients (Zutaten) ; allergènes mis en évidence.
3. Quantité nette (Nettofüllmenge) ; date de durabilité minimale (« mindestens haltbar bis »).
4. Nom et adresse de l'exploitant ; déclaration nutritionnelle (Nährwertdeklaration).
Pièges fréquents : « tisane » se dit Kräutertee ; l'allemand doit figurer sur l'étiquette arrière.
À faire relire par un professionnel avant impression : aide pratique, pas un avis juridique."""
DEMANDE_PAULINE = "Je dois faire traduire mes étiquettes de vin en allemand pour un salon à Stuttgart."


class Demo:
    def __init__(self, tax: Taxonomie, ia: Optional[Intelligence] = None):
        self.tax, self._ia = tax, ia
        self.reinitialiser()

    def reinitialiser(self) -> None:
        self.club = ClubPulse(self.tax, ia=Intelligence(self.tax, self._ia.f if self._ia else None) if self._ia else None)
        self.etape = 0
        self.ctx: dict = {}
        self.traces: list[dict] = []

    # --------------------------------------------------------------- les étapes (acte, légende, geste joué ?)
    def _e1_rejoindre(self) -> dict:
        c = self.club
        acces = c.activer_compte(c.coffre.code_invitation(md.SOPHIE))
        self.ctx["session_sophie"] = acces["session"]
        aide = c.proposer("tisanes de plantes alpines bio", "aide")                  # → Production de boissons : confirmée
        cherche = c.proposer("faire valider la conformité de nos étiquettes pour le marché allemand", "cherche")
        self.ctx["correction"] = [x["libelle"] for x in cherche if x["concept"]]      # le moteur propose « emballage »…
        c.onboarding(md.SOPHIE, aide=[aide[0]], cherche=[cherche[-1]], visible=True)   # …Sophie corrige : « tel quel »
        return {"acte": "Rejoindre", "legende": "Sophie scanne le QR du Club, active son compte d'adhérente et dit en deux phrases ce qu'elle "
                "offre et ce qu'elle cherche. Le système propose « " + ", ".join(self.ctx["correction"]) + " » : elle corrige, c'est "
                "une question de conformité. Invisible par défaut, elle choisit d'être sollicitable.", "joue": True,
                "ecran": {"app": md.SOPHIE, "vue": "profil"}}

    def _e2_rencontre(self) -> dict:
        c = self.club
        note = c.capturer(md.SOPHIE, NOTE_SOPHIE, evenement=md.FOIRE)
        idx = next(i for i, p in enumerate(note["propositions"]) if p["type"] == "ajouter_recherche")
        c.partager(md.SOPHIE, note["id"], idx)
        return {"acte": "Mémoire", "legende": "Elle dicte une note sur sa rencontre avec Markus à la Foire. La note reste PRIVÉE ; elle "
                "choisit de partager une seule chose : « je cherche : traduction ».", "joue": True,
                "ecran": {"app": md.SOPHIE, "vue": "memoire"}, "ia": note["ia"]}

    def _e3_scanner(self) -> dict:
        scan = self.club.scanner(force=True)
        o = next(o for o in scan["opportunites"] if o.beneficiaire == md.SOPHIE)
        self.ctx["opp"] = o.id
        return {"acte": "Pouls", "legende": f"Le réseau est analysé : {len(scan['opportunites'])} opportunités. L'une concerne Sophie, "
                "et personne ne l'a demandée : une suite à sa rencontre, un salon dans 12 jours, une capacité du Club.",
                "joue": False, "ecran": {"console": "scan", "app": md.SOPHIE, "vue": "pouls"}}

    def _e4_pourquoi(self) -> dict:
        x = self.club.expliquer(self.ctx["opp"], Spectateur("membre", md.SOPHIE))
        return {"acte": "Pourquoi", "legende": "Pourquoi maintenant, ce qui manque, ce qui peut échouer — chaque ligne vient d'un fait.",
                "joue": False, "ecran": {"app": md.SOPHIE, "vue": "opportunite", "cible": self.ctx["opp"]}, "ia": x["ia"]}

    def _e5_activer(self) -> dict:
        aid = self.club.activer(self.ctx["opp"], Spectateur("membre", md.SOPHIE))
        self.ctx["aid"] = aid
        return {"acte": "Activer", "legende": "Sophie active. Le Club sollicite en privé une traductrice et Markus ; chacun ne voit "
                "que sa part, sans savoir qui demande.", "joue": True, "ecran": {"app": md.ANNA, "vue": "demandes"}}

    def _e6_refus(self) -> dict:
        self.club.repondre(self.ctx["aid"], md.ANNA, False)
        return {"acte": "Refus", "legende": "La traductrice décline. Personne ne saura qui a dit non — même pas le Club. "
                "Le plan se recompose : une alternative remplit 5 conditions sur 7 ; la disponibilité est à vérifier.",
                "joue": True, "ecran": {"console": "activation", "cible": self.ctx["aid"]}}

    def _e7_accords(self) -> dict:
        self.club.repondre(self.ctx["aid"], md.MARKUS, True)
        self.club.repondre(self.ctx["aid"], md.LEA, True)
        return {"acte": "Consentement", "legende": "Léa confirme sa disponibilité et accepte ; Markus aussi. Les noms ne sont révélés "
                "qu'à présent, et seulement aux personnes concernées.", "joue": True,
                "ecran": {"app": md.SOPHIE, "vue": "activation", "cible": self.ctx["aid"]}}

    def _e8_contributions(self) -> dict:
        c, aid = self.club, self.ctx["aid"]
        c.contribuer(aid, md.LEA, "ressource", "Fiche : étiqueter un produit alimentaire pour l'Allemagne", FICHE,
                     reutilisable=True, attribution=True)
        c.contribuer(aid, md.MARKUS, "rencontre", "Rendez-vous au Salon Bio de Munich",
                     "20 minutes le mardi matin ; il apporte ses conditions de représentation.")
        return {"acte": "Action", "legende": "Une fiche pratique (partageable avec le Club, avec le nom de Léa) et un rendez-vous au salon. "
                "Deux contributions, pas deux contacts.", "joue": True, "ecran": {"app": md.SOPHIE, "vue": "activation", "cible": aid}}

    def _e9_resultat(self) -> dict:
        self.club.avancer(14)
        r = self.club.confirmer(self.ctx["aid"], md.SOPHIE, "debloque", True, "étiquettes traduites ; rendez-vous tenu au salon")
        return {"acte": "Résultat", "legende": f"Deux semaines plus tard, Sophie répond : « Oui, cela a débloqué ma prochaine étape ». "
                f"{r['statut']}. Le résultat devient une mémoire vérifiée — anonymisée.", "joue": True,
                "ecran": {"app": md.SOPHIE, "vue": "activation", "cible": self.ctx["aid"]}}

    def _e10_reutilisation(self) -> dict:
        c = self.club
        c.activer_compte(c.coffre.code_invitation(md.PAULINE))
        rep = c.demander(md.PAULINE, DEMANDE_PAULINE)
        o = next(x for x in rep["opportunites"] if x["type"] == "MEMOIRE")
        self.ctx["opp_memoire"] = o["id"]
        aid = c.activer(o["id"], Spectateur("membre", md.PAULINE))
        c.reutiliser(aid)
        c.confirmer(aid, md.PAULINE, "partiel", True, "fiche utile ; le vin a ses propres mentions à vérifier")
        self.ctx["aid2"] = aid
        return {"acte": "Réutilisation", "legende": "Une vigneronne pose une question semblable. Le Club retrouve le motif vérifié : "
                "réponse immédiate, personne n'est dérangé, et la différence de secteur est signalée. Le réseau vient d'apprendre.",
                "joue": True, "ecran": {"app": md.PAULINE, "vue": "activation", "cible": aid}}

    ETAPES: list[Callable[["Demo"], dict]] = [_e1_rejoindre, _e2_rencontre, _e3_scanner, _e4_pourquoi, _e5_activer, _e6_refus,
                                              _e7_accords, _e8_contributions, _e9_resultat, _e10_reutilisation]

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

    PERSONAS = (md.SOPHIE, md.ANNA, md.LEA, md.MARKUS, md.PAULINE)

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
