"""FoundItem: An item someone has found and handed in. Stored, matched, claimed, archived or escalated."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping

from models.ai_flags import AIFlags
from models.constants import DATETIME_FORMAT
from models.extracted_field import ExtractedField
from models.item import Item
from models.value_assessment import ValueAssessment


class FoundItem(Item):
    """An item someone has found and handed in. Stored, matched, claimed, archived or escalated.

    Composition: the item owns its ValueAssessment (None = never assessed, e.g. older records).
    Encapsulation: status changes only through archive(), escalated_at only through mark_escalated().
    """

    ACTIVE = "active"
    ARCHIVED = "archived"

    def __init__(self, fields: Mapping[str, ExtractedField] | None = None,
                 flags: AIFlags | None = None, item_id: str | None = None,
                 reported_at: str | None = None, status: str = ACTIVE, *,
                 assessment: ValueAssessment | None = None,
                 escalated_at: str | None = None) -> None:
        """A found item; item_id and reported_at are set when it is saved, escalated_at when the admins are emailed."""
        super().__init__(fields, flags)
        if status not in (self.ACTIVE, self.ARCHIVED):
            raise ValueError(f"status must be 'active' or 'archived', not {status!r}")
        self.__item_id = item_id
        self.__reported_at = reported_at
        self.__status = status
        self.__assessment = assessment
        self.__escalated_at = escalated_at

    @property
    def report_type(self) -> str:
        return "found"

    @property
    def item_id(self) -> str | None:
        return self.__item_id

    @property
    def reported_at(self) -> str | None:
        return self.__reported_at

    @property
    def status(self) -> str:
        return self.__status

    @property
    def assessment(self) -> ValueAssessment | None:
        """Gemini's value assessment; None if the item was never assessed."""
        return self.__assessment

    @property
    def value_category(self) -> str | None:
        """HIGH_VALUE / ORDINARY, or None if the item was never assessed."""
        return None if self.__assessment is None else self.__assessment.category

    @property
    def is_high_value(self) -> bool:
        """True only for an assessed HIGH_VALUE item (not assessed counts as ordinary)."""
        return self.__assessment is not None and self.__assessment.is_high_value

    @property
    def escalated_at(self) -> str | None:
        """When the admins were last emailed about this item (YYYY-MM-DDTHH:MM), or None."""
        return self.__escalated_at

    def is_active(self) -> bool:
        """True while the item can still be matched and claimed."""
        return self.__status == self.ACTIVE

    def archive(self) -> None:
        """Mark the item archived (left unclaimed too long). The only way status can change."""
        self.__status = self.ARCHIVED

    def mark_escalated(self, at: datetime) -> None:
        """Record a successful admin email at this time. The only way escalated_at can change."""
        self.__escalated_at = at.strftime(DATETIME_FORMAT)

    def assign_id(self, item_id: str, reported_at: str) -> None:
        """Give the item its stored ID and report time. Allowed once, when it is first saved."""
        if self.__item_id is not None:
            raise ValueError(f"Item already has ID {self.__item_id}")
        self.__item_id = item_id
        self.__reported_at = reported_at

    def reported_datetime(self) -> datetime | None:
        """When the report was saved, as a datetime; None if missing or unreadable."""
        return self._parse(self.__reported_at)

    def escalated_datetime(self) -> datetime | None:
        """When the admins were last emailed, as a datetime; None if never or unreadable."""
        return self._parse(self.__escalated_at)

    def is_overdue(self, now: datetime, days: int) -> bool:
        """True if the item was reported strictly more than `days` days before now.

        An item without a readable report time is never overdue.
        """
        reported = self.reported_datetime()
        return reported is not None and now - reported > timedelta(days=days)

    @staticmethod
    def _parse(text: str | None) -> datetime | None:
        """A stored YYYY-MM-DDTHH:MM time as a datetime; None if missing or unreadable."""
        try:
            return datetime.strptime(text or "", DATETIME_FORMAT)
        except (TypeError, ValueError):
            return None

    def _copy(self, fields: dict[str, ExtractedField], flags: AIFlags) -> "FoundItem":
        """Copies keep the ID, report time, status, assessment and escalation time."""
        return FoundItem(fields, flags, self.__item_id, self.__reported_at, self.__status,
                         assessment=self.__assessment, escalated_at=self.__escalated_at)

    def _assessment_record(self) -> dict[str, Any]:
        """The four valuation keys when assessed; nothing otherwise."""
        return {} if self.__assessment is None else self.__assessment.to_dict()

    def to_dict(self) -> dict[str, Any]:
        """Stored record: the item fields plus item_id, reported_at, status, the assessment and escalated_at."""
        record = super().to_dict()
        if self.__item_id is not None:
            record["item_id"] = self.__item_id
        if self.__reported_at is not None:
            record["reported_at"] = self.__reported_at
        record["status"] = self.__status
        record.update(self._assessment_record())
        if self.__escalated_at is not None:
            record["escalated_at"] = self.__escalated_at
        return record

    def ai_record(self) -> dict[str, Any]:
        """The report in Gemini's shape plus the assessment, so a follow-up can re-evaluate it.

        Never includes item_id, reported_at, status or escalated_at.
        """
        record = Item.to_dict(self)
        record.update(self._assessment_record())
        return record

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FoundItem":
        """Load a stored record, including ones saved by the Phase 1 app (no assessment)."""
        status = data.get("status", cls.ACTIVE)
        escalated_at = data.get("escalated_at")
        return cls(
            Item.fields_from_dict(data),
            AIFlags.from_dict(data),
            item_id=data.get("item_id"),
            reported_at=data.get("reported_at"),
            status=status if status in (cls.ACTIVE, cls.ARCHIVED) else cls.ACTIVE,
            assessment=ValueAssessment.from_dict(data),
            escalated_at=escalated_at if isinstance(escalated_at, str) else None,
        )
