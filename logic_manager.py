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
LOW_CONFIDENCE_THRESHOLD = 0.60   # fields Gemini is less sure about than this are re-asked
MAX_FOLLOW_UP_ROUNDS = 3   # stop re-asking after this many rounds

# Fields that must have a value before a report is accepted.
# item_brand and item_unique_info are optional.
REQUIRED_FIELDS = (
    "item_description",
    "item_type",
    "item_colour",
    "datetime",
    "location",
)

def field_value(item_data: dict, field: str) -> str:
    """Return a field's value as trimmed text, or "" if it is missing or null."""
    field_data = item_data.get(field)    # expected shape: {"value": ..., "confidence": ...}
    if not isinstance(field_data, dict) or field_data.get("value") is None:
        return ""
    return str(field_data["value"]).strip()

def field_confidence(item_data: dict, field: str) -> float:
    """Return a field's confidence, or 0.0 if it is missing or not a number."""
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
    """Required fields that are empty, listed as missing by Gemini, or below the threshold."""
    ai_missing = item_data.get("missing_fields") or []    # fields Gemini says it could not extract
    flagged = []    # fields that need a follow-up question

    for field in REQUIRED_FIELDS:
        if (
            not field_value(item_data, field)
            or field in ai_missing
            or field_confidence(item_data, field) < threshold
        ):
            flagged.append(field)

    return flagged

def is_prohibited_item(item_data: dict) -> bool:
    """True if Gemini judged the item to be a living thing or food/drink/fruit."""
    return item_data.get("prohibited_item") is True

def get_item_rejection(item_data: dict) -> str | None:
    """Why the item type must be re-asked: "prohibited", "unrecognised", or None if it is fine."""
    if is_prohibited_item(item_data):
        return "prohibited"
    if item_data.get("item_recognised") is False:
        return "unrecognised"
    return None

def is_vague_location(item_data: dict) -> bool:
    """True if Gemini gave a location but judged it too vague to find."""
    return bool(field_value(item_data, "location")) and item_data.get("location_specific") is False

# Thresholds for lost-item searches: 0.70+ is a top match, 0.50+ a possible match.
MATCH_CONFIG = {
    "display_threshold": 0.70,
    "review_threshold": 0.50,
    "max_results": 5,
}

# A new found report scoring this high against a stored one is treated as a likely duplicate.
DUPLICATE_THRESHOLD = 0.90

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


def score_match(reference: dict, candidate: dict, directional: bool = True) -> float:
    """Weighted similarity between two AI-structured item records, in [0, 1].

    Fields missing on either side are skipped and the weights re-normalised.
    directional=True treats reference as the lost report and candidate as
    the found item (used for searches); False compares both ways (duplicates).
    """
    total = 0.0          # sum of weight x similarity for fields both items have
    weight_used = 0.0    # sum of the weights that were actually compared

    for field, weight in MATCH_WEIGHTS.items():
        first = field_value(reference, field)
        second = field_value(candidate, field)

        if field == "datetime":
            similarity = datetime_similarity(first, second, directional)
        else:
            similarity = text_similarity(first, second)

        if similarity is None:
            continue

        total += weight * similarity
        weight_used += weight

    if weight_used == 0:
        return 0.0

    score = total / weight_used


    # Different kinds of item should never rank highly, whatever else matches.
    type_similarity = text_similarity(
        field_value(reference, "item_type"),
        field_value(candidate, "item_type"),
    )
    if type_similarity is not None and type_similarity < 0.5:
        score *= 0.5

    # An item is unlikely to be found long before it was lost.
    if directional and found_too_early(
        field_value(reference, "datetime"),
        field_value(candidate, "datetime"),
    ):
        score *= EARLY_FOUND_PENALTY

    return round(min(max(score, 0.0), 1.0), 4)



def find_matches(
    lost_data: dict,
    found_items: list[dict],
    config: dict | None = None,
) -> dict:
    """Score found items against a lost report.

    Returns {"matches": [...DISPLAY...], "possible_matches": [...REVIEW...]},
    each list holding up to max_results dicts:
    {"item_id": str, "confidence": float, "decision": str, "item": found_item}.
    """
    config = MATCH_CONFIG if config is None else config
    items_by_id = {item["item_id"]: item for item in found_items if item.get("item_id")}    # ID -> found item
    scored = [    # (item_id, match score) pairs for the decision engine
        (item_id, score_match(lost_data, item))
        for item_id, item in items_by_id.items()
    ]

    def attach_items(results: list[dict]) -> list[dict]:
        """Add the full found item to each decision result so it can be displayed."""
        return [{**result, "item": items_by_id[result["item_id"]]} for result in results]

    return {
        "matches": attach_items(get_displayable_items(scored, config)),
        "possible_matches": attach_items(
            get_review_items(scored, config)[: config["max_results"]]
        ),
    }


def find_duplicates(
    new_item: dict,
    existing_items: list[dict],
    threshold: float = DUPLICATE_THRESHOLD,
) -> list[dict]:
    """Existing found items that look like the same report as new_item."""
    return [
        item for item in existing_items
        if score_match(new_item, item, directional=False) >= threshold
    ]


ARCHIVE_AFTER_DAYS = 7   # found items older than this stop appearing in searches


def get_expired_item_ids(
    items: list[dict],
    days: int = ARCHIVE_AFTER_DAYS,
    now: datetime | None = None,
) -> list[str]:
    """IDs of active items reported more than `days` ago. Does not change any data."""
    now = datetime.now() if now is None else now
    cutoff = now - timedelta(days=days)    # anything reported before this has expired
    expired = []

    for item in items:
        if item.get("status", "active") != "active":
            continue
        reported_at = parse_datetime(item.get("reported_at", ""))
        if reported_at is not None and reported_at < cutoff:
            expired.append(item["item_id"])

    return expired

def get_colour_options(item_data: dict) -> list[str]:
    """Distinct colours Gemini found, in order, ignoring case and blanks."""
    options = []    # colours kept so far, without duplicates
    for colour in item_data.get("colour_options") or []:
        colour = str(colour).strip()
        if colour and colour.lower() not in [option.lower() for option in options]:
            options.append(colour)
    return options


def apply_colour_choice(item_data: dict, colour: str) -> dict:
    """Store the colour the user picked as the item's single, confirmed colour."""
    item_data["item_colour"] = {"value": colour, "confidence": 1.0}
    item_data["colour_options"] = [colour]
    # The colour is no longer missing, so it must not be asked again.
    item_data["missing_fields"] = [
        field for field in item_data.get("missing_fields") or [] if field != "item_colour"
    ]
    return item_data