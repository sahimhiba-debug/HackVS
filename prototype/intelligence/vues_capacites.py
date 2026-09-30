"""Ce qu'on MONTRE du registre des capacités. En RÔLES seulement : ni nom, ni texte d'offre (un texte d'offre peut
désigner quelqu'un — « le stand de la distillerie »), ni qui a consenti ou non. Un consentement perdu est dit par
l'emplacement (« salle : consentement retiré »), jamais par la personne."""
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Optional

from .capacites import Instance

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

LIBELLES = {"ONE_AWAY": "il manque une pièce", "PROPOSED": "toutes les pièces existent — aucun consentement encore",
            "CONSENTED": "consentements en cours", "ACTIVE": "le Club peut le faire", "DEGRADED": "un consentement ne vaut plus",
            "EXTINCT": "la fenêtre est passée"}


class VuesCapacites:
    def __init__(self, club: "ClubPulse"):
        self.c = club

    def instance(self, i: Instance) -> dict:
        p = self.c.capacites.patron(i.finalite)
        pieces = []
        for e in p.emplacements:
            v, cons = i.liaisons.get(e.id), i.consentements.get(e.id)
            pieces.append({"emplacement": e.id, "role": e.role, "libelle": e.libelle, "presente": v is not None,
                           "consentement": None if v is None else ("donné" if cons is None else "à demander"),
                           "manquante": i.manquant == e.id, "critique": e.id in i.critiques,
                           "fournie_par": "une personne du Club" if v is not None else None})     # pseudonymisé : jamais un nom
        roles = {e.id: e.role for e in p.emplacements}
        return {"finalite": i.finalite, "version": i.version, "titre": i.titre, "statut": i.statut,
                "statut_libelle": LIBELLES.get(i.statut or "", ""), "distance": i.distance, "date": self.c.jour.isoformat(),
                "jour": p.fenetre.jour.isoformat(), "fenetre": f"{p.fenetre.jour.strftime('%d.%m')} {p.fenetre.debut}–{p.fenetre.fin}",
                "creneau": i.creneau.texte() if i.creneau else None, "pieces": pieces,
                "ask": {"texte": i.ask.texte, "expire": i.ask.expire.isoformat(), "levier": i.ask.levier, "debloque": i.ask.debloque,
                        "libelle": i.ask.libelle} if i.ask else None,
                "critiques": [roles[k] for k in i.critiques], "resultats": "aucun résultat déclaré pour cette capacité",
                # une pièce perdue est dite par son RÔLE, sans la raison : ni qui, ni pourquoi (retrait jamais attribué)
                "perdus": [f"{roles.get(x.split(' : ', 1)[0], x.split(' : ', 1)[0])} : ce composant n'est plus disponible" for x in i.perdus],
                "recomposition": {k: v for k, v in i.recomposition.items() if k != "pieces"} if i.recomposition else None,
                "sans_solution": i.sans_solution, "hypotheses": i.hypotheses, "fictif": i.fictif}

    def console(self) -> dict:
        """Le registre : ce que le Club PEUT faire (distance 0) et ce qu'il lui manque une pièce pour faire (distance 1) —
        et, pour l'animation, SEULEMENT ce qui bloque, ce qui exige une décision, ce qui expire."""
        caps = [self.instance(i) for i in self.c.projection_capacites() if i.statut is not None]
        bientot = (self.c.jour + timedelta(days=2)).isoformat()
        return {"capacites": caps, "date": self.c.jour.isoformat(), "fictif": True,
                "attention": {"bloque": [x["titre"] for x in caps if x["statut"] == "DEGRADED"],
                              "decision": [x["titre"] for x in caps if x["recomposition"] or x["sans_solution"]],
                              "expire": [f"{x['titre']} ({x['fenetre']})" for x in caps
                                         if x["statut"] not in ("ACTIVE", "EXTINCT") and x["jour"] <= bientot]},
                "regle": "Une capacité n'existe que si chaque pièce est déclarée, valable à cette date et consentie pour "
                         "cette finalité. Rôles seulement : aucun nom."}

    def asks(self, pid: str) -> list[dict]:
        return [{"id": a, "titre": i.titre, "texte": i.ask.texte, "libelle": i.ask.libelle, "minimums": i.ask.minimums,  # type: ignore[union-attr]
                 "expire": i.ask.expire.isoformat(), "choix": ["oui", "non", "pas cette fois"]}  # type: ignore[union-attr]
                for i, a in self.c.asks_pour(pid)]

    def mes_donnees(self, pid: str) -> dict:
        """Ce que le système sait de MOI, pourquoi, et jusqu'à quand — lu dans le journal, pour moi seul·e."""
        j = self.c.jour
        claims = [x for x in self.c.claims() if x.membre == pid]
        courants = [x for x in claims if x.superseded_at is None]
        nature = {"SKILL": "compétence", "RESOURCE": "ressource", "NEED": "intérêt", "SLOT": "créneau"}
        reponses = [e for e in self.c.journal.evenements("ASK_REPONSE") if e.acteurs[0] == pid]
        return {"date": j.isoformat(), "fictif": True,
                "declarations": [{"type": nature[x.kind], "texte": x.texte, "depuis_position": x.recorded_at,
                                  "valable_jusqu_au": x.valid_until.isoformat() if x.valid_until else "sans date (jusqu'à ce que vous la retiriez)",
                                  "etat": "valable" if x.valable(j) else "expirée (gardée dans l'historique, plus utilisée)",
                                  "pourquoi": "composer ce que le Club peut faire ; jamais affiché avec votre nom sans votre accord"}
                                 for x in courants],
                "historique": len(claims) - len(courants),
                "consentements": self.c.capacites.recus(pid),
                "reponses_aux_demandes": [{"le": e.le.isoformat(), "reponse": "oui" if e.donnees["oui"] else "non"} for e in reponses],
                "notes_privees": len(self.c.notes.get(pid, [])),
                "hors_du_journal": "votre nom, votre organisation et vos coordonnées vivent dans un coffre séparé ; "
                                   "le moteur ne les voit jamais"}

    def apres_reponse(self, i: Instance, pid: Optional[str] = None) -> dict:
        return self.instance(i) | {"vous": "votre pièce est enregistrée, avec votre consentement pour cette seule finalité"}
