"""BaseAIManager: Turns user free-text input into a validated item using AI."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Mapping
from models.item import Item

class BaseAIManager(ABC):
    @abstractmethod
    def analyse(self, report_type: str, answers: Mapping[str, str],
                previous: Item | None = None) -> Item | None:
        """Send the answers to the AI and return a schema-validated item.

        First call: answers = {"description", "date_time", "location"}.
        Follow-up call: answers = {field_name: answer} plus previous item,
        so only those fields are updated. Returns None if the AI fails."""
