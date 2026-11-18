"""SqliteColumnMigrator: Adds columns that an older version of a table does not have yet."""
from __future__ import annotations

import sqlite3
from typing import Mapping


class SqliteColumnMigrator:
    """Adds columns that an older version of a table does not have yet.

    Uses ALTER TABLE ... ADD COLUMN only: existing rows are not rewritten and keep every value;
    the new columns read NULL. SqliteDatabase runs apply() inside its BEGIN IMMEDIATE transaction,
    so a failure rolls the new columns back too, and a second app window waits for the lock and
    then finds the columns already there.

    Table and column names come from the owning store's class constants, never from user input.
    """

    def __init__(self, table: str, columns: Mapping[str, str]) -> None:
        """table: the table to upgrade. columns: name -> declaration (type and CHECK), in the order to add them."""
        self._table = table
        self._columns = dict(columns)

    def missing(self, db: sqlite3.Connection) -> list[str]:
        """Column names the table does not have yet, in the order given."""
        existing = {row[1] for row in db.execute(f'PRAGMA table_info("{self._table}")')}
        return [name for name in self._columns if name not in existing]

    def apply(self, db: sqlite3.Connection) -> list[str]:
        """Add every missing column; return the names added (empty if the table is up to date)."""
        added = self.missing(db)
        for name in added:
            db.execute(f'ALTER TABLE "{self._table}" ADD COLUMN "{name}" {self._columns[name]}')
        return added
