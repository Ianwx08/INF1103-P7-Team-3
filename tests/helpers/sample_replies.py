"""SampleReplies: Hard-coded sample Gemini replies for offline tests (no API calls)."""
from __future__ import annotations

import copy
from typing import Any, Iterable


class SampleReplies:
    """Hard-coded sample Gemini replies for offline tests (no API calls)."""

    @staticmethod
    def field(value: str | None, confidence: float = 0.95) -> dict[str, Any]:
        return {"value": value, "confidence": confidence if value is not None else 0.0}


    @staticmethod
    def ai_reply(report_type: str = "found", description: str | None = "black Samsung Galaxy S25",
                 item_type: str | None = "phone", colour: str | None = "black", brand: str | None = "Samsung",
                 unique: str | None = None, when: str | None = "2026-10-10T15:00",
                 where: str | None = "SIT Punggol food court", *, colour_conf: float = 0.95,
                 colours: list[str] | None = None, prohibited: bool = False, recognised: bool = True,
                 specific: bool = True, missing: Iterable[str] = ()) -> dict[str, Any]:
        """A schema-valid Gemini reply; arguments change single fields."""
        return {
            "report_type": report_type,
            "item_description": SampleReplies.field(description),
            "item_type": SampleReplies.field(item_type),
            "item_colour": SampleReplies.field(colour, colour_conf),
            "item_brand": SampleReplies.field(brand, 0.9),
            "item_unique_info": SampleReplies.field(unique, 0.9),
            "datetime": SampleReplies.field(when),
            "location": SampleReplies.field(where),
            "colour_options": colours if colours is not None else ([colour] if colour else []),
            "prohibited_item": prohibited,
            "item_recognised": recognised,
            "location_specific": specific,
            "missing_fields": list(missing),
            "overall_confidence": 0.9,
        }


    @staticmethod
    def copy_reply(reply: dict[str, Any], **changes: Any) -> dict[str, Any]:
        """Deep copy of a reply with some top-level keys replaced."""
        result = copy.deepcopy(reply)
        result.update(changes)
        return result
