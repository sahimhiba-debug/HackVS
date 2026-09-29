"""Projections de lecture de Club Pulse : ce qu'UN spectateur voit (membre, animatrice), rendu par la politique.

Séparation commandes / requêtes : `ClubPulse` possède l'état et exécute les gestes ; `Vues` ne modifie jamais l'état
métier (seule trace écrite : l'appel d'IA qui rédige une sollicitation, journalisé pour l'audit). Toute sortie vers un
humain passe par `Rendu` — aucune identité n'y figure sans que la politique de visibilité l'autorise.
"""
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import networkx as nx

from app.models import Offre

from . import apprentissage
from .activation import FINAUX
from .erreurs import Interdit, Introuvable
from .modele import Opportunite
from .politique import Spectateur

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

LIBELLES_TYPE = {"LATENTE": "Opportunité latente", "SUIVI": "Suite d'une rencontre", "COMPOSITION": "Composition",
                 "COMPLEMENTARITE": "Complémentarité", "CONVERGENCE": "Besoin émergent", "LACUNE": "Manque du Club",
                 "MEMOIRE": "Mémoire vérifiée", "CAPACITE_DORMANTE": "Capacité dormante"}
LIBELLES_ETAT = {"DETECTEE": "détectée", "EVALUEE": "évaluée", "PLANIFIEE": "planifiée", "EN_ATTENTE_ACCORD": "en attente d'accord",
                 "ACTIVEE": "activée", "TERMINEE": "contributions reçues", "BLOQUEE": "bloquée", "REPLANIFICATION": "replanification",
                 "ALTERNATIVE_PROPOSEE": "alternative proposée", "ABANDONNEE": "arrêtée faute d'alternative", "REJETEE": "rejetée",
                 "RESULTAT_CONFIRME": "demande débloquée", "RESULTAT_PARTIEL": "partiellement débloquée",
                 "RESULTAT_NEGATIF": "non débloquée", "RESULTAT_INCONNU": "résultat inconnu", "EN_PAUSE": "en pause", "ANNULEE": "annulée"}


class Vues:
    def __init__(self, club: "ClubPulse"):
        self.c = club

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

    def _vue_note(self, pid: str, note: dict) -> dict:
        rendu = self.c.rendu()
        return note | {"avec_nom": rendu.nom(Spectateur("membre", pid), note["avec"]) if note["avec"] else None}

    def notes_de(self, pid: str) -> list[dict]:
        return [self._vue_note(pid, n) for n in self.c.notes.get(pid, [])]

    def _vue_blocage(self, x: dict) -> dict:
        lib = self.c.tax.libelle(x["concept"]) if x["concept"] in self.c.tax.concepts else x["concept"]
        if x["absente"]:
            pourquoi = f"Le Club ne compte aujourd'hui personne qui déclare : {lib}."
            suite = "Signalé à l'animatrice ; précisez si une autre compétence proche vous aiderait."
        else:
            pourquoi = f"Des membres déclarent « {lib} », mais une règle les écarte : " + ", ".join(f"{k} ({v})" for k, v in x["raisons"].items()) + "."
            suite = "La plus petite modification : lever cette contrainte, si elle n'est pas indispensable."
        return {"capacite": lib, "pourquoi": pourquoi, "prochaine_action": suite}

    def vue_opportunite(self, o: Opportunite, sp: Spectateur) -> dict:
        rendu = self.c.rendu()
        t = lambda x: rendu.texte(sp, x)  # noqa: E731
        if sp.role == "membre" and sp.id != o.beneficiaire and sp.id not in {r.membre for r in o.roles if r.role == "participant"}:
            raise Interdit("cette opportunité ne vous concerne pas (encore) : vous serez sollicité·e en privé si elle est activée")
        roles = [{"qui": rendu.nom(sp, r.membre), "role": r.role, "capacite": self.c.tax.libelle(r.concept) if r.concept else None,
                  "preuve": r.preuve if sp.role == "animatrice" or r.membre == sp.id else None}
                 for r in o.roles if r.membre != sp.id]
        return {"id": o.id, "type": o.type, "type_libelle": LIBELLES_TYPE.get(o.type, o.type), "titre": t(o.titre),
                "pourquoi_maintenant": t(o.pourquoi_maintenant or ""), "pourquoi": [t(x) for x in o.raisonnement],
                "manque": o.manque, "action": t(o.action), "risques": [t(x) for x in o.risques], "confiance": o.confiance,
                "confiance_raisons": o.confiance_raisons, "demandes_servies": o.demandes_servies,
                "personnes_a_solliciter": o.personnes_a_solliciter, "capacites": [self.c.tax.libelle(c) for c in o.capacites if c in self.c.tax.concepts],
                "roles": roles, "mecanismes": [t(x) for x in o.mecanismes],
                "evenement": next((e.nom for e in self.c.r.evenements if e.id == o.evenement), None),
                "partage": ("Avant tout accord : votre secteur et ce que vous cherchez, rien d'autre. Votre nom seulement aux personnes "
                            "qui acceptent ; vos coordonnées seulement après accord mutuel."),
                "activable": o.type != "LACUNE"}

    def demandes_pour(self, pid: str) -> list[dict]:
        """Sollicitations privées ouvertes pour ce membre, avec un message rédigé (IA contrôlée ou gabarit)."""
        res = []
        rep = {k for a in self.c.moteur.activations() for k in self.c.moteur._reponses(a)}
        for ev in self.c.r.memoire.evenements("SOLLICITATION_PRIVEE"):
            aid = ev.donnees["aid"]
            if ev.acteurs[0] != pid or (ev.donnees["etape"], pid) in rep or self.c.moteur.etat(aid) in FINAUX:
                continue
            res.append(self.vue_demande(aid, pid))
        return res

    def vue_demande(self, aid: str, pid: str) -> dict:
        v = self.c.moteur.vue_membre(aid, pid)
        opp = self.c.moteur.opportunite(aid)
        sp = Spectateur("membre", pid)
        rendu = self.c.rendu()
        etape = next(e for e in self.c.moteur.plan(aid)["etapes"] if e.get("membre") == pid and (e["id"], pid) in self.c.moteur._sollicitations(aid))
        est_benef = opp.beneficiaire == pid
        benef = self.c.r.par_id().get(opp.beneficiaire or "")
        capa = next((o.texte for o in self.c.profil(pid).offre if o.concept == etape.get("concept")), None)
        message = None
        cle = (aid, etape["id"], pid)
        if not est_benef and benef and cle not in self.c.messages:
            # rédigé UNE fois par sollicitation puis mémorisé : relire la page ne rappelle pas le modèle (coût, latence)
            # et n'ajoute rien au journal (une lecture répétée reste sans effet)
            per = self.c.coffre.identite(benef.id)
            faits = {"capacite_declaree": capa or etape["libelle"], "demande": etape["demande"],
                     "secteur_demandeur": self.c.tax.libelle(benef.secteurs[0]) if benef.secteurs else "non précisé",
                     "partage": "votre nom et votre courriel à cette personne seulement si vous acceptez ; rien si vous refusez"}
            r_ = self.c.ia.rediger_sollicitation(faits, [per.nom if per else "", self.c.coffre.pseudonyme(benef.id)])
            self.c.messages[cle] = {"texte": r_.sortie["message"], "ia": r_.appel.model_dump(include={"fournisseur", "modele", "statut", "repli"})}
        if not est_benef and benef:
            message = self.c.messages[cle]
        return {"activation": aid, "etat": self.c.moteur.etat(aid), "pour_vous": est_benef,
                "titre": ("Le Club a repéré une occasion pour vous" if est_benef else "Un membre du Club a une demande qui correspond à votre capacité"),
                "pourquoi_vous": (None if est_benef else f"Votre capacité déclarée : « {capa or etape['libelle']} »"),
                "qui_demande": rendu.texte(sp, v["qui_demande"]) if v["qui_demande"] else None,
                "votre_part": v["votre_part"], "accepte": v["accepte"], "creneaux_communs": v["creneaux_communs"],
                "ce_qui_serait_fait": v.get("ce_qui_serait_fait"),
                "visibilite": ("Votre identité reste cachée tant que vous n'avez pas accepté. Si vous refusez, personne ne le saura."
                               if not est_benef else "Rien n'est transmis à personne avant votre accord."),
                "message": message}

    def vue_activation(self, aid: str, sp: Spectateur) -> dict:
        opp = self.c.moteur.opportunite(aid)
        participants = {e.get("membre") for e in self.c.moteur.plan(aid)["etapes"] if e.get("membre")}
        if sp.role == "membre" and sp.id not in participants:
            raise Introuvable("activation inconnue")
        rendu = self.c.rendu()
        etat = self.c.moteur.etat(aid)
        chrono = [{"etat": j["etat"], "libelle": LIBELLES_ETAT.get(j["etat"], j["etat"]), "le": j["le"],
                   "agent": j["agent"], "raison": rendu.texte(sp, j["raison"]) if sp.role == "animatrice" else self._raison_publique(j)}
                  for j in self.c.moteur.journal(aid)]
        contribs = [{"qui": rendu.nom(sp, e.acteurs[0]), "nature": e.donnees["nature"], "titre": e.donnees["titre"],
                     "contenu": e.donnees["contenu"], "le": e.le.isoformat()} for e in self.c.moteur._evs(aid, "CONTRIBUTION_RECUE")]
        vue = {"id": aid, "numero": self.c.moteur.activations().index(aid) + 1, "etat": etat, "etat_libelle": LIBELLES_ETAT.get(etat, etat),
               "objectif": rendu.texte(sp, opp.titre), "type": LIBELLES_TYPE.get(opp.type, opp.type), "chronologie": chrono,
               "resultat": self.c.moteur.resultat(aid), "contributions": contribs if sp.role == "animatrice" or sp.id == opp.beneficiaire else
               [c for c, e in zip(contribs, self.c.moteur._evs(aid, "CONTRIBUTION_RECUE"), strict=True) if e.acteurs[0] == sp.id],
               "anonyme": self.c.moteur.plan(aid)["anonyme"]}
        if sp.role == "animatrice":
            vue["etapes"] = []
            for e in self.c.moteur.plan(aid)["etapes"]:
                statut = self._statut_etape(aid, e)
                cache = statut == "a décliné"             # même le Club ne sait pas QUI a dit non
                vue["etapes"].append({"etape": e["libelle"], "type": e["type"], "statut": "une personne a décliné" if cache else statut,
                                      "qui": None if cache or not e.get("membre") else rendu.nom(sp, e["membre"]),
                                      "question": e.get("question"), "reserve": len(e.get("alternatives") or [])})
        elif sp.id is not None and sp.id == opp.beneficiaire:
            vb = self.c.moteur.vue_beneficiaire(aid, sp.id)
            vue["etapes"] = [{"etape": x["etape"], "statut": rendu.texte(sp, x["statut"])} for x in vb["etapes"]]
            vue["contacts"] = [{"qui": rendu.nom(sp, x), "contact": rendu.contact(sp, x)} for x in sorted(participants - {sp.id})
                               if rendu.contact(sp, x)]
            vue["a_confirmer"] = etat in ("TERMINEE", "RESULTAT_INCONNU")
            vue["reutilisation"] = opp.type == "MEMOIRE" and etat == "ACTIVEE"
        elif sp.id is not None:
            vue["etapes"] = [{"etape": x["libelle"], "statut": "votre part"} for x in self.c.moteur.vue_membre(aid, sp.id)["votre_part"]]
            vue["peut_contribuer"] = etat == "ACTIVEE" and not any(e.acteurs[0] == sp.id for e in self.c.moteur._evs(aid, "CONTRIBUTION_RECUE"))
        vue["evolution"] = self.evolution(aid, sp) if etat in ("TERMINEE", "RESULTAT_CONFIRME", "RESULTAT_PARTIEL", "RESULTAT_INCONNU") else None
        return vue

    @staticmethod
    def _raison_publique(j: dict) -> str:
        return {"BLOQUEE": "Une personne sollicitée n'est pas disponible : le Club cherche une alternative.",
                "REPLANIFICATION": "Le plan est recalculé.", "ALTERNATIVE_PROPOSEE": "Une alternative a été trouvée et sollicitée en privé.",
                "ABANDONNEE": "Aucune alternative éligible : l'activation s'arrête proprement.",
                }.get(j["etat"], LIBELLES_ETAT.get(j["etat"], j["etat"]).capitalize() + ".")

    def _statut_etape(self, aid: str, e: dict) -> str:
        if e["type"] == "hors_club":
            return "à trouver hors du Club"
        if not e.get("membre"):
            return ""
        rep, sol = self.c.moteur._reponses(aid), self.c.moteur._sollicitations(aid)
        k = (e["id"], e["membre"])
        if any(x.donnees["etape"] == e["id"] for x in self.c.moteur._evs(aid, "CONTRIBUTION_RECUE")):
            return "contribution reçue"
        if k in rep:
            return "a accepté" if rep[k].donnees["accepte"] else "a décliné"
        return "sollicité·e en privé" if k in sol else "pas encore sollicité·e"

    def activations_de(self, pid: str) -> list[dict]:
        sp = Spectateur("membre", pid)
        res = []
        for aid in self.c.moteur.activations():
            p = self.c.moteur.plan(aid)
            opp = Opportunite(**p["opportunite"])
            engage = opp.beneficiaire == pid or any(k[1] == pid and v.donnees["accepte"] for k, v in self.c.moteur._reponses(aid).items())
            if engage:
                res.append(self.vue_activation(aid, sp))
        return res

    def evolution(self, aid: str, sp: Spectateur) -> dict:
        opp = self.c.moteur.opportunite(aid)
        # Seules figurent les personnes ENGAGÉES (bénéficiaire, et qui a accepté). Lister tous les rôles de l'opportunité
        # révélait qui avait été sollicité — donc, par différence, qui avait décliné (défaut trouvé par le banc).
        engages = {k[1] for k, v in self.c.moteur._reponses(aid).items() if v.donnees["accepte"]}
        noeuds = [x for x in dict.fromkeys([opp.beneficiaire or "", *(r.membre for r in opp.roles),
                                            *(e["membre"] for e in self.c.moteur.plan(aid)["etapes"] if e.get("membre"))])
                  if x and (x == opp.beneficiaire or x in engages)]
        limite = self.c.jour - timedelta(days=365)
        g_avant, g_apres = nx.Graph(), nx.Graph()
        for ev in self.c.r.memoire.evenements("RENCONTRE", "COLLABORATION"):
            if len(ev.acteurs) < 2 or ev.le < limite:
                continue
            g_apres.add_edge(*ev.acteurs[:2])
            if not (ev.type == "COLLABORATION" and ev.donnees.get("aid") == aid):
                g_avant.add_edge(*ev.acteurs[:2])
        b = opp.beneficiaire
        rendu = self.c.rendu()
        nouveaux = [(ev.acteurs[0], ev.acteurs[1]) for ev in self.c.r.memoire.evenements("COLLABORATION") if ev.donnees.get("aid") == aid]
        return {"noeuds": [{"cle": f"n{i}", "nom": rendu.nom(sp, x), "beneficiaire": x == b} for i, x in enumerate(noeuds)],
                "liens_avant": [[f"n{noeuds.index(a)}", f"n{noeuds.index(c)}"] for a, c in g_avant.subgraph(noeuds).edges()],
                "liens_nouveaux": [[f"n{noeuds.index(a)}", f"n{noeuds.index(c)}"] for a, c in nouveaux if a in noeuds and c in noeuds],
                "relations_beneficiaire": {"avant": g_avant.degree(b) if b in g_avant else 0, "apres": g_apres.degree(b) if b in g_apres else 0},
                "reseau_atteignable": {"avant": len(nx.node_connected_component(g_avant, b)) if b in g_avant else 1,
                                       "apres": len(nx.node_connected_component(g_apres, b)) if b in g_apres else 1},
                "phrase": f"Cette activation a créé {len(nouveaux)} collaboration(s) confirmée(s) par une contribution reçue."}

    def memoire_club(self, sp: Spectateur) -> list[dict]:
        rendu = self.c.rendu()
        res = []
        for x in apprentissage.motifs(self.c.r.memoire, self.c.jour):
            res.append({"id": x["motif_id"], "capacites": [self.c.tax.libelle(c) for c in x["concepts"]],
                        "resultat": x["resultat"], "confirmations": x["confirmations"], "age_jours": x["age_jours"], "frais": x["frais"],
                        "secteur": self.c.tax.libelle(x["secteur"]) if x["secteur"] else None, "sequence": x["sequence"],
                        "ressources": [{"titre": c["titre"], "auteur": rendu.nom(sp, c["auteur"]) if c.get("attribution") and c.get("auteur") else "anonyme",
                                        "telecharger": f"/api/pulse/memoire/{x['motif_id']}/fiche"} for c in x["contributions"] if c.get("reutilisable")],
                        "statut": x["statut"],
                        "visibilite": "motif anonymisé : ni le bénéficiaire, ni les contributeurs sans leur accord"})
        return res

    def fiche(self, motif_id: str) -> str:
        x = next((m for m in apprentissage.motifs(self.c.r.memoire, self.c.jour) if m["motif_id"] == motif_id), None)
        c = next((c for c in (x or {}).get("contributions", []) if c.get("reutilisable")), None)
        if x is None or c is None:
            raise Introuvable("aucune ressource partageable pour ce motif")
        per = self.c.coffre.identite(c.get("auteur", "")) if c.get("attribution") else None
        return (f"{c['titre']}\n{'=' * len(c['titre'])}\n\n{c['contenu']}\n\n---\nProvenance : contribution de "
                f"{per.nom if per else 'un membre (anonyme à sa demande)'} ; effet confirmé par le bénéficiaire "
                f"({x['confirmations']} confirmation(s), la dernière il y a {x['age_jours']} jours). Le bénéficiaire n'est pas nommé.\n"
                f"DONNÉES FICTIVES — monde de démonstration Club Pulse, dates simulées. Statut : {x['statut']}.\n")

    def pouls_membre(self, pid: str) -> dict:
        sp = Spectateur("membre", pid)
        per = self.c.coffre.identite(pid)
        items = []
        for d in self.demandes_pour(pid):
            items.append({"type": "contribution" if not d["pour_vous"] else "accord", "titre": d["titre"], "cible": d["activation"],
                          "detail": d["pourquoi_vous"] or "Rien n'est transmis avant votre accord."})
        for o in self.c.scanner()["opportunites"]:
            if o.beneficiaire == pid:
                v = self.vue_opportunite(o, sp)
                items.append({"type": "opportunite", "titre": v["titre"], "cible": o.id, "detail": v["pourquoi_maintenant"],
                              "etiquette": v["type_libelle"]})
        for a in self.activations_de(pid):
            if a["etat"] not in FINAUX or a["etat"] in ("RESULTAT_CONFIRME", "RESULTAT_PARTIEL"):
                items.append({"type": "activation", "titre": f"Activation n°{a['numero']} : {a['etat_libelle']}", "cible": a["id"],
                              "detail": a["objectif"]})
        for ev in self.c.r.evenements:
            if pid in ev.participants and 0 <= (ev.le - self.c.jour).days <= 30:
                items.append({"type": "evenement", "titre": ev.nom, "cible": ev.id,
                              "detail": f"dans {(ev.le - self.c.jour).days} jours : préparez vos rencontres"})
        motifs = self.memoire_club(sp)
        if motifs:
            items.append({"type": "memoire", "titre": f"{len(motifs)} résultat(s) vérifié(s) dans la mémoire du Club", "cible": "memoire",
                          "detail": "ce qui a vraiment aidé, anonymisé"})
        return {"bonjour": per.nom.split()[0] if per else "", "date": self.c.jour.isoformat(), "items": items,
                "ia": self.c.ia.etat(), "fictif": True}

    def tour(self) -> dict:
        scan = self.c.scanner()
        acts = self.c.moteur.activations()
        etats = {a: self.c.moteur.etat(a) for a in acts}
        attention = [a for a, e in etats.items() if e in ("BLOQUEE", "ALTERNATIVE_PROPOSEE", "RESULTAT_INCONNU", "ABANDONNEE", "EN_PAUSE")]
        manques: dict[str, set[str]] = {}
        for o in scan["opportunites"]:
            for m_ in o.manque:
                manques.setdefault(m_, set()).update({o.beneficiaire or r.membre for r in o.roles})
        for x in scan["bloques"]:
            lib = self.c.tax.libelle(x["concept"]) if x["concept"] in self.c.tax.concepts else x["concept"]
            manques.setdefault(lib, set()).add(x["auteur"])
        intervention = max(manques.items(), key=lambda kv: (len(kv[1]), kv[0]), default=None)
        sp = Spectateur("animatrice")
        motifs = apprentissage.motifs(self.c.r.memoire, self.c.jour)
        return {
            "date": self.c.jour.isoformat(), "monde": self.c.r.nom, "ia": self.c.ia.etat(),
            "situation": [
                {"cle": "opportunites", "valeur": len(scan["opportunites"]), "libelle": "opportunités actives"},
                {"cle": "attention", "valeur": len(attention), "libelle": "demandent une attention humaine"},
                {"cle": "en_cours", "libelle": "activations en cours",
                 "valeur": sum(1 for e in etats.values() if e not in FINAUX and e not in ("TERMINEE", "RESULTAT_INCONNU"))},
                {"cle": "confirmees", "libelle": "demandes débloquées",
                 "valeur": sum(1 for e in etats.values() if e in ("RESULTAT_CONFIRME", "RESULTAT_PARTIEL"))},
                {"cle": "motifs", "valeur": sum(1 for x in motifs if x["frais"]), "libelle": "motifs vérifiés"},
                {"cle": "sans_solution", "valeur": len(scan["bloques"]), "libelle": "demandes sans solution dans le Club"}],
            "priorites": [self.vue_opportunite(o, sp) for o in scan["opportunites"][:3]],
            "toutes": [{"id": o.id, "type": LIBELLES_TYPE.get(o.type, o.type), "titre": self.c.rendu().texte(sp, o.titre),
                        "confiance": o.confiance, "demandes_servies": o.demandes_servies} for o in scan["opportunites"]],
            "intervention": ({"capacite": intervention[0], "demandes": len(intervention[1]),
                              "phrase": f"Trouver 1 compétence — {intervention[0]} — débloquerait {len(intervention[1])} demande(s) ou opportunité(s)."}
                             if intervention else None),
            "phases": scan["phases"], "ecartees": scan["ecartees"],
            "activations": [{"id": a, "numero": i + 1, "etat": etats[a], "etat_libelle": LIBELLES_ETAT.get(etats[a], etats[a]),
                             "objectif": self.c.rendu().texte(sp, self.c.moteur.opportunite(a).titre)} for i, a in enumerate(acts)],
            "adhesions": {"source": self.c.coffre.source, "synthetique": self.c.coffre.synthetique, "organisations": len(self.c.coffre.orgs),
                          "adhesions": len(self.c.coffre.adhesions),
                          "cartes_entreprise": sum(1 for a in self.c.coffre.adhesions.values() if a.formule == "entreprise"),
                          "personnes": len(self.c.coffre._personnes), "comptes_actives": len(self.c.coffre.actives),
                          "api_club": "non connectée (autorisation et accès technique du Club requis)"},
            "appels_ia": [a.model_dump(exclude={"controle"}) for a in self.c.ia.appels[-12:]]}

    def evenements_de(self, pid: str) -> list[dict]:
        """Avant / pendant / après chaque événement à venir, pour ce membre."""
        c = self.c
        scan = c.scanner()
        sp = Spectateur("membre", pid)
        res = []
        for ev in sorted(c.r.evenements, key=lambda e: e.le):
            if (ev.le - c.jour).days < 0:
                continue
            inscrit = pid in ev.participants
            a_preparer = [self.vue_opportunite(o, sp) for o in scan["opportunites"]
                          if o.evenement == ev.id and o.beneficiaire == pid] if inscrit else []
            res.append({"id": ev.id, "nom": ev.nom, "le": ev.le.isoformat(), "dans_jours": (ev.le - c.jour).days,
                        "inscrit": inscrit, "participants": len(ev.participants), "avant": a_preparer,
                        "pendant": "Notez vos rencontres : la note reste privée.",
                        "apres": "Les suites utiles apparaîtront dans votre pouls."})
        return res
