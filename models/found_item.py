"""FoundItem: An item someone has found and handed in. Stored, matched, claimed or archived."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from models.ai_flags import AIFlags
from models.constants import DATETIME_FORMAT
from models.extracted_field import ExtractedField
from models.item import Item


class FoundItem(Item):
    """An item someone has found and handed in. Stored, matched, claimed or archived."""

    ACTIVE = "active"
    ARCHIVED = "archived"

    def __init__(self, fields: Mapping[str, ExtractedField] | None = None,
                 flags: AIFlags | None = None, item_id: str | None = None,
                 reported_at: str | None = None, status: str = ACTIVE) -> None:
        """A found item; item_id and reported_at are set when it is saved."""
        super().__init__(fields, flags)
        if status not in (self.ACTIVE, self.ARCHIVED):
            raise ValueError(f"status must be 'active' or 'archived', not {status!r}")
        self.__item_id = item_id
        self.__reported_at = reported_at
        self.__status = status

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

    def is_active(self) -> bool:
        """True while the item can still be matched and claimed."""
        return self.__status == self.ACTIVE

    def archive(self) -> None:
        """Mark the item archived (left unclaimed too long). The only way status can change."""
        self.__status = self.ARCHIVED

    def assign_id(self, item_id: str, reported_at: str) -> None:
        """Give the item its stored ID and report time. Allowed once, when it is first saved."""
        if self.__item_id is not None:
            raise ValueError(f"Item already has ID {self.__item_id}")
        self.__item_id = item_id
        self.__reported_at = reported_at

    def reported_datetime(self) -> datetime | None:
        """When the report was saved, as a datetime; None if missing or unreadable."""
        try:
            return datetime.strptime(self.__reported_at or "", DATETIME_FORMAT)
        except ValueError:
            return None

    def _copy(self, fields: dict[str, ExtractedField], flags: AIFlags) -> "FoundItem":
        """Copies keep the ID, report time and status."""
        return FoundItem(fields, flags, self.__item_id, self.__reported_at, self.__status)

    def to_dict(self) -> dict[str, Any]:
        """Stored record: the item fields plus item_id, reported_at and status."""
        record = super().to_dict()
        if self.__item_id is not None:
            record["item_id"] = self.__item_id
        if self.__reported_at is not None:
            record["reported_at"] = self.__reported_at
        record["status"] = self.__status
        return record

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FoundItem":
        """Load a stored record, including ones saved by the Phase 1 app."""
        status = data.get("status", cls.ACTIVE)
        return cls(
            Item.fields_from_dict(data),
            AIFlags.from_dict(data),
            item_id=data.get("item_id"),
            reported_at=data.get("reported_at"),
            status=status if status in (cls.ACTIVE, cls.ARCHIVED) else cls.ACTIVE,
        )
