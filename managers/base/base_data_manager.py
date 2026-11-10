"""BaseDataManager: Stores found items. Lost reports are never stored."""
from __future__ import annotations

from abc import ABC, abstractmethod

from models.found_item import FoundItem


class BaseDataManager(ABC):
    """Stores found items. Lost reports are never stored."""

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

        Used to check an item is still available just before it is claimed. Concrete, so
        every store has it; a store may override it with a faster lookup that returns the same item.
        """
        return next((item for item in self.load_all() if item.item_id == item_id), None)

    def get_active(self) -> list[FoundItem]:
        """Items that can still be matched (not archived). Shared by every implementation."""
        return [item for item in self.load_all() if item.is_active()]
