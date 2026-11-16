"""ItemSortOrder: One way to order stored found items for the overview screen."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from models.found_item import FoundItem


class ItemSortOrder(ABC):
    """One way to order stored found items for the overview screen.

    New orders are new subclasses passed to OverviewService (Open/Closed); every
    order returns a new list and never changes or drops the items it is given (Liskov).
    """

    label: str = ""   # shown in the sort menu, e.g. "Item type (A-Z)"

    @abstractmethod
    def sort(self, items: Sequence[FoundItem]) -> list[FoundItem]:
        """The same items in this order, as a new list."""
