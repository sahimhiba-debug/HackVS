"""Mémoire du réseau : journal d'événements en ajout seul, horloge explicite, graphe des relations DÉRIVÉ.

Rien n'est stocké comme « état » : le graphe, la force des liens et les indicateurs de croissance sont recalculés en
repliant les événements. Conséquences : tout est rejouable, rien ne s'efface en silence, et l'horloge est un
PARAMÈTRE (jamais datetime.now() dans la logique) — en démonstration elle est avancée à la main, et c'est dit.

Types d'événements (génériques) : EVENEMENT_TENU, RENCONTRE, RENCONTRE_CONFIRMEE, BESOIN_PUBLIE, RELANCE_PROPOSEE,
RELANCE_ACCEPTEE, RELANCE_REFUSEE, SUIVI, OPPORTUNITE_OUVERTE, HORLOGE.
"""
from __future__ import annotations

import hashlib
import json
import math
import threading
from contextlib import contextmanager
from datetime import date
from typing import Any, Callable, Iterator, Optional

import networkx as nx
from pydantic import BaseModel, ConfigDict

from .affirmations import Statut
from .optimisation import cle
from .stockage import ouvrir


class Evt(BaseModel):
    model_config = ConfigDict(frozen=True)    # les événements lus sont partagés (cache) : jamais modifiés en place
    type: str
    le: date
    acteurs: list[str] = []
    donnees: dict[str, Any] = {}
    statut: Statut
    seq: int = 0

    @property
    def id(self) -> str:
        brut = json.dumps([self.type, self.le.isoformat(), self.acteurs, self.donnees], sort_keys=True, ensure_ascii=False, default=str)
        return "e_" + hashlib.sha256(brut.encode()).hexdigest()[:16]


class MondeRemplace(RuntimeError):
    """Écriture dans le journal d'un monde REMPLACÉ (réinitialisation de la démonstration) : refusée, jamais égarée."""


class Memoire:
    def __init__(self, chemin: str = ":memory:", *, migrer_schema: bool = True):
        # ANNÉE 1 · LOT 1 : le moteur se choisit par l'adresse (`:memory:`, un fichier → SQLite ; `postgresql://` →
        # PostgreSQL) ; le schéma vient des migrations (un journal d'avant ce lot est adopté tel quel)
        from .migrations import migrer
        self._db = ouvrir(chemin)
        self._v = threading.RLock()      # réentrant : une transaction garde le verrou pendant toutes ses écritures
        self._profondeur = 0             # > 0 : dans une transaction (les écritures attendent sa validation)
        with self._v:
            if migrer_schema:            # audit M3 : une SAUVEGARDE lit le journal tel qu'il est, sans jamais le migrer
                migrer(self._db)
        self._cache: list[Evt] = []      # journal APPEND-ONLY déjà désérialisé (lu une fois, puis par incrément)
        # appelés après l'ANNULATION de la transaction la plus externe : qui tient un état dérivé du journal (en mémoire,
        # en cache) le reconstruit — sinon il garderait des faits qui n'existent plus (F27)
        self.sur_annulation: list[Callable[[], None]] = []
        self._ferme = False                # monde remplacé : plus aucune écriture (F28)
        self._figee = 0                    # > 0 : lecture figée (un calcul en lecture seule relit le journal UNE fois)
        self._sale = False                 # une écriture a eu lieu pendant la lecture figée : on relit
        self._generation = 0               # +1 à chaque remise à zéro du cache (annulation, vidage, relecture complète)

    def _synchroniser(self) -> list[Evt]:
        """Cache incrémental : ne désérialise que les événements nouveaux. Resynchronisé à chaque lecture par une
        requête légère (dernier seq, nombre) : reste exact si un autre objet écrit dans le même fichier ou le vide."""
        dernier, nombre = self._db.dernier_et_nombre()
        connu = self._cache[-1].seq if self._cache else 0
        if dernier > connu:
            for s, d in self._db.depuis(connu):
                self._cache.append(Evt.model_validate_json(d).model_copy(update={"seq": s}))
        if len(self._cache) != nombre:                     # vidé ou modifié ailleurs : relecture complète
            self._generation += 1
            self._cache = [Evt.model_validate_json(d).model_copy(update={"seq": s}) for s, d in self._db.depuis(0)]
        return self._cache

    def ajouter(self, e: Evt) -> Evt:
        """Idempotent : le même événement (même contenu) n'est jamais compté deux fois."""
        with self._v:
            self._sale = True
            if self._ferme:
                raise MondeRemplace("ce monde a été remplacé : écriture refusée")
            seq = self._db.inserer(e.id, e.model_dump_json(exclude={"seq"}))   # validé seul hors transaction
        return e.model_copy(update={"seq": seq})

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Tout ou rien : les faits écrits dans le bloc sont validés ensemble, ou aucun si une exception s'échappe.
        Pendant le bloc, les autres fils attendent (verrou réentrant) ; le fil courant lit ses propres écritures.
        Imbrication : seule la transaction la plus externe valide ou annule."""
        with self._v:
            if not self._profondeur:
                self._db.debut()
            self._profondeur += 1
            try:
                yield
            except BaseException:
                self._profondeur -= 1
                if not self._profondeur:
                    self._annulee()
                raise
            self._profondeur -= 1
            if not self._profondeur:
                try:
                    self._db.valider()
                except BaseException:                      # AUDIT B2 : validation refusée (connexion perdue…) = annulée
                    self._annulee()
                    raise

    def _annulee(self) -> None:
        """Après une annulation : le cache a pu lire des faits annulés (relecture complète), et les abonnés le savent (F27)
        — même si l'annulation elle-même échoue (connexion perdue : le serveur a déjà tout annulé)."""
        try:
            self._db.annuler()
        finally:
            self._cache = []
            self._sale = True
            self._generation += 1
            for f in self.sur_annulation:
                f()

    def _lus(self) -> list[Evt]:
        if self._figee and not self._sale:
            return self._cache
        self._sale = False
        return self._synchroniser()

    def evenements(self, *types: str, jusqu_au: Optional[date] = None) -> list[Evt]:
        with self._v:
            res = self._lus()
            return [e for e in res if (not types or e.type in types) and (jusqu_au is None or e.le <= jusqu_au)]

    @contextmanager
    def figee(self) -> Iterator[None]:
        """Lecture figée : pendant un calcul en lecture seule (projeter les capacités), le journal n'est resynchronisé
        avec le fichier qu'UNE fois au lieu d'une fois par lecture (H2 : 160 000 requêtes pour une projection). Toute
        écriture pendant le bloc — y compris d'un autre fil, puisque le verrou est tenu — force une relecture."""
        with self._v:
            self._sale = True                          # la première lecture du bloc se synchronise
            self._figee += 1
            try:
                yield
            finally:
                self._figee -= 1

    def version(self) -> tuple[int, int, int]:
        """Ce qui change dès que le journal change, en temps constant : génération du cache, nombre de faits, numéro du
        dernier. Sert de clé aux index dérivés. La génération change à chaque annulation ou vidage : SQLite peut alors
        réutiliser un numéro de séquence pour un AUTRE fait."""
        with self._v:
            res = self._lus()
            return self._generation, len(res), (res[-1].seq if res else 0)

    def maintenant(self, defaut: date) -> date:
        h = self.evenements("HORLOGE")
        return h[-1].le if h else defaut

    def avancer(self, jours: int, defaut: date, statut: Statut = Statut.SIMULE) -> date:
        """Avance l'horloge (démo : SIMULE — aucune vraie journée ne s'est écoulée)."""
        d = date.fromordinal(self.maintenant(defaut).toordinal() + jours)
        self.ajouter(Evt(type="HORLOGE", le=d, donnees={"avance_jours": jours}, statut=statut))
        return d

    def empreinte(self) -> str:
        return hashlib.sha256("".join(e.id for e in self.evenements()).encode()).hexdigest()

    def fermer(self) -> None:
        """Le monde qui portait ce journal est remplacé : toute écriture ultérieure lève `MondeRemplace`."""
        with self._v:
            self._ferme = True

    def reecrire(self, transformer: Callable[[Evt], Evt], fait: Optional[Evt] = None) -> int:
        """ANNÉE 1 · LOT 3 — PURGE RÉELLE : réécrit tout le journal en UNE transaction (tout ou rien), chaque fait passé par
        `transformer` (réécrit à sa place), puis ajoute `fait` (la trace de la purge, sans contenu). Deux faits devenus
        identiques : ValueError, rien n'est modifié (et la contrainte d'unicité de la base en dernier rempart). Rend le nombre de faits modifiés. Le seul
        geste qui modifie le passé : réservé à l'effacement définitif demandé par un membre."""
        with self._v:
            if self._ferme:
                raise MondeRemplace("ce monde a été remplacé : écriture refusée")
            if self._profondeur:
                raise RuntimeError("réécriture refusée dans une transaction en cours (elle en validerait une partie)")
            avant = list(self._synchroniser())
            apres = [transformer(e) for e in avant]
            modifies = sum(1 for a, b in zip(avant, apres, strict=True) if a.id != b.id)
            if len({e.id for e in apres + ([fait] if fait else [])}) != len(apres) + (1 if fait else 0):
                raise ValueError("réécriture refusée : deux faits deviendraient identiques — rien n'est modifié")
            self._db.debut()
            try:
                for a, b in zip(avant, apres, strict=True):
                    if a.id != b.id:      # même place dans le journal (seq) : l'ordre et les autres faits ne bougent pas
                        self._db.executer("UPDATE evenements SET id = ?, donnees = ? WHERE seq = ?",
                                          (b.id, b.model_dump_json(exclude={"seq"}), a.seq))
                if fait:
                    self._db.inserer(fait.id, fait.model_dump_json(exclude={"seq"}))
                self._db.valider()
            except BaseException:
                self._db.annuler()
                raise
            finally:
                self._cache = []
                self._sale = True
                self._generation += 1
            return modifies

    def charger_sauvegarde(self, lignes: list[str], verifier: Callable[[list[str]], None]) -> None:
        """ANNÉE 1 · LOT 1 (audit I2, I3) — restauration TOUT OU RIEN dans ce journal VIDE : chaque fait à son numéro
        d'origine (`seq`), puis `verifier` relit ce qui est écrit AVANT la validation ; la moindre erreur annule tout."""
        with self._v:
            if self._ferme:
                raise MondeRemplace("ce monde a été remplacé : écriture refusée")
            if self._profondeur:
                raise RuntimeError("restauration refusée dans une transaction en cours")
            self._db.debut()
            try:
                if self._db.dernier_et_nombre()[1]:
                    raise ValueError("le journal cible n'est pas vide : restauration refusée (jamais de mélange)")
                for x in lignes:
                    e = Evt.model_validate_json(x)
                    self._db.inserer_a(e.seq, e.id, e.model_dump_json(exclude={"seq"}))
                verifier([Evt.model_validate_json(d).model_copy(update={"seq": s}).model_dump_json()
                          for s, d in self._db.depuis(0)])
                self._db.valider()
            except BaseException:
                self._db.annuler()
                raise
            finally:
                self._cache = []
                self._sale = True
                self._generation += 1

    def vider(self) -> None:
        with self._v:
            if self._profondeur:         # audit M1 : SQLite en validait la moitié, PostgreSQL l'annulait — refusé partout
                raise RuntimeError("vider le journal est refusé dans une transaction en cours")
            self._db.vider()
            self._cache = []
            self._sale = True
            self._generation += 1


# ------------------------------------------------------------------ graphe dérivé
LIENS = ("RENCONTRE", "SUIVI")


def graphe(m: Memoire, jusqu_au: Optional[date] = None) -> nx.Graph:
    """Arêtes = rencontres et suivis ; attributs : première/dernière interaction, nombre, statut le plus fort."""
    g = nx.Graph()
    rang = {Statut.SIMULE: 0, Statut.SYNTHETIQUE: 0, Statut.INFERE: 0, Statut.DECLARE: 1, Statut.OBSERVE: 2, Statut.VERIFIE: 3}
    confirmees = {cle(*e.acteurs) for e in m.evenements("RENCONTRE_CONFIRMEE", jusqu_au=jusqu_au)}
    for e in m.evenements(*LIENS, jusqu_au=jusqu_au):
        a, b = e.acteurs[:2]
        st = Statut.DECLARE if e.type == "RENCONTRE" and cle(a, b) in confirmees else e.statut  # un membre l'a déclaré
        if g.has_edge(a, b):
            d = g[a][b]
            d["derniere"] = max(d["derniere"], e.le)
            d["nombre"] += 1
            d["types"].add(e.type)
            if rang.get(st, 0) > rang.get(d["statut"], 0):
                d["statut"] = st
        else:
            g.add_edge(a, b, premiere=e.le, derniere=e.le, nombre=1, types={e.type}, statut=st)
    return g


def force(derniere: date, maintenant: date, demi_vie_jours: float = 30.0) -> float:
    """Décroissance exponentielle depuis la dernière interaction (hypothèse de modélisation, pas une mesure)."""
    return round(math.exp(-math.log(2) * max(0, (maintenant - derniere).days) / demi_vie_jours), 3)


def fermetures(g: nx.Graph) -> list[tuple[str, str, str]]:
    """Triades ouvertes a–via–c (a et c ne se connaissent pas) : candidates à une présentation par « via »."""
    res = []
    for via in sorted(g.nodes):
        voisins = sorted(g.neighbors(via))
        for i, a in enumerate(voisins):
            for c in voisins[i + 1:]:
                if not g.has_edge(a, c):
                    res.append((a, via, c))
    return res


def indicateurs(g: nx.Graph, maintenant: date, seuil_actif: float = 0.5) -> dict:
    if not g.number_of_nodes():
        return {"membres_relies": 0, "liens": 0, "liens_actifs": 0, "composantes": 0, "plus_grande_composante": 0,
                "portee_moyenne_2_sauts": 0.0}
    comps = list(nx.connected_components(g))
    portee = [len(nx.single_source_shortest_path_length(g, n, cutoff=2)) - 1 for n in g.nodes]
    return {"membres_relies": g.number_of_nodes(), "liens": g.number_of_edges(),
            "liens_actifs": sum(1 for _, _, d in g.edges(data=True) if force(d["derniere"], maintenant) >= seuil_actif),
            "composantes": len(comps), "plus_grande_composante": max(len(c) for c in comps),
            "portee_moyenne_2_sauts": round(sum(portee) / len(portee), 2)}


def croissance(m: Memoire) -> list[dict]:
    """Indicateurs du réseau juste après chaque événement tenu, puis à la date courante."""
    points = []
    for e in m.evenements("EVENEMENT_TENU"):
        points.append({"apres": e.donnees.get("nom", e.id), "le": e.le.isoformat(), **indicateurs(graphe(m, e.le), e.le)})
    return points
