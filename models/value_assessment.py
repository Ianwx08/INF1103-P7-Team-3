"""ValueAssessment: Gemini's value estimate for a found item, and the HIGH_VALUE / ORDINARY rule. Immutable."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, ClassVar, Mapping


@dataclass(frozen=True)
class ValueAssessment:
    """Gemini's value estimate for a found item, and the HIGH_VALUE / ORDINARY rule. Immutable.

    Gemini supplies the estimate, the sensitive mark and the reason. The category is always
    worked out here (never taken from Gemini or from a stored record), so the S$1,000 rule
    lives in exactly one place (SRP). The schema validator calls category_for() too.
    """

    HIGH_VALUE: ClassVar[str] = "HIGH_VALUE"
    ORDINARY: ClassVar[str] = "ORDINARY"
    HIGH_VALUE_THRESHOLD_SGD: ClassVar[int] = 1000

    estimated_value_sgd: float | None = None   # rough estimate in Singapore dollars; None = could not tell
    sensitive: bool = False                    # IDs, bank cards, passports, keys: cannot be priced
    reason: str = ""                           # Gemini's explanation of the estimate

    @classmethod
    def category_for(cls, estimated_value_sgd: float | None, sensitive: bool) -> str:
        """HIGH_VALUE if sensitive or estimated at S$1,000 or more; otherwise ORDINARY."""
        high = sensitive or (estimated_value_sgd or 0) >= cls.HIGH_VALUE_THRESHOLD_SGD
        return cls.HIGH_VALUE if high else cls.ORDINARY

    @property
    def category(self) -> str:
        """This assessment's category, computed from the value and the sensitive mark."""
        return self.category_for(self.estimated_value_sgd, self.sensitive)

    @property
    def is_high_value(self) -> bool:
        """True when the category is HIGH_VALUE."""
        return self.category == self.HIGH_VALUE

    def to_dict(self) -> dict[str, Any]:
        """The four stored / Gemini keys (value_category is derived, written for querying only)."""
        return {
            "estimated_value_sgd": self.estimated_value_sgd,
            "sensitive": self.sensitive,
            "valuation_reason": self.reason,
            "value_category": self.category,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ValueAssessment | None":
        """Read an assessment from a Gemini reply or a stored record; None if it was never assessed.

        An item is assessed exactly when `sensitive` is a real boolean. A value that is not a
        finite nonnegative number becomes None. A stored value_category is ignored (recomputed).
        """
        sensitive = data.get("sensitive")
        if not isinstance(sensitive, bool):
            return None
        value = data.get("estimated_value_sgd")
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or value < 0:
            value = None
        return cls(value, sensitive, str(data.get("valuation_reason") or ""))
