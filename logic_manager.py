import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Iterable
 
# Possible outcomes for a single candidate item.
DISPLAY = "display"   # confident enough to show the user
REVIEW = "review"     # borderline; flag for staff / secondary check
HIDE = "hide"         # too weak to show

# Tunable settings. Placeholder values; adjust once real data exists.
DEFAULT_CONFIG = {
    "display_threshold": 0.80,   # >= this -> DISPLAY
    "review_threshold": 0.50,    # >= this (and < display) -> REVIEW
    "max_results": 5,            # cap on items shown to the user
}

def validate_config(config: dict | None = None) -> dict:
    """Return a checked config dict (DEFAULT_CONFIG when None).

    Raises ValueError if the thresholds are out of order or max_results < 1.
    """
    config = DEFAULT_CONFIG if config is None else config
    if not (0.0 <= config["review_threshold"] <= config["display_threshold"] <= 1.0):
        raise ValueError(
            "Thresholds must satisfy 0 <= review <= display <= 1."
        )
    if config["max_results"] < 1:
        raise ValueError("max_results must be at least 1.")
    return config
# A candidate result is a dict:
# {"item_id": str, "confidence": float, "decision": DISPLAY | REVIEW | HIDE}

def validate_confidence(confidence: float) -> float:
    """Ensure a confidence value is a number in the range [0.0, 1.0] and return it as a float."""
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise TypeError("Confidence must be a number.")
    if not (0.0 <= confidence <= 1.0):
        raise ValueError(f"Confidence {confidence} is outside [0.0, 1.0].")
    return float(confidence)
 
def decide(confidence: float, config: dict | None = None) -> str:
    """Decide what to do with one confidence score: DISPLAY, REVIEW or HIDE."""
    config = validate_config(config)
    confidence = validate_confidence(confidence)
    if confidence >= config["display_threshold"]:
        return DISPLAY
    if confidence >= config["review_threshold"]:
        return REVIEW
    return HIDE
 
def evaluate_candidates(
    scored_items: Iterable[tuple[str, float]],
    config: dict | None = None,
) -> list[dict]:
    """
    Evaluate many (item_id, confidence) pairs.

    Returns every candidate with its decision, sorted by confidence (highest
    first). Items the user should see are those with decision == DISPLAY,
    limited to config["max_results"] by get_displayable_items().
    """
    results = [
        {
            "item_id": item_id,
            "confidence": validate_confidence(conf),
            "decision": decide(conf, config),
        }
        for item_id, conf in scored_items
    ]
    return sorted(results, key=lambda r: r["confidence"], reverse=True)

def get_displayable_items(
    scored_items: Iterable[tuple[str, float]],
    config: dict | None = None,
) -> list[dict]:
    """Return only the items that should be shown to the claimant (at most max_results)."""
    config = validate_config(config)
    results = evaluate_candidates(scored_items, config)
    displayable = [r for r in results if r["decision"] == DISPLAY]
    return displayable[: config["max_results"]]
 
def get_review_items(
    scored_items: Iterable[tuple[str, float]],
    config: dict | None = None,
) -> list[dict]:
    """Return borderline items that need a secondary check; shown as "possible matches"."""
    results = evaluate_candidates(scored_items, config)
    return [r for r in results if r["decision"] == REVIEW]

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


def get_flagged_fields(
    item_data: dict,
    threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> list[str]:
    """Required fields that are missing, flagged by the AI, or below threshold."""
    ai_missing = item_data.get("missing_fields") or []
    flagged = []

    for field in REQUIRED_FIELDS:
        if (
            not _field_value(item_data, field)
            or field in ai_missing
            or _field_confidence(item_data, field) < threshold
        ):
            flagged.append(field)

    return flagged

def refresh_ai_summary(item_data: dict) -> dict:
    """Recompute missing_fields and overall_confidence after user corrections."""
    item_data["missing_fields"] = [
        field for field in REQUIRED_FIELDS if not _field_value(item_data, field)
    ]
    confidences = [_field_confidence(item_data, field) for field in REQUIRED_FIELDS]
    item_data["overall_confidence"] = round(min(confidences), 2)
    return item_data


# How much each field counts towards a match score (they add up to 1.0).
MATCH_WEIGHTS = {
    "item_type": 0.25,
    "item_colour": 0.20,
    "item_description": 0.15,
    "location": 0.15,
    "item_brand": 0.10,
    "datetime": 0.10,
    "item_unique_info": 0.05,
}

# Words that mean the same thing, mapped to one form before comparing text.
_WORD_SYNONYMS = {
    "gray": "grey",
    "colour": "color",
    "handphone": "phone",
    "mobile": "phone",
    "smartphone": "phone",
    "earbuds": "earphones",
    "earpods": "earphones",
    "headphone": "headphones",
    "notebook": "laptop",
    "purse": "wallet",
}

MAX_DATE_GAP_DAYS = 7               # date weightage falls to 0 past 7 days
EARLY_FOUND_TOLERANCE_HOURS = 48    # "found before lost" is allowed up to 48 hours
EARLY_FOUND_PENALTY = 0.8           # score multiplier when found long before it was lost

def tokens(text: str) -> list[str]:
    """Split text into lower-case words and replace synonyms, e.g. "Gray Mobile" -> ["grey", "phone"]."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [_WORD_SYNONYMS.get(word, word) for word in words]


def text_similarity(first: str, second: str) -> float | None:
    """Similarity of two texts in [0, 1]; None when either side is empty.

    Takes the best of three measures: shared words out of all words
    (Jaccard), shared words out of the shorter text (overlap), and
    character-level similarity (SequenceMatcher).
    """
    first_tokens = tokens(first)
    second_tokens = tokens(second)
    if not first_tokens or not second_tokens:
        return None

    first_set = set(first_tokens)
    second_set = set(second_tokens)
    shared = len(first_set & second_set)    # number of words in both texts
    jaccard = shared / len(first_set | second_set)
    overlap = shared / min(len(first_set), len(second_set))
    sequence = SequenceMatcher(None, " ".join(first_tokens), " ".join(second_tokens)).ratio()

    return max(jaccard, 0.9 * overlap, sequence)

def parse_datetime(value: str) -> datetime | None:
    """Read a "YYYY-MM-DDTHH:MM" string; returns None if it is missing or invalid."""
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        return None


def found_too_early(lost_value: str, found_value: str) -> bool:
    """True if the item was found more than EARLY_FOUND_TOLERANCE_HOURS before it was lost."""
    lost_time = parse_datetime(lost_value)
    found_time = parse_datetime(found_value)
    if lost_time is None or found_time is None:
        return False
    gap_hours = (found_time - lost_time).total_seconds() / 3600    # negative = found before lost
    return gap_hours < -EARLY_FOUND_TOLERANCE_HOURS


def datetime_similarity(lost_value: str, found_value: str, directional: bool) -> float | None:
    """1.0 for the same day, falling to 0 at MAX_DATE_GAP_DAYS apart.

    When directional, an item found well before it was lost scores 0.
    Returns None if either date is missing.
    """
    lost_time = parse_datetime(lost_value)
    found_time = parse_datetime(found_value)
    if lost_time is None or found_time is None:
        return None

    gap_hours = (found_time - lost_time).total_seconds() / 3600
    if directional and found_too_early(lost_value, found_value):
        return 0.0

    gap_days = max(abs(gap_hours) / 24 - 1, 0)    # the first day apart is free
    return max(0.0, 1 - gap_days / MAX_DATE_GAP_DAYS)