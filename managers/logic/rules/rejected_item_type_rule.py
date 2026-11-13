"""RejectedItemTypeRule: Base for rules that reject the item type and re-ask it. Blocking: asked on its own."""
from __future__ import annotations
from typing import Sequence
from managers.base.base_io_manager import BaseIOManager
from managers.base.follow_up_rule import FollowUpRule
from models.item import Item

class RejectedItemTypeRule(FollowUpRule):
    """Base for rules that reject the item type and re-ask it. Blocking: asked on its own."""

    blocking = True
    handled_fields = ("item_type",)
    message = ""   # set by subclasses

    def ask(self, io: BaseIOManager, item: Item, report_type: str,
            skip_fields: Sequence[str] = ()) -> dict[str, str] | None:
        action = "lose" if report_type == "lost" else "find"
        io.show_message("\n" + self.message)
        answer = io.ask_detail(
            f"  What kind of item did you {action}? (e.g. phone, wallet, bottle; "
            f"'{io.BACK_COMMAND}' for main menu): ", 1, 30,
            "Please enter the item type (up to 30 words).")
        return None if answer is None else {"item_type": answer}