"""DecisionEngine: Turns match scores into decisions: DISPLAY, REVIEW or HIDE."""
from __future__ import annotations
from typing import Iterable
from managers.logic.threshold_config import ThresholdConfig
from models.found_item import FoundItem
from models.item_match import ItemMatch
from models.match_decision import MatchDecision

class DecisionEngine:
    """Turns match scores into decisions: DISPLAY, REVIEW or HIDE."""

    def __init__(self, config: ThresholdConfig | None = None) -> None:
        self._config = config or ThresholdConfig()

    @property
    def config(self) -> ThresholdConfig:
        return self._config

    def decide(self, score: float) -> MatchDecision:
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise TypeError("Confidence must be a number.")
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Confidence {score} is outside [0.0, 1.0].")
        if score >= self._config.display_threshold:
            return MatchDecision.DISPLAY
        if score >= self._config.review_threshold:
            return MatchDecision.REVIEW
        return MatchDecision.HIDE

    def evaluate(self, scored: Iterable[tuple[FoundItem, float]]) -> list[ItemMatch]:
        """Every candidate with its decision, best score first."""
        matches = [ItemMatch(item, float(score), self.decide(score)) for item, score in scored]
        return sorted(matches, key=lambda match: match.score, reverse=True)

    def displayable(self, scored: Iterable[tuple[FoundItem, float]]) -> list[ItemMatch]:
        """Top matches, at most max_results."""
        shown = [m for m in self.evaluate(scored) if m.decision is MatchDecision.DISPLAY]
        return shown[: self._config.max_results]

    def review(self, scored: Iterable[tuple[FoundItem, float]]) -> list[ItemMatch]:
        """Possible matches, at most max_results."""
        borderline = [m for m in self.evaluate(scored) if m.decision is MatchDecision.REVIEW]
        return borderline[: self._config.max_results]