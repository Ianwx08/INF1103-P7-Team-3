"""DataMigrator: Copies every item from one store into another, keeping IDs, report times and status."""
from __future__ import annotations

from managers.base.base_data_manager import BaseDataManager


class DataMigrator:
    """Copies every item from one store into another, keeping IDs, report times and status.

    Works with any two BaseDataManager objects (it only uses the interface), so the same
    class could move data from the database back to JSON, or into a future store.
    """

    def __init__(self, source: BaseDataManager, target: BaseDataManager) -> None:
        self._source = source
        self._target = target

    def migrate(self) -> int:
        """Copy the items if the target is empty; returns how many were copied.

        A target that already holds items is left alone, so data is never mixed or duplicated.
        """
        if self._target.load_all():
            return 0
        items = self._source.load_all()
        for item in items:
            self._target.add(item)      # items keep their IDs: add() only numbers new items
        return len(items)
