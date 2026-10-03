"""ANNÉE 1 · LOT 1 — Stockage INTERCHANGEABLE sous le journal : SQLite pour la démo, PostgreSQL pour la production.

Le moteur se choisit par l'adresse (HACKVS_ESSAIS_DB) : `:memory:` ou un chemin → SQLite (comportement d'avant,
inchangé) ; `postgresql://…` → PostgreSQL (psycopg, dépendance facultative). Le journal ne voit qu'une petite interface :
dernier numéro et nombre de faits, lecture depuis un numéro, insertion idempotente, transaction, vidage. Les schémas
viennent des migrations (plateforme/migrations.py) ; aucun SQL de schéma ici."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional, Protocol


class Stockage(Protocol):
    dialecte: str

    def executer(self, sql: str, params: tuple = ()) -> Any: ...
    def dernier_et_nombre(self) -> tuple[int, int]: ...
    def depuis(self, seq: int) -> Iterable[tuple[int, str]]: ...
    def inserer(self, id_: str, donnees: str) -> int: ...
    def debut(self) -> None: ...
    def valider(self) -> None: ...
    def annuler(self) -> None: ...
    def vider(self) -> None: ...
    def table_existe(self, nom: str) -> bool: ...


class _Sqlite:
    """Le comportement d'avant ce lot, à l'identique : transactions implicites du module sqlite3, validées à la main."""
    dialecte = "sqlite"

    def __init__(self, chemin: str):
        if chemin != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(chemin, check_same_thread=False)
        self._tx = False

    def executer(self, sql: str, params: tuple = ()) -> Any:
        return self._db.execute(sql, params)

    def dernier_et_nombre(self) -> tuple[int, int]:
        d, n = self._db.execute("SELECT COALESCE(MAX(seq), 0), COUNT(*) FROM evenements").fetchone()
        return int(d), int(n)

    def depuis(self, seq: int) -> Iterable[tuple[int, str]]:
        return self._db.execute("SELECT seq, donnees FROM evenements WHERE seq > ? ORDER BY seq", (seq,)).fetchall()

    def inserer(self, id_: str, donnees: str) -> int:
        cur = self._db.execute("INSERT OR IGNORE INTO evenements (id, donnees) VALUES (?, ?)", (id_, donnees))
        if not self._tx:
            self._db.commit()
        if cur.rowcount:
            return int(cur.lastrowid or 0)
        return int(self._db.execute("SELECT seq FROM evenements WHERE id = ?", (id_,)).fetchone()[0])

    def debut(self) -> None:
        self._tx = True

    def valider(self) -> None:
        self._tx = False
        self._db.commit()

    def annuler(self) -> None:
        self._tx = False
        self._db.rollback()

    def vider(self) -> None:
        self._db.execute("DELETE FROM evenements")
        self._db.commit()

    def table_existe(self, nom: str) -> bool:
        return self._db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (nom,)).fetchone() is not None


class _Postgres:
    """PostgreSQL : mode auto-validation, et BEGIN / COMMIT / ROLLBACK explicites pour les transactions du journal."""
    dialecte = "postgres"

    def __init__(self, url: str):
        try:
            import psycopg
        except ImportError as e:                       # dépendance facultative : la démo n'en a jamais besoin
            raise RuntimeError("PostgreSQL demandé, mais psycopg n'est pas installé (pip install 'psycopg[binary]')") from e
        self._db = psycopg.connect(url, autocommit=True)
        self._tx = False

    def executer(self, sql: str, params: tuple = ()) -> Any:
        return self._db.execute(sql.replace("?", "%s"), params)

    def dernier_et_nombre(self) -> tuple[int, int]:
        r = self._db.execute("SELECT COALESCE(MAX(seq), 0), COUNT(*) FROM evenements").fetchone()
        assert r is not None
        return int(r[0]), int(r[1])

    def depuis(self, seq: int) -> Iterable[tuple[int, str]]:
        return self._db.execute("SELECT seq, donnees FROM evenements WHERE seq > %s ORDER BY seq", (seq,)).fetchall()

    def inserer(self, id_: str, donnees: str) -> int:
        r = self._db.execute("INSERT INTO evenements (id, donnees) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING RETURNING seq",
                             (id_, donnees)).fetchone()
        if r:
            return int(r[0])
        s = self._db.execute("SELECT seq FROM evenements WHERE id = %s", (id_,)).fetchone()
        assert s is not None
        return int(s[0])

    def debut(self) -> None:
        self._db.execute("BEGIN")
        self._tx = True

    def valider(self) -> None:
        self._tx = False
        self._db.execute("COMMIT")

    def annuler(self) -> None:
        self._tx = False
        self._db.execute("ROLLBACK")

    def vider(self) -> None:
        self._db.execute("DELETE FROM evenements")

    def table_existe(self, nom: str) -> bool:
        r = self._db.execute("SELECT to_regclass(%s)", (nom,)).fetchone()
        return r is not None and r[0] is not None


def ouvrir(adresse: Optional[str]) -> Stockage:
    """`:memory:`, un chemin de fichier, ou `postgresql://…` (`postgres://…`). Toute autre adresse est refusée."""
    a = adresse or ":memory:"
    if a.startswith(("postgresql://", "postgres://")):
        return _Postgres(a)
    if "://" in a:
        raise ValueError(f"moteur de stockage inconnu : {a.split('://', 1)[0]}:// (SQLite ou postgresql:// seulement)")
    return _Sqlite(a)
