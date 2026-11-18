"""FoundItemRowMapper: Converts a FoundItem to a database row and back. Knows the columns, nothing else."""
from __future__ import annotations

import json
from typing import Any, Mapping

from models.constants import FIELD_NAMES
from models.found_item import FoundItem


class FoundItemRowMapper:
    """Converts a FoundItem to a database row and back. Knows the columns, nothing else.

    Each of the seven item fields is two real columns (value and confidence), so the
    database can be queried directly, e.g. SELECT item_id FROM found_items WHERE item_type = 'phone'.
    Lists (colour options, missing fields) are stored as JSON text; booleans as 0/1.
    The value assessment is four columns, all NULL when the item was never assessed;
    value_category is written for querying but recomputed (never read back) on load.
    """

    KEY_COLUMNS = ("item_id", "report_type", "reported_at", "status")
    FIELD_COLUMNS = tuple(column for name in FIELD_NAMES for column in (name, f"{name}_confidence"))
    LIST_FLAGS = ("colour_options", "missing_fields")
    BOOL_FLAGS = ("prohibited_item", "item_recognised", "location_specific")
    FLAG_COLUMNS = ("colour_options", "prohibited_item", "item_recognised",
                    "location_specific", "missing_fields", "overall_confidence")
    VALUE_COLUMNS = ("estimated_value_sgd", "sensitive", "valuation_reason", "value_category")
    COLUMNS = KEY_COLUMNS + FIELD_COLUMNS + FLAG_COLUMNS + VALUE_COLUMNS + ("escalated_at",)


    def to_row(self, item: FoundItem) -> dict[str, Any]:
        """Column name -> value, ready for a parameterised INSERT or UPDATE."""
        record = item.to_dict()
        row: dict[str, Any] = {
            "item_id": item.item_id,
            "report_type": item.report_type,
            "reported_at": item.reported_at,
            "status": item.status,
        }
        for name in FIELD_NAMES:
            row[name] = record[name]["value"]
            row[f"{name}_confidence"] = record[name]["confidence"]
        for flag in self.LIST_FLAGS:
            row[flag] = json.dumps(record[flag], ensure_ascii=False)
        for flag in self.BOOL_FLAGS:
            row[flag] = int(record[flag])
        row["overall_confidence"] = record["overall_confidence"]
        if item.assessment is None:
            row.update({column: None for column in self.VALUE_COLUMNS})
        else:
            row.update({column: record[column] for column in self.VALUE_COLUMNS})
            row["sensitive"] = int(record["sensitive"])
        row["escalated_at"] = item.escalated_at
        return row

    def from_row(self, row: Mapping[str, Any]) -> FoundItem:
        """Rebuild the FoundItem from a row (through the same from_dict the JSON store uses)."""
        record: dict[str, Any] = {key: row[key] for key in ("item_id", "reported_at", "status")}
        for name in FIELD_NAMES:
            record[name] = {"value": row[name], "confidence": row[f"{name}_confidence"]}
        for flag in self.LIST_FLAGS:
            record[flag] = json.loads(row[flag] or "[]")
        for flag in self.BOOL_FLAGS:
            record[flag] = bool(row[flag])
        record["overall_confidence"] = row["overall_confidence"]
        if row["sensitive"] is not None:      # NULL = never assessed: leave the keys out
            record["estimated_value_sgd"] = row["estimated_value_sgd"]
            record["sensitive"] = bool(row["sensitive"])
            record["valuation_reason"] = row["valuation_reason"]
        record["escalated_at"] = row["escalated_at"]
        return FoundItem.from_dict(record)
