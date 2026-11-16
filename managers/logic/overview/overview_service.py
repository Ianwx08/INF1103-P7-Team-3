"""OverviewService: Builds the overview of stored found items."""
from __future__ import annotations

from collections import Counter
from typing import Sequence

from managers.base.item_sort_order import ItemSortOrder
from managers.logic.overview.found_date_order import FoundDateOrder
from managers.logic.overview.item_type_order import ItemTypeOrder
from models.found_item import FoundItem
from models.stored_items_overview import StoredItemsOverview


class OverviewService:
    """Builds the overview of stored found items.

    Aggregation: holds the sort orders it is given, so a new order is a new
    ItemSortOrder subclass passed in here; this class does not change (Open/Closed).
    """

    UNKNOWN_TYPE = "unknown"

    def __init__(self, orders: Sequence[ItemSortOrder] | None = None) -> None:
        orders = list(orders) if orders is not None else self.default_orders()
        if not orders:
            raise ValueError("OverviewService needs at least one sort order")
        labels = [order.label for order in orders]
        if len(set(labels)) != len(labels):
            raise ValueError(f"Sort order labels must be unique: {labels}")
        self._orders = tuple(orders)

    @staticmethod
    def default_orders() -> list[ItemSortOrder]:
        """The choices shown to the user, in menu order."""
        return [FoundDateOrder(newest_first=True), FoundDateOrder(newest_first=False), ItemTypeOrder()]

    @property
    def orders(self) -> tuple[ItemSortOrder, ...]:
        return self._orders

    @property
    def labels(self) -> list[str]:
        """The sort menu options."""
        return [order.label for order in self._orders]

    def find_order(self, label: str) -> ItemSortOrder:
        """The order with this menu label. KeyError if there is none."""
        for order in self._orders:
            if order.label == label:
                return order
        raise KeyError(f"Unknown sort order: {label}")

    def build(self, items: Sequence[FoundItem], order: ItemSortOrder) -> StoredItemsOverview:
        """Active items in the chosen order, a count per item type, and how many are archived."""
        active = [item for item in items if item.is_active()]
        counts = Counter(item.item_type.text.lower() or self.UNKNOWN_TYPE for item in active)
        type_counts = tuple(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))
        return StoredItemsOverview(
            sort_label=order.label,
            items=tuple(order.sort(active)),
            type_counts=type_counts,
            archived_count=len(items) - len(active),
        )
