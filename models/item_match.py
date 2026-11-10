"""ItemMatch: A found item paired with how well it matches a lost report."""
from __future__ import annotations

from dataclasses import dataclass

from models.found_item import FoundItem
from models.match_decision import MatchDecision


@dataclass(frozen=True)
class ItemMatch:
    """A found item paired with how well it matches a lost report.

    Aggregation: the match refers to the FoundItem but does not own it.
    """

    item: FoundItem
    score: float
    decision: MatchDecision

    def __post_init__(self) -> None:
        """Reject scores outside 0 to 1."""
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)) \
                or not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be a number from 0 to 1, not {self.score!r}")
