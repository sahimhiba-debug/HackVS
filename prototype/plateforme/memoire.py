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
import sqlite3
import threading
from datetime import date
from pathlib import Path
from typing import Any, Optional

import networkx as nx
from pydantic import BaseModel, ConfigDict

from .affirmations import Statut
from .optimisation import cle


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


class Memoire:
    def __init__(self, chemin: str = ":memory:"):
        if chemin != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(chemin, check_same_thread=False)
        self._v = threading.Lock()
        with self._v:
            self._db.execute("CREATE TABLE IF NOT EXISTS evenements (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE, donnees TEXT)")
            self._db.commit()
        self._cache: list[Evt] = []      # journal APPEND-ONLY déjà désérialisé (lu une fois, puis par incrément)

    def _synchroniser(self) -> list[Evt]:
        """Cache incrémental : ne désérialise que les événements nouveaux. Resynchronisé à chaque lecture par une
        requête légère (dernier seq, nombre) : reste exact si un autre objet écrit dans le même fichier ou le vide."""
        dernier, nombre = self._db.execute("SELECT COALESCE(MAX(seq), 0), COUNT(*) FROM evenements").fetchone()
        connu = self._cache[-1].seq if self._cache else 0
        if dernier > connu:
            for s, d in self._db.execute("SELECT seq, donnees FROM evenements WHERE seq > ? ORDER BY seq", (connu,)):
                self._cache.append(Evt.model_validate_json(d).model_copy(update={"seq": s}))
        if len(self._cache) != nombre:                     # vidé ou modifié ailleurs : relecture complète
            self._cache = [Evt.model_validate_json(d).model_copy(update={"seq": s})
                           for s, d in self._db.execute("SELECT seq, donnees FROM evenements ORDER BY seq")]
        return self._cache

    def ajouter(self, e: Evt) -> Evt:
        """Idempotent : le même événement (même contenu) n'est jamais compté deux fois."""
        with self._v:
            cur = self._db.execute("INSERT OR IGNORE INTO evenements (id, donnees) VALUES (?, ?)",
                                   (e.id, e.model_dump_json(exclude={"seq"})))
            self._db.commit()
            seq = cur.lastrowid if cur.rowcount else self._db.execute("SELECT seq FROM evenements WHERE id = ?", (e.id,)).fetchone()[0]
        return e.model_copy(update={"seq": seq})

    def evenements(self, *types: str, jusqu_au: Optional[date] = None) -> list[Evt]:
        with self._v:
            res = self._synchroniser()
            return [e for e in res if (not types or e.type in types) and (jusqu_au is None or e.le <= jusqu_au)]

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

    def vider(self) -> None:
        with self._v:
            self._db.execute("DELETE FROM evenements")
            self._db.commit()
            self._cache = []


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
