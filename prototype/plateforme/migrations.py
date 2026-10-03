"""ANNÉE 1 · LOT 1 — Migrations du schéma, avec retour arrière.

Chaque migration a une montée et une descente, par moteur (SQLite, PostgreSQL). La table `schema_migrations` garde le
niveau. Un journal d'AVANT ce lot (table `evenements` sans table de migrations) est adopté tel quel : la migration 1
crée la table « si elle n'existe pas ». Descendre sous le niveau 1 détruirait le journal : refusé sans confirmation
explicite (`Destructeur`)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .stockage import Stockage


class Destructeur(RuntimeError):
    """Cette descente effacerait des faits du journal : il faut le confirmer explicitement."""


# (niveau, nom, {dialecte: [montée]}, {dialecte: [descente]}, destructrice)
MIGRATIONS: list[tuple[int, str, dict[str, list[str]], dict[str, list[str]], bool]] = [
    (1, "journal d'événements en ajout seul",
     {"sqlite": ["CREATE TABLE IF NOT EXISTS evenements (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE, donnees TEXT)"],
      "postgres": ["CREATE TABLE IF NOT EXISTS evenements (seq BIGSERIAL PRIMARY KEY, id TEXT UNIQUE NOT NULL, donnees TEXT NOT NULL)"]},
     {"sqlite": ["DROP TABLE IF EXISTS evenements"], "postgres": ["DROP TABLE IF EXISTS evenements"]}, True),
    (2, "métadonnées du journal (création, moteur)",
     {"sqlite": ["CREATE TABLE IF NOT EXISTS journal_meta (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL)"],
      "postgres": ["CREATE TABLE IF NOT EXISTS journal_meta (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL)"]},
     {"sqlite": ["DROP TABLE IF EXISTS journal_meta"], "postgres": ["DROP TABLE IF EXISTS journal_meta"]}, False),
]
DERNIERE = MIGRATIONS[-1][0]


def _table(b: Stockage) -> None:
    b.executer("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, nom TEXT NOT NULL, applique_le TEXT NOT NULL)")


def niveau(b: Stockage) -> int:
    if not b.table_existe("schema_migrations"):
        return 0
    r = b.executer("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
    return int(r[0])


def migrer(b: Stockage, cible: Optional[int] = None, *, confirmer_destruction: bool = False) -> int:
    """Monte (ou descend) jusqu'au niveau `cible` (défaut : le dernier). Chaque pas est une transaction. Rend le niveau."""
    cible = DERNIERE if cible is None else cible
    if not 0 <= cible <= DERNIERE:
        raise ValueError(f"niveau de schéma inconnu : {cible} (0 à {DERNIERE})")
    b.debut()
    try:
        _table(b)
        b.valider()
    except BaseException:
        b.annuler()
        raise
    actuel = niveau(b)
    pas = [m for m in MIGRATIONS if actuel < m[0] <= cible] if cible >= actuel else \
        [m for m in reversed(MIGRATIONS) if cible < m[0] <= actuel]
    if cible < actuel and any(m[4] for m in pas) and not confirmer_destruction:
        raise Destructeur(f"descendre au niveau {cible} effacerait le journal : confirmer_destruction=True requis")
    for version, nom, montee, descente, _ in pas:
        b.debut()
        try:
            if cible >= actuel:
                for sql in montee[b.dialecte]:
                    b.executer(sql)
                b.executer("INSERT INTO schema_migrations (version, nom, applique_le) VALUES (?, ?, ?)",
                           (version, nom, datetime.now(timezone.utc).isoformat(timespec="seconds")))
            else:
                for sql in descente[b.dialecte]:
                    b.executer(sql)
                b.executer("DELETE FROM schema_migrations WHERE version = ?", (version,))
            b.valider()
        except BaseException:
            b.annuler()
            raise
    return niveau(b)
