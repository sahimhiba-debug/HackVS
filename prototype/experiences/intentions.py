"""Intentions scellées : rapprocher des intentions que personne n'écrit publiquement, sans que le Club les lise.

Exemples : « je cherche un repreneur pour ma menuiserie », « je veux racheter une entreprise de transport en Valais »,
« je cherche un investisseur discret », « je cherche un directeur pour me succéder ».

Chaque membre a un AGENT PERSONNEL qui garde ses intentions en clair CHEZ LUI. Deux agents confrontent leurs
intentions par intersection privée d'ensembles (psi.py) à travers un RELAIS (le serveur du Club) qui ne transporte
que des points aléatoires et des pseudonymes. Une compatibilité n'entraîne AUCUNE révélation d'identité : chaque
humain décide ensuite, et l'identité n'est échangée que si les DEUX acceptent (engagement puis ouverture simultanée).

Jetons : une intention produit un jeton « ce que je suis » et un ou plusieurs jetons « ce que je cherche ».
Compatibilité A↔B ⇔ soi(A) ∩ cherche(B) ≠ ∅ ET cherche(A) ∩ soi(B) ≠ ∅ (deux PSI, une par sens).
Remplissage : chaque ensemble est complété par des jetons aléatoires jusqu'à une taille fixe, pour ne pas révéler
combien d'intentions un membre porte.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field

from . import psi

# type d'intention → (rôle que je joue, rôle que je cherche)
COMPLEMENTS = {
    "ceder": ("cedant", "repreneur"),
    "reprendre": ("repreneur", "cedant"),
    "lever_fonds": ("cherche_capital", "investisseur"),
    "investir": ("investisseur", "cherche_capital"),
    "chercher_dirigeant": ("cherche_dirigeant", "candidat_dirigeant"),
    "devenir_dirigeant": ("candidat_dirigeant", "cherche_dirigeant"),
}
LIBELLES = {"ceder": "céder mon entreprise", "reprendre": "reprendre une entreprise", "lever_fonds": "lever des fonds",
            "investir": "investir dans une PME", "chercher_dirigeant": "trouver un·e dirigeant·e",
            "devenir_dirigeant": "devenir dirigeant·e d'une PME"}
TAILLE_ENSEMBLE = 6  # nombre fixe de jetons par sens, après remplissage


K_ANONYMAT = 3  # un jeton ne doit désigner qu'une catégorie partagée par au moins k membres de l'annuaire


def generaliser(secteur: str, annuaire: dict[str, int], parents: dict[str, str | None], k: int = K_ANONYMAT) -> str:
    """Secteur → catégorie assez peuplée dans l'annuaire PUBLIC du Club (k-anonymat) : sinon parent, sinon « * »."""
    s: str | None = secteur
    while s is not None:
        if annuaire.get(s, 0) >= k:
            return s
        s = parents.get(s)
    return "*"


@dataclass(frozen=True)
class Intention:
    type: str          # clé de COMPLEMENTS
    secteurs: tuple    # concepts de la taxonomie (le secteur de MON entreprise, ou ceux que je cherche)
    region: str        # zone (« Valais »…)

    def jetons(self, general=lambda s: s) -> tuple[list[str], list[str]]:
        moi, cherche = COMPLEMENTS[self.type]
        secteurs = sorted({general(s) for s in self.secteurs})
        soi = [f"{moi}|{s}|{self.region}" for s in secteurs]
        vise = [f"{cherche}|{s}|{self.region}" for s in secteurs]
        return soi, vise


def _remplir(jetons: list[str]) -> list[str]:
    if len(jetons) > TAILLE_ENSEMBLE:
        raise ValueError(f"Au plus {TAILLE_ENSEMBLE} jetons par sens (limite anti-sondage).")
    return jetons + [f"__bourrage__|{secrets.token_hex(16)}" for _ in range(TAILLE_ENSEMBLE - len(jetons))]


@dataclass
class Relais:
    """Le serveur du Club : il transporte, compte, et ne peut rien lire (il ne voit que des points aléatoires)."""
    vus: list = field(default_factory=list)   # tout ce qui a transité (pour prouver ce que le Club voit)
    octets: int = 0

    def transporter(self, de: str, vers: str, charge: list[bytes]) -> list[bytes]:
        self.vus.append((de, vers, [c.hex() for c in charge]))
        self.octets += sum(len(c) for c in charge)
        return list(charge)


@dataclass
class Agent:
    """Agent personnel d'un membre. `membre_id` et les intentions ne quittent jamais l'agent."""
    membre_id: str
    intentions: list[Intention] = field(default_factory=list)
    pseudonyme: str = field(default_factory=lambda: secrets.token_hex(4))
    general: object = None  # fonction de généralisation k-anonyme (None : secteurs précis)

    def ensembles(self) -> tuple[list[str], list[str]]:
        soi, vise = [], []
        for it in self.intentions:
            s, v = it.jetons(self.general or (lambda x: x))
            soi += s
            vise += v
        return _remplir(sorted(set(soi))), _remplir(sorted(set(vise)))


def _psi_via_relais(a: Agent, xs: list[str], b: Agent, ys: list[str], relais: Relais) -> set[str]:
    """A apprend xs ∩ ys ; B n'apprend rien ; le relais ne voit que des points aléatoires."""
    ka, kb = psi.Cle(), psi.Cle()
    m1 = relais.transporter(a.pseudonyme, b.pseudonyme, [ka.aveugler_texte(x) for x in xs])
    retour = relais.transporter(b.pseudonyme, a.pseudonyme, [kb.aveugler_point(p) for p in m1])
    m2 = relais.transporter(b.pseudonyme, a.pseudonyme, [kb.aveugler_texte(y) for y in ys])
    theirs = {ka.aveugler_point(p) for p in m2}
    return {x for x, r in zip(xs, retour, strict=True) if r in theirs and not x.startswith("__bourrage__")}


def compatibilite(a: Agent, b: Agent, relais: Relais) -> list[str]:
    """Jetons compatibles (vus par A seulement). Vide ⇒ ni A ni B n'apprennent quoi que ce soit l'un sur l'autre."""
    soi_a, vise_a = a.ensembles()
    soi_b, vise_b = b.ensembles()
    b_cherche_ce_que_je_suis = _psi_via_relais(a, soi_a, b, vise_b, relais)
    je_cherche_ce_que_b_est = _psi_via_relais(a, vise_a, b, soi_b, relais)
    if not (b_cherche_ce_que_je_suis and je_cherche_ce_que_b_est):
        return []
    return sorted(je_cherche_ce_que_b_est)


def engagement(membre_id: str) -> tuple[str, str]:
    """Révélation équitable : chacun publie d'abord H(identité‖nonce), puis les deux ouvrent. Personne ne révèle en premier."""
    nonce = secrets.token_hex(16)
    return hashlib.sha256(f"{membre_id}|{nonce}".encode()).hexdigest(), nonce


def ouvrir(engagement_publie: str, membre_id: str, nonce: str) -> bool:
    return hashlib.sha256(f"{membre_id}|{nonce}".encode()).hexdigest() == engagement_publie
