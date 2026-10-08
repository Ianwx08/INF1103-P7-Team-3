from datetime import datetime

_COLOR_NAMES = {
    "black", "white", "red", "blue", "green", "yellow", "orange",
    "purple", "violet", "indigo", "pink", "brown", "grey", "gray",
    "silver", "gold", "beige", "cream", "ivory", "tan", "maroon",
    "burgundy", "navy", "teal", "turquoise", "cyan", "magenta",
    "lavender", "lilac", "peach", "coral", "salmon", "mint", "olive",
    "khaki", "charcoal", "slate", "aqua", "bronze", "copper", "rose",
    "blush", "sage", "taupe", "mauve", "fuchsia", "crimson", "scarlet",
    "amber", "periwinkle", "plum", "mustard", "clear", "transparent",
    "multicolor", "multicolour",
}

_COLOR_MODIFIERS = {
    "light", "dark", "pale", "deep", "bright", "neon",
}


def _clean_text(value):
    return " ".join(value.strip().split())


def _valid_words_only(value):
    words = value.split()
    return bool(words) and all(word.isalpha() for word in words)


def _valid_color(value):
    if not value or value.startswith("-") or value.endswith("-") or "--" in value:
        return False

    if not all(character.isalpha() or character.isspace() or character == "-" for character in value):
        return False

    words = value.lower().replace("-", " ").split()
    allowed_words = _COLOR_NAMES | _COLOR_MODIFIERS | {"and"}

    return (
        bool(words)
        and all(word in allowed_words for word in words)
        and any(word in _COLOR_NAMES for word in words)
    )
def _valid_brand(value):
    words = value.split()
    return bool(words) and all(word.isalnum() for word in words)


def _valid_unique_description(value):
    return len(value.split()) <= 80


def _prompt_valid(prompt, validator, error_message, optional=False):
    while True:
        value = _clean_text(input(prompt))

        if optional and not value:
            return ""

        if validator(value):
            return value

        print(error_message)
def _valid_datetime(value):
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M")
        return parsed.strftime("%Y-%m-%dT%H:%M") == value
    except ValueError:
        return False


def _valid_location(value):
    words = value.split()

    if not words or len(words) > 30:
        return False

    if value.startswith("-") or value.endswith("-") or "--" in value:
        return False

    return all(
        character.isalnum() or character.isspace() or character == "-"
        for character in value
    )
def _repair_value(value, prompt, validator, error_message, optional=False):
    value = "" if value is None else _clean_text(str(value))

    if optional and not value:
        return value

    if validator(value):
        return value

    print(error_message)

    while True:
        value = _clean_text(input(prompt))

        if optional and not value:
            return value

        if validator(value):
            return value

        print(error_message)

def menu():
    print("===============================")
    print("Lost and Found Management System")
    print("===============================\n")
    print("What are you here for?")
    print("1. Find a lost item")
    print("2. Report a found item\n")

    while True:
        user_input = input("Enter your choice (1 or 2): ").strip()

        if user_input == "1":
            print("\nYou selected: Find a lost item\n")
            return "lost"

        if user_input == "2":
            print("\nYou selected: Report a found item\n")
            return "found"

        print("Invalid choice. Enter 1 or 2.")

def get_item_description():
    item_type = _prompt_valid(
        "Enter the item type: ",
        _valid_words_only,
        "Invalid item type. Use letters and spaces only."
    )

    item_color = _prompt_valid(
        "Enter the item color: ",
        _valid_color,
        "Invalid color. Use a complete color name with letters, spaces, or single hyphens."
    )

    item_brand = _prompt_valid(
        "Enter the item brand (optional; press Enter to skip): ",
        _valid_brand,
        "Invalid brand. Use letters, numbers, and spaces only.",
        optional=True
    )

    item_description = _prompt_valid(
        "Enter the item unique description (optional; maximum 80 words): ",
        _valid_unique_description,
        "Invalid description. It must be 80 words or fewer.",
        optional=True
    )

    return item_type, item_color, item_brand, item_description

def get_datetimelocation():
    date_time = _prompt_valid(
        "Enter the date and time (YYYY-MM-DDTHH:MM): ",
        _valid_datetime,
        "Invalid date or time. Use YYYY-MM-DDTHH:MM, for example 2026-10-08T14:30."
    )

    location = _prompt_valid(
        "Enter the location (maximum 30 words): ",
        _valid_location,
        "Invalid location. Use letters, numbers, spaces, and single hyphens only; enter no more than 30 words."
    )

    return date_time, location

def invalid_inputs(item_data):
    field_rules = [
        (
            "item_type",
            "Enter the item type: ",
            _valid_words_only,
            "Invalid item type. Use letters and spaces only.",
            False,
        ),
        (
            "item_colour",
            "Enter the item color: ",
            _valid_color,
            "Invalid color. Use a complete color name with letters, spaces, or single hyphens.",
            False,
        ),
        (
            "item_brand",
            "Enter the item brand (optional; press Enter to skip): ",
            _valid_brand,
            "Invalid brand. Use letters, numbers, and spaces only.",
            True,
        ),
        (
            "item_unique_info",
            "Enter the item unique description (optional; maximum 80 words): ",
            _valid_unique_description,
            "Invalid description. It must be 80 words or fewer.",
            True,
        ),
        (
            "datetime",
            "Enter the date and time (YYYY-MM-DDTHH:MM): ",
            _valid_datetime,
            "Invalid date or time. Use YYYY-MM-DDTHH:MM, for example 2026-10-08T14:30.",
            False,
        ),
        (
            "location",
            "Enter the location (maximum 30 words): ",
            _valid_location,
            "Invalid location. Use letters, numbers, spaces, and single hyphens only; enter no more than 30 words.",
            False,
        ),
    ]

    for field, prompt, validator, error_message, optional in field_rules:
        if field not in item_data or not isinstance(item_data[field], dict):
            item_data[field] = {"value": None, "confidence": 0.0}

        item_data[field]["value"] = _repair_value(
            item_data[field].get("value"),
            prompt,
            validator,
            error_message,
            optional=optional
        )

    return item_data


def display_matches(top_matches):
    print("Displaying top five matches...\n")
    for lines in top_matches:
        print(lines)

def items_not_found():
    print("No matching items found. Please try again later or report a found item.")

