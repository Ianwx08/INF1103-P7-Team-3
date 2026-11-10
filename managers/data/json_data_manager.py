"""JsonDataManager: Stores found items as a list of records in one JSON file."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Callable

from managers.base.base_data_manager import BaseDataManager
from managers.data.constants import DEFAULT_DATA_DIR
from models.constants import DATETIME_FORMAT
from models.found_item import FoundItem


class JsonDataManager(BaseDataManager):
    """Stores found items as a list of records in one JSON file.

    Safe saving: writes to <file>.tmp first and swaps it in, so a crash mid-save cannot
    corrupt the data. A file that cannot be read is renamed to <file>.corrupt-<time>
    instead of being overwritten. The JSON shape is the same as Phase 1.
    """

    ID_PREFIX = "FND-"   # IDs look like FND-0001

    def __init__(self, file_path: str | None = None,
                 notify: Callable[[str], None] = print) -> None:
        """Use file_path, or DATA_DIR/found_items.json. notify shows warnings (default: print)."""
        if file_path is None:
            file_path = os.path.join(os.getenv("DATA_DIR", DEFAULT_DATA_DIR), "found_items.json")
        self.__file_path = file_path
        self._notify = notify

    @property
    def file_path(self) -> str:
        """Where the items are stored (read-only)."""
        return self.__file_path

    # ---- BaseDataManager interface ----
    def load_all(self) -> list[FoundItem]:
        return [FoundItem.from_dict(record) for record in self._read_records()]

    def add(self, item: FoundItem) -> FoundItem:
        records = self._read_records()
        if item.item_id is None:
            item.assign_id(self._next_id(records), datetime.now().strftime(DATETIME_FORMAT))
        records.append(item.to_dict())
        self._write_records(records)
        return item

    def update(self, item: FoundItem) -> bool:
        records = self._read_records()
        for index, record in enumerate(records):
            if item.item_id is not None and record.get("item_id") == item.item_id:
                records[index] = item.to_dict()
                self._write_records(records)
                return True
        return False

    def delete(self, item_id: str) -> bool:
        records = self._read_records()
        remaining = [record for record in records if record.get("item_id") != item_id]
        if len(remaining) == len(records):
            return False
        self._write_records(remaining)
        return True

    # ---- file handling (protected: only this class and subclasses use it) ----
    def _read_records(self) -> list[dict[str, Any]]:
        """All stored records. Missing file -> []. Corrupt file -> backed up, then []."""
        os.makedirs(os.path.dirname(self.__file_path) or ".", exist_ok=True)
        if not os.path.exists(self.__file_path):
            return []
        try:
            with open(self.__file_path, "r", encoding="utf-8") as file:
                records = json.load(file)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._backup_corrupt_file()
            return []
        if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
            self._backup_corrupt_file()
            return []
        return records

    def _write_records(self, records: list[dict[str, Any]]) -> None:
        """Write to a temporary file, then swap it in so the real file is never half-written."""
        os.makedirs(os.path.dirname(self.__file_path) or ".", exist_ok=True)
        temp_path = self.__file_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(records, file, indent=2, ensure_ascii=False)
        os.replace(temp_path, self.__file_path)

    def _backup_corrupt_file(self) -> None:
        """Rename an unreadable file to <file>.corrupt-<YYYYMMDDHHMMSS> so its data is kept."""
        backup_path = f"{self.__file_path}.corrupt-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        os.replace(self.__file_path, backup_path)
        self._notify(f"Warning: found items file was unreadable. Backed up to {backup_path}")

    def _next_id(self, records: list[dict[str, Any]]) -> str:
        """Next sequential ID after the highest one stored, e.g. FND-0004."""
        highest = 0
        for record in records:
            item_id = str(record.get("item_id", ""))
            suffix = item_id[len(self.ID_PREFIX):]
            if item_id.startswith(self.ID_PREFIX) and suffix.isdigit():
                highest = max(highest, int(suffix))
        return f"{self.ID_PREFIX}{highest + 1:04d}"
