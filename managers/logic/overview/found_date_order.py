"""FoundDateOrder: By when the item was found. Items with no readable date go last, in their stored order."""
from __future__ import annotations

from typing import Sequence

from managers.base.item_sort_order import ItemSortOrder
from models.found_item import FoundItem


class FoundDateOrder(ItemSortOrder):
    """By when the item was found. Items with no readable date go last, in their stored order."""

    def __init__(self, newest_first: bool = True) -> None:
        self._newest_first = newest_first
        self.label = "Date found (newest first)" if newest_first else "Date found (oldest first)"

    def sort(self, items: Sequence[FoundItem]) -> list[FoundItem]:
        dated = [item for item in items if item.occurred_at is not None]
        undated = [item for item in items if item.occurred_at is None]
        dated.sort(key=lambda item: item.occurred_at, reverse=self._newest_first)
        return dated + undated
