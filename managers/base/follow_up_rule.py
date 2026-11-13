"""FollowUpRule: One reason to ask the user a follow-up question about Gemini's result."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Sequence
from managers.base.base_io_manager import BaseIOManager
from models.item import Item

class FollowUpRule(ABC):
    """One reason to ask the user a follow-up question about Gemini's result.
    Rules are checked in order each round. A blocking rule is asked on its own; the
    answers of all non-blocking rules are combined so Gemini is called once per round.
    """
    
    blocking: bool = False                 # True: only this question this round; fail if unresolved
    handled_fields: tuple[str, ...] = ()   # fields this rule asks about, so later rules skip them

    @abstractmethod
    def applies(self, item: Item) -> bool:
        """True if this rule needs to ask something about the item."""

    @abstractmethod
    def ask(self, io: BaseIOManager, item: Item, report_type: str,
            skip_fields: Sequence[str] = ()) -> dict[str, str] | None:
        """Ask the question(s); return {field: answer} for Gemini, or None if the user typed 'back'.

        skip_fields lists fields an earlier rule already asked about this round.
        """

    def give_up(self, item: Item) -> Item:
        """What to do if the rule still applies after the last round. Default: keep the item."""
        return item