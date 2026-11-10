"""LostItem: An item someone has lost. Used for a one-time search and never stored."""
from __future__ import annotations

from models.item import Item


class LostItem(Item):
    """An item someone has lost. Used for a one-time search and never stored."""

    @property
    def report_type(self) -> str:
        return "lost"
