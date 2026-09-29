"""DÉTECTER : ce que le réseau pourrait faire maintenant, qu'il ne faisait pas hier.

Mécanismes (chacun produit des SIGNAUX sourcés ; aucune proximité ne suffit) :
- COMPLEMENTARITE  : un besoin publié, une personne qui déclare la capacité ;
- COMPOSITION      : un besoin à plusieurs capacités, le plus petit groupe qui les couvre toutes ;
- CONVERGENCE      : ≥ 3 besoins récents sur la même capacité → UNE action collective plutôt que 3 introductions ;
- LATENTE          : personne n'a rien publié, mais un intérêt DÉCLARÉ rencontre une capacité DÉCLARÉE, et un
                     « pourquoi maintenant » existe (événement commun proche et/ou intérêt réciproque) ;
- LACUNE           : ≥ 2 besoins bloqués par la même capacité absente — avec la plus petite levée qui débloquerait ;
- MEMOIRE          : un motif vérifié (effet confirmé) répond déjà : zéro personne à solliciter ;
- « capacité dormante » : marque une opportunité qui réveille un membre sans rencontre depuis 6 mois.
Chaque exclusion est comptée par raison (jamais nominative) : une opportunité peut ne pas exister.
"""
from __future__ import annotations

import hashlib
import time
from collections import Counter
from typing import Optional

from app.matching import _mots
from app.models import Besoin, Profil
from app.taxonomy import Taxonomie

from . import apprentissage
from .modele import BesoinActif, Contrainte, Opportunite, Reseau, Role, Signal
from .observateur import CONVERGENCE_MIN, PROFIL_OBSOLETE_JOURS, Etat, observer, pouls

ORDRE_CONFIANCE = {"elevee": 0, "moyenne": 1, "faible": 2}
RAISONS_SILENCIEUSES = {"vous-même", "même organisation"}


def _oid(*parts: str) -> str:
    return "o" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:10]


def _etapes(b: BesoinActif, auteur: Profil) -> list[str]:
    """Capacités demandées, sans les mots qui décrivent la propre activité du demandeur (« vin » pour une vigneronne)."""
    propres = {o.concept for o in auteur.offre if o.concept} | set(auteur.secteurs)
    toutes = list(dict.fromkeys(c.valeur for c in b.besoin.criteres if c.type == "expertise"))
    utiles = [c for c in toutes if c not in propres]
    return utiles or toutes


def _nom(e: Etat, pid: str) -> str:
    p = e.reseau.par_id().get(pid)
    return p.nom if p else pid


class Detecteur:
    def __init__(self, reseau: Reseau, tax: Taxonomie, exclus: Optional[set[str]] = None):
        self.r, self.tax = reseau, tax
        self.exclus = exclus or set()                 # membres retirés (perturbation, refus d'une activation…)
        self.e: Etat = observer(reseau, tax)
        self.ecartees: Counter = Counter()           # raison → nombre (jamais nominatif)
        self.paires_ecartees: list[tuple[str, str, str]] = []   # INTERNE (banc, audit) : jamais exposé à l'interface
        self.bloques: list[dict] = []

    # ------------------------------------------------------------------ fournisseurs éligibles d'une capacité
    def fournisseurs(self, beneficiaire: Profil, concept: str, besoin: Optional[Besoin] = None,
                     texte: str = "", introduction: bool = True) -> list[dict]:
        par_id = self.r.par_id()
        res = []
        for pid, extrait, nature in self.e.offreurs.get(concept, []):
            if pid == beneficiaire.id or pid in self.exclus:
                continue
            raison = self.e.exclusion(beneficiaire, par_id[pid], besoin, introduction)
            if raison:
                if raison not in RAISONS_SILENCIEUSES:
                    self.ecartees[raison] += 1
                self.paires_ecartees.append((beneficiaire.id, pid, raison))
                continue
            res.append({"id": pid, "extrait": extrait, "nature": nature, "dormant": self.e.dormant(pid)})
        # l'offre la plus SPÉCIFIQUE à la demande (mots communs), déclarée avant déduite, disponible maintenant avant
        # « disponible plus tard », profil le plus récent, puis identifiant (déterministe)
        demande = {m[:6] for m in _mots(texte or (besoin.texte if besoin else ""))}
        return sorted(res, key=lambda x: (-len(demande & {m[:6] for m in _mots(x["extrait"])}), x["nature"] != "declare",
                                          bool(par_id[x["id"]].note_disponibilite), self.e.age_profil(par_id[x["id"]]) or 0, x["id"]))

    def raisons_blocage(self, beneficiaire: Profil, concept: str, besoin: Optional[Besoin]) -> dict:
        """Capacité non couverte : absente du Club, ou présente mais écartée — et par quelle règle (comptes seulement)."""
        par_id = self.r.par_id()
        raisons: Counter = Counter()
        for pid, _, _ in self.e.offreurs.get(concept, []):
            if pid != beneficiaire.id:
                r = self.e.exclusion(beneficiaire, par_id[pid], besoin) or ("retiré du réseau" if pid in self.exclus else None)
                if r and r not in RAISONS_SILENCIEUSES:
                    raisons[r] += 1
        return {"absente": not raisons, "raisons": dict(sorted(raisons.items()))}

    # ------------------------------------------------------------------ mécanismes
    def _besoins(self) -> list[BesoinActif]:
        par_id = self.r.par_id()
        return [b for b in self.r.besoins if b.auteur in par_id and b.auteur not in self.exclus and b.le <= self.e.aujourd_hui]

    def detecter(self) -> dict:
        t0 = time.perf_counter()
        par_id = self.r.par_id()
        opps: dict[str, Opportunite] = {}
        besoins = self._besoins()
        mesures = dict(self.e.mesures)

        # 1. besoins publiés : mémoire vérifiée d'abord, puis complémentarité / composition
        par_concept: dict[str, list[tuple[BesoinActif, list[dict]]]] = {}
        for b in besoins:
            auteur = par_id[b.auteur]
            etapes = _etapes(b, auteur)
            if not etapes:
                continue
            couverts: dict[str, list[dict]] = {}
            for c in etapes:
                f = self.fournisseurs(auteur, c, b.besoin)
                couverts[c] = f
                par_concept.setdefault(c, []).append((b, f))
            memo = apprentissage.chercher(self.r.memoire, set(etapes), self.e.aujourd_hui, auteur.secteurs[0] if auteur.secteurs else None)
            if memo and set(etapes) <= set(memo[0]["couvre"]):
                self._ajouter(opps, self._memoire(b, auteur, etapes, memo[0]))
                continue
            couvrables = [c for c in etapes if couverts[c]]
            for c in etapes:
                if not couverts[c]:
                    self.bloques.append({"besoin": b.id, "auteur": b.auteur, "concept": c,
                                         **self.raisons_blocage(auteur, c, b.besoin)})
            if couvrables:
                self._ajouter(opps, self._composition(b, auteur, etapes, couverts))
        mesures["besoins_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        # 2. convergence et lacunes : plusieurs besoins sur la même capacité
        t1 = time.perf_counter()
        for c, lst in sorted(par_concept.items()):
            auteurs = sorted({b.auteur for b, _ in lst})
            if len(auteurs) >= CONVERGENCE_MIN:
                self._convergence(opps, c, lst)
            if len(auteurs) >= 2 and all(not f for _, f in lst):
                self._ajouter(opps, self._lacune(c, lst))
        # 3. latentes : intérêts déclarés, sans besoin publié, avec un « pourquoi maintenant »
        publies = {(b.auteur, c) for b in besoins for c in _etapes(b, par_id[b.auteur])}
        chercheurs = sorted({aid for lst in self.e.recherches.values() for aid, _ in lst})
        for aid in chercheurs:
            if aid in self.exclus or aid not in par_id:
                continue
            o = self._latente(par_id[aid], publies)
            if o:
                self._ajouter(opps, o)
        mesures["complementarite_ms"] = round((time.perf_counter() - t1) * 1000, 1)
        # une latente incluse dans une plus large (mêmes personnes, même événement) n'est pas une opportunité de plus
        latentes = [o for o in opps.values() if o.type == "LATENTE"]
        for k, o in list(opps.items()):
            ens = {r.membre for r in o.roles}
            hote = next((h for h in latentes if h is not o and h.evenement == o.evenement
                         and ens < {r.membre for r in h.roles}), None) if o.type == "LATENTE" else None
            if hote:
                hote.mecanismes.append(f"inclut l'intérêt de {_nom(self.e, o.beneficiaire or '')}")
                hote.demandes_servies = max(hote.demandes_servies, len(hote.roles) - 1)
                del opps[k]
        for o in opps.values():
            o.risques = self._risques(o)
        # rang : ce que l'action débloque (demandes servies), puis la solidité, puis l'urgence, puis le coût en attention
        liste = sorted(opps.values(), key=lambda o: (-o.demandes_servies, ORDRE_CONFIANCE[o.confiance],
                                                     o.evenement is None, o.personnes_a_solliciter, o.id))
        mesures["total_ms"] = round(sum(v for k, v in mesures.items() if k != "total_ms"), 1)
        return {"opportunites": liste, "ecartees": dict(sorted(self.ecartees.items())), "bloques": self.bloques,
                "pouls": pouls(self.e, besoins), "mesures": mesures, "membres": len(self.r.profils),
                "besoins": len(besoins), "date": self.e.aujourd_hui.isoformat()}

    def _risques(self, o: Opportunite) -> list[str]:
        """Pourquoi cette opportunité pourrait échouer — calculé, pas imaginé."""
        par_id = self.r.par_id()
        res = [f"capacité absente du Club : {m_}" for m_ in o.manque]
        benef = par_id.get(o.beneficiaire or "")
        dans = {r.membre for r in o.roles}
        for r in o.roles:
            if r.membre == o.beneficiaire or r.role in ("participant", "demandeur bloqué"):
                continue
            if self.e.dormant(r.membre):
                res.append(f"{par_id[r.membre].nom} n'a eu aucune rencontre depuis 6 mois : réponse incertaine")
            if benef and r.concept and not r.role.startswith("partenaire"):
                alt = [x for x in self.fournisseurs(benef, r.concept, introduction=False) if x["id"] not in dans]
                if not alt:
                    res.append(f"aucune alternative si {par_id[r.membre].nom} refuse")
        ev = next((e for e in self.r.evenements if e.id == o.evenement), None)
        if ev and (ev.le - self.e.aujourd_hui).days <= 14:
            res.append(f"fenêtre courte : {ev.nom} dans {(ev.le - self.e.aujourd_hui).days} jours")
        if o.confiance == "faible":
            res.append("une capacité n'est qu'affirmée dans une présentation, pas déclarée")
        return res

    def _ajouter(self, opps: dict[str, Opportunite], o: Optional[Opportunite]) -> None:
        if o is None:
            return
        cle = _oid("|".join(sorted(r.membre for r in o.roles)), "|".join(sorted(o.capacites)))
        if cle in opps:                               # même personnes, mêmes capacités : UNE opportunité
            if o.type not in opps[cle].mecanismes and o.type != opps[cle].type:
                opps[cle].mecanismes.append(o.type)
            return
        opps[cle] = o.model_copy(update={"id": cle})

    # ------------------------------------------------------------------ constructeurs
    def _fenetre(self, a: str, autres: list[str]) -> Optional[tuple[str, str]]:
        par_id = self.r.par_id()
        for ev in self.e.evenements_proches:
            if a in ev.participants and all(x in ev.participants for x in autres):
                qui = ", ".join(par_id[x].nom for x in [a, *autres] if x in par_id)
                return ev.id, f"{ev.nom}, le {ev.le.isoformat()} (dans {(ev.le - self.e.aujourd_hui).days} jours) : {qui} y sont inscrits"
        return None

    def _contraintes(self, b: BesoinActif) -> list[Contrainte]:
        res = [Contrainte(libelle=f"langue : {c.libelle}", statut="respectee") for c in b.besoin.criteres
               if c.type == "langue" and c.obligatoire]
        if b.besoin.exclure_concurrents:
            res.append(Contrainte(libelle="pas un concurrent direct", statut="respectee"))
        res.append(Contrainte(libelle="consentement des personnes sollicitées", statut="a_verifier"))
        return res

    def _composition(self, b: BesoinActif, auteur: Profil, etapes: list[str], couverts: dict[str, list[dict]]) -> Opportunite:
        # plus petit groupe (glouton de couverture, déterministe) ; une personne peut couvrir plusieurs étapes
        a_couvrir, choix = {c for c in etapes if couverts[c]}, {}
        while a_couvrir:
            cover: dict[str, list[str]] = {}
            for c in sorted(a_couvrir):
                for f in couverts[c]:
                    cover.setdefault(f["id"], []).append(c)
            meilleur = min(cover, key=lambda pid: (-len(cover[pid]), pid))
            for c in cover[meilleur]:
                choix[c] = meilleur
            a_couvrir -= set(cover[meilleur])
        manque = [c for c in etapes if c not in choix]
        tax = self.tax
        signaux = [Signal(source="besoin", membre=auteur.id, extrait=b.texte, le=b.le.isoformat())]
        roles = [Role(membre=auteur.id, role="bénéficiaire")]
        for c in etapes:
            if c in choix:
                f = next(x for x in couverts[c] if x["id"] == choix[c])
                signaux.append(Signal(source="offre", membre=f["id"], extrait=f["extrait"]))
                if not any(r.membre == f["id"] for r in roles):
                    roles.append(Role(membre=f["id"], role=f"contributeur : {tax.libelle(c)}", concept=c, preuve=f["extrait"]))
        contributeurs = [r.membre for r in roles[1:]]
        fen = self._fenetre(auteur.id, contributeurs)
        dormants = [x for x in contributeurs if self.e.dormant(x)]
        deduits = [c for c in choix if next(x for x in couverts[c] if x["id"] == choix[c])["nature"] != "declare"]
        typ = "COMPOSITION" if len(etapes) > 1 else "COMPLEMENTARITE"
        raisons = [f"{len(choix)}/{len(etapes)} capacité(s) couverte(s) par une offre {'déclarée' if not deduits else 'déclarée ou affirmée'}"]
        confiance = "elevee"
        if deduits:
            confiance = "moyenne"
            raisons.append("au moins une capacité seulement affirmée dans une présentation : à vérifier")
        if manque:
            confiance = "moyenne" if confiance == "elevee" else "faible"
            raisons.append(f"capacité manquante : {', '.join(tax.libelle(c) for c in manque)}")
        raisonnement = [f"{_nom(self.e, auteur.id)} a publié un besoin le {b.le.isoformat()}."]
        raisonnement += [f"{_nom(self.e, choix[c])} déclare : « {next(x for x in couverts[c] if x['id'] == choix[c])['extrait']} »."
                         for c in etapes if c in choix]
        raisonnement.append("Aucune règle dure violée : consentement, disponibilité, organisation, langue, concurrence, "
                            "profil récent, pas de refus antérieur.")
        if fen:
            raisonnement.append(f"Fenêtre : {fen[1]}.")
        if dormants:
            raisonnement.append(f"Réveille une capacité dormante ({', '.join(_nom(self.e, x) for x in dormants)} : aucune rencontre depuis 6 mois).")
        if manque:
            raisonnement.append(f"Reste bloquant : {', '.join(tax.libelle(c) for c in manque)} — personne d'éligible dans le Club.")
        return Opportunite(
            id="", type=typ, titre=" + ".join(tax.libelle(c) for c in etapes) + f" pour {_nom(self.e, auteur.id)}",
            declencheur=f"besoin publié : {len(etapes)} capacité(s) demandée(s)", pourquoi_maintenant=fen[1] if fen else f"besoin publié le {b.le.isoformat()}",
            signaux=signaux, roles=roles, capacites=etapes, manque=[tax.libelle(c) for c in manque],
            contraintes=self._contraintes(b), raisonnement=raisonnement,
            action=(f"Solliciter en privé {', '.join(_nom(self.e, x) for x in contributeurs)} "
                    f"({len(contributeurs)} personne(s)), chacun pour sa seule part."),
            consentements=[auteur.id, *contributeurs], confiance=confiance, confiance_raisons=raisons,
            demandes_servies=1, personnes_a_solliciter=len(contributeurs), besoin_id=b.id, beneficiaire=auteur.id,
            evenement=fen[0] if fen else None, mecanismes=["capacité dormante"] if dormants else [])

    def _memoire(self, b: BesoinActif, auteur: Profil, etapes: list[str], motif: dict) -> Opportunite:
        tax = self.tax
        contrib = motif["contributions"][0] if motif["contributions"] else {"titre": "séquence d'actions"}
        raisons = [f"{motif['confirmations']} confirmation(s) par un bénéficiaire, il y a {motif['age_jours']} jours"]
        if motif["differences"]:
            raisons += motif["differences"]
        return Opportunite(
            id="", type="MEMOIRE", titre=f"{' + '.join(tax.libelle(c) for c in etapes)} : déjà résolu dans le Club",
            declencheur="un besoin publié ressemble à un résultat confirmé", pourquoi_maintenant=f"besoin publié le {b.le.isoformat()}",
            signaux=[Signal(source="besoin", membre=auteur.id, extrait=b.texte, le=b.le.isoformat()),
                     Signal(source="memoire", extrait=f"{contrib['titre']} — effet confirmé ({motif['resultat']})", le=motif["le"])],
            roles=[Role(membre=auteur.id, role="bénéficiaire")], capacites=etapes,
            contraintes=[Contrainte(libelle=d, statut="a_verifier") for d in motif["differences"]],
            raisonnement=[f"{_nom(self.e, auteur.id)} a publié un besoin le {b.le.isoformat()}.",
                          f"Le Club a déjà débloqué ce type de besoin : « {contrib['titre']} », confirmé par la personne aidée.",
                          "Personne n'a besoin d'être sollicité pour transmettre une ressource vérifiée et partageable.",
                          *motif["differences"]],
            action=f"Transmettre « {contrib['titre']} » et demander à {_nom(self.e, auteur.id)} si cela débloque sa prochaine étape.",
            consentements=[auteur.id], confiance="elevee" if not motif["differences"] else "moyenne",
            confiance_raisons=raisons, demandes_servies=1, personnes_a_solliciter=0, besoin_id=b.id,
            beneficiaire=auteur.id, motif=motif["motif_id"])

    def _convergence(self, opps: dict[str, Opportunite], c: str, lst: list[tuple[BesoinActif, list[dict]]]) -> None:
        # une experte éligible pour le PLUS de demandeurs (règles dures appliquées à chacun)
        eligibles: Counter = Counter()
        extraits = {}
        for _, f in lst:
            for x in f:
                eligibles[x["id"]] += 1
                extraits[x["id"]] = x["extrait"]
        if not eligibles:
            return
        expert, n = min(eligibles.items(), key=lambda kv: (-kv[1], kv[0]))
        if n < CONVERGENCE_MIN:
            return
        servis = sorted({b.auteur for b, f in lst if any(x["id"] == expert for x in f)})
        for b, _ in lst:                                       # absorbe les introductions individuelles équivalentes
            for k in [k for k, o in opps.items() if o.besoin_id == b.id and o.capacites == [c] and o.type == "COMPLEMENTARITE"]:
                del opps[k]
        libelle = self.tax.libelle(c)
        dates = sorted(b.le for b, _ in lst if b.auteur in servis)
        self._ajouter(opps, Opportunite(
            id="", type="CONVERGENCE", titre=f"Atelier « {libelle} » : {len(servis)} demandes, une experte du Club",
            declencheur=f"{len(servis)} membres demandent la même capacité en {(dates[-1] - dates[0]).days + 1} jours",
            pourquoi_maintenant=f"demandes du {dates[0].isoformat()} au {dates[-1].isoformat()}",
            signaux=[Signal(source="besoin", membre=b.auteur, extrait=b.texte, le=b.le.isoformat()) for b, _ in lst if b.auteur in servis]
                    + [Signal(source="offre", membre=expert, extrait=extraits[expert])],
            roles=[Role(membre=a, role="participant") for a in servis]
                  + [Role(membre=expert, role=f"animatrice : {libelle}", concept=c, preuve=extraits[expert])],
            capacites=[c], raisonnement=[f"{len(servis)} besoins publiés portent sur « {libelle} ».",
                                         f"{_nom(self.e, expert)} déclare : « {extraits[expert]} ».",
                                         f"Une séance commune sollicite 1 personne au lieu de {len(servis)} introductions séparées.",
                                         "Chaque participant garde le choix de venir ; aucun ne voit les demandes des autres avant d'avoir accepté."],
            contraintes=[Contrainte(libelle="consentement de chaque participant", statut="a_verifier")],
            action=f"Proposer à {_nom(self.e, expert)} une séance de 45 minutes pour les {len(servis)} demandeurs.",
            consentements=[expert, *servis], confiance="elevee",
            confiance_raisons=[f"{len(servis)} besoins publiés, offre déclarée, règles dures respectées pour chacun"],
            demandes_servies=len(servis), personnes_a_solliciter=1, mecanismes=["capacité dormante"] if self.e.dormant(expert) else [],
            evenement=None, beneficiaire=None))

    def _lacune(self, c: str, lst: list[tuple[BesoinActif, list[dict]]]) -> Opportunite:
        par_id = self.r.par_id()
        libelle = self.tax.libelle(c)
        auteurs = sorted({b.auteur for b, _ in lst})
        raisons: Counter = Counter()
        for b, _ in lst:
            for k, v in self.raisons_blocage(par_id[b.auteur], c, b.besoin)["raisons"].items():
                raisons[k] += v
        presque = ", ".join(f"{k} ({v})" for k, v in sorted(raisons.items()))
        return Opportunite(
            id="", type="LACUNE", titre=f"Il manque au Club : {libelle}",
            declencheur=f"{len(auteurs)} demandes bloquées par la même capacité",
            signaux=[Signal(source="besoin", membre=b.auteur, extrait=b.texte, le=b.le.isoformat()) for b, _ in lst],
            roles=[Role(membre=a, role="demandeur bloqué") for a in auteurs], capacites=[c], manque=[libelle],
            raisonnement=[f"{len(auteurs)} besoins publiés demandent « {libelle} ».",
                          ("Personne dans le Club ne déclare cette capacité." if not raisons else
                           f"Des membres la déclarent mais une règle dure les écarte : {presque}."),
                          "Une introduction inventée serait pire que l'aveu du manque."],
            action=(f"Pour l'animatrice : inviter un·e prestataire « {libelle} » à rejoindre le Club, ou chercher à l'extérieur"
                    + (" ; ou lever la contrainte qui bloque, si les demandeurs l'acceptent." if raisons else ".")),
            consentements=[], confiance="elevee", confiance_raisons=["comptage des besoins bloqués"],
            demandes_servies=len(auteurs), personnes_a_solliciter=0)

    def _latente(self, a: Profil, publies: set[tuple[str, str]]) -> Optional[Opportunite]:
        """Tout ce que `a` déclare chercher (sans l'avoir publié), plus qui cherche ce que `a` produit — retenu seulement
        s'il existe un « pourquoi maintenant » : un événement proche commun, ou un intérêt réciproque déclaré."""
        par_id, tax = self.r.par_id(), self.tax
        interets = [r for r in a.recherche if not (r.concept and (a.id, r.concept) in publies)]
        age = self.e.age_profil(a)
        if not interets or not a.accepte_introductions or not a.disponible or age is None or age > PROFIL_OBSOLETE_JOURS:
            return None                               # sans demande de sa part, on ne sollicite que qui l'accepte
        offres_a = {o.concept for o in a.offre if o.concept} | set(a.secteurs)
        couverts: list[tuple[str, str, dict, Profil]] = []       # (concept, extrait de l'intérêt, fournisseur, profil)
        manque: list[str] = []
        for r in interets:
            f = self.fournisseurs(a, r.concept, texte=r.texte, introduction=False) if r.concept else []
            if not f:
                manque.append(r.texte if not r.concept else tax.libelle(r.concept))
                continue
            # préférer qui sera au même événement proche, puis qui cherche ce que `a` produit
            def cle(ix: tuple[int, dict]) -> tuple:
                b = par_id[ix[1]["id"]]
                recip = any(rr.concept and any(tax.meme_famille(rr.concept, o) for o in offres_a) for rr in b.recherche)
                return (self._fenetre(a.id, [b.id]) is None, not recip, ix[0])   # ix[0] : rang de spécificité
            x = min(enumerate(f), key=cle)[1]
            couverts.append((r.concept or "", r.texte, x, par_id[x["id"]]))
        if not couverts:
            return None
        # partenaires réciproques : cherchent ce que `a` produit (règles dures appliquées)
        reciproques: list[tuple[Profil, str]] = []
        for c in sorted(offres_a):
            for bid, texte in self.e.recherches.get(c, []):
                b = par_id.get(bid)
                if b and bid != a.id and bid not in self.exclus and not self.e.exclusion(a, b, introduction=False):
                    if (b, texte) not in reciproques:
                        reciproques.append((b, texte))
        contributeurs = list(dict.fromkeys(p.id for _, _, _, p in couverts))
        recip_utiles = [(b, t) for b, t in reciproques if b.id in contributeurs or self._fenetre(a.id, [b.id])]
        partenaires = contributeurs + [b.id for b, _ in recip_utiles if b.id not in contributeurs]
        fen = next((f_ for f_ in (self._fenetre(a.id, [x]) for x in partenaires) if f_), None)
        if not fen and not any(b.id in contributeurs for b, _ in recip_utiles):
            return None                               # intérêt + capacité, sans « pourquoi maintenant » : on se tait
        roles = [Role(membre=a.id, role="bénéficiaire")]
        signaux = [Signal(source="recherche", membre=a.id, extrait=t) for _, t, _, _ in couverts]
        signaux += [Signal(source="recherche", membre=a.id, extrait=m_) for m_ in manque]
        raisonnement = [f"{a.nom} indique dans son profil chercher : " + " ; ".join(f"« {t} »" for _, t, _, _ in couverts)
                        + " — sans avoir publié de demande."]
        for c, _, x, p in couverts:
            if not any(r_.membre == p.id for r_ in roles):
                roles.append(Role(membre=p.id, role=f"contributeur : {tax.libelle(c)}", concept=c, preuve=x["extrait"]))
            signaux.append(Signal(source="offre", membre=p.id, extrait=x["extrait"]))
            raisonnement.append(f"{p.nom} déclare : « {x['extrait']} ».")
        for b, t in recip_utiles:
            signaux.append(Signal(source="recherche", membre=b.id, extrait=t))
            raisonnement.append(f"{b.nom} cherche : « {t} » — exactement ce que {a.nom} produit.")
            if not any(r_.membre == b.id for r_ in roles):
                roles.append(Role(membre=b.id, role="partenaire : cherche ce que le bénéficiaire produit",
                                  preuve=t, concept=next((o for o in sorted(offres_a)), None)))
        ev = next((e for e in self.e.evenements_proches if e.id == fen[0]), None) if fen else None
        if fen and ev:
            signaux.append(Signal(source="evenement", extrait=fen[1], le=ev.le.isoformat()))
            raisonnement.append(f"Pourquoi maintenant : {fen[1]}.")
        ids_roles = [r_.membre for r_ in roles[1:]]
        suivis = [q for q in ids_roles if frozenset((a.id, q)) in self.e.relies]
        for q in suivis:
            quand, ou = self.e.relation_info[frozenset((a.id, q))]
            signaux.append(Signal(source="relation", membre=q, extrait=f"rencontre : {ou}", le=quand.isoformat()))
            raisonnement.append(f"{a.nom} a déjà rencontré {par_id[q].nom} ({ou}, le {quand.isoformat()}) : "
                                "c'est une suite à donner, pas une introduction.")
            for r_ in roles:
                if r_.membre == q:
                    r_.role = r_.role.split(" — ")[0] + " — suite d'une rencontre"
        nouveaux = [q for q in ids_roles if q not in suivis]
        raisonnement.append(("Aucune autre personne n'est déjà en relation avec " + a.nom if nouveaux and suivis else
                             "Aucun d'eux n'est déjà en relation avec " + a.nom if nouveaux else "Personne d'autre n'est sollicité")
                            + " ; aucune règle dure violée.")
        if manque:
            raisonnement.append("Reste bloquant : " + " ; ".join(manque) + " — personne d'éligible dans le Club.")
        declares = all(x["nature"] == "declare" for _, _, x, _ in couverts)
        confiance = "elevee" if (fen and recip_utiles and declares and not manque) else "moyenne" if declares else "faible"
        raisons = [r for r, ok in (("intérêt réciproque déclaré", recip_utiles), ("événement commun proche", fen),
                                   ("offres déclarées", declares)) if ok]
        raisons += [f"capacité manquante : {m_}" for m_ in manque]
        theme = next((c for c in (ev.themes if ev else ()) if c), None)
        sujet = tax.libelle(theme) if theme else " + ".join(tax.libelle(c) for c, _, _, _ in couverts)
        ids_partenaires = [r_.membre for r_ in roles[1:]]
        capacites = sorted({c for c, _, _, _ in couverts} | ({next(iter(sorted(offres_a)))} if recip_utiles else set()))
        return Opportunite(
            id="", type="SUIVI" if suivis else "LATENTE", titre=f"{sujet} : {a.nom}" + (f" — {ev.nom}" if ev else ""),
            declencheur=("une rencontre récente prend un sens nouveau" if suivis else
                         "intérêts déclarés dans des profils, sans demande publiée"),
            pourquoi_maintenant=fen[1] if fen else "intérêt réciproque déclaré",
            signaux=signaux, roles=roles, capacites=capacites, manque=manque, raisonnement=raisonnement,
            contraintes=[Contrainte(libelle="accord de chacun avant toute présentation", statut="a_verifier")]
                        + [Contrainte(libelle=f"manque : {m_}", statut="bloquante") for m_ in manque],
            action=(f"Demander d'abord à {a.nom} si c'est utile maintenant ; si oui, solliciter en privé "
                    + ", ".join(par_id[x].nom for x in ids_partenaires)
                    + (f" pour un rendez-vous de 20 minutes à « {ev.nom} »." if ev else " pour un échange de 20 minutes.")),
            consentements=[a.id, *ids_partenaires], confiance=confiance, confiance_raisons=raisons,
            demandes_servies=len(couverts) + len(recip_utiles), personnes_a_solliciter=len(ids_partenaires),
            beneficiaire=a.id, evenement=fen[0] if fen else None,
            mecanismes=["capacité dormante"] if any(self.e.dormant(x) for x in ids_partenaires) else [])


def scanner(reseau: Reseau, tax: Taxonomie, exclus: Optional[set[str]] = None) -> dict:
    return Detecteur(reseau, tax, exclus).detecter()

