"""EscalationService: Emails the administrators about high-value found items left unclaimed too long."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from managers.base.base_data_manager import BaseDataManager
from managers.base.base_email_manager import BaseEmailManager
from managers.email.escalation_email_builder import EscalationEmailBuilder
from models.found_item import FoundItem


class EscalationService:
    """Emails the administrators about high-value found items left unclaimed too long.

    Association: uses the data manager and email manager it is given (any implementation).
    Composition: owns its EscalationEmailBuilder unless one is supplied.
    An item is due when it is active, HIGH_VALUE and was reported strictly more than 7 days ago
    (a claim deletes the record, so a claimed item is never due). Each item is included at most
    once per calendar day: after a successful send its escalated_at is set and stored. A failed
    or disabled send records nothing, so the next start tries again. If storing fails after the
    email went out, a message is shown and those items may be emailed again the same day.
    """

    ESCALATION_DAYS = 7

    def __init__(self, data: BaseDataManager, email: BaseEmailManager,
                 notify: Callable[[str], None] = print,
                 clock: Callable[[], datetime] = datetime.now,
                 builder: EscalationEmailBuilder | None = None) -> None:
        """data holds the found items; email sends the summary; clock gives "now" (tests pass a fixed one)."""
        self._data = data
        self._email = email
        self._notify = notify
        self._clock = clock
        self._builder = builder or EscalationEmailBuilder()

    def due(self, now: datetime) -> list[FoundItem]:
        """Active HIGH_VALUE found items reported more than 7 days ago (reminded today or not)."""
        return [item for item in self._data.get_active()
                if item.is_high_value and item.is_overdue(now, self.ESCALATION_DAYS)]

    def to_remind(self, now: datetime) -> list[FoundItem]:
        """The due items that have not had a reminder today (calendar day of the clock)."""
        return [item for item in self.due(now) if not self._reminded_today(item, now)]

    @staticmethod
    def _reminded_today(item: FoundItem, now: datetime) -> bool:
        """True if the item's last successful reminder was on now's calendar day (or later)."""
        last = item.escalated_datetime()
        return last is not None and last.date() >= now.date()

    def check(self) -> int:
        """Send one email covering every item to remind; returns how many were in it.

        Storage errors become a message, never a crash: the app must still start.
        """
        try:
            now = self._clock()
            items = self.to_remind(now)
            if not items or not self._email.send(self._builder.build(items, self.ESCALATION_DAYS)):
                return 0
            for item in items:
                item.mark_escalated(now)
                self._data.update(item)       # False (claimed in the meantime) is fine to ignore
            return len(items)
        except OSError as error:
            self._notify(f"Could not check or record found-item escalations: {error}")
            return 0
