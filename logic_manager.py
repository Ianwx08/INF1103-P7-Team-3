from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Tuple
 
 
class MatchDecision(Enum):
    """Possible outcomes for a single candidate item."""
    DISPLAY = "display"   # confident enough to show the user
    REVIEW = "review"     # borderline; flag for staff / secondary check
    HIDE = "hide"         # too weak to show
 
 
@dataclass(frozen=True)
class LogicConfig:
    """Tunable settings. Placeholder values; adjust once real data exists."""
    display_threshold: float = 0.80   # >= this -> DISPLAY
    review_threshold: float = 0.50    # >= this (and < display) -> REVIEW
    max_results: int = 5              # cap on items shown to the user
 
    def __post_init__(self):
        if not (0.0 <= self.review_threshold <= self.display_threshold <= 1.0):
            raise ValueError(
                "Thresholds must satisfy 0 <= review <= display <= 1."
            )
        if self.max_results < 1:
            raise ValueError("max_results must be at least 1.")
 
 
@dataclass(frozen=True)
class CandidateResult:
    """A candidate item paired with its decision."""
    item_id: str
    confidence: float
    decision: MatchDecision
 
 
def validate_confidence(confidence: float) -> float:
    """Ensure a confidence value is a number in the range [0.0, 1.0]."""
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise TypeError("Confidence must be a number.")
    if not (0.0 <= confidence <= 1.0):
        raise ValueError(f"Confidence {confidence} is outside [0.0, 1.0].")
    return float(confidence)
 
 
def decide(confidence: float, config: LogicConfig = LogicConfig()) -> MatchDecision:
    """Decide what to do with one confidence score."""
    confidence = validate_confidence(confidence)
    if confidence >= config.display_threshold:
        return MatchDecision.DISPLAY
    if confidence >= config.review_threshold:
        return MatchDecision.REVIEW
    return MatchDecision.HIDE
 
 
def evaluate_candidates(
    scored_items: Iterable[Tuple[str, float]],
    config: LogicConfig = LogicConfig(),
) -> List[CandidateResult]:
    """
    Evaluate many (item_id, confidence) pairs.
 
    Returns every candidate with its decision, sorted by confidence (highest
    first). Items the user should see are those with decision == DISPLAY,
    limited to config.max_results by get_displayable_items().
    """
    results = [
        CandidateResult(item_id, validate_confidence(conf), decide(conf, config))
        for item_id, conf in scored_items
    ]
    return sorted(results, key=lambda r: r.confidence, reverse=True)
 
 
def get_displayable_items(
    scored_items: Iterable[Tuple[str, float]],
    config: LogicConfig = LogicConfig(),
) -> List[CandidateResult]:
    """Return only the items that should be shown to the claimant."""
    results = evaluate_candidates(scored_items, config)
    displayable = [r for r in results if r.decision is MatchDecision.DISPLAY]
    return displayable[: config.max_results]
 
 
def get_review_items(
    scored_items: Iterable[Tuple[str, float]],
    config: LogicConfig = LogicConfig(),
) -> List[CandidateResult]:
    """Return borderline items that need a secondary check (e.g. staff)."""
    results = evaluate_candidates(scored_items, config)
    return [r for r in results if r.decision is MatchDecision.REVIEW]

# -------------------------
# AI output evaluation
# -------------------------
LOW_CONFIDENCE_THRESHOLD = 0.60

REQUIRED_FIELDS = (
    "item_description",
    "item_type",
    "item_colour",
    "datetime",
    "location",
)

def _field_value(item_data: dict, field: str) -> str:
    field_data = item_data.get(field)
    if not isinstance(field_data, dict) or field_data.get("value") is None:
        return ""
    return str(field_data["value"]).strip()


def _field_confidence(item_data: dict, field: str) -> float:
    field_data = item_data.get(field)
    if not isinstance(field_data, dict):
        return 0.0
    confidence = field_data.get("confidence", 0.0)
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return 0.0
    return float(confidence)
