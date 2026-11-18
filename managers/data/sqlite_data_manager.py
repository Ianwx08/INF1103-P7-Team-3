"""SqliteDataManager: Stores found items in the found_items table of an SQLite database file."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Callable, TypeVar

from managers.base.base_data_manager import BaseDataManager
from managers.data.constants import DEFAULT_DATA_DIR
from managers.data.found_item_row_mapper import FoundItemRowMapper
from managers.data.sqlite_column_migrator import SqliteColumnMigrator
from managers.data.sqlite_database import SqliteDatabase
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
    - An older database gains the newer columns (value assessment, escalated_at) automatically
      on first use; existing rows keep every value.
    Composition: owns a SqliteDatabase, which does the file handling and transactions, and gives
    it a SqliteColumnMigrator for the columns in ADDED_COLUMNS.
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
            overall_confidence           REAL NOT NULL DEFAULT 0,
            estimated_value_sgd          REAL,
            sensitive                    INTEGER CHECK (sensitive IN (0, 1)),
            valuation_reason             TEXT,
            value_category               TEXT CHECK (value_category IN ('HIGH_VALUE', 'ORDINARY')),
            escalated_at                 TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_found_items_status ON found_items (status);
        CREATE INDEX IF NOT EXISTS idx_found_items_type ON found_items (item_type);
    """
     # Columns added after the first version of the table. Databases made before then gain them
    # on first use (SqliteColumnMigrator); no index on them here, because SCHEMA runs before that.
    ADDED_COLUMNS = {
        "estimated_value_sgd": "REAL",
        "sensitive": "INTEGER CHECK (sensitive IN (0, 1))",
        "valuation_reason": "TEXT",
        "value_category": "TEXT CHECK (value_category IN ('HIGH_VALUE', 'ORDINARY'))",
        "escalated_at": "TEXT",
    }

    def __init__(self, db_path: str | None = None, notify: Callable[[str], None] = print,
                 mapper: FoundItemRowMapper | None = None) -> None:
        """Use db_path, or DATA_DIR/found_items.db. notify shows warnings (default: print)."""
        if db_path is None:
            db_path = os.path.join(os.getenv("DATA_DIR", DEFAULT_DATA_DIR), "found_items.db")
        self._database = SqliteDatabase(db_path, self.SCHEMA, notify,
                                        SqliteColumnMigrator(self.TABLE, self.ADDED_COLUMNS))
        self._mapper = mapper or FoundItemRowMapper()

    @property
    def db_path(self) -> str:
        """Where the database file is (read-only)."""
        return self._database.db_path

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
        """Run action in one transaction of the database file (see SqliteDatabase.run)."""
        return self._database.run(action)
