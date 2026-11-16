"""StoredItemsOverview: What the "View stored items" screen shows. Immutable, so the IO layer cannot change it."""
from __future__ import annotations

from dataclasses import dataclass

from models.found_item import FoundItem


@dataclass(frozen=True)
class StoredItemsOverview:
    """What the "View stored items" screen shows. Immutable, so the IO layer cannot change it.

    items        active found items, already sorted
    sort_label   how they were sorted, e.g. "Date found (newest first)"
    type_counts  (item type, how many), most common first
    archived_count  archived items that exist but are not listed
    """

    sort_label: str
    items: tuple[FoundItem, ...]
    type_counts: tuple[tuple[str, int], ...] = ()
    archived_count: int = 0

    def __post_init__(self) -> None:
        if self.archived_count < 0:
            raise ValueError("archived_count cannot be negative")

    @property
    def total(self) -> int:
        """How many items are listed."""
        return len(self.items)

    def is_empty(self) -> bool:
        """True when there is nothing to list."""
        return not self.items
