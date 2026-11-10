"""SchemaValidator: Checks a Gemini reply's keys, types and formats before any logic uses it."""
from __future__ import annotations
from datetime import datetime
from typing import Any
from managers.ai.constants import REPORT_TYPES
from models.constants import DATETIME_FORMAT, FIELD_NAMES

class SchemaValidator:

    def validate(self, data: Any) -> list[str]:
        """Return problems found; an empty list means reply is valid."""
        if not isinstance(data, dict):
            return ["Response is not a JSON object."]
        problems: list[str] = []

        if data.get("report_type") not in REPORT_TYPES:
            problems.append(f"report_type must be one of {REPORT_TYPES}.")

        for name in FIELD_NAMES:
            field = data.get(name)
            if not isinstance(field, dict):
                problems.append(f"{name} must be an object with value and confidence.")
                continue
            if "value" not in field or not (field["value"] is None or isinstance(field["value"], str)):
                problems.append(f"{name}.value must be a string or null.")
            if not self._is_confidence(field.get("confidence")):
                problems.append(f"{name}.confidence must be a number between 0 and 1.")

        date_field = data.get("datetime")
        if isinstance(date_field, dict) and isinstance(date_field.get("value"), str):
            try:
                datetime.strptime(date_field["value"], DATETIME_FORMAT)
            except ValueError:
                problems.append("datetime.value must use the format YYYY-MM-DDTHH:MM.")

        colour_options = data.get("colour_options")
        if not isinstance(colour_options, list) or not all(isinstance(c, str) for c in colour_options):
            problems.append("colour_options must be a list of strings.")

        for flag in ("prohibited_item", "item_recognised", "location_specific"):
            if not isinstance(data.get(flag), bool):
                problems.append(f"{flag} must be true or false.")

        missing_fields = data.get("missing_fields")
        if not isinstance(missing_fields, list):
            problems.append("missing_fields must be a list.")
        elif not all(isinstance(name, str) and name in FIELD_NAMES for name in missing_fields):
            problems.append("missing_fields may only contain known field names.")

        if not self._is_confidence(data.get("overall_confidence")):
            problems.append("overall_confidence must be a number between 0 and 1.")
        return problems

    def is_valid(self, data: Any) -> bool:
        """Is true if validate() found no problems."""
        return not self.validate(data)

    @staticmethod
    def _is_confidence(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and 0.0 <= value <= 1.0
