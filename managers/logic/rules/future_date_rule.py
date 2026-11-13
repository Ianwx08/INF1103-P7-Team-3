"""FutureDateRule: An item cannot be lost or found in the future. If still future after the last round, the date is cleared."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Callable, Sequence
from managers.base.base_io_manager import BaseIOManager
from managers.base.follow_up_rule import FollowUpRule
from models.extracted_field import ExtractedField
from models.item import Item

class FutureDateRule(FollowUpRule):
    """An item cannot be lost or found in the future. If still future after the last round, the date is cleared."""

    handled_fields = ("datetime",)
    TOLERANCE_HOURS = 1   # allow small clock differences

    def __init__(self, clock: Callable[[], datetime] = datetime.now) -> None:
        self._clock = clock

    def applies(self, item: Item) -> bool:
        when = item.occurred_at
        return when is not None and when > self._clock() + timedelta(hours=self.TOLERANCE_HOURS)

    def ask(self, io: BaseIOManager, item: Item, report_type: str,
            skip_fields: Sequence[str] = ()) -> dict[str, str] | None:
        verb = "lost" if report_type == "lost" else "found"
        io.show_message(f"\n'{item.when.value}' is in the future, so it cannot be when the item was {verb}.")
        answer = io.ask_detail(
            f"  When was it {verb}? (e.g. 'yesterday 3pm', '8 Oct around noon'; "
            f"'{io.BACK_COMMAND}' for main menu): ", 1, 20,
            "Please enter a date/time of up to 20 words.")
        return None if answer is None else {"datetime": answer}

    def give_up(self, item: Item) -> Item:
        return item.with_field("datetime", ExtractedField(None, 0.0))