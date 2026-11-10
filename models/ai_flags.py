"""AIFlags: Gemini's judgements about a report, separate from the field values. Immutable."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AIFlags:
    """Gemini's judgements about a report, separate from the field values. Immutable.

    Defaults match older stored records that were saved before these flags existed.
    """

    colour_options: tuple[str, ...] = ()
    prohibited_item: bool = False      # living thing, food, drink or fruit
    item_recognised: bool = True       # the item type is a real, physical object
    location_specific: bool = True     # a stranger could find the place from the words alone
    missing_fields: tuple[str, ...] = ()
    overall_confidence: float = 0.0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AIFlags":
        """Read the flag keys from a Gemini reply or a stored record."""
        confidence = data.get("overall_confidence", 0.0)
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            confidence = 0.0
        return cls(
            colour_options=tuple(str(c) for c in data.get("colour_options") or ()),
            prohibited_item=data.get("prohibited_item") is True,
            item_recognised=data.get("item_recognised") is not False,
            location_specific=data.get("location_specific") is not False,
            missing_fields=tuple(str(f) for f in data.get("missing_fields") or ()),
            overall_confidence=float(confidence),
        )

    def to_dict(self) -> dict[str, Any]:
        """The flag keys, in the stored JSON shape."""
        return {
            "colour_options": list(self.colour_options),
            "prohibited_item": self.prohibited_item,
            "item_recognised": self.item_recognised,
            "location_specific": self.location_specific,
            "missing_fields": list(self.missing_fields),
            "overall_confidence": self.overall_confidence,
        }
