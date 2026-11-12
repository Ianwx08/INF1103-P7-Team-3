"""DateSimilarity: 1.0 within a day, falling to 0 at max_gap_days (+1 free day) apart."""
from __future__ import annotations

from datetime import datetime

from managers.base.similarity_strategy import SimilarityStrategy
from models.constants import DATETIME_FORMAT


class DateSimilarity(SimilarityStrategy):
    """1.0 within a day, falling to 0 at max_gap_days (+1 free day) apart.

    Directional (lost search): found more than early_tolerance_hours before the loss scores 0.
    """

    def __init__(self, max_gap_days: int = 7, early_tolerance_hours: int = 48) -> None:
        self._max_gap_days = max_gap_days
        self._early_tolerance_hours = early_tolerance_hours

    @staticmethod
    def parse(value: str) -> datetime | None:
        """Read "YYYY-MM-DDTHH:MM"; None if missing or invalid."""
        try:
            return datetime.strptime(value, DATETIME_FORMAT)
        except (TypeError, ValueError):
            return None

    def found_too_early(self, lost_value: str, found_value: str) -> bool:
        """True if found more than early_tolerance_hours before it was lost."""
        lost_time, found_time = self.parse(lost_value), self.parse(found_value)
        if lost_time is None or found_time is None:
            return False
        gap_hours = (found_time - lost_time).total_seconds() / 3600
        return gap_hours < -self._early_tolerance_hours

    def compare(self, first: str, second: str, *, directional: bool = True) -> float | None:
        lost_time, found_time = self.parse(first), self.parse(second)
        if lost_time is None or found_time is None:
            return None
        if directional and self.found_too_early(first, second):
            return 0.0
        gap_hours = (found_time - lost_time).total_seconds() / 3600
        gap_days = max(abs(gap_hours) / 24 - 1, 0)
        return max(0.0, 1 - gap_days / self._max_gap_days)
