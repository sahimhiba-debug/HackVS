"""Adhésions et identités : le Club existe déjà ; Club Pulse ACTIVE des comptes, il n'inscrit personne de zéro.

    Système d'adhésion du Club ─→ FournisseurAdhesions ─→ Coffre (identités) ─→ compte Club Pulse (pseudonyme)

- `FournisseurAdhesions` : l'interface d'import. Implémentations : `AdhesionsSynthetiques` (prototype),
  `AdhesionsCSV` (export fourni par le Club), `AdhesionsAPIClub` (FUTURE : non connectée — aucun accès au système
  réel du Club n'existe ; l'appeler le dit).
- Modèle : Organisation → Adhésion (nominative ou carte entreprise) → Personne (membre nommé ou représentant·e
  délégué·e) → rôle et portée d'accès.
- `Coffre` : SEUL endroit où vivent nom, organisation, courriel et téléphone. Le moteur d'intelligence reçoit des
  profils PSEUDONYMISÉS (« MEMBRE-042 ») : il raisonne sur des capacités, jamais sur des identités. Supprimer une
  identité du coffre rend le journal (ajout seul) illisible pour cette personne : effacement par destruction du lien.
- Accès : code d'invitation (QR) vérifié → compte activé. Prototype : codes dérivés d'un secret local ; en production,
  le Club émet les invitations depuis son système d'adhésion (lien magique ou code).
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import os
from typing import Literal, Optional, Protocol

from pydantic import BaseModel

from app.matching import organisation as cle_organisation
from app.models import Profil

Formule = Literal["nominative", "entreprise"]
RoleCompte = Literal["membre", "representant", "animatrice"]


class Organisation(BaseModel):
    id: str
    nom: str
    secteur: Optional[str] = None


class Adhesion(BaseModel):
    id: str
    organisation_id: str
    formule: Formule                 # « entreprise » : cartes non nominatives, portées par des représentant·es
    statut: Literal["active", "suspendue"] = "active"


class Personne(BaseModel):
    id: str                          # identifiant interne stable (jamais montré)
    adhesion_id: str
    role: RoleCompte = "membre"
    nom: str
    courriel: str
    telephone: str = ""


class Import(BaseModel):
    source: str
    synthetique: bool
    organisations: list[Organisation]
    adhesions: list[Adhesion]
    personnes: list[Personne]
    avertissements: list[str] = []


class FournisseurAdhesions(Protocol):
    nom: str

    def importer(self) -> Import: ...


class AdhesionsSynthetiques:
    """Prototype : adhésions dérivées d'un réseau SYNTHÉTIQUE. Une organisation à plusieurs personnes = carte entreprise."""
    nom = "synthétique"

    def __init__(self, profils: list[Profil]):
        self.profils = profils

    def importer(self) -> Import:
        orgs: dict[str, Organisation] = {}
        membres: dict[str, list[Profil]] = {}
        for p in self.profils:
            k = cle_organisation(p) or f"individuel-{p.id}"
            oid = "org-" + hashlib.sha256(k.encode()).hexdigest()[:8]
            orgs.setdefault(oid, Organisation(id=oid, nom=p.entreprise or "(non renseignée)", secteur=p.secteurs[0] if p.secteurs else None))
            membres.setdefault(oid, []).append(p)
        adhesions, personnes = [], []
        for oid, ps in sorted(membres.items()):
            formule: Formule = "entreprise" if len(ps) > 1 else "nominative"
            aid = "adh-" + oid[4:]
            adhesions.append(Adhesion(id=aid, organisation_id=oid, formule=formule))
            for i, p in enumerate(sorted(ps, key=lambda x: x.id)):
                local = ".".join(p.nom.lower().split())[:40] or p.id
                personnes.append(Personne(id=p.id, adhesion_id=aid, role="representant" if formule == "entreprise" and i else "membre",
                                          nom=p.nom, courriel=f"{local}@exemple.invalid", telephone=""))
        return Import(source=self.nom, synthetique=True, organisations=list(orgs.values()), adhesions=adhesions,
                      personnes=personnes, avertissements=["Données SYNTHÉTIQUES : aucune adhésion réelle du Club."])


class AdhesionsCSV:
    """Export CSV fourni par le Club (colonnes : id, organisation, secteur, formule, nom, courriel, role)."""
    nom = "csv"

    def __init__(self, texte: str):
        self.texte = texte

    def importer(self) -> Import:
        orgs: dict[str, Organisation] = {}
        adh: dict[str, Adhesion] = {}
        personnes, avert = [], []
        for n, ligne in enumerate(csv.DictReader(io.StringIO(self.texte)), start=2):
            try:
                oid = "org-" + hashlib.sha256(ligne["organisation"].strip().lower().encode()).hexdigest()[:8]
                orgs.setdefault(oid, Organisation(id=oid, nom=ligne["organisation"].strip(), secteur=ligne.get("secteur") or None))
                formule = "entreprise" if ligne.get("formule", "").strip() == "entreprise" else "nominative"
                adh.setdefault(oid, Adhesion(id="adh-" + oid[4:], organisation_id=oid, formule=formule))
                role = ligne.get("role", "membre").strip() or "membre"
                if role not in ("membre", "representant"):
                    raise ValueError(f"rôle inconnu « {role} »")
                if "@" not in ligne["courriel"]:
                    raise ValueError("courriel invalide")
                personnes.append(Personne(id=ligne["id"].strip(), adhesion_id="adh-" + oid[4:], role=role,
                                          nom=ligne["nom"].strip(), courriel=ligne["courriel"].strip()))
            except (KeyError, ValueError) as e:
                avert.append(f"ligne {n} ignorée : {e}")
        return Import(source=self.nom, synthetique=False, organisations=list(orgs.values()), adhesions=list(adh.values()),
                      personnes=personnes, avertissements=avert)


class NonConnecte(RuntimeError):
    pass


class AdhesionsAPIClub:
    """FUTUR : connecteur vers le système d'adhésion du Club. Non implémenté — aucun accès n'existe à ce jour."""
    nom = "api-club"

    def importer(self) -> Import:
        raise NonConnecte("Le système d'adhésion du Club n'est pas connecté : autorisation du Club et accès technique "
                          "requis (voir competition/IDENTITY_AND_PRIVACY.md, « Intégration »).")


class Coffre:
    """Identités (nom, organisation, contact) séparées des capacités. Le moteur ne voit que des pseudonymes."""

    def __init__(self, imp: Import, secret: Optional[str] = None):
        self.source, self.synthetique = imp.source, imp.synthetique
        self.orgs = {o.id: o for o in imp.organisations}
        self.adhesions = {a.id: a for a in imp.adhesions}
        self._personnes = {p.id: p for p in imp.personnes}
        self._pseudo = {pid: f"MEMBRE-{i:03d}" for i, pid in enumerate(sorted(self._personnes), start=1)}
        self._inverse = {v: k for k, v in self._pseudo.items()}
        self._secret = (secret or os.environ.get("HACKVS_SECRET_INVITATIONS") or "demo-seulement").encode()
        self.actives: set[str] = set()

    # -- pseudonymes
    def pseudonyme(self, pid: str) -> str:
        return self._pseudo.get(pid, "MEMBRE-SUPPRIMÉ")

    def depuis_pseudonyme(self, pseudo: str) -> Optional[str]:
        return self._inverse.get(pseudo)

    def pseudonymiser(self, p: Profil) -> Profil:
        """Profil pour le moteur : capacités, langues, disponibilité ; nom = pseudonyme ; organisation = clé opaque."""
        per = self._personnes.get(p.id)
        org = self.adhesions[per.adhesion_id].organisation_id if per else f"org-{p.id}"
        return p.model_copy(update={"nom": self.pseudonyme(p.id), "entreprise": org, "fonction": "", "commune": p.commune})

    # -- identités
    def identite(self, pid: str) -> Optional[Personne]:
        return self._personnes.get(pid)

    def organisation_de(self, pid: str) -> Optional[Organisation]:
        per = self._personnes.get(pid)
        return self.orgs.get(self.adhesions[per.adhesion_id].organisation_id) if per else None

    def supprimer(self, pid: str) -> None:
        """Droit à l'effacement : l'identité disparaît ; le journal ne contient que l'identifiant, désormais sans lien."""
        self._personnes.pop(pid, None)
        pseudo = self._pseudo.pop(pid, None)
        if pseudo:
            self._inverse.pop(pseudo, None)
        self.actives.discard(pid)

    # -- accès
    def code_invitation(self, pid: str) -> str:
        return hmac.new(self._secret, pid.encode(), hashlib.sha256).hexdigest()[:6].upper()

    def activer(self, code: str) -> Optional[str]:
        """Code d'invitation (QR) → compte. Comparaison à temps constant ; un code inconnu ne révèle rien."""
        code = (code or "").strip().upper()
        trouve = None
        for pid in sorted(self._personnes):
            if hmac.compare_digest(self.code_invitation(pid), code):
                trouve = pid
        if trouve and self.adhesions[self._personnes[trouve].adhesion_id].statut == "active":
            self.actives.add(trouve)
            return trouve
        return None
