"""Constants shared by the models: the date format and the seven item field names."""
from __future__ import annotations

# Format every date/time uses, e.g. "2026-10-08T14:30".
DATETIME_FORMAT = "%Y-%m-%dT%H:%M"

# The seven item fields Gemini extracts, each an ExtractedField.
FIELD_NAMES: tuple[str, ...] = (
    "item_description",
    "item_type",
    "item_colour",
    "item_brand",
    "item_unique_info",
    "datetime",
    "location",
)
