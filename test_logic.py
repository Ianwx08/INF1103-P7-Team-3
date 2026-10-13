"""Offline tests for logic_manager.py using hard-coded sample AI outputs.

No Gemini call and no API key needed: every sample below is a dictionary in
the same shape ai_manager.analyse_user_input() returns.

Run:  python test_logic.py
"""
import copy
import sys
from datetime import datetime

import logic_manager

# -------------------------
# Hard-coded sample AI outputs
# -------------------------
# A lost report, as Gemini returns it for:
# "my black Samsung Galaxy S25, cracked screen protector / yesterday 2pm / SIT Punggol food court"
LOST_PHONE = {
    "report_type": "lost",
    "item_description": {"value": "Samsung Galaxy S25", "confidence": 0.98},
    "item_type": {"value": "phone", "confidence": 0.95},
    "item_colour": {"value": "black", "confidence": 1.0},
    "item_brand": {"value": "Samsung", "confidence": 1.0},
    "item_unique_info": {"value": "cracked screen protector", "confidence": 0.9},
    "datetime": {"value": "2026-10-10T14:00", "confidence": 0.95},
    "location": {"value": "SIT Punggol food court", "confidence": 0.95},
    "colour_options": ["black"],
    "prohibited_item": False,
    "item_recognised": True,
    "location_specific": True,
    "missing_fields": [],
    "overall_confidence": 0.95,
}

# The same phone, reported as found (stored record, so it has an ID and status).
FOUND_PHONE = {
    "report_type": "found",
    "item_description": {"value": "Samsung Galaxy S25", "confidence": 0.98},
    "item_type": {"value": "phone", "confidence": 0.95},
    "item_colour": {"value": "black", "confidence": 1.0},
    "item_brand": {"value": "Samsung", "confidence": 1.0},
    "item_unique_info": {"value": "cracked screen protector", "confidence": 0.9},
    "datetime": {"value": "2026-10-10T15:00", "confidence": 0.95},
    "location": {"value": "SIT Punggol food court", "confidence": 0.95},
    "colour_options": ["black"],
    "prohibited_item": False,
    "item_recognised": True,
    "location_specific": True,
    "missing_fields": [],
    "overall_confidence": 0.95,
    "item_id": "FND-0001",
    "reported_at": "2026-10-10T16:00",
    "status": "active",
}

# A different phone: similar type, different colour and place -> should be a "possible match".
FOUND_WHITE_PHONE = {
    "report_type": "found",
    "item_description": {"value": "Samsung phone", "confidence": 0.9},
    "item_type": {"value": "phone", "confidence": 0.95},
    "item_colour": {"value": "white", "confidence": 0.95},
    "item_brand": {"value": None, "confidence": 0.0},
    "item_unique_info": {"value": None, "confidence": 0.0},
    "datetime": {"value": "2026-10-10T15:00", "confidence": 0.9},
    "location": {"value": "Tampines Mall", "confidence": 0.95},
    "colour_options": ["white"],
    "prohibited_item": False,
    "item_recognised": True,
    "location_specific": True,
    "missing_fields": [],
    "overall_confidence": 0.9,
    "item_id": "FND-0002",
    "reported_at": "2026-10-10T16:30",
    "status": "active",
}

# Something unrelated -> should be hidden from a phone search.
FOUND_UMBRELLA = {
    "report_type": "found",
    "item_description": {"value": "red foldable umbrella", "confidence": 0.95},
    "item_type": {"value": "umbrella", "confidence": 0.95},
    "item_colour": {"value": "red", "confidence": 1.0},
    "item_brand": {"value": None, "confidence": 0.0},
    "item_unique_info": {"value": None, "confidence": 0.0},
    "datetime": {"value": "2026-10-10T15:00", "confidence": 0.9},
    "location": {"value": "Jurong East MRT station", "confidence": 0.95},
    "colour_options": ["red"],
    "prohibited_item": False,
    "item_recognised": True,
    "location_specific": True,
    "missing_fields": [],
    "overall_confidence": 0.93,
    "item_id": "FND-0003",
    "reported_at": "2026-10-10T17:00",
    "status": "active",
}

# Gemini could not find a colour and is unsure of the date.
INCOMPLETE_REPORT = {
    "report_type": "found",
    "item_description": {"value": "Lenovo laptop charger", "confidence": 0.95},
    "item_type": {"value": "charger", "confidence": 0.9},
    "item_colour": {"value": None, "confidence": 0.0},
    "item_brand": {"value": "Lenovo", "confidence": 1.0},
    "item_unique_info": {"value": None, "confidence": 0.0},
    "datetime": {"value": "2026-10-10T12:00", "confidence": 0.45},
    "location": {"value": "SIT library level 1", "confidence": 0.95},
    "colour_options": [],
    "prohibited_item": False,
    "item_recognised": True,
    "location_specific": True,
    "missing_fields": ["item_colour"],
    "overall_confidence": 0.6,
}

# A living thing ("big fat black dog").
DOG_REPORT = {
    "report_type": "found",
    "item_description": {"value": "big fat black dog", "confidence": 0.95},
    "item_type": {"value": "dog", "confidence": 0.95},
    "item_colour": {"value": "black", "confidence": 0.95},
    "item_brand": {"value": None, "confidence": 0.0},
    "item_unique_info": {"value": None, "confidence": 0.0},
    "datetime": {"value": "2026-10-10T12:00", "confidence": 0.65},
    "location": {"value": "Punggol MRT station", "confidence": 0.95},
    "colour_options": ["black"],
    "prohibited_item": True,
    "item_recognised": True,
    "location_specific": True,
    "missing_fields": [],
    "overall_confidence": 0.9,
}

# Gibberish item type ("asdf"): Gemini blanks the type and says it is not recognised.
GIBBERISH_REPORT = {
    "report_type": "found",
    "item_description": {"value": None, "confidence": 0.0},
    "item_type": {"value": None, "confidence": 0.0},
    "item_colour": {"value": "black", "confidence": 0.9},
    "item_brand": {"value": None, "confidence": 0.0},
    "item_unique_info": {"value": None, "confidence": 0.0},
    "datetime": {"value": "2026-10-10T12:00", "confidence": 0.65},
    "location": {"value": "Punggol MRT station", "confidence": 0.95},
    "colour_options": ["black"],
    "prohibited_item": False,
    "item_recognised": False,
    "location_specific": True,
    "missing_fields": ["item_description", "item_type"],
    "overall_confidence": 0.3,
}

# Two colours and a vague place ("black and red backpack, outside my house").
BACKPACK_REPORT = {
    "report_type": "found",
    "item_description": {"value": "black and red Jansport backpack", "confidence": 0.95},
    "item_type": {"value": "backpack", "confidence": 0.95},
    "item_colour": {"value": "black", "confidence": 0.7},
    "item_brand": {"value": "Jansport", "confidence": 1.0},
    "item_unique_info": {"value": None, "confidence": 0.0},
    "datetime": {"value": "2026-10-10T13:00", "confidence": 0.95},
    "location": {"value": "outside my house", "confidence": 0.9},
    "colour_options": ["black", "Red", "BLACK", " "],
    "prohibited_item": False,
    "item_recognised": True,
    "location_specific": False,
    "missing_fields": [],
    "overall_confidence": 0.85,
}


# -------------------------
# Tiny test runner (no classes, so no unittest)
# -------------------------
RESULTS = []    # (name, passed, detail)


def check(name: str, condition: bool, detail: str = "") -> None:
    """Record one test result and print it."""
    RESULTS.append((name, condition, detail))
    status = "PASS" if condition else "FAIL"
    print(f"  {status}  {name}" + (f"   ({detail})" if detail else ""))


def raises(error_type, function, *args) -> bool:
    """True if calling function(*args) raises error_type."""
    try:
        function(*args)
    except error_type:
        return True
    return False


def with_date(record: dict, value: str) -> dict:
    """Copy of a sample with a different datetime value."""
    changed = copy.deepcopy(record)
    changed["datetime"]["value"] = value
    return changed


# -------------------------
# Tests, one function per area of logic_manager
# -------------------------
def test_decision_engine() -> None:
    print("\n1. Decision engine (score -> display / review / hide)")
    check("decide(0.85) is DISPLAY", logic_manager.decide(0.85) == logic_manager.DISPLAY)
    check("decide(0.60) is REVIEW", logic_manager.decide(0.60) == logic_manager.REVIEW)
    check("decide(0.20) is HIDE", logic_manager.decide(0.20) == logic_manager.HIDE)
    check("decide uses a custom config",
          logic_manager.decide(0.72, logic_manager.MATCH_CONFIG) == logic_manager.DISPLAY)

    results = logic_manager.evaluate_candidates([("A", 0.4), ("B", 0.9), ("C", 0.6)])
    check("evaluate_candidates sorts best first", [r["item_id"] for r in results] == ["B", "C", "A"])

    many = [(f"ID{n}", 0.95) for n in range(8)]
    check("get_displayable_items caps at max_results (5)", len(logic_manager.get_displayable_items(many)) == 5)
    check("get_review_items keeps only borderline scores",
          [r["item_id"] for r in logic_manager.get_review_items([("A", 0.9), ("B", 0.6), ("C", 0.1)])] == ["B"])

    check("validate_confidence rejects True", raises(TypeError, logic_manager.validate_confidence, True))
    check("validate_confidence rejects 1.5", raises(ValueError, logic_manager.validate_confidence, 1.5))
    bad = {"display_threshold": 0.4, "review_threshold": 0.6, "max_results": 5}
    check("validate_config rejects thresholds out of order", raises(ValueError, logic_manager.validate_config, bad))


def test_reading_fields() -> None:
    print("\n2. Reading fields safely")
    check("field_value reads a value", logic_manager.field_value(LOST_PHONE, "item_type") == "phone")
    check("field_value gives '' for null", logic_manager.field_value(INCOMPLETE_REPORT, "item_colour") == "")
    check("field_value gives '' for a missing field", logic_manager.field_value({}, "location") == "")
    check("field_confidence reads a number", logic_manager.field_confidence(LOST_PHONE, "item_type") == 0.95)
    check("field_confidence gives 0.0 when missing", logic_manager.field_confidence({}, "item_type") == 0.0)


def test_follow_up_checks() -> None:
    print("\n3. Deciding what to re-ask")
    check("complete report has no flagged fields", logic_manager.get_flagged_fields(LOST_PHONE) == [])
    flagged = logic_manager.get_flagged_fields(INCOMPLETE_REPORT)
    check("missing colour and unsure date (0.45 < 0.60) are flagged",
          flagged == ["item_colour", "datetime"], f"got {flagged}")

    check("dog is rejected as prohibited", logic_manager.get_item_rejection(DOG_REPORT) == "prohibited")
    check("gibberish is rejected as unrecognised", logic_manager.get_item_rejection(GIBBERISH_REPORT) == "unrecognised")
    check("phone is not rejected", logic_manager.get_item_rejection(LOST_PHONE) is None)
    check("older record without the flags is not rejected", logic_manager.get_item_rejection({}) is None)

    check("'outside my house' is a vague location", logic_manager.is_vague_location(BACKPACK_REPORT))
    check("'SIT Punggol food court' is specific", not logic_manager.is_vague_location(LOST_PHONE))


def test_colours() -> None:
    print("\n4. Several colours")
    options = logic_manager.get_colour_options(BACKPACK_REPORT)
    check("duplicates and blanks removed, first spelling kept", options == ["black", "Red"], f"got {options}")
    check("single colour gives one option", logic_manager.get_colour_options(LOST_PHONE) == ["black"])

    picked = logic_manager.apply_colour_choice(copy.deepcopy(INCOMPLETE_REPORT), "silver")
    check("chosen colour stored with full confidence", picked["item_colour"] == {"value": "silver", "confidence": 1.0})
    check("colour no longer listed as missing", "item_colour" not in picked["missing_fields"])
    check("colour options reduced to the choice", picked["colour_options"] == ["silver"])


def test_text_similarity() -> None:
    print("\n5. Text similarity")
    check("tokens: lower-case words with synonyms", logic_manager.tokens("Gray Mobile!") == ["grey", "phone"])
    check("gray and grey are the same", logic_manager.text_similarity("Gray", "grey") == 1.0)
    check("joined spelling still matches (Hydro Flask / Hydroflask)",
          logic_manager.text_similarity("Hydro Flask", "Hydroflask") > 0.9)
    score = logic_manager.text_similarity("SIT Punggol food court", "Punggol campus food court")
    check("similar places score fairly high", 0.7 <= score <= 0.8, f"{score:.2f}")
    check("unrelated words score low", logic_manager.text_similarity("wallet", "umbrella") < 0.5)
    check("empty text gives None (field skipped)", logic_manager.text_similarity("black", "") is None)


def test_dates() -> None:
    print("\n6. Dates")
    check("parse_datetime reads the strict format",
          logic_manager.parse_datetime("2026-10-10T15:00") == datetime(2026, 10, 10, 15, 0))
    check("parse_datetime rejects other formats", logic_manager.parse_datetime("10 Oct 3pm") is None)

    lost = "2026-10-10T15:00"
    check("found 1 day before lost is allowed (48h tolerance)",
          not logic_manager.found_too_early(lost, "2026-10-09T15:00"))
    check("found 49h before lost is too early", logic_manager.found_too_early(lost, "2026-10-08T14:00"))
    check("same day scores 1.0", logic_manager.datetime_similarity(lost, "2026-10-10T18:00", True) == 1.0)
    two_days = logic_manager.datetime_similarity(lost, "2026-10-12T15:00", True)
    check("2 days apart scores about 0.86", abs(two_days - 0.857) < 0.01, f"{two_days:.3f}")
    check("8 days apart scores 0", logic_manager.datetime_similarity(lost, "2026-10-18T15:00", True) == 0.0)
    check("too early scores 0 in a lost search",
          logic_manager.datetime_similarity(lost, "2026-10-05T15:00", True) == 0.0)
    check("same gap is fine in a duplicate check (directional=False)",
          logic_manager.datetime_similarity(lost, "2026-10-05T15:00", False) > 0.0)
    check("missing date gives None", logic_manager.datetime_similarity(lost, "", True) is None)


def test_matching() -> None:
    print("\n7. Match scores")
    same = logic_manager.score_match(LOST_PHONE, FOUND_PHONE)
    check("same phone scores very high", same >= 0.95, f"{same:.2f}")
    other = logic_manager.score_match(LOST_PHONE, FOUND_WHITE_PHONE)
    check("white phone elsewhere is a possible match (0.50-0.69)", 0.5 <= other < 0.7, f"{other:.2f}")
    umbrella = logic_manager.score_match(LOST_PHONE, FOUND_UMBRELLA)
    check("umbrella scores low (type penalty)", umbrella < 0.5, f"{umbrella:.2f}")

    early_found = with_date(FOUND_PHONE, "2026-10-05T15:00")
    early = logic_manager.score_match(LOST_PHONE, early_found)
    # Everything matches except the date (scores 0, worth 10%) -> 0.9, then the specified x0.8 penalty.
    # 0.8 is written out here on purpose: the test states the rule, it does not copy the code's value.
    expected = round(0.9 * 0.8, 4)
    check("found 5 days before lost: date scores 0, then x0.8 penalty",
          abs(early - expected) < 0.001, f"{early:.2f}, expected {expected:.2f}")

    wallet = copy.deepcopy(FOUND_PHONE)
    wallet["item_type"] = {"value": "wallet", "confidence": 0.95}
    wallet["item_description"] = {"value": "black leather wallet", "confidence": 0.95}
    wallet_score = logic_manager.score_match(LOST_PHONE, wallet)
    check("same colour, brand and place but a wallet: not a match", wallet_score < 0.5, f"{wallet_score:.2f}")

    no_brand = copy.deepcopy(FOUND_PHONE)
    no_brand["item_brand"] = {"value": None, "confidence": 0.0}
    check("missing brand is skipped, not counted as a mismatch",
          logic_manager.score_match(LOST_PHONE, no_brand) >= 0.95)

    results = logic_manager.find_matches(LOST_PHONE, [FOUND_PHONE, FOUND_WHITE_PHONE, FOUND_UMBRELLA])
    check("find_matches: phone is a top match", [m["item_id"] for m in results["matches"]] == ["FND-0001"])
    check("find_matches: white phone is a possible match",
          [m["item_id"] for m in results["possible_matches"]] == ["FND-0002"])
    check("find_matches: each result carries the full item", results["matches"][0]["item"] is FOUND_PHONE)
    check("find_matches with nothing stored gives two empty lists",
          logic_manager.find_matches(LOST_PHONE, []) == {"matches": [], "possible_matches": []})

    new_report = copy.deepcopy(FOUND_PHONE)
    new_report.pop("item_id")
    duplicates = logic_manager.find_duplicates(new_report, [FOUND_PHONE, FOUND_WHITE_PHONE, FOUND_UMBRELLA])
    check("find_duplicates finds only the same phone", [d["item_id"] for d in duplicates] == ["FND-0001"])


def test_archiving() -> None:
    print("\n8. 7-day archiving")
    now = datetime(2026, 10, 18, 12, 0)
    items = [
        {"item_id": "OLD", "reported_at": "2026-10-10T12:00", "status": "active"},          # 8 days old
        {"item_id": "EXACT", "reported_at": "2026-10-11T12:00", "status": "active"},        # exactly 7 days
        {"item_id": "NEW", "reported_at": "2026-10-17T12:00", "status": "active"},          # 1 day old
        {"item_id": "DONE", "reported_at": "2026-09-01T12:00", "status": "archived"},       # already archived
        {"item_id": "BROKEN", "reported_at": "not a date", "status": "active"},              # unreadable
    ]
    expired = logic_manager.get_expired_item_ids(items, now=now)
    check("only the 8-day-old active item expires", expired == ["OLD"], f"got {expired}")

def test_date_rules() -> None:
    print("\n9. Future dates and dates that rule out a match")
    now = datetime(2026, 10, 14, 12, 0)
    check("date 2 hours in the future is rejected",
          logic_manager.is_future_datetime(with_date(LOST_PHONE, "2026-10-14T14:00"), now=now))
    check("date 30 minutes ahead is allowed (1-hour tolerance)",
          not logic_manager.is_future_datetime(with_date(LOST_PHONE, "2026-10-14T12:30"), now=now))
    check("past date is fine", not logic_manager.is_future_datetime(LOST_PHONE, now=now))
    check("missing date is not treated as future", not logic_manager.is_future_datetime(INCOMPLETE_REPORT | {
        "datetime": {"value": None, "confidence": 0.0}}, now=now))

    lost = "2026-10-09T02:00"
    check("found 12 days after lost rules out a match", logic_manager.dates_rule_out_match(lost, "2026-10-21T02:00"))
    check("found 3 days before lost rules out a match", logic_manager.dates_rule_out_match(lost, "2026-10-06T02:00"))
    check("found 1 day after lost does not", not logic_manager.dates_rule_out_match(lost, "2026-10-10T02:00"))
    check("missing date never rules out a match", not logic_manager.dates_rule_out_match(lost, ""))

    # The reported bug: found item dated 12 days after the loss used to be a top match (0.89).
    lost_report = with_date(LOST_PHONE, lost)
    far_found = with_date(FOUND_PHONE, "2026-10-21T02:00")
    results = logic_manager.find_matches(lost_report, [far_found])
    check("12 days apart: shown only as a possible match, not a top match",
          results["matches"] == [] and [m["item_id"] for m in results["possible_matches"]] == ["FND-0001"])
    early_found = with_date(FOUND_PHONE, "2026-10-06T02:00")
    results = logic_manager.find_matches(lost_report, [early_found])
    check("found 3 days before lost: possible match only",
          results["matches"] == [] and len(results["possible_matches"]) == 1)
    close_found = with_date(FOUND_PHONE, "2026-10-10T02:00")
    check("sensible dates are still a top match",
          [m["item_id"] for m in logic_manager.find_matches(lost_report, [close_found])["matches"]] == ["FND-0001"])
    weak = with_date(FOUND_UMBRELLA, "2026-10-21T02:00")
    check("a weak match far apart stays hidden",
          logic_manager.find_matches(lost_report, [weak]) == {"matches": [], "possible_matches": []})


# -------------------------


# -------------------------
# Run everything
# -------------------------
if __name__ == "__main__":
    print("Testing logic_manager with hard-coded sample AI outputs")
    test_decision_engine()
    test_reading_fields()
    test_follow_up_checks()
    test_colours()
    test_text_similarity()
    test_dates()
    test_matching()
    test_archiving()
    test_date_rules()

    failed = [name for name, passed, _ in RESULTS if not passed]
    print(f"\n{len(RESULTS) - len(failed)} of {len(RESULTS)} tests passed")
    if failed:
        print("Failed:", ", ".join(failed))
        sys.exit(1)
