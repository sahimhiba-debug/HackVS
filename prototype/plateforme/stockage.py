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
    def signature(self) -> tuple[int, int, str]: ...
    def depuis(self, seq: int) -> Iterable[tuple[int, str]]: ...
    def inserer(self, id_: str, donnees: str) -> int: ...
    def inserer_a(self, seq: int, id_: str, donnees: str) -> None: ...
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
        self._db.execute("PRAGMA secure_delete = ON")   # audit des lots 2-3, I4 : un texte purgé est écrasé sur le disque
        self._tx = False
        self._meta = False

    def executer(self, sql: str, params: tuple = ()) -> Any:
        return self._db.execute(sql, params)

    def dernier_et_nombre(self) -> tuple[int, int]:
        d, n = self._db.execute("SELECT COALESCE(MAX(seq), 0), COUNT(*) FROM evenements").fetchone()
        return int(d), int(n)

    def signature(self) -> tuple[int, int, str]:
        """(dernier seq, nombre, compteur de réécritures) en UNE requête — audit des lots 2-3, I5 : une purge faite par un
        autre objet (ou un autre processus) sur le même journal se voit, même si elle ne change ni le dernier seq ni le
        nombre de faits."""
        if not self._meta:
            self._meta = self.table_existe("journal_meta")
        if not self._meta:
            d, n = self.dernier_et_nombre()
            return d, n, ""
        r = self.executer("SELECT COALESCE(MAX(seq), 0), COUNT(*), (SELECT valeur FROM journal_meta WHERE cle = 'reecritures') "
                          "FROM evenements").fetchone()
        return int(r[0]), int(r[1]), r[2] or ""

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
        # AUDIT I5 : BEGIN explicite — sans lui, le module sqlite3 exécute le DDL (migrations) HORS transaction
        if not self._db.in_transaction:
            self._db.execute("BEGIN")
        self._tx = True

    def valider(self) -> None:
        self._tx = False
        self._db.commit()

    def annuler(self) -> None:
        self._tx = False
        self._db.rollback()

    def inserer_a(self, seq: int, id_: str, donnees: str) -> None:
        """Restauration : à son numéro d'origine (la suite reprend après le plus grand, AUTOINCREMENT oblige)."""
        self._db.execute("INSERT INTO evenements (seq, id, donnees) VALUES (?, ?, ?)", (seq, id_, donnees))

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
        self._url = url
        self._db = psycopg.connect(url, autocommit=True)
        self._tx = False
        self._meta = False

    def _x(self, sql: str, params: Optional[tuple] = None) -> Any:
        """AUDIT B2 : une connexion perdue (redémarrage, mise à jour, coupure) est rouverte HORS transaction, et la
        requête rejouée une fois (toutes sont idempotentes hors transaction : lectures, insertion ON CONFLICT, DELETE).
        Pendant une transaction : l'erreur remonte, et le journal annule tout."""
        import psycopg
        if self._db.closed and not self._tx:
            self._db = psycopg.connect(self._url, autocommit=True)
        try:
            return self._db.execute(sql, params)
        except psycopg.OperationalError:
            if self._tx or not self._db.closed:
                raise
            self._db = psycopg.connect(self._url, autocommit=True)
            return self._db.execute(sql, params)

    def executer(self, sql: str, params: tuple = ()) -> Any:
        # audit M2 : sans paramètre, le SQL part tel quel (un « ? » ou un « % » littéral ne casse rien) ; avec des
        # paramètres, les marques « ? » deviennent « %s » et un « % » littéral est doublé
        if not params:
            return self._x(sql)
        return self._x(sql.replace("%", "%%").replace("?", "%s"), params)

    def dernier_et_nombre(self) -> tuple[int, int]:
        r = self._x("SELECT COALESCE(MAX(seq), 0), COUNT(*) FROM evenements").fetchone()
        assert r is not None
        return int(r[0]), int(r[1])

    def signature(self) -> tuple[int, int, str]:
        """(dernier seq, nombre, compteur de réécritures) en UNE requête — audit des lots 2-3, I5 : une purge faite par un
        autre objet (ou un autre processus) sur le même journal se voit, même si elle ne change ni le dernier seq ni le
        nombre de faits."""
        if not self._meta:
            self._meta = self.table_existe("journal_meta")
        if not self._meta:
            d, n = self.dernier_et_nombre()
            return d, n, ""
        r = self.executer("SELECT COALESCE(MAX(seq), 0), COUNT(*), (SELECT valeur FROM journal_meta WHERE cle = 'reecritures') "
                          "FROM evenements").fetchone()
        return int(r[0]), int(r[1]), r[2] or ""

    def depuis(self, seq: int) -> Iterable[tuple[int, str]]:
        return self._x("SELECT seq, donnees FROM evenements WHERE seq > %s ORDER BY seq", (seq,)).fetchall()

    def inserer(self, id_: str, donnees: str) -> int:
        r = self._x("INSERT INTO evenements (id, donnees) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING RETURNING seq",
                             (id_, donnees)).fetchone()
        if r:
            return int(r[0])
        s = self._x("SELECT seq FROM evenements WHERE id = %s", (id_,)).fetchone()
        assert s is not None
        return int(s[0])

    def debut(self) -> None:
        self._x("BEGIN")
        self._tx = True

    def valider(self) -> None:
        self._tx = False
        self._x("COMMIT")

    def annuler(self) -> None:
        """Ne lève jamais : connexion perdue → le serveur a déjà tout annulé ; autre échec → connexion fermée (rouverte
        à la prochaine requête), jamais réutilisée dans un état inconnu."""
        import psycopg
        self._tx = False
        try:
            self._db.execute("ROLLBACK")
        except psycopg.Error:
            self._db.close()

    def inserer_a(self, seq: int, id_: str, donnees: str) -> None:
        """Restauration : à son numéro d'origine, puis la séquence repart après le plus grand."""
        self._x("INSERT INTO evenements (seq, id, donnees) VALUES (%s, %s, %s)", (seq, id_, donnees))
        self._x("SELECT setval(pg_get_serial_sequence('evenements', 'seq'), "
                         "GREATEST((SELECT MAX(seq) FROM evenements), 1))")

    def vider(self) -> None:
        self._x("DELETE FROM evenements")

    def table_existe(self, nom: str) -> bool:
        r = self._x("SELECT to_regclass(%s)", (nom,)).fetchone()
        return r is not None and r[0] is not None


def ouvrir(adresse: Optional[str]) -> Stockage:
    """`:memory:`, un chemin de fichier, ou `postgresql://…` (`postgres://…`). Toute autre adresse est refusée."""
    a = adresse or ":memory:"
    if a.startswith(("postgresql://", "postgres://")):
        return _Postgres(a)
    if "://" in a:
        raise ValueError(f"moteur de stockage inconnu : {a.split('://', 1)[0]}:// (SQLite ou postgresql:// seulement)")
    return _Sqlite(a)
