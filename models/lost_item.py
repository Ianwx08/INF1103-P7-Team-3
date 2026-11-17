"""LostItem: A lost-item search: the details matching uses. Never stored."""
from __future__ import annotations

from models.item import Item


class LostItem(Item):
    """A lost-item search: the details matching uses. Never stored.

    It has the seven fields and Gemini's flags only. Gemini still returns a value assessment
    with every reply (one schema), but a lost search does not keep it.
    """

    @property
    def report_type(self) -> str:
        return "lost"
