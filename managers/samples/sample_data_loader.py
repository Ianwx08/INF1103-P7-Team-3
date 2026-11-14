"""SampleDataLoader: Reads the sample file and turns each entry into a schema-validated FoundItem."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Callable, Mapping

from managers.ai.schema_validator import SchemaValidator
from models.constants import DATETIME_FORMAT
from models.found_item import FoundItem
from models.item import Item

DEFAULT_SAMPLE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "samples", "sample_found_items.json")


class SampleDataLoader:
    """Reads the sample file and turns each entry into a schema-validated FoundItem.

    Entry keys: description, item_type, colour, location, found_days_ago (0-6), found_time ("HH:MM");
    optional brand and unique_info (null if unknown).
    """

    REQUIRED_KEYS = ("description", "item_type", "colour", "location", "found_days_ago", "found_time")
    TEXT_KEYS = ("description", "item_type", "colour", "location")
    OPTIONAL_KEYS = ("brand", "unique_info")
    CONFIDENCE = 0.95          # sample values are certain, like a clear report
    MAX_DAYS_AGO = 6           # older samples would be archived (7 days) as soon as they are loaded
    TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

    def __init__(self, file_path: str | None = None, clock: Callable[[], datetime] = datetime.now,
                 validator: SchemaValidator | None = None) -> None:
        self._file_path = file_path or DEFAULT_SAMPLE_FILE
        self._clock = clock
        self._validator = validator or SchemaValidator()

    @property
    def file_path(self) -> str:
        return self._file_path

    def load(self) -> list[FoundItem]:
        """Every sample as a FoundItem (not yet stored). ValueError names the first bad entry."""
        with open(self._file_path, "r", encoding="utf-8") as file:
            entries = json.load(file)
        if not isinstance(entries, list):
            raise ValueError(f"{self._file_path} must contain a list of sample items.")
        now = self._clock()
        items = []
        for number, entry in enumerate(entries, start=1):
            reply = self.to_reply(entry, number, now)
            problems = self._validator.validate(reply)
            if problems:
                raise ValueError(f"Sample #{number} does not match the AI schema: {'; '.join(problems)}")
            items.append(Item.from_ai_response("found", reply))
        return items

    def to_reply(self, entry: Any, number: int, now: datetime) -> dict[str, Any]:
        """One entry in the same JSON shape as a Gemini reply."""
        if not isinstance(entry, Mapping):
            raise ValueError(f"Sample #{number} must be an object.")
        missing = [key for key in self.REQUIRED_KEYS if key not in entry]
        if missing:
            raise ValueError(f"Sample #{number} is missing: {', '.join(missing)}")
        for key in self.TEXT_KEYS:
            if not isinstance(entry[key], str) or not entry[key].strip():
                raise ValueError(f"Sample #{number}: {key} must be non-empty text.")
        for key in self.OPTIONAL_KEYS:
            if entry.get(key) is not None and not isinstance(entry[key], str):
                raise ValueError(f"Sample #{number}: {key} must be text or null.")

        def field(value: str | None) -> dict[str, Any]:
            return {"value": value, "confidence": self.CONFIDENCE if value else 0.0}

        return {
            "report_type": "found",
            "item_description": field(entry["description"]),
            "item_type": field(entry["item_type"]),
            "item_colour": field(entry["colour"]),
            "item_brand": field(entry.get("brand")),
            "item_unique_info": field(entry.get("unique_info")),
            "datetime": field(self.found_at(entry, number, now)),
            "location": field(entry["location"]),
            "colour_options": [entry["colour"]],
            "prohibited_item": False,
            "item_recognised": True,
            "location_specific": True,
            "missing_fields": [],
            "overall_confidence": self.CONFIDENCE,
        }

    def found_at(self, entry: Mapping[str, Any], number: int, now: datetime) -> str:
        """found_days_ago + found_time as a date, never later than now."""
        days = entry["found_days_ago"]
        if isinstance(days, bool) or not isinstance(days, int) or not 0 <= days <= self.MAX_DAYS_AGO:
            raise ValueError(f"Sample #{number}: found_days_ago must be a whole number from 0 to {self.MAX_DAYS_AGO}.")
        time_text = entry["found_time"]
        if not isinstance(time_text, str) or not self.TIME_PATTERN.match(time_text):
            raise ValueError(f"Sample #{number}: found_time must look like 15:00.")
        hour, minute = (int(part) for part in time_text.split(":"))
        moment = (now - timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        return min(moment, now.replace(second=0, microsecond=0)).strftime(DATETIME_FORMAT)
