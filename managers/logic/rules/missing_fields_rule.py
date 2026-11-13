"""MissingFieldsRule: Required fields that are empty, listed as missing by Gemini, or below the confidence threshold."""
from __future__ import annotations
from typing import Sequence
from managers.base.base_io_manager import BaseIOManager
from managers.base.follow_up_rule import FollowUpRule
from models.item import Item

class MissingFieldsRule(FollowUpRule):
    """Required fields that are empty, listed as missing by Gemini, or below the confidence threshold."""

    REQUIRED_FIELDS = ("item_description", "item_type", "item_colour", "datetime", "location")
    LOW_CONFIDENCE_THRESHOLD = 0.60
    LABELS = {
        "item_description": "item description", "item_type": "item type", "item_colour": "colour",
        "item_brand": "brand", "item_unique_info": "unique features",
        "datetime": "date and time", "location": "location",
    }
    QUESTIONS = {
        "item_description": "Please describe the item (e.g. Samsung Galaxy S25): ",
        "item_type": "What kind of item is it (e.g. phone, wallet, bottle)? ",
        "item_colour": "What colour is it? ",
        "datetime": "When was it {verb}? (e.g. 'yesterday 3pm', '8 Oct around noon'): ",
        "location": "Where was it {verb}? ",
    }

    def flagged(self, item: Item) -> list[str]:
        """The required fields that need a question."""
        return [name for name in self.REQUIRED_FIELDS
                if item.field(name).is_empty() or name in item.flags.missing_fields
                or item.field(name).confidence < self.LOW_CONFIDENCE_THRESHOLD]

    def applies(self, item: Item) -> bool:
        return bool(self.flagged(item))

    def ask(self, io: BaseIOManager, item: Item, report_type: str,
            skip_fields: Sequence[str] = ()) -> dict[str, str] | None:
        fields = [name for name in self.flagged(item) if name not in skip_fields]
        if not fields:
            return {}
        verb = "lost" if report_type == "lost" else "found"
        io.show_message(f"\nWe need a few more details (type '{io.BACK_COMMAND}' for main menu):")
        answers: dict[str, str] = {}
        for name in fields:
            current, label = item.field(name).value, self.LABELS[name]
            if current:
                answer = io.ask_confirm_or_correct(
                    f"  We understood the {label} as '{current}'. Press Enter to confirm, or type a correction: ")
                if answer is None:
                    return None
                answers[name] = answer if answer else f"{current} (confirmed by the user)"
            else:
                answer = io.ask_detail("  " + self.QUESTIONS[name].format(verb=verb), 1, 30,
                                       f"Please enter the {label} (up to 30 words).")
                if answer is None:
                    return None
                answers[name] = answer
        return answers