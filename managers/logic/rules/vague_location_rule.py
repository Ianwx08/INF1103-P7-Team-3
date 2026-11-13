"""VagueLocationRule: The place is too vague for someone else to find. Enter cannot skip it."""
from __future__ import annotations
from typing import Sequence
from managers.base.base_io_manager import BaseIOManager
from managers.base.follow_up_rule import FollowUpRule
from models.item import Item

class VagueLocationRule(FollowUpRule):
    """The place is too vague for someone else to find. Enter cannot skip it."""

    handled_fields = ("location",)

    def applies(self, item: Item) -> bool:
        return not item.location.is_empty() and not item.flags.location_specific

    def ask(self, io: BaseIOManager, item: Item, report_type: str,
            skip_fields: Sequence[str] = ()) -> dict[str, str] | None:
        verb = "lost" if report_type == "lost" else "found"
        io.show_message(f"\n'{item.location.value}' is too vague for someone else to find.")
        answer = io.ask_detail(
            f"  Where exactly was it {verb}? (e.g. building and level, mall, MRT station, "
            f"street name; '{io.BACK_COMMAND}' for main menu): ", 1, 30,
            "Please enter a location of up to 30 words.")
        return None if answer is None else {"location": answer}