"""BaseIOManager: Everything the user sees or types. Holds no business rules."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from models.found_item import FoundItem
from models.item import Item
from models.item_match import ItemMatch


class BaseIOManager(ABC):
    """Everything the user sees or types. Holds no business rules."""

    BACK_COMMAND = "back"   # typing this at a question returns to the main menu

    @abstractmethod
    def menu(self) -> str:
        """Show the main menu; return "lost", "found" or "exit"."""

    @abstractmethod
    def get_report_details(self, report_type: str) -> dict[str, str] | None:
        """Ask description, date/time and place, then confirm them. None if the user goes back."""

    @abstractmethod
    def ask_detail(self, prompt: str, min_words: int, max_words: int, error: str) -> str | None:
        """Ask until the answer has an allowed number of words. None if the user types 'back'."""

    @abstractmethod
    def ask_confirm_or_correct(self, prompt: str) -> str | None:
        """Ask a question where Enter keeps the current value. Returns "" for Enter, None for 'back'."""

    @abstractmethod
    def choose_option(self, heading: str, options: Sequence[str]) -> str | None:
        """Pick one option from a numbered list. None if the user types 'back'."""

    @abstractmethod
    def choose_match(self, matches: Sequence[ItemMatch],
                     possible_matches: Sequence[ItemMatch]) -> FoundItem | None:
        """Show top and possible matches as one numbered list; return the chosen item or None."""

    @abstractmethod
    def confirm(self, prompt: str) -> bool:
        """Ask a yes/no question."""

    @abstractmethod
    def confirm_duplicate(self, duplicates: Sequence[FoundItem]) -> bool:
        """Show similar stored items; True if the user still wants to save the new report."""

    @abstractmethod
    def show_item(self, item: Item) -> None:
        """Show one item."""

    @abstractmethod
    def show_not_found(self) -> None:
        """Tell the user no stored item matched."""

    @abstractmethod
    def show_message(self, message: str) -> None:
        """Show a line of text."""