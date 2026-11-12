"""ThresholdConfig: Score thresholds: display_threshold+ is a top match, review_threshold+ a possible match."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ThresholdConfig:
    """Score thresholds: display_threshold+ is a top match, review_threshold+ a possible match."""

    display_threshold: float = 0.80
    review_threshold: float = 0.50
    max_results: int = 5

    def __post_init__(self) -> None:
        if not 0.0 <= self.review_threshold <= self.display_threshold <= 1.0:
            raise ValueError("Thresholds must satisfy 0 <= review <= display <= 1.")
        if self.max_results < 1:
            raise ValueError("max_results must be at least 1.")