"""ItemTypeOrder: By item type A-Z (ignoring case); items without a type go last."""
from __future__ import annotations

from typing import Sequence

from managers.base.item_sort_order import ItemSortOrder
from managers.logic.overview.found_date_order import FoundDateOrder
from models.found_item import FoundItem


class ItemTypeOrder(ItemSortOrder):
    """By item type A-Z (ignoring case); items without a type go last.

    Items of the same type keep the order of a second sort order, newest found
    first by default (composition: this order owns the tie-breaking order).
    """

    label = "Item type (A-Z)"

    def __init__(self, within_type: ItemSortOrder | None = None) -> None:
        self._within_type = within_type or FoundDateOrder(newest_first=True)

    def sort(self, items: Sequence[FoundItem]) -> list[FoundItem]:
        ordered = self._within_type.sort(items)
        typed = [item for item in ordered if not item.item_type.is_empty()]
        untyped = [item for item in ordered if item.item_type.is_empty()]
        typed.sort(key=lambda item: item.item_type.text.lower())   # stable: keeps the date order
        return typed + untyped
