"""MatchingService: Finds matches for lost reports, duplicate found reports and expired items."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence

from managers.logic.decision_engine import DecisionEngine
from managers.logic.match_scorer import MatchScorer
from managers.logic.threshold_config import ThresholdConfig
from models.found_item import FoundItem
from models.item import Item
from models.item_match import ItemMatch


class MatchingService:
    """Finds matches for lost reports, duplicate found reports and expired items."""

    MATCH_CONFIG = ThresholdConfig(display_threshold=0.70, review_threshold=0.50, max_results=5)
    DUPLICATE_THRESHOLD = 0.90
    ARCHIVE_AFTER_DAYS = 7

    def __init__(self, scorer: MatchScorer | None = None, engine: DecisionEngine | None = None) -> None:
        self._scorer = scorer or MatchScorer()
        self._engine = engine or DecisionEngine(self.MATCH_CONFIG)

    def find_matches(self, lost: Item, found_items: Sequence[FoundItem]) -> tuple[list[ItemMatch], list[ItemMatch]]:
        """(top matches, possible matches). A match the dates rule out is at most a possible match."""
        cap = round(self._engine.config.display_threshold - 0.01, 4)
        scored = []
        for item in found_items:
            if not item.item_id:
                continue
            score = self._scorer.score(lost, item)
            if self._scorer.dates_rule_out(lost, item):
                score = min(score, cap)
            scored.append((item, score))
        return self._engine.displayable(scored), self._engine.review(scored)

    def find_duplicates(self, new_item: Item, existing: Sequence[FoundItem],
                        threshold: float = DUPLICATE_THRESHOLD) -> list[FoundItem]:
        """Stored items that look like the same report (dates compared both ways)."""
        return [item for item in existing if self._scorer.score(new_item, item, directional=False) >= threshold]

    def expired(self, items: Sequence[FoundItem], now: datetime | None = None,
                days: int = ARCHIVE_AFTER_DAYS) -> list[FoundItem]:
        """Active items reported more than `days` ago."""
        cutoff = (now or datetime.now()) - timedelta(days=days)
        return [item for item in items if item.is_active()
                and item.reported_datetime() is not None and item.reported_datetime() < cutoff]
