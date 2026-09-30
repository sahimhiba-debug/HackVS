"""REGISTRE DES CAPACITÉS — ce que le Club PEUT faire ensemble, et la pièce qui lui manque pour le faire.

    patron (écrit par des humains)  ×  claims (offres datées, compétences déclarées)  ×  consentements de finalité
        ─→ `projeter(t)` : une INSTANCE par patron — recalculée, jamais stockée — avec sa distance (0 ou 1), ses
           liaisons, la pièce manquante, et son statut

Aucun second moteur : la composition est CELLE du banc d'essai (`Banc.solutions(None, …)`), avec ses règles (offre
active, durée, capacité, plage horaire DÉCLARÉE, contraintes numériques, une personne ↔ un emplacement, pas deux
engagements qui se chevauchent). Le consentement est l'ACCORD du banc, porté par une finalité (`consentir_finalite`).

Statuts (projection) :
  ONE_AWAY   il manque exactement UNE pièce : une Ask (demande minimale) la décrit ;
  PROPOSED   toutes les pièces existent (distance 0), aucun consentement de finalité encore donné ;
  CONSENTED  distance 0, consentements EN COURS de collecte (certains, pas tous) — distinct de PROPOSED dans le code :
             PROPOSED = rien n'est demandé, CONSENTED = au moins une personne a déjà dit oui pour CETTE finalité ;
  ACTIVE     distance 0 ET un consentement valable pour chaque pièce liée, à t. ACTIVE ≡ « AUTORISÉ » : le Club PEUT le
             faire ; l'exécution (EN_COURS) reste au niveau de l'accord d'un essai, le résultat au niveau de l'observation ;
  DEGRADED   un consentement donné pour cette finalité ne vaut plus (offre changée, retirée, expirée, finalité changée)
             et la capacité n'est plus active ;
  EXTINCT    la fenêtre du patron est passée.
  (distance ≥ 2 : aucune capacité n'est affichée — on n'expose que 0 et 1.)

Invariants (tests/test_capacites.py, tests/test_capacites_oracle.py) : ACTIVE ⇒ chaque composant couvre son
emplacement à t ET porte un consentement valable pour cette finalité ; l'instance est une projection (même journal ⇒
même projection) ; une claim expirée devient invalide mais reste dans l'index ; aucun appel au modèle de langage ici.
Données des patrons : FICTIVES, écrites comme si le Club les avait rédigées (`data/patrons/`).
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Callable, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.models import Profil
from plateforme.memoire import Memoire

from .erreurs import Conflit, Introuvable, Invalide
from .essai import HEURE, Banc, Creneau, Etape, Nature, OffreVolontaire, Plage, Protocole

DOSSIER_PATRONS = Path(__file__).resolve().parents[1] / "data" / "patrons"
StatutCapacite = Literal["ONE_AWAY", "PROPOSED", "CONSENTED", "ACTIVE", "DEGRADED", "EXTINCT"]
_MACHINE = re.compile(r"\b(ia|ai|llm|gpt|claude|apertus|mod[eè]le|g[eé]n[eé]r[eé])\b", re.I)
PARTAGE_FINALITE = ("Votre offre n'est utilisée que pour cette capacité, jusqu'à la date indiquée. Aucune autre personne "
                    "n'est nommée à l'écran commun ; vous pouvez retirer ce consentement.")


# ---------------------------------------------------------------------- patrons (écrits par des HUMAINS)
class Emplacement(BaseModel):
    id: str = Field(pattern=r"^[a-z_]{2,8}$")          # = identifiant du geste composé par le banc (8 caractères au plus)
    role: str = Field(min_length=2, max_length=24)
    nature: Nature
    concept: Optional[str] = Field(default=None, max_length=64)
    libelle: str = Field(min_length=3, max_length=120)             # « Un minibus de 12 places ou plus »
    geste: str = Field(min_length=3, max_length=200)
    minimums: dict[str, int] = Field(default_factory=dict, max_length=4)


class Fenetre(BaseModel):
    jour: date
    debut: str = Field(pattern=HEURE)
    fin: str = Field(pattern=HEURE)


class Patron(BaseModel):
    """Une recette de capacité : des emplacements typés et contraints, une fenêtre, une durée. Rédigée par une
    personne (`auteur`), jamais par un modèle de langage ; versionnée (un consentement porte sur UNE version)."""
    id: str = Field(pattern=r"^[a-z_]{3,40}$")
    version: int = Field(ge=1)
    titre: str = Field(min_length=5, max_length=120)
    auteur: str = Field(min_length=3, max_length=120)
    fictif: bool
    fenetre: Fenetre
    duree_min: int = Field(ge=15, le=120)
    emplacements: list[Emplacement] = Field(min_length=2, max_length=4)

    @model_validator(mode="after")
    def _coherence(self) -> "Patron":
        ids = [e.id for e in self.emplacements]
        if len(set(ids)) != len(ids):
            raise ValueError("deux emplacements portent le même identifiant")
        if _MACHINE.search(self.auteur):
            raise ValueError("un patron est rédigé par une personne, jamais par un modèle")
        Plage(jour=self.fenetre.jour, debut=self.fenetre.debut, fin=self.fenetre.fin)     # ordre des heures
        return self

    def protocole(self, sans: Optional[str] = None, garder_seul: Optional[str] = None) -> Protocole:
        """Le patron comme protocole à composer par le banc (emplacements = gestes), éventuellement privé d'un
        emplacement (`sans`) ou réduit à un seul (`garder_seul`)."""
        f = self.fenetre
        etapes = [Etape(id=e.id, nature=e.nature, geste=e.geste, duree_min=self.duree_min, concept=e.concept, role=e.role[:24],
                        minimums=e.minimums) for e in self.emplacements if e.id != sans and (garder_seul is None or e.id == garder_seul)]
        return Protocole(question=self.titre, echeance=f.jour, etapes=etapes, fenetre=Plage(jour=f.jour, debut=f.debut, fin=f.fin))

    def portee(self, emplacement: str) -> dict:
        """Ce qu'une personne accepte en consentant : cette finalité (patron, version), SON emplacement, la fenêtre."""
        e = next(x for x in self.emplacements if x.id == emplacement)
        return {"finalite": self.id, "version": self.version, "titre": self.titre, "emplacement": e.model_dump(mode="json"),
                "fenetre": self.fenetre.model_dump(mode="json"), "duree_min": self.duree_min, "partage": PARTAGE_FINALITE}


def charger_patrons(dossier: Path = DOSSIER_PATRONS, concepts: Optional[set[str]] = None) -> list[Patron]:
    """Patrons validés (schéma, cohérence, capacités du catalogue). Un fichier invalide fait ÉCHOUER le chargement."""
    res = []
    for f in sorted(dossier.glob("*.json")):
        p = Patron(**json.loads(f.read_text(encoding="utf-8")))
        inconnus = {e.concept for e in p.emplacements if e.concept} - (concepts if concepts is not None else {e.concept for e in p.emplacements if e.concept})
        if inconnus:
            raise ValueError(f"{f.name} : capacité hors catalogue : {sorted(inconnus)}")
        res.append(p)
    if len({p.id for p in res}) != len(res):
        raise ValueError("deux patrons portent le même identifiant")
    return res


# ---------------------------------------------------------------------- claims : index BI-TEMPOREL (projection du journal)
class Claim(BaseModel):
    """Un fait déclaré par un membre, avec son temps de VALIDITÉ (du/au, plages) et son temps d'ENREGISTREMENT
    (position dans le journal ; remplacé par une version ultérieure ou un retrait). Jamais supprimé : une claim
    expirée ou remplacée reste dans l'index, et cesse seulement d'être valable."""
    id: str
    kind: Literal["NEED", "SKILL", "RESOURCE", "SLOT"]
    membre: str
    concept: Optional[str] = None
    texte: str
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    recorded_at: int                                   # seq du fait (0 : monde de départ, données préparées)
    superseded_at: Optional[int] = None                # seq de la version suivante ou du retrait
    provenance: Literal["SELF_DECLARED", "AI_PROPOSED_CONFIRMED"] = "SELF_DECLARED"
    statut: str                                        # SYNTHETIQUE / DECLARE / JOUE (journal)
    plages: list[Plage] = Field(default_factory=list)

    def valable(self, t: date, vu_au: Optional[int] = None) -> bool:
        """Valable au temps t, tel que le journal le savait à la position `vu_au` (None : aujourd'hui)."""
        connu = vu_au is None or self.recorded_at <= vu_au
        pas_remplace = self.superseded_at is None or (vu_au is not None and self.superseded_at > vu_au)
        dans_la_periode = (self.valid_from is None or self.valid_from <= t) and (self.valid_until is None or t <= self.valid_until)
        return connu and pas_remplace and dans_la_periode


def _nature_kind(o: OffreVolontaire) -> Literal["SKILL", "RESOURCE"]:
    return "RESOURCE" if o.nature in ("lieu", "objet") else "SKILL"


def index_claims(m: Memoire, profils_de_depart: dict[str, Profil]) -> list[Claim]:
    """Toutes les versions de toutes les claims : offres (RESOURCE/SKILL, leurs plages = SLOT) et déclarations de profil
    (compétences = SKILL, intérêts = NEED), du monde de départ puis du journal. Pur : même journal ⇒ même index."""
    res: list[Claim] = []
    ouvertes: dict[str, Claim] = {}                   # clé stable → version courante (pour la remplacer)

    def ouvrir(cle: str, c: Claim) -> None:
        if cle in ouvertes:
            ouvertes[cle].superseded_at = c.recorded_at
        ouvertes[cle] = c
        res.append(c)

    def fermer(cle: str, seq: int) -> None:
        if cle in ouvertes and ouvertes[cle].superseded_at is None:
            ouvertes[cle].superseded_at = seq
        ouvertes.pop(cle, None)

    def profil(pid: str, champs: dict, seq: int, statut: str) -> None:
        for k, kind in (("offre", "SKILL"), ("recherche", "NEED")):
            if k not in champs:
                continue
            neufs = {f"profil:{pid}:{kind}:{x.get('concept') or x['texte'][:40]}": x for x in champs[k]}
            for cle in [c for c in ouvertes if c.startswith(f"profil:{pid}:{kind}:") and c not in neufs]:
                fermer(cle, seq)
            for cle, x in neufs.items():
                ancien = ouvertes.get(cle)
                if ancien is None or ancien.texte != x["texte"]:
                    ouvrir(cle, Claim(id=f"{cle}@{seq}", kind=kind, membre=pid, concept=x.get("concept"), texte=x["texte"],  # type: ignore[arg-type]
                                      recorded_at=seq, statut=statut))

    for pid in sorted(profils_de_depart):
        p = profils_de_depart[pid]
        profil(pid, p.model_dump(mode="json", include={"offre", "recherche"}), 0, "SYNTHETIQUE")
    for e in m.evenements("OFFRE", "OFFRE_RETIREE", "PROFIL"):
        if e.type == "PROFIL":
            profil(e.donnees["membre"], e.donnees["champs"], e.seq, e.statut.value)
        elif e.type == "OFFRE_RETIREE":
            fermer(f"offre:{e.donnees['offre']}", e.seq)
        else:
            o = OffreVolontaire(**e.donnees["offre"])
            ouvrir(f"offre:{o.id}", Claim(id=f"{o.id}@v{o.version}", kind=_nature_kind(o), membre=o.auteur, concept=o.concept,
                                          texte=o.quoi, valid_from=o.du, valid_until=o.au, recorded_at=e.seq, statut=e.statut.value,
                                          plages=o.plages))
    return res


# ---------------------------------------------------------------------- instances (projection) et Ask
class HypotheticalClaim(BaseModel):
    """Une pièce IMAGINÉE (« et si quelqu'un offrait… ») : typée à part, jamais écrite au journal, jamais consentie, ne
    réserve rien. Sert au « et si » de la démonstration et au LEVIER d'une demande — calculés par le même compositeur."""
    nature: Nature
    concept: Optional[str] = Field(default=None, max_length=64)
    quoi: str = Field(default="pièce hypothétique", min_length=3, max_length=200)
    attributs: dict[str, int] = Field(default_factory=dict, max_length=4)
    plages: list[Plage] = Field(min_length=1, max_length=8)
    du: date
    au: date

    def offre(self, n: int) -> OffreVolontaire:
        return OffreVolontaire(id=f"hyp-{n}", auteur=f"HYPOTHESE-{n}", nature=self.nature, quoi=self.quoi, capacite=1, du=self.du,
                               au=self.au, concept=self.concept, plages=self.plages, attributs=self.attributs)


class Ask(BaseModel):
    """Une demande MINIMALE : la seule pièce qui manque, pour un créneau précis, adressée à une CATÉGORIE (jamais à une
    personne choisie par le système), limitée dans le temps."""
    id: str
    finalite: str
    titre: str
    emplacement: str
    libelle: str
    nature: str
    concept: Optional[str]
    minimums: dict[str, int]
    creneau: Creneau
    expire: date
    texte: str
    levier: int = 1                                      # capacités qui deviendraient composables avec CETTE pièce
    debloque: list[str] = Field(default_factory=list)    # leurs titres


class Instance(BaseModel):
    finalite: str
    version: int
    titre: str
    fictif: bool
    statut: Optional[StatutCapacite]                     # None : distance ≥ 2 (non exposée)
    distance: Optional[int]                              # 0 ou 1 ; None au-delà
    creneau: Optional[Creneau] = None
    liaisons: dict[str, Optional[str]] = Field(default_factory=dict)       # emplacement → offre
    consentements: dict[str, Optional[str]] = Field(default_factory=dict)  # emplacement → None (valable) ou raison
    manquant: Optional[str] = None
    ask: Optional[Ask] = None
    perdus: list[str] = Field(default_factory=list)      # consentements donnés pour cette finalité qui ne valent plus
    hypotheses: list[str] = Field(default_factory=list)
    # DEGRADED : ce que le moteur propose pour recomposer (calculé, jamais appliqué) — ou, s'il n'y a rien de sûr,
    # « aucune solution sûre » dit honnêtement : la cause, ce qu'on sait, ce qu'on ignore, ce qui débloquerait
    recomposition: Optional[dict] = None
    sans_solution: Optional[dict] = None
    # pièces liées SANS lesquelles la capacité ne se compose plus (contrefactuel calculé : « si elle disparaît, tient-elle ? »)
    critiques: list[str] = Field(default_factory=list)
    hypothetique: bool = False                           # projection calculée sous une hypothèse (« et si ») : jamais un état


def _texte_ask(p: Patron, e: Emplacement, c: Creneau) -> str:
    return (f"{e.libelle} ? Le {c.texte()}. Votre réponse rendrait possible « {p.titre} ». "
            f"Usage jusqu'au {p.fenetre.jour.strftime('%d.%m')}.")


def pulse_diff(avant: list[Instance], apres: list[Instance]) -> dict:
    """Ce qui a changé dans ce que le Club PEUT faire entre deux projections (chacune obtenue par REJEU du journal) :
    apparues (devenues actives), éteintes (actives avant, plus maintenant), recomposées (actives des deux côtés, autres
    pièces), fragiles (actives avec au moins une pièce critique), à une pièce près (nouvellement). En titres et statuts
    seulement — jamais une personne."""
    a = {i.finalite: i for i in avant}
    res: dict[str, list[dict]] = {"apparues": [], "eteintes": [], "recomposees": [], "fragiles": [], "a_une_piece": []}
    for i in apres:
        j = a.get(i.finalite)
        ligne = {"finalite": i.finalite, "titre": i.titre, "avant": j.statut if j else None, "apres": i.statut}
        actif_avant = j is not None and j.statut == "ACTIVE"
        if i.statut == "ACTIVE" and not actif_avant:
            res["apparues"].append(ligne)
        if actif_avant and i.statut != "ACTIVE":
            res["eteintes"].append(ligne)
        if actif_avant and i.statut == "ACTIVE" and j is not None and j.liaisons != i.liaisons:
            res["recomposees"].append(ligne)
        if i.statut == "ACTIVE" and i.critiques:
            res["fragiles"].append(ligne | {"pieces_critiques": len(i.critiques)})
        if i.statut == "ONE_AWAY" and (j is None or j.statut != "ONE_AWAY"):
            res["a_une_piece"].append(ligne)
    return res


def choisir_asks(instances: list[Instance], n: int) -> list[Instance]:
    """Les `n` demandes à montrer : le plus fort LEVIER d'abord (une pièce qui débloque plusieurs capacités), puis la
    plus proche de son expiration, puis un ordre stable. Jamais une personne choisie : une catégorie compatible."""
    avec = [i for i in instances if i.ask is not None]
    return sorted(avec, key=lambda i: (-i.ask.levier, i.ask.expire, i.finalite))[:n]  # type: ignore[union-attr]


class Registre:
    """Projection des capacités et les deux commandes de la Phase 1 (répondre à une Ask ; consentir pour une finalité).
    Lit et écrit le journal du banc — un seul journal, un seul compositeur."""

    def __init__(self, banc: Banc, patrons: list[Patron], jour: Callable[[], date]):
        self.b, self.patrons, self._jour = banc, {p.id: p for p in patrons}, jour

    def patron(self, finalite: str) -> Patron:
        if finalite not in self.patrons:
            raise Introuvable("capacité inconnue")
        return self.patrons[finalite]

    def retires(self, finalite: str) -> set[str]:
        """Les PIÈCES (offres) retirées pour cette finalité : jamais liées à nouveau pour elle. La personne, elle, n'est
        pas exclue : une nouvelle déclaration avec un nouveau consentement reste possible (accord n+1)."""
        return self.b.pieces_retirees(finalite)

    def _consentements(self, p: Patron) -> tuple[dict[str, list[OffreVolontaire]], list[str]]:
        """Par emplacement : les offres qu'un consentement VALABLE met à disposition de cette finalité ; et la liste des
        consentements donnés qui ne valent plus (en rôles : emplacement et raison — jamais qui)."""
        valables: dict[str, list[OffreVolontaire]] = {}
        perdus = []
        for e in self.b.consentements_finalite(p.id):
            emp = e.donnees["emplacement"]
            if emp not in {x.id for x in p.emplacements}:
                continue
            raison = self.b.raison_consentement(e, p.portee(emp))
            if raison is None:
                valables.setdefault(emp, []).append(self.b.offre(e.donnees["offre"]))
            else:
                perdus.append(f"{emp} : {raison}")
        ordre = [e.id for e in p.emplacements]                # l'ordre du PATRON, jamais celui des membres
        return valables, sorted(perdus, key=lambda x: ordre.index(x.split(" : ", 1)[0]))

    def instance(self, p: Patron) -> Instance:
        base = {"finalite": p.id, "version": p.version, "titre": p.titre, "fictif": p.fictif}
        hyp = ["disponibilités et attributs DÉCLARÉS par les membres, non vérifiés par le système"]
        if p.fenetre.jour < self._jour():
            return Instance(**base, statut="EXTINCT", distance=None, hypotheses=["la fenêtre de cette capacité est passée"])
        tronquees = self.b.recherches_tronquees
        inst = self._instance(p, base, hyp)
        if self.b.recherches_tronquees != tronquees:
            inst.hypotheses.append("recherche bornée atteinte : une composition a pu échapper au calcul (absence non garantie)")
        return inst

    def _instance(self, p: Patron, base: dict, hyp: list[str]) -> Instance:
        inst = self._composer(p, base, hyp)
        if inst.statut == "DEGRADED":
            self._recomposer(p, inst)
        if inst.distance == 0:
            inst.critiques = self._critiques(p, inst)
        return inst

    def _critiques(self, p: Patron, inst: Instance) -> list[str]:
        """Contrefactuel, par le compositeur : sans CETTE pièce liée, une composition existe-t-elle encore ?"""
        exclus = self.retires(p.id)
        tous = {o.id for o in self.b.offres(publiques=True) if o.id not in exclus}
        res = []
        for k, oid in inst.liaisons.items():
            if oid is None:
                continue
            permis = {e.id: tous - {oid} for e in p.emplacements}
            if not self.b.solutions(None, p.protocole(), maximum=1, permis=permis):
                res.append(k)
        return res

    # ------------------------------------------------------------------ « et si » (I3) et levier (I1)
    def status_if(self, hypotheses: list[HypotheticalClaim]) -> list[Instance]:
        """La projection SI ces pièces étaient déclarées — sans rien écrire, sans consentement : au mieux « composable,
        en attente de consentement ». Chaque instance rendue est marquée `hypothetique`."""
        avant = self.b.m.empreinte()
        with self.b.hypothese([h.offre(i) for i, h in enumerate(hypotheses, start=1)]):
            res = [i.model_copy(update={"hypothetique": True}) for i in self._projeter(levier=False)]
        assert self.b.m.empreinte() == avant, "une hypothèse a écrit dans le journal"
        return res

    def levier(self, ask: Ask) -> tuple[int, list[str]]:
        """Combien de capacités deviennent composables (distance 0) avec LA pièce demandée — calculé par le compositeur
        partagé sous hypothèse, jamais par une boucle à part."""
        h = HypotheticalClaim(nature=ask.nature, concept=ask.concept, quoi=ask.libelle, attributs=dict(ask.minimums),  # type: ignore[arg-type]
                              plages=[Plage(jour=ask.creneau.jour, debut=ask.creneau.debut, fin=ask.creneau.fin)],
                              du=self._jour(), au=ask.expire)
        avant = {i.finalite: i.distance for i in self._projeter(levier=False)}
        apres = [i for i in self.status_if([h]) if i.distance == 0 and avant.get(i.finalite) != 0]
        return len(apres), [i.titre for i in apres]

    def _recomposer(self, p: Patron, inst: Instance) -> None:
        """Ce qui peut remplacer la pièce perdue — calculé par le même compositeur, jamais appliqué : une personne décide."""
        libelle = {e.id: e.libelle for e in p.emplacements}
        role = {e.id: e.role for e in p.emplacements}
        if inst.distance == 0:
            pieces = [k for k, r in inst.consentements.items() if r is not None]
            inst.recomposition = {"type": "consentir", "pieces": pieces, "a_decider": ["la personne qui offre cette pièce"],
                                  "texte": "Une autre pièce existe pour : " + ", ".join(libelle[k] for k in pieces)
                                           + ". Elle ne comptera qu'avec le consentement de la personne qui l'offre."}
        elif inst.distance == 1:
            inst.recomposition = {"type": "demander", "pieces": [inst.manquant], "a_decider": ["un membre qui répond à la demande"],
                                  "texte": f"Il manque de nouveau : {libelle[inst.manquant or '']}. Une demande est adressée "
                                           "aux membres qui peuvent la fournir."}
        else:
            exclus = self.retires(p.id)
            seules = {e.id: bool(self.b.solutions(None, p.protocole(garder_seul=e.id), maximum=1, permis=self._permis(p, exclus, [e.id])))
                      for e in p.emplacements}
            manquent = [libelle[k] for k, ok in seules.items() if not ok]
            inst.sans_solution = {
                "cause": [f"{role[x.split(' : ', 1)[0]]} : ce composant n'est plus disponible" for x in inst.perdus],
                "sait": [f"{libelle[k]} : au moins une pièce déclarée couvre la fenêtre" for k, ok in seules.items() if ok],
                "ignore": ["si d'autres membres pourraient fournir " + (", ".join(manquent) or "les pièces restantes au même moment")
                           + " : personne ne l'a déclaré pour cette fenêtre"],
                "debloquerait": [f"{x} le {p.fenetre.jour.strftime('%d.%m')} entre {p.fenetre.debut} et {p.fenetre.fin}" for x in manquent]
                                or ["des disponibilités qui se recouvrent sur un même créneau"]}

    def _permis(self, p: Patron, exclus: set[str], emplacements: Optional[list[str]] = None) -> Optional[dict[str, set[str]]]:
        """Offres utilisables pour cette finalité : toutes, sauf les pièces retirées pour elle (None : aucune restriction)."""
        if not exclus:
            return None
        ids = {o.id for o in self.b.offres(publiques=True) if o.id not in exclus}
        return {k: ids for k in (emplacements or [e.id for e in p.emplacements])}

    def _composer(self, p: Patron, base: dict, hyp: list[str]) -> Instance:
        valables, perdus = self._consentements(p)
        exclus = self.retires(p.id)
        ids = {k: {o.id for o in v} for k, v in valables.items()}
        garder: dict[str, Optional[OffreVolontaire]] = {e.id: valables[e.id][0] if valables.get(e.id) else None for e in p.emplacements}

        def consentis(choix: dict[str, Optional[str]]) -> dict[str, Optional[str]]:
            return {k: (None if v is not None and v in ids.get(k, set()) else
                        "consentement à demander" if v is not None else "pièce manquante") for k, v in choix.items()}
        # ACTIVE : existe-t-il une composition dont CHAQUE pièce est consentie pour cette finalité (à n'importe quel
        # créneau de la fenêtre) ? Sinon : la composition libre qui garde le plus de consentements.
        sol = self.b.solutions(None, p.protocole(), maximum=1, garder=garder, permis=ids) if len(ids) == len(p.emplacements) else []
        if not sol:
            toutes = self.b.solutions(None, p.protocole(), maximum=10_000, garder=garder, permis=self._permis(p, exclus))
            sol = sorted(toutes, key=lambda x: -sum(1 for r in consentis(x["choix"]).values() if r is None))[:1]
        if sol:
            choix = sol[0]["choix"]
            cons = consentis(choix)
            n = sum(1 for x in cons.values() if x is None)
            statut: StatutCapacite = ("ACTIVE" if n == len(cons) else "DEGRADED" if perdus else "CONSENTED" if n else "PROPOSED")
            return Instance(**base, statut=statut, distance=0, creneau=sol[0]["creneau"], liaisons=choix, consentements=cons,
                            perdus=perdus, hypotheses=hyp)
        for e in p.emplacements:                        # distance 1 : sans CET emplacement, le reste se compose-t-il ?
            sous = self.b.solutions(None, p.protocole(sans=e.id), maximum=1, garder={k: v for k, v in garder.items() if k != e.id},
                                    permis=self._permis(p, exclus, [x.id for x in p.emplacements if x.id != e.id]))
            if sous:
                c = sous[0]["creneau"]
                ask = Ask(id=f"{p.id}:{p.version}:{e.id}:{c.jour.isoformat()}:{c.debut}", finalite=p.id, titre=p.titre, emplacement=e.id,
                          libelle=e.libelle, nature=e.nature, concept=e.concept, minimums=e.minimums, creneau=c, expire=p.fenetre.jour,
                          texte=_texte_ask(p, e, c))
                choix = sous[0]["choix"] | {e.id: None}
                return Instance(**base, statut="DEGRADED" if perdus else "ONE_AWAY", distance=1, creneau=c, liaisons=choix,
                                consentements=consentis(choix), manquant=e.id, ask=ask, perdus=perdus, hypotheses=hyp)
        return Instance(**base, statut="DEGRADED" if perdus else None, distance=None, perdus=perdus, hypotheses=hyp)

    def projeter(self) -> list[Instance]:
        return self._projeter(levier=True)

    def _projeter(self, levier: bool) -> list[Instance]:
        res = [self.instance(p) for p in sorted(self.patrons.values(), key=lambda x: x.id)]
        if levier:
            for i in res:
                if i.ask is not None:
                    n, titres = self.levier(i.ask)
                    i.ask.levier, i.ask.debloque = n, titres
        return res

    # ------------------------------------------------------------------ commandes
    def repondre(self, membre: str, ask_id: str, oui: bool, attributs: Optional[dict[str, int]] = None,
                 quoi: Optional[str] = None, competences: Optional[set[str]] = None) -> Instance:
        """Répondre à une Ask. « Oui » = déclarer SA pièce (une offre datée, pour le créneau demandé, avec ses attributs)
        ET consentir à son usage pour CETTE finalité jusqu'à la fin de la fenêtre — rien de plus. « Non » : journalisé,
        sans effet sur personne, jamais attribué. L'Ask est relue AU MOMENT de répondre : si elle n'existe plus (une autre
        réponse l'a déjà comblée), refus — une seule liaison, déterministe."""
        finalite = ask_id.split(":", 1)[0]
        p = self.patron(finalite)
        inst = self.instance(p)
        if inst.ask is None or inst.ask.id != ask_id:
            raise Conflit("cette demande n'est plus d'actualité : la pièce a déjà été trouvée, ou la capacité a changé")
        ask = inst.ask
        e = next(x for x in p.emplacements if x.id == ask.emplacement)
        with self.b.m.transaction():
            if not oui:
                self.b._ecrire("ASK_REPONSE", [membre], ask=ask_id, oui=False)
                return self.instance(p)
            if e.concept is not None and e.concept not in (competences or set()):
                raise Invalide("capacité non déclarée dans votre profil : ajoutez-la d'abord à « je peux aider »")
            attributs = {k: v for k, v in (attributs or {}).items() if k in e.minimums}
            manque = [f"{k} ≥ {v}" for k, v in e.minimums.items() if attributs.get(k, 0) < v]
            if manque:
                raise Invalide("ne couvre pas la demande : " + ", ".join(manque))
            c = ask.creneau
            oid = self.b.publier_offre(membre, e.nature, (quoi or e.libelle)[:200], 1, self._jour(), p.fenetre.jour, concept=e.concept,
                                       conditions=f"déclarée en réponse à une demande pour « {p.titre[:80]} »", attributs=attributs,
                                       plages=[Plage(jour=c.jour, debut=c.debut, fin=c.fin)])
            self.b.consentir_finalite(membre, p.id, e.id, oid, p.portee(e.id), p.fenetre.jour)
            self.b._ecrire("ASK_REPONSE", [membre], ask=ask_id, oui=True, offre=oid)
            apres = self.instance(p)
            if apres.liaisons.get(e.id) != oid:                  # la pièce déclarée ne comble pas : rien n'est écrit
                raise Conflit("votre réponse ne complète pas cette capacité (horaire ou attributs) : rien n'a été enregistré")
        return apres

    def retirer(self, membre: str, finalite: str) -> Instance:
        """Retirer, en un geste, tous ses consentements pour cette finalité. La capacité est recalculée à la projection
        suivante : dégradée, recomposée si possible — jamais attribuée à la personne qui s'est retirée."""
        p = self.patron(finalite)
        miens = [e for e in self.b.consentements_finalite(p.id) if e.acteurs[0] == membre and e.type == "ACCORD"]
        if not miens:
            raise Introuvable("aucun consentement en cours pour cette capacité")
        nees_d_une_reponse = {e.donnees.get("offre") for e in self.b.m.evenements("ASK_REPONSE") if e.acteurs[0] == membre}
        with self.b.m.transaction():
            for e in miens:
                self.b.retirer_finalite(membre, p.id, e.donnees["emplacement"])
                oid = e.donnees["offre"]
                # une pièce DÉCLARÉE en répondant à cette demande n'avait pas d'autre raison d'être : elle meurt aussi
                if oid in nees_d_une_reponse and self.b.etat_offre(oid) != "retiree":
                    self.b.retirer_offre(membre, oid)
        return self.instance(p)

    def recus(self, membre: str) -> list[dict]:
        """Les REÇUS de TOUS ses consentements, dans l'ordre : finalité, portée, depuis quand, jusqu'à quand, état. Un
        accord retiré le reste pour toujours ; un nouvel accord (n+1) a son propre reçu."""
        res = []
        evs = [e for e in self.b.m.evenements("ACCORD", "RETRAIT") if e.acteurs[0] == membre and e.donnees.get("finalite")]
        compte: dict[tuple[str, str], int] = {}
        for i, accord in enumerate(evs):
            if accord.type != "ACCORD" or accord.donnees["finalite"] not in self.patrons:
                continue
            p = self.patrons[accord.donnees["finalite"]]
            cle = (p.id, accord.donnees["emplacement"])
            compte[cle] = compte.get(cle, 0) + 1
            retrait = next((x for x in evs[i + 1:] if x.type == "RETRAIT" and x.donnees["finalite"] == p.id
                            and x.donnees["offre"] == accord.donnees["offre"]), None)
            emp = next((x for x in p.emplacements if x.id == accord.donnees["emplacement"]), None)
            if retrait is not None:
                raison: Optional[str] = "consentement retiré"
            elif emp is None:
                raison = "cette pièce n'existe plus dans la capacité"
            else:
                raison = self.b.raison_consentement(accord, p.portee(emp.id))
            res.append({"finalite": p.id, "titre": p.titre, "version": accord.donnees["portee"]["version"], "accord": compte[cle],
                        "piece": emp.libelle if emp else accord.donnees["portee"]["emplacement"]["libelle"],
                        "offre": self.b.offre(accord.donnees["offre"]).quoi, "donne_le": accord.le.isoformat(),
                        "jusqu_au": accord.donnees["jusqu_au"], "fenetre": accord.donnees["portee"]["fenetre"],
                        "partage": accord.donnees["portee"]["partage"], "reference": accord.donnees["empreinte"][:12] + f"-{accord.seq}",
                        "etat": "valable" if raison is None else raison,
                        "retire_le": retrait.le.isoformat() if retrait else None, "revocable": raison is None})
        return res

    def consentir(self, membre: str, finalite: str) -> Instance:
        """Un membre dont l'offre est LIÉE à une capacité composée consent à son usage pour cette finalité."""
        p = self.patron(finalite)
        inst = self.instance(p)
        emp = next((k for k, v in inst.liaisons.items() if v is not None and self.b.offre(v).auteur == membre), None)
        if emp is None or inst.distance is None:
            raise Introuvable("aucune de vos offres ne compose cette capacité aujourd'hui")
        if inst.consentements.get(emp) is None:
            return inst                                        # déjà consenti : idempotent
        self.b.consentir_finalite(membre, p.id, emp, inst.liaisons[emp], p.portee(emp), p.fenetre.jour)  # type: ignore[arg-type]
        return self.instance(p)
