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
from .essai import HEURE, NATURES, Banc, Creneau, Etape, Nature, OffreVolontaire, Plage, Protocole

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

    def protocole(self, sans: Optional[str] = None) -> Protocole:
        """Le patron comme protocole à composer par le banc (emplacements = gestes), éventuellement privé d'un emplacement."""
        f = self.fenetre
        etapes = [Etape(id=e.id, nature=e.nature, geste=e.geste, duree_min=self.duree_min, concept=e.concept, role=e.role[:24],
                        minimums=e.minimums) for e in self.emplacements if e.id != sans]
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


def _texte_ask(p: Patron, e: Emplacement, c: Creneau) -> str:
    return (f"{e.libelle} ? Le {c.texte()}. Votre réponse rendrait possible « {p.titre} ». "
            f"Usage jusqu'au {p.fenetre.jour.strftime('%d.%m')}.")


class Registre:
    """Projection des capacités et les deux commandes de la Phase 1 (répondre à une Ask ; consentir pour une finalité).
    Lit et écrit le journal du banc — un seul journal, un seul compositeur."""

    def __init__(self, banc: Banc, patrons: list[Patron], jour: Callable[[], date]):
        self.b, self.patrons, self._jour = banc, {p.id: p for p in patrons}, jour

    def patron(self, finalite: str) -> Patron:
        if finalite not in self.patrons:
            raise Introuvable("capacité inconnue")
        return self.patrons[finalite]

    def _consentements(self, p: Patron) -> tuple[dict[str, OffreVolontaire], list[str]]:
        """Par emplacement : l'offre qu'un consentement VALABLE met à disposition de cette finalité ; et la liste des
        consentements donnés qui ne valent plus (en rôles : emplacement et raison — jamais qui)."""
        valables: dict[str, OffreVolontaire] = {}
        perdus = []
        for e in self.b.consentements_finalite(p.id):
            emp = e.donnees["emplacement"]
            if emp not in {x.id for x in p.emplacements}:
                continue
            raison = self.b.raison_consentement(e, p.portee(emp))
            if raison is None:
                valables.setdefault(emp, self.b.offre(e.donnees["offre"]))
            else:
                perdus.append(f"{emp} : {raison}")
        return valables, perdus

    def instance(self, p: Patron) -> Instance:
        base = {"finalite": p.id, "version": p.version, "titre": p.titre, "fictif": p.fictif}
        hyp = ["disponibilités et attributs DÉCLARÉS par les membres, non vérifiés par le système"]
        if p.fenetre.jour < self._jour():
            return Instance(**base, statut="EXTINCT", distance=None, hypotheses=["la fenêtre de cette capacité est passée"])
        valables, perdus = self._consentements(p)
        garder: dict[str, Optional[OffreVolontaire]] = {e.id: valables.get(e.id) for e in p.emplacements}
        sol = self.b.solutions(None, p.protocole(), maximum=1, garder=garder)
        if sol:
            choix = sol[0]["choix"]
            cons = {k: (None if valables.get(k) is not None and valables[k].id == v else "consentement à demander") for k, v in choix.items()}
            n = sum(1 for x in cons.values() if x is None)
            statut: StatutCapacite = ("ACTIVE" if n == len(cons) else "DEGRADED" if perdus else "CONSENTED" if n else "PROPOSED")
            return Instance(**base, statut=statut, distance=0, creneau=sol[0]["creneau"], liaisons=choix, consentements=cons,
                            perdus=perdus, hypotheses=hyp)
        for e in p.emplacements:                        # distance 1 : sans CET emplacement, le reste se compose-t-il ?
            sous = self.b.solutions(None, p.protocole(sans=e.id), maximum=1, garder={k: v for k, v in garder.items() if k != e.id})
            if sous:
                c = sous[0]["creneau"]
                ask = Ask(id=f"{p.id}:{p.version}:{e.id}:{c.jour.isoformat()}:{c.debut}", finalite=p.id, titre=p.titre, emplacement=e.id,
                          libelle=e.libelle, nature=e.nature, concept=e.concept, minimums=e.minimums, creneau=c, expire=p.fenetre.jour,
                          texte=_texte_ask(p, e, c))
                choix = sous[0]["choix"] | {e.id: None}
                cons = {k: (None if v is not None and valables.get(k) is not None and valables[k].id == v else
                            "consentement à demander" if v is not None else "pièce manquante") for k, v in choix.items()}
                return Instance(**base, statut="DEGRADED" if perdus else "ONE_AWAY", distance=1, creneau=c, liaisons=choix,
                                consentements=cons, manquant=e.id, ask=ask, perdus=perdus, hypotheses=hyp)
        return Instance(**base, statut="DEGRADED" if perdus else None, distance=None, perdus=perdus, hypotheses=hyp)

    def projeter(self) -> list[Instance]:
        return [self.instance(p) for p in sorted(self.patrons.values(), key=lambda x: x.id)]

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


def libelle_nature(n: str) -> str:
    return NATURES.get(n, n)
