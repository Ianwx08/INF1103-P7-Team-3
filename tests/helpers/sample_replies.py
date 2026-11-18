"""SampleReplies: Hard-coded sample Gemini replies for offline tests (no API calls)."""
from __future__ import annotations

import copy
from typing import Any, Iterable

from models.found_item import FoundItem
from models.item import Item
from models.value_assessment import ValueAssessment


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
            "estimated_value_sgd": 800,
            "sensitive": False,
            "value_category": "ORDINARY",
            "valuation_reason": "Rough model-based estimate for offline testing.",
        }

    @staticmethod
    def found_reply(value: float | None = 1000, sensitive: bool = False, **changes: Any) -> dict[str, Any]:
        """A schema-valid reply for a found report with this value assessment (category worked out to match)."""
        reply = SampleReplies.ai_reply("found", **changes)
        reply.update(estimated_value_sgd=value, sensitive=sensitive,
                     value_category=ValueAssessment.category_for(value, sensitive))
        return reply

    @staticmethod
    def found_item(value: float | None = 1000, sensitive: bool = False, *, item_id: str | None = None,
                   reported_at: str | None = None, status: str = FoundItem.ACTIVE, **changes: Any) -> FoundItem:
        """A FoundItem built from found_reply() the way the app does, then given its ID, report time and status."""
        base = Item.from_ai_response("found", SampleReplies.found_reply(value, sensitive, **changes))
        return FoundItem(base.fields, base.flags, item_id, reported_at, status, assessment=base.assessment)

    @staticmethod
    def copy_reply(reply: dict[str, Any], **changes: Any) -> dict[str, Any]:
        """Deep copy of a reply with some top-level keys replaced."""
        result = copy.deepcopy(reply)
        result.update(changes)
        return result
