"""DataManagerFactory: Builds the data manager chosen by STORAGE_BACKEND ("sqlite" by default, or "json")."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Callable

from managers.base.base_data_manager import BaseDataManager
from managers.data.constants import DEFAULT_DATA_DIR
from managers.data.data_migrator import DataMigrator
from managers.data.json_data_manager import JsonDataManager
from managers.data.sqlite_data_manager import SqliteDataManager


class DataManagerFactory:
    """Builds the data manager chosen by STORAGE_BACKEND ("sqlite" by default, or "json").

    Factory pattern: main.py asks for "a BaseDataManager" and never names a class, so adding
    another store means adding it here only (Open/Closed).
    The first time the database is used, items in an old found_items.json are imported and
    that file is renamed to found_items.json.imported-<time> so they are not imported twice.
    """

    SQLITE = "sqlite"
    JSON = "json"
    BACKENDS = (SQLITE, JSON)
    DEFAULT_BACKEND = SQLITE
    JSON_FILE = "found_items.json"
    DB_FILE = "found_items.db"

    def __init__(self, backend: str | None = None, data_dir: str | None = None,
                 notify: Callable[[str], None] = print) -> None:
        """backend and data_dir default to the STORAGE_BACKEND and DATA_DIR settings."""
        chosen = (backend or os.getenv("STORAGE_BACKEND") or self.DEFAULT_BACKEND).strip().lower()
        if chosen not in self.BACKENDS:
            raise ValueError(f"STORAGE_BACKEND must be one of {', '.join(self.BACKENDS)}, not {chosen!r}.")
        self._backend = chosen
        self._data_dir = data_dir or os.getenv("DATA_DIR", DEFAULT_DATA_DIR)
        self._notify = notify

    @property
    def backend(self) -> str:
        return self._backend

    def create(self) -> BaseDataManager:
        """The data manager to use, with old JSON data imported into the database if needed."""
        json_store = JsonDataManager(os.path.join(self._data_dir, self.JSON_FILE), self._notify)
        if self._backend == self.JSON:
            return json_store
        database = SqliteDataManager(os.path.join(self._data_dir, self.DB_FILE), self._notify)
        if os.path.exists(json_store.file_path):
            self._import_json(json_store, database)
        return database

    def _import_json(self, json_store: JsonDataManager, database: SqliteDataManager) -> None:
        """One-time import of found_items.json into an empty database. Errors are reported, not fatal."""
        try:
            copied = DataMigrator(json_store, database).migrate()
        except OSError as error:
            self._notify(f"Could not import {json_store.file_path} into the database: {error}")
            return
        if copied:
            done_path = f"{json_store.file_path}.imported-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            os.replace(json_store.file_path, done_path)
            self._notify(f"Imported {copied} found item(s) into the database. "
                         f"The old file was kept as {done_path}")
