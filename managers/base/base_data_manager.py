"""BaseDataManager: Found-item storage (the only thing the app stores)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from managers.base.sequential_id import SequentialId
from models.found_item import FoundItem


class BaseDataManager(ABC):
    """Stores found items, with their value assessment and last escalation time. Lost searches are never stored."""

    ID_PREFIX = "FND-"   # every store gives IDs like FND-0001

    @abstractmethod
    def load_all(self) -> list[FoundItem]:
        """Every stored found item, active and archived."""

    @abstractmethod
    def add(self, item: FoundItem) -> FoundItem:
        """Save a new found item; gives it an ID and report time. Returns the stored item."""

    @abstractmethod
    def update(self, item: FoundItem) -> bool:
        """Save changes to an existing item (matched by ID). True if it was found."""

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """Remove an item, e.g. when it is claimed. True if it existed."""

    def get(self, item_id: str) -> FoundItem | None:
        """One stored item by its ID (active or archived), or None if there is none.

        Default: search load_all(). A store may override it with a faster lookup,
        as long as it returns the same item (the database store uses its primary key).
        """
        return next((item for item in self.load_all() if item.item_id == item_id), None)

    def get_active(self) -> list[FoundItem]:
        """Items that can still be matched (not archived).

        Default: filter load_all(). A store may override it with a faster query,
        as long as it returns the same items (the database store does).
        """
        return [item for item in self.load_all() if item.is_active()]

    @classmethod
    def _next_id_from(cls, existing_ids: Iterable[str | None]) -> str:
        """The next sequential ID after the highest one in existing_ids, e.g. FND-0004.

        One rule for every store, so JSON and the database number items the same way.
        """
        return SequentialId(cls.ID_PREFIX).next_after(existing_ids)
