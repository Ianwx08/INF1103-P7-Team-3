"""SqliteDatabase: One SQLite file: opens it, makes sure a table exists, runs work in a transaction."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Callable, TypeVar

from managers.data.sqlite_column_migrator import SqliteColumnMigrator

T = TypeVar("T")


class SqliteDatabase:
    """One SQLite file: opens it, makes sure a table exists, runs work in a transaction.

    Stores that keep a table in the file own one of these (composition) instead of
    inheriting from each other, so each store only has the methods of its own interface.
    - Every run() is one transaction: saved completely or not at all.
    - Database errors are raised as OSError, the error type the app already handles.
    - A file that is not a valid database is renamed to <file>.corrupt-<time> and a new one started.
    - An optional SqliteColumnMigrator (composition) upgrades an older table inside the same
      transaction as the work, so the upgrade is all-or-nothing too.
    """

    def __init__(self, db_path: str, schema: str, notify: Callable[[str], None] = print,
                 migrator: SqliteColumnMigrator | None = None) -> None:
        """schema is the CREATE TABLE IF NOT EXISTS script for the owner's table; migrator adds newer columns."""
        self.__db_path = db_path
        self._schema = schema
        self._notify = notify
        self._migrator = migrator

    @property
    def db_path(self) -> str:
        """Where the database file is (read-only)."""
        return self.__db_path

    def run(self, action: Callable[[sqlite3.Connection], T]) -> T:
        """Run action in one transaction. Unreadable file -> backed up, then retried on a new one."""
        try:
            try:
                return self._transaction(action)
            except sqlite3.DatabaseError as error:
                # Only a plain DatabaseError ("file is not a database", "malformed") means a corrupt
                # file. Its subclasses are real failures that must not discard data: IntegrityError
                # (e.g. duplicate ID), OperationalError (locked, cannot open), and so on.
                if type(error) is not sqlite3.DatabaseError or not os.path.exists(self.__db_path):
                    raise
                self._backup_corrupt_file()
                return self._transaction(action)
        except sqlite3.Error as error:
            raise OSError(f"database error: {error}") from error

    def _transaction(self, action: Callable[[sqlite3.Connection], T]) -> T:
        """Open the database, make sure the table exists and is up to date, run action, commit (or roll back), close."""
        os.makedirs(os.path.dirname(self.__db_path) or ".", exist_ok=True)
        db = sqlite3.connect(self.__db_path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.executescript(self._schema)
            db.execute("BEGIN IMMEDIATE")      # lock for writing, so two app windows cannot clash
            try:
                if self._migrator is not None:
                    self._migrator.apply(db)   # rolled back with everything else if anything fails
                result = action(db)
            except BaseException:
                db.execute("ROLLBACK")
                raise
            db.execute("COMMIT")
            return result
        finally:
            db.close()

    def _backup_corrupt_file(self) -> None:
        """Rename an unreadable database to <file>.corrupt-<YYYYMMDDHHMMSS> so its data is kept."""
        backup_path = f"{self.__db_path}.corrupt-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        os.replace(self.__db_path, backup_path)
        self._notify(f"Warning: found items database was unreadable. Backed up to {backup_path}")
