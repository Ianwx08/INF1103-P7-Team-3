"""Item: A reported item: seven extracted fields plus Gemini's flags."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Mapping

from models.ai_flags import AIFlags
from models.constants import DATETIME_FORMAT, FIELD_NAMES
from models.extracted_field import ExtractedField


class Item(ABC):
    """A reported item: seven extracted fields plus Gemini's flags.

    Abstract: create a LostItem or FoundItem. Field values are read-only; use
    with_field() / with_flags() to get an updated copy instead of changing this one.
    """

    def __init__(self, fields: Mapping[str, ExtractedField] | None = None,
                 flags: AIFlags | None = None) -> None:
        """Store the fields (unknown names are rejected; missing ones become empty) and flags."""
        fields = dict(fields or {})
        unknown = set(fields) - set(FIELD_NAMES)
        if unknown:
            raise ValueError(f"Unknown item field(s): {sorted(unknown)}")
        self._fields: dict[str, ExtractedField] = {
            name: fields.get(name, ExtractedField()) for name in FIELD_NAMES
        }
        self._flags: AIFlags = flags or AIFlags()

    # ---- what kind of report this is (each subclass answers differently) ----
    @property
    @abstractmethod
    def report_type(self) -> str:
        """"lost" or "found"."""

    # ---- read-only access to the fields ----
    def field(self, name: str) -> ExtractedField:
        """One field by name, e.g. item.field("item_colour")."""
        if name not in self._fields:
            raise KeyError(f"Unknown item field: {name}")
        return self._fields[name]

    @property
    def fields(self) -> dict[str, ExtractedField]:
        """A copy of all seven fields, so callers cannot change this item's own dict."""
        return dict(self._fields)

    @property
    def flags(self) -> AIFlags:
        """Gemini's judgements about this report."""
        return self._flags

    @property
    def description(self) -> ExtractedField:
        return self._fields["item_description"]

    @property
    def item_type(self) -> ExtractedField:
        return self._fields["item_type"]

    @property
    def colour(self) -> ExtractedField:
        return self._fields["item_colour"]

    @property
    def brand(self) -> ExtractedField:
        return self._fields["item_brand"]

    @property
    def unique_info(self) -> ExtractedField:
        return self._fields["item_unique_info"]

    @property
    def when(self) -> ExtractedField:
        return self._fields["datetime"]

    @property
    def location(self) -> ExtractedField:
        return self._fields["location"]

    @property
    def occurred_at(self) -> datetime | None:
        """When the item was lost or found, as a datetime; None if missing or unreadable."""
        try:
            return datetime.strptime(self.when.text, DATETIME_FORMAT)
        except ValueError:
            return None

    # ---- updated copies (the original is never changed) ----
    def with_field(self, name: str, new_field: ExtractedField) -> "Item":
        """A copy of this item with one field replaced."""
        fields = self.fields
        if name not in fields:
            raise KeyError(f"Unknown item field: {name}")
        fields[name] = new_field
        return self._copy(fields, self._flags)

    def with_flags(self, flags: AIFlags) -> "Item":
        """A copy of this item with different AI flags."""
        return self._copy(self.fields, flags)

    def _copy(self, fields: dict[str, ExtractedField], flags: AIFlags) -> "Item":
        """Build a new item of the same class; subclasses with extra state override this."""
        return type(self)(fields, flags)

    # ---- conversion to and from the JSON shape ----
    def to_dict(self) -> dict[str, Any]:
        """The record in the same JSON shape Phase 1 stored, so existing data keeps working."""
        record: dict[str, Any] = {"report_type": self.report_type}
        record.update({name: f.to_dict() for name, f in self._fields.items()})
        record.update(self._flags.to_dict())
        return record

    def ai_record(self) -> dict[str, Any]:
        """The report in the shape Gemini returns (no ID or status), for follow-up prompts."""
        return Item.to_dict(self)

    @staticmethod
    def fields_from_dict(data: Mapping[str, Any]) -> dict[str, ExtractedField]:
        """Read the seven fields out of a Gemini reply or a stored record."""
        return {name: ExtractedField.from_dict(data.get(name)) for name in FIELD_NAMES}

    @staticmethod
    def from_ai_response(report_type: str, data: Mapping[str, Any]) -> "Item":
        """Create the right subclass from a validated Gemini reply (the menu choice decides the type)."""
        # Imported here, not at the top: LostItem and FoundItem inherit from Item, so a top-level
        # import would be circular (each file needs the other to exist first).
        from models.found_item import FoundItem
        from models.lost_item import LostItem

        kinds: dict[str, type[Item]] = {"lost": LostItem, "found": FoundItem}
        if report_type not in kinds:
            raise ValueError(f"report_type must be 'lost' or 'found', not {report_type!r}")
        return kinds[report_type](Item.fields_from_dict(data), AIFlags.from_dict(data))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.description.text!r}, type={self.item_type.text!r})"
