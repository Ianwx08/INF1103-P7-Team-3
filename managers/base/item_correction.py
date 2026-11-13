"""ItemCorrection: A fix the user makes directly, without another Gemini call (e.g. picking one colour)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from managers.base.base_io_manager import BaseIOManager
from models.item import Item

class ItemCorrection(ABC):
    """A fix the user makes directly, without another Gemini call (e.g. picking one colour)."""

    @abstractmethod
    def applies(self, item: Item) -> bool:
        """True if the user needs to make this correction."""

    @abstractmethod
    def correct(self, io: BaseIOManager, item: Item) -> Item | None:
        """Ask the user and return the corrected copy, or None if they typed 'back'."""