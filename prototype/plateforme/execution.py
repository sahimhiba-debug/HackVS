"""Exécution de décision (Decision Run) : l'unité de rejeu, d'audit, d'évaluation et de démonstration.

Une exécution conserve l'INSTANTANÉ complet qu'elle a consommé (pas seulement son empreinte) : on peut la rejouer
sans les données vivantes et vérifier qu'elle donne exactement le même résultat. La trace contient des durées
MESURÉES ; rien n'est simulé pour l'affichage.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel


class Etape(BaseModel):
    nom: str
    debut_ms: float
    duree_ms: float
    resume: dict[str, Any] = {}


class Budget(BaseModel):
    appels_llm: int = 0
    appels_outils: int = 0
    appels_solveur: int = 0
    jetons: int = 0
    branches_paralleles: int = 0
    transferts_de_contexte: int = 0


class ExecutionDecision(BaseModel):
    run_id: str
    cree_le: str
    parent_id: Optional[str] = None
    intervention: Optional[dict] = None       # ce qui distingue une branche de son parent
    demande: str
    compilation: dict
    spec: Optional[dict] = None
    plan: list[str] = []
    strategie_contexte: dict = {}
    instantane_empreinte: str = ""
    etapes: list[Etape] = []
    frontiere: list[dict] = []
    retenue: Optional[dict] = None
    verdicts: list[dict] = []
    avis: list[dict] = []
    mediation: Optional[dict] = None
    graphe: dict = {}
    budget: Budget = Budget()
    versions: dict = {}
    resultat_empreinte: str = ""
    decision_humaine: Optional[dict] = None


def empreinte(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


class Traceur:
    def __init__(self) -> None:
        self.t0 = time.perf_counter()
        self.etapes: list[Etape] = []

    @contextmanager
    def etape(self, nom: str):
        debut = time.perf_counter()
        resume: dict[str, Any] = {}
        yield resume
        self.etapes.append(Etape(nom=nom, debut_ms=round((debut - self.t0) * 1000, 1),
                                 duree_ms=round((time.perf_counter() - debut) * 1000, 1), resume=resume))


def nouvel_id() -> str:
    return "run_" + uuid.uuid4().hex[:12]


def maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Journal:
    """Persistance des exécutions et de leurs instantanés (SQLite)."""

    def __init__(self, chemin: str = ":memory:"):
        self._db = sqlite3.connect(chemin, check_same_thread=False)
        self._verrou = threading.Lock()
        with self._verrou:
            self._db.execute("CREATE TABLE IF NOT EXISTS executions (run_id TEXT PRIMARY KEY, cree_le TEXT, parent_id TEXT, donnees TEXT)")
            self._db.execute("CREATE TABLE IF NOT EXISTS instantanes (empreinte TEXT PRIMARY KEY, donnees TEXT)")
            self._db.commit()

    def enregistrer(self, run: ExecutionDecision, instantane: Optional[dict] = None) -> None:
        with self._verrou:
            self._db.execute("INSERT OR REPLACE INTO executions VALUES (?, ?, ?, ?)",
                             (run.run_id, run.cree_le, run.parent_id, run.model_dump_json()))
            if instantane is not None:
                self._db.execute("INSERT OR IGNORE INTO instantanes VALUES (?, ?)",
                                 (run.instantane_empreinte, json.dumps(instantane, ensure_ascii=False)))
            self._db.commit()

    def lire(self, run_id: str) -> ExecutionDecision:
        with self._verrou:
            l = self._db.execute("SELECT donnees FROM executions WHERE run_id = ?", (run_id,)).fetchone()
        if not l:
            raise KeyError(run_id)
        return ExecutionDecision.model_validate_json(l[0])

    def instantane(self, emp: str) -> dict:
        with self._verrou:
            l = self._db.execute("SELECT donnees FROM instantanes WHERE empreinte = ?", (emp,)).fetchone()
        if not l:
            raise KeyError(emp)
        return json.loads(l[0])

    def liste(self, limite: int = 50) -> list[dict]:
        with self._verrou:
            ls = self._db.execute("SELECT donnees FROM executions ORDER BY cree_le DESC LIMIT ?", (limite,)).fetchall()
        res = []
        for (d,) in ls:
            r = ExecutionDecision.model_validate_json(d)
            res.append({"run_id": r.run_id, "cree_le": r.cree_le, "parent_id": r.parent_id, "demande": r.demande,
                        "intervention": r.intervention, "decision": (r.mediation or {}).get("decision", r.compilation.get("decision"))})
        return res

    def arbre(self, racine: str) -> dict:
        with self._verrou:
            ls = self._db.execute("SELECT run_id, parent_id FROM executions").fetchall()
        enfants: dict[str, list[str]] = {}
        for rid, pid in ls:
            enfants.setdefault(pid, []).append(rid)

        def noeud(rid: str) -> dict:
            return {"run_id": rid, "branches": [noeud(c) for c in sorted(enfants.get(rid, []))]}
        return noeud(racine)
