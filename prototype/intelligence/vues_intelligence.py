"""Ce qu'UNE personne voit de la Network Intelligence : son profil, ses notes privées, ses DÉCOUVERTES (une opportunité
détectée et son « pourquoi » structuré) — et, pour le Club, le panneau d'intelligence de la salle de contrôle.

Aucune écriture. Tout texte qui sort passe par `Rendu` pour CE spectateur : l'explication est calculée sur des
profils pseudonymisés (MEMBRE-xxx) puis rendue — un nom n'apparaît que si la politique l'autorise (rencontre passée,
accord donné dans un essai), sinon un descripteur (« une personne du Club · capacité »). Les identifiants internes
des membres ne sortent jamais. Une découverte n'est pas une décision : seule la personne aidée peut en faire un essai.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.models import Offre

from . import memoire_club
from .erreurs import Interdit
from .explication import contributeurs, expliquer
from .modele import Opportunite
from .passerelle import essai_existant
from .politique import Rendu, Spectateur

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

LIBELLES_TYPE = {"LATENTE": "Intérêt latent", "SUIVI": "Suite d'une rencontre", "COMPOSITION": "Plusieurs capacités réunies",
                 "COMPLEMENTARITE": "Une capacité pour un besoin publié", "CONVERGENCE": "Besoin partagé par plusieurs membres",
                 "LACUNE": "Capacité absente du Club", "CAPACITE_DORMANTE": "Capacité dormante"}
RUBRIQUES = ("besoin", "capacite", "contexte", "relation", "consentement", "preuves", "inconnues")


class VuesIntelligence:
    def __init__(self, club: "ClubPulse"):
        self.c = club

    # ------------------------------------------------------------------ profil et notes (propriétaire seul)
    def _element(self, o: Offre) -> dict:
        return {"concept": o.concept, "libelle": self.c.tax.libelle(o.concept) if o.concept else "hors catalogue", "texte": o.texte}

    def vue_profil(self, pid: str) -> dict:
        p = self.c.profil(pid)
        per = self.c.coffre.identite(pid)
        org = self.c.coffre.organisation_de(pid)
        prefs = {**{k: "SUR_CONSENTEMENT" for k in ("nom", "organisation")}, **{k: "CLUB_DECOUVRABLE" for k in ("capacites", "interets")},
                 **{k: v for k, v in self.c.preferences.get(pid, {}).items()}}
        return {"nom": per.nom if per else None, "organisation": org.nom if org else None, "role": per.role if per else None,
                "adhesion": "carte entreprise" if per and self.c.coffre.adhesions[per.adhesion_id].formule == "entreprise" else "nominative",
                "je_peux_aider": [self._element(o) for o in p.offre], "je_cherche": [self._element(r) for r in p.recherche],
                "langues": p.langues, "disponible": p.disponible, "sollicitable": p.accepte_introductions, "visibilite": prefs,
                "note": "Votre nom et votre entreprise ne sont montrés qu'après votre accord ; vos notes restent privées."}

    def vue_note(self, pid: str, note: dict) -> dict:
        """La note telle que sa propriétaire la relit : la personne mentionnée est RENDUE (nom ou descripteur), jamais
        son identifiant interne."""
        return {k: v for k, v in note.items() if k != "avec"} | {
            "avec_nom": self.c.rendu().nom(Spectateur("membre", pid), note["avec"]) if note["avec"] else None}

    def notes_de(self, pid: str) -> list[dict]:
        return [self.vue_note(pid, n) for n in self.c.notes.get(pid, [])]

    def vue_blocage(self, x: dict) -> dict:
        lib = self.c.tax.libelle(x["concept"]) if x["concept"] in self.c.tax.concepts else x["concept"]
        if x["absente"]:
            pourquoi = f"Le Club ne compte aujourd'hui personne qui déclare : {lib}."
            suite = "Signalé au Club ; précisez si une autre compétence proche vous aiderait."
        else:
            pourquoi = f"Des membres déclarent « {lib} », mais une règle les écarte : " + ", ".join(f"{k} ({v})" for k, v in x["raisons"].items()) + "."
            suite = "La plus petite modification : lever cette contrainte, si elle n'est pas indispensable."
        return {"capacite": lib, "pourquoi": pourquoi, "prochaine_action": suite}

    # ------------------------------------------------------------------ découvertes
    def _disponibilites(self, o: Opportunite) -> dict[str, list[dict]]:
        """La seule disponibilité CONNUE : une offre volontaire active, publique, que la personne a publiée pour la
        capacité que la découverte lui prête (15 minutes de relecture ne disent rien d'une heure de conseil export)."""
        b = self.c.banc
        besoin = {(r.membre, r.concept) for r in o.roles if r.membre in contributeurs(o) and r.concept}
        res: dict[str, list[dict]] = {}
        for x in b.offres(publiques=True):
            if (x.auteur, x.concept) in besoin and b.etat_offre(x.id) == "active":
                res.setdefault(x.auteur, []).append({"quoi": x.quoi, "duree_max_min": x.duree_max_min, "au": x.au.isoformat()})
        return res

    def _rendre_items(self, rendu: Rendu, sp: Spectateur, items: list[dict]) -> list[dict]:
        return [{**{k: rendu.texte(sp, v) if isinstance(v, str) else v for k, v in x.items() if k != "qui"},
                 "qui": rendu.nom(sp, x["qui"]) if x.get("qui") else None} for x in items]

    def decouverte(self, o: Opportunite, sp: Spectateur) -> dict:
        """La découverte telle que CE spectateur a le droit de la voir (membre : seulement s'il en est la personne aidée)."""
        if sp.role == "membre" and sp.id != o.beneficiaire:
            raise Interdit("cette découverte ne vous concerne pas : vous serez sollicité·e en privé si la personne aidée le décide")
        c = self.c
        rendu = c.rendu()
        contrib = contributeurs(o)
        tous = memoire_club.souvenirs(c.banc)
        mem = memoire_club.accessibles(tous, sp.id) if sp.role == "membre" and sp.id else memoire_club.reutilisables_par_le_club(tous)
        e = expliquer(o, c.r, c.tax, self._disponibilites(o), mem)
        pourquoi: dict = {k: self._rendre_items(rendu, sp, e[k]) for k in RUBRIQUES}
        pourquoi |= {"resume": self._rendre_items(rendu, sp, [e["resume"]])[0],
                     "moment": self._rendre_items(rendu, sp, [e["moment"]])[0] if e["moment"] else None,
                     "risques": [rendu.texte(sp, x) for x in e["risques"]],
                     "confiance": {**e["confiance"], "raisons": [rendu.texte(sp, x) for x in e["confiance"]["raisons"]],
                                   "effet_memoire": rendu.texte(sp, e["confiance"]["effet_memoire"]) if e["confiance"]["effet_memoire"] else None},
                     "question": e["question"]}
        eid = essai_existant([(x, c.banc.protocole(x).origine, c.banc.etat(x)) for x in c.banc.essais()], o.id) \
            if o.beneficiaire else None
        ev = next((x for x in c.r.evenements if x.id == o.evenement), None)
        return {"id": o.id, "type": o.type, "type_libelle": LIBELLES_TYPE.get(o.type, o.type), "titre": rendu.texte(sp, o.titre),
                "capacites": [c.tax.libelle(k) for k in o.capacites if k in c.tax.concepts],
                "personnes": [{"qui": rendu.nom(sp, r.membre), "role": r.role.split(" :")[0],
                               "capacite": c.tax.libelle(r.concept) if r.concept else None} for r in o.roles if r.membre in contrib],
                "evenement": {"nom": ev.nom, "le": ev.le.isoformat(), "dans_jours": (ev.le - c.jour).days} if ev else None,
                "pourquoi": pourquoi, "memoire": "mémoire du Club" in o.mecanismes, "essai": eid,
                "peut_proposer": sp.role == "membre" and sp.id == o.beneficiaire and bool(contrib) and eid is None and o.type != "LACUNE",
                "nature": "INFÉRÉ : une possibilité détectée par le système, pas une décision ni une recommandation de personne",
                "fictif": True}

    def decouvertes_de(self, pid: str) -> list[dict]:
        sp = Spectateur("membre", pid)
        return [self.decouverte(o, sp) for o in self.c.scanner()["opportunites"] if o.beneficiaire == pid]

    def decouverte_de(self, pid: str, oid: str) -> dict:
        o = self.c.trouver_opportunite(oid)
        return self.decouverte(o, Spectateur("membre", pid))

    # ------------------------------------------------------------------ panneau d'intelligence (salle de contrôle)
    def panneau(self) -> dict:
        """Ce que le réseau pourrait faire, et pourquoi — pour le Club. Des comptes et des découvertes ; les raisons
        d'écartement restent des comptes (jamais « qui a été écarté »)."""
        c = self.c
        scan = c.scanner()
        sp = Spectateur("animatrice")
        rendu = c.rendu()
        manques: dict[str, set[str]] = {}
        for x in scan["bloques"]:
            lib = c.tax.libelle(x["concept"]) if x["concept"] in c.tax.concepts else x["concept"]
            manques.setdefault(lib, set()).add(x["auteur"])
        levier = max(manques.items(), key=lambda kv: (len(kv[1]), kv[0]), default=None)
        par_type: dict[str, int] = {}
        for o in scan["opportunites"]:
            par_type[LIBELLES_TYPE.get(o.type, o.type)] = par_type.get(LIBELLES_TYPE.get(o.type, o.type), 0) + 1
        return {"membres": len(c.r.profils), "decouvertes": len(scan["opportunites"]), "par_type": par_type,
                "avec_memoire": sum("mémoire du Club" in o.mecanismes for o in scan["opportunites"]),
                "premieres": [{"id": o.id, "type": LIBELLES_TYPE.get(o.type, o.type), "titre": rendu.texte(sp, o.titre),
                               "pourquoi_maintenant": rendu.texte(sp, o.pourquoi_maintenant or ""), "confiance": o.confiance,
                               "memoire": "mémoire du Club" in o.mecanismes} for o in scan["opportunites"][:6]],
                "sans_solution": len(scan["bloques"]),
                "levier": ({"capacite": levier[0], "demandes": len(levier[1]),
                            "phrase": f"Trouver une personne qui offre « {levier[0]} » débloquerait {len(levier[1])} demande(s)."}
                           if levier else None),
                "ecartees": scan["ecartees"], "etapes": scan["phases"],
                "regle": "Le système détecte et explique ; il ne sollicite personne. Seule la personne aidée propose un essai."}

    def opportunite_console(self, oid: str) -> dict:
        return self.decouverte(self.c.trouver_opportunite(oid), Spectateur("animatrice"))
