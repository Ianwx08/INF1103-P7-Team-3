"""SqliteDataManager: Stores found items in the found_items table of an SQLite database file."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Callable, TypeVar

from managers.base.base_data_manager import BaseDataManager
from managers.data.constants import DEFAULT_DATA_DIR
from managers.data.found_item_row_mapper import FoundItemRowMapper
from models.constants import DATETIME_FORMAT
from models.found_item import FoundItem

T = TypeVar("T")


class SqliteDataManager(BaseDataManager):
    """Stores found items in the found_items table of an SQLite database file.

    - Every operation runs in one transaction: it is saved completely or not at all.
    - All values are passed as SQL parameters (never pasted into the SQL text), so
      a description such as "x'); DROP TABLE found_items; --" is stored as plain text.
    - Database errors are raised as OSError, the same error type JsonDataManager raises,
      so the app's "Could not read or save the data file" handling works unchanged (LSP).
    - A file that is not a valid database is renamed to <file>.corrupt-<time>, like the JSON store.
    """

    TABLE = "found_items"
    SCHEMA = """
        CREATE TABLE IF NOT EXISTS found_items (
            item_id                      TEXT PRIMARY KEY,
            report_type                  TEXT NOT NULL DEFAULT 'found',
            reported_at                  TEXT,
            status                       TEXT NOT NULL DEFAULT 'active'
                                         CHECK (status IN ('active', 'archived')),
            item_description             TEXT,
            item_description_confidence  REAL NOT NULL DEFAULT 0,
            item_type                    TEXT,
            item_type_confidence         REAL NOT NULL DEFAULT 0,
            item_colour                  TEXT,
            item_colour_confidence       REAL NOT NULL DEFAULT 0,
            item_brand                   TEXT,
            item_brand_confidence        REAL NOT NULL DEFAULT 0,
            item_unique_info             TEXT,
            item_unique_info_confidence  REAL NOT NULL DEFAULT 0,
            "datetime"                   TEXT,
            datetime_confidence          REAL NOT NULL DEFAULT 0,
            location                     TEXT,
            location_confidence          REAL NOT NULL DEFAULT 0,
            colour_options               TEXT NOT NULL DEFAULT '[]',
            prohibited_item              INTEGER NOT NULL DEFAULT 0,
            item_recognised              INTEGER NOT NULL DEFAULT 1,
            location_specific            INTEGER NOT NULL DEFAULT 1,
            missing_fields               TEXT NOT NULL DEFAULT '[]',
            overall_confidence           REAL NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_found_items_status ON found_items (status);
        CREATE INDEX IF NOT EXISTS idx_found_items_type ON found_items (item_type);
    """

    def __init__(self, db_path: str | None = None, notify: Callable[[str], None] = print,
                 mapper: FoundItemRowMapper | None = None) -> None:
        """Use db_path, or DATA_DIR/found_items.db. notify shows warnings (default: print)."""
        if db_path is None:
            db_path = os.path.join(os.getenv("DATA_DIR", DEFAULT_DATA_DIR), "found_items.db")
        self.__db_path = db_path
        self._notify = notify
        self._mapper = mapper or FoundItemRowMapper()

    @property
    def db_path(self) -> str:
        """Where the database file is (read-only)."""
        return self.__db_path

    # ---- BaseDataManager interface ----
    def load_all(self) -> list[FoundItem]:
        rows = self._run(lambda db: db.execute(f"SELECT * FROM {self.TABLE} ORDER BY rowid").fetchall())
        return [self._mapper.from_row(row) for row in rows]

    def get(self, item_id: str) -> FoundItem | None:
        """Same result as the base version, but one primary-key lookup instead of loading every row."""
        row = self._run(lambda db: db.execute(
            f"SELECT * FROM {self.TABLE} WHERE item_id = ?", (item_id,)).fetchone())
        return None if row is None else self._mapper.from_row(row)

    def get_active(self) -> list[FoundItem]:
        """Same result as the base version, but filtered by the database (uses the status index)."""
        rows = self._run(lambda db: db.execute(
            f"SELECT * FROM {self.TABLE} WHERE status = ? ORDER BY rowid", (FoundItem.ACTIVE,)).fetchall())
        return [self._mapper.from_row(row) for row in rows]

    def add(self, item: FoundItem) -> FoundItem:
        def insert(db: sqlite3.Connection) -> None:
            if item.item_id is None:
                existing = [row[0] for row in db.execute(f"SELECT item_id FROM {self.TABLE}")]
                item.assign_id(self._next_id_from(existing), datetime.now().strftime(DATETIME_FORMAT))
            columns = self._mapper.COLUMNS
            db.execute(
                f"INSERT INTO {self.TABLE} ({', '.join(self._quote(c) for c in columns)}) "
                f"VALUES ({', '.join(':' + c for c in columns)})",
                self._mapper.to_row(item))
        self._run(insert)
        return item

    def update(self, item: FoundItem) -> bool:
        if item.item_id is None:
            return False
        assignments = ", ".join(f"{self._quote(c)} = :{c}" for c in self._mapper.COLUMNS if c != "item_id")
        changed = self._run(lambda db: db.execute(
            f"UPDATE {self.TABLE} SET {assignments} WHERE item_id = :item_id",
            self._mapper.to_row(item)).rowcount)
        return changed > 0

    def delete(self, item_id: str) -> bool:
        removed = self._run(lambda db: db.execute(
            f"DELETE FROM {self.TABLE} WHERE item_id = ?", (item_id,)).rowcount)
        return removed > 0

    # ---- database handling (protected: only this class and subclasses use it) ----
    @staticmethod
    def _quote(column: str) -> str:
        """Column names in double quotes, so "datetime" is never read as SQL's datetime()."""
        return f'"{column}"'

    def _run(self, action: Callable[[sqlite3.Connection], T]) -> T:
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
        """Open the database, make sure the table exists, run action, commit (or roll back), close."""
        os.makedirs(os.path.dirname(self.__db_path) or ".", exist_ok=True)
        db = sqlite3.connect(self.__db_path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.executescript(self.SCHEMA)
            db.execute("BEGIN IMMEDIATE")      # lock for writing, so two app windows cannot clash
            try:
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
