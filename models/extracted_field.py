"""ExtractedField: One value Gemini extracted, with how confident it is (0 to 1). Immutable."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ExtractedField:
    """One value Gemini extracted, with how confident it is (0 to 1). Immutable."""

    value: str | None = None
    confidence: float = 0.0

    @property
    def text(self) -> str:
        """The value as trimmed text, or "" when there is no value."""
        return "" if self.value is None else str(self.value).strip()

    def is_empty(self) -> bool:
        """True when the field has no usable value."""
        return self.text == ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "ExtractedField":
        """Build from {"value": ..., "confidence": ...}; a missing or malformed entry becomes empty."""
        if not isinstance(data, Mapping):
            return cls()
        confidence = data.get("confidence", 0.0)
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            confidence = 0.0
        value = data.get("value")
        return cls(value=None if value is None else str(value), confidence=float(confidence))

    def to_dict(self) -> dict[str, Any]:
        """The same {"value", "confidence"} shape that is stored in found_items.json."""
        return {"value": self.value, "confidence": self.confidence}
