"""Ce qu'UNE personne voit du banc d'essai. Toute vue passe ici ; aucune ne lit le journal pour un autre usage.

Règles de nom (testées) :
- le porteur est nommé aux personnes à qui sa proposition est faite (il l'a publiée pour cela) ;
- un contributeur n'est nommé qu'après SON accord (au porteur et aux autres participants qui ont accepté) ;
- qui décline, se tait ou se retire n'est jamais nommé : le porteur lit « la personne sollicitée a décliné » ;
- la console voit des états et des comptes, pas le contenu des observations ni les noms de qui a décliné.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .erreurs import Introuvable
from .essai import A_REDEMANDER, FINAUX, NATURES, PARTAGE, Banc

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

LIBELLES = {"BROUILLON": "brouillon (visible de vous seul)", "PROPOSE": "proposé : en attente de choix",
            "AUTORISE": "autorisé : tous les accords couvrent cette version", "A_ADAPTER": "une condition a changé : à adapter",
            "EN_COURS": "en cours", "CONTRIBUTION_RECUE": "contributions reçues (aucun résultat en découle)",
            "OBSERVEE": "observation déclarée", "ANNULE": "annulé", "EXPIRE": "expiré sans lancement",
            "IMPOSSIBLE": "impossible en l'état", "RESULTAT_INCONNU": "résultat inconnu"}
QUALIF = {"positif": "positif", "negatif": "négatif", "mitige": "mitigé", "non_concluant": "non concluant"}


class VuesEssai:
    def __init__(self, club: "ClubPulse"):
        self.c = club

    @property
    def b(self) -> Banc:
        return self.c.banc

    # ------------------------------------------------------------------ noms
    def _engage(self, eid: str, pid: Optional[str]) -> bool:
        """A accepté (sa dernière décision est un accord positif, non retiré) : condition pour être nommé."""
        a = self.b._dernier_accord(eid, pid or "")
        return a is not None and a.type == "ACCORD" and bool(a.donnees["accepte"])

    def nom(self, eid: str, spectateur: Optional[str], pid: str, console: bool = False) -> str:
        per = self.c.coffre.identite(pid)
        if per is None:
            return "un ancien membre"
        if pid == spectateur:
            return "vous"
        porteur = self.b.porteur(eid)
        if pid == porteur:
            return per.nom
        if self._engage(eid, pid) and (console or spectateur == porteur or self._engage(eid, spectateur)):
            return per.nom
        return "une personne du Club"

    # ------------------------------------------------------------------ une proposition / un essai
    def essai(self, eid: str, pid: Optional[str], console: bool = False) -> dict:
        b = self.b
        if not console and pid not in b.personnes(eid):
            raise Introuvable("essai inconnu")                # ni existence, ni contenu pour les autres
        porteur, p, etat = b.porteur(eid), b.protocole(eid), b.etat(eid)
        if not console and pid != porteur and etat == "BROUILLON":
            raise Introuvable("essai inconnu")
        mien = [e for e in p.etapes if e.contributeur == pid]
        if not console and pid != porteur and not mien:       # sollicité autrefois, plus concerné (a décliné, remplacé…)
            dern = b._dernier_accord(eid, pid) if pid else None
            return {"id": eid, "role": "ancien", "question": p.question, "etat": "vous n'êtes plus concerné(e) par cet essai",
                    "votre_decision": ("décliné" if dern and dern.type == "ACCORD" and not dern.donnees["accepte"] else
                                       "retiré" if dern and dern.type == "RETRAIT" else "non requis"), "actions": []}
        cov = b.couverture(eid)
        recues = {x.donnees["etape"] for x in b._evs(eid, "CONTRIBUTION")}
        etapes = []
        for e in p.etapes:
            o = b.offre_de(eid, e)
            statut = ("contribution reçue" if e.id in recues else
                      "accord valable" if e.contributeur and cov.get(e.contributeur) is None else
                      self._statut_public(cov.get(e.contributeur or f"etape:{e.id}")))
            if e.contributeur == pid:                          # à la personne elle-même, en clair
                statut = {"en attente de sa réponse": "à vous de choisir",
                          "sa part a changé depuis son accord": "votre part a changé depuis votre accord : à redonner",
                          "la personne sollicitée a décliné": "vous avez décliné",
                          "la personne sollicitée a retiré sa participation": "vous vous êtes retiré(e)"}.get(statut, statut)
            etapes.append({"id": e.id, "nature": NATURES[e.nature], "geste": e.geste, "duree_min": e.duree_min,
                           "qui": self.nom(eid, pid, e.contributeur, console) if e.contributeur else "personne",
                           "offre": ({"quoi": o.quoi, "conditions": o.conditions, "duree_max_min": o.duree_max_min,
                                      "jusqu_au": o.au.isoformat()} if o else None),
                           "statut": statut, "vous": e.contributeur == pid,
                           "invitation": e.invitation,
                           "offre_id": o.id if o and e.contributeur == pid else None})   # sa PROPRE offre seulement
        role = "porteur" if pid == porteur else ("console" if console else "contributeur")
        v = {"id": eid, "role": role, "version": b.version(eid), "etat": etat, "etat_libelle": LIBELLES.get(etat, etat),
             "porteur": self.nom(eid, pid, porteur, console), "question": p.question, "objet": p.objet, "pourquoi": p.pourquoi,
             "critere": p.critere, "echeance": p.echeance.isoformat(), "etapes": etapes, "partage": PARTAGE,
             "manque": [self._statut_public(x) + (f" ({k.split(':')[1]})" if k.startswith("etape:") else "")
                        for k, x in cov.items() if x], "final": etat in FINAUX,
             "prochaine": self._prochaine(eid, pid, role, etat, cov), "actions": self._actions(eid, pid, role, etat, cov),
             "historique": self._historique(eid, pid, console), "mode": "monde de démonstration FICTIF"}
        if etat == "A_ADAPTER":
            v["adaptation"] = self._adaptation(eid, pid, console)
        if etat == "BROUILLON" and pid == porteur:              # le porteur choisit parmi les offres ADMISSIBLES (anonymes)
            for x, e in zip(etapes, p.etapes, strict=True):
                x["offres_admissibles"] = [{"id": o.id, "quoi": o.quoi, "duree_max_min": o.duree_max_min, "conditions": o.conditions,
                                            "jusqu_au": o.au.isoformat(), "qui": "une personne du Club"}
                                           for o in b.candidats(eid, e, p.echeance)]
        if role == "contributeur":
            v["votre_part"] = {"gestes": [x for x in etapes if x["vous"]], "accord": self._mon_accord(eid, pid)}
        obs = b._evs(eid, "OBSERVATION")
        if obs and (console or pid in b.participants(eid)):
            v["observation"] = self._observation(eid, pid, console)
        if not console and pid in b.participants(eid) and obs:
            v["reutilisation"] = {"vous": b.droits(eid).get(pid or ""), "niveau_effectif": b.niveau_partage(eid)}
        return v

    @staticmethod
    def _statut_public(raison: Optional[str]) -> str:
        if raison is None:
            return "couvert"
        return "la personne sollicitée " + raison if raison in ("a décliné", "a retiré sa participation") else raison

    def _mon_accord(self, eid: str, pid: Optional[str]) -> dict:
        a = self.b._dernier_accord(eid, pid or "")
        if a is None:
            return {"statut": "à décider"}
        if a.type == "RETRAIT":
            return {"statut": "retiré", "le": a.le.isoformat()}
        valable = self.b.couverture(eid).get(pid or "") is None
        return {"statut": ("accepté" if a.donnees["accepte"] else "décliné") + ("" if valable or not a.donnees["accepte"] else
                " — mais la proposition a changé depuis : à redonner"), "version": a.donnees["version"], "le": a.le.isoformat()}

    def _prochaine(self, eid: str, pid: Optional[str], role: str, etat: str, cov: dict) -> str:
        if etat == "BROUILLON":
            return "Relisez le brouillon puis publiez la proposition."
        if etat in ("PROPOSE", "AUTORISE") and role == "contributeur" and cov.get(pid or "") is not None:
            return "À vous de choisir : acceptez votre part, ou déclinez (sans justification)."
        if etat == "PROPOSE":
            return "En attente des choix : " + ", ".join(self._statut_public(x) for x in cov.values() if x) + "."
        if etat == "AUTORISE":
            return "Tous les accords couvrent cette version : le porteur peut lancer l'essai." if role != "porteur" else \
                "Tous les accords couvrent cette version : vous pouvez lancer l'essai."
        if etat == "A_ADAPTER":
            return "Une condition a changé : le porteur choisit une adaptation, ou annule."
        if etat == "EN_COURS":
            return "Réalisez les gestes prévus ; le porteur constate chaque contribution reçue."
        if etat == "CONTRIBUTION_RECUE":
            return "Contributions reçues. Aucun résultat n'en découle : le porteur doit déclarer ce qu'il a observé."
        if etat == "OBSERVEE":
            return "Observation déclarée. Les participants peuvent la confirmer ou la contester, et choisir sa réutilisation."
        return LIBELLES.get(etat, etat)

    def _actions(self, eid: str, pid: Optional[str], role: str, etat: str, cov: dict) -> list[str]:
        if role == "console":
            return ["annuler"] if etat not in FINAUX and etat not in ("CONTRIBUTION_RECUE", "RESULTAT_INCONNU") else []
        a: list[str] = []
        if role == "porteur":
            a += {"BROUILLON": ["corriger", "publier", "annuler"], "PROPOSE": ["modifier", "annuler"], "AUTORISE": ["lancer", "modifier", "annuler"],
                  "A_ADAPTER": ["choisir_adaptation", "annuler"], "EN_COURS": ["constater", "annuler"],
                  "CONTRIBUTION_RECUE": ["observer"], "RESULTAT_INCONNU": ["observer"], "OBSERVEE": ["corriger_observation", "reutilisation"]}.get(etat, [])
        else:
            # choisir n'a de sens que pour une part À REDEMANDER : si son offre ne couvre plus le geste, c'est au porteur
            # d'adapter d'abord (accepter serait refusé)
            if etat in ("PROPOSE", "AUTORISE") and cov.get(pid or "") in A_REDEMANDER and pid not in self.b.refus(eid):
                a += ["accepter", "decliner"]
            if etat not in FINAUX and self.b._dernier_accord(eid, pid or "") is not None:
                a += ["retirer"]
            if etat == "OBSERVEE" and pid in self.b.participants(eid):
                a += ["confirmer", "contester", "reutilisation"]
        return a

    def _adaptation(self, eid: str, pid: Optional[str], console: bool) -> dict:
        ad = self.b._evs(eid, "ADAPTATION")
        d: dict = ad[-1].donnees if ad else {"cause": "", "perdus": {}}
        cov = self.b.couverture(eid)
        preserves = [self.nom(eid, pid, m, console) for m, r in cov.items() if not m.startswith("etape:") and r is None
                     and m != self.b.porteur(eid)]
        return {"cause": d["cause"], "ne_couvre_plus": [(f"{self.nom(eid, pid, k, console)} : " if not k.startswith("etape:") else "")
                                                        + self._statut_public(r) for k, r in d["perdus"].items()],
                "reste_valable": preserves,
                "alternatives": [{"id": x["id"], "texte": x["texte"], "a_decider": ["le porteur", "la personne concernée"]}
                                 for x in self.b.alternatives(eid)] if (console or pid == self.b.porteur(eid)) else []}

    def _historique(self, eid: str, pid: Optional[str], console: bool) -> list[dict]:
        res = []
        for e in self.b._evs(eid, "ESSAI_ETAT", "ESSAI_VERSION"):
            if e.type == "ESSAI_VERSION":
                res.append({"le": e.le.isoformat(), "quoi": f"version {e.donnees['version']} : {e.donnees['motif']}"})
            else:
                res.append({"le": e.le.isoformat(), "quoi": LIBELLES.get(e.donnees["vers"], e.donnees["vers"]) + " — " + e.donnees["raison"]})
        return res

    def _observation(self, eid: str, pid: Optional[str], console: bool) -> dict:
        obs = self.b._evs(eid, "OBSERVATION")
        dern = obs[-1].donnees
        avis = [e for e in self.b._evs(eid, "AVIS") if e.donnees["revision"] == dern["revision"]]
        res = {"revision": dern["revision"], "auteur": self.nom(eid, pid, obs[-1].acteurs[0], console),
               "nature": "déclaration humaine du porteur — non vérifiée par le système", "qualification": QUALIF[dern["qualification"]],
               "tardive": dern.get("tardive", False), "revisions": len(obs),
               "confirmations": sum(1 for e in avis if e.donnees["avis"] == "confirme"),
               "contestations": [{"par": self.nom(eid, pid, e.acteurs[0], console), "raison": e.donnees["raison"]}
                                 for e in avis if e.donnees["avis"] == "conteste"]}
        if not console:                                       # le texte reste aux participants
            res |= {"texte": dern["texte"], "limites": dern["limites"]}
        return res

    # ------------------------------------------------------------------ A. mes actions
    def actions(self, pid: str) -> dict:
        b = self.b
        a_choisir: list[dict] = []
        en_cours: list[dict] = []
        a_faire: list[dict] = []
        resultats: list[dict] = []
        for eid in reversed(b.essais()):
            if pid not in b.personnes(eid):
                continue
            etat, p = b.etat(eid), b.protocole(eid)
            carte = {"id": eid, "question": p.question, "etat": LIBELLES.get(etat, etat), "porteur": self.nom(eid, pid, b.porteur(eid))}
            role = "porteur" if b.porteur(eid) == pid else "contributeur"
            if role == "contributeur" and not any(e.contributeur == pid for e in p.etapes):
                continue                                      # plus concerné : n'encombre pas l'écran
            acts = self._actions(eid, pid, role, etat, b.couverture(eid))
            if {"accepter", "publier", "lancer", "choisir_adaptation", "observer", "constater"} & set(acts):
                a_choisir.append(carte | {"attend": self._prochaine(eid, pid, role, etat, b.couverture(eid))})
            elif etat == "OBSERVEE" and pid in b.participants(eid):
                resultats.append(carte | {"qualification": QUALIF[b._evs(eid, "OBSERVATION")[-1].donnees["qualification"]]})
            elif etat not in FINAUX:
                (en_cours if role == "contributeur" else a_faire).append(carte)
            elif etat in FINAUX and etat != "OBSERVEE":
                resultats.append(carte)
        return {"a_choisir": a_choisir, "contributions": en_cours, "mes_essais": a_faire, "recents": resultats[:5]}

    # ------------------------------------------------------------------ C. mes souvenirs et mes accords
    def souvenirs(self, pid: str) -> dict:
        b = self.b
        offres = [{"id": o.id, "nature": NATURES[o.nature], "quoi": o.quoi, "duree_max_min": o.duree_max_min, "capacite": o.capacite,
                   "reservees": b.reservations(o.id), "du": o.du.isoformat(), "au": o.au.isoformat(), "conditions": o.conditions,
                   "etat": b.etat_offre(o.id)} for o in b.offres() if o.auteur == pid]
        accords, contributions, observations = [], [], []
        for eid in b.essais():
            if pid not in b.personnes(eid):
                continue
            q = b.protocole(eid).question
            for e in b._evs(eid, "ACCORD", "RETRAIT"):
                if e.acteurs[0] != pid:
                    continue
                statut = ("retrait" if e.type == "RETRAIT" else "accepté" if e.donnees["accepte"] else "décliné")
                valable = e.type == "ACCORD" and e.donnees["accepte"] and b._accord_donne(eid, pid, b.protocole(eid), b.porteur(eid))
                accords.append({"essai": eid, "question": q, "version": e.donnees.get("version"), "le": e.le.isoformat(),
                                "statut": statut, "encore_valable": bool(valable),
                                "portee": self._portee_lisible(e.donnees.get("portee")) if e.type == "ACCORD" else None})
            for x in b._evs(eid, "CONTRIBUTION"):
                if x.donnees["contributeur"] == pid:
                    contributions.append({"essai": eid, "question": q, "le": x.le.isoformat(), "constatee_par": self.nom(eid, pid, x.acteurs[0])})
            if pid in b.participants(eid) and b._evs(eid, "OBSERVATION"):
                o = self._observation(eid, pid, False)
                observations.append({"essai": eid, "question": q, **o, "reutilisation": b.droits(eid).get(pid),
                                     "niveau_effectif": b.niveau_partage(eid)})
        return {"notes_privees": [{"id": n["id"], "le": n["le"], "texte": n["texte"], "visibilite": "vous seul·e"}
                                  for n in self.c.notes.get(pid, [])],
                "offres": offres, "accords": accords, "contributions": contributions, "observations": observations,
                "reutilisables": [x for x in observations if x["niveau_effectif"] == "club"],
                "rappel": "Une note privée ne devient jamais une offre : une offre se publie explicitement, avec ses conditions."}

    @staticmethod
    def _portee_lisible(pt: Optional[dict]) -> Optional[str]:
        if not pt:
            return None
        if pt.get("porteur"):
            return f"Proposition publiée (version complète) : « {pt['question']} », critère : {pt.get('critere') or '—'}"
        gestes = " ; ".join(f"{g['geste']} ({g['duree_min']} min)" for g in pt.get("gestes", []))
        return f"{gestes} — pour « {pt['question']} », avant le {pt['echeance']}. {pt['partage']}"

    # ------------------------------------------------------------------ D. console légère
    def console(self) -> dict:
        b = self.b
        lignes = []
        for eid in reversed(b.essais()):
            etat, cov = b.etat(eid), b.couverture(eid)
            if etat == "BROUILLON":
                continue
            contest = [e for e in b._evs(eid, "AVIS") if e.donnees["avis"] == "conteste"]
            lignes.append({"id": eid, "question": b.protocole(eid).question, "etat": etat, "etat_libelle": LIBELLES.get(etat, etat),
                           "version": b.version(eid), "accords_manquants": sum(1 for x in cov.values() if x),
                           "contributions_attendues": (len(b.protocole(eid).etapes) - len(b._evs(eid, "CONTRIBUTION"))) if etat == "EN_COURS" else 0,
                           "contestee": bool(contest), "porteur": self.nom(eid, None, b.porteur(eid), console=True)})
        offres = [{"id": o.id, "quoi": o.quoi, "auteur": getattr(self.c.coffre.identite(o.auteur), "nom", "un ancien membre"),
                   "etat": b.etat_offre(o.id), "au": o.au.isoformat(), "reservees": b.reservations(o.id), "capacite": o.capacite}
                  for o in b.offres()]
        return {"essais": lignes, "bloques": [x for x in lignes if x["etat"] in ("A_ADAPTER", "IMPOSSIBLE")],
                "accords_manquants": [x for x in lignes if x["etat"] == "PROPOSE"],
                "contributions_en_attente": [x for x in lignes if x["etat"] == "EN_COURS"],
                "observations_contestees": [x for x in lignes if x["contestee"]],
                "offres_expirees": [o for o in offres if o["etat"] == "expiree"], "offres": offres, "date": self.c.jour.isoformat(),
                "ia": self.c.ia.etat(), "mode": "monde de démonstration FICTIF · horloge simulée"}

