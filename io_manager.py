from datetime import datetime

def clean_text(value):
    """Trim an answer and collapse repeated spaces, e.g. "  black   wallet " -> "black wallet"."""
    return " ".join(value.strip().split())

# Typing this at any detail or follow-up prompt returns to the main menu.
BACK_COMMAND = "back"


def menu():
    """Show the main menu and return the user's choice: "lost", "found" or "exit"."""
    print("===============================")
    print("Lost and Found Management System")
    print("===============================\n")
    print("What are you here for?")
    print("1. Find a lost item")
    print("2. Report a found item")
    print("3. Exit\n")

    while True:
        user_input = input("Enter your choice (1-3): ").strip()    # raw menu answer

        if user_input == "1":
            print("\nYou selected: Find a lost item\n")
            return "lost"

        if user_input == "2":
            print("\nYou selected: Report a found item\n")
            return "found"

        if user_input == "3":
            return "exit"

        print("Invalid choice. Enter 1, 2 or 3.")

def items_not_found():
    """Tell the user that no stored found item matched their lost item."""
    print("No matching items found. Please try again later or report a found item.")


def word_count_between(minimum: int, maximum: int):
    """Return a check that passes when an answer has between minimum and maximum words."""
    return lambda value: minimum <= len(value.split()) <= maximum


def prompt_detail(prompt: str, validator, error_message: str) -> str | None:
    """Ask a question until the answer passes `validator`.

    Prints `error_message` after each invalid answer. Returns the cleaned
    answer, or None if the user types 'back'.
    """
    while True:
        value = clean_text(input(prompt))    # the user's cleaned answer

        if value.lower() == BACK_COMMAND:
            return None

        if validator(value):
            return value

        print(error_message)


def get_report_details(report_type: str) -> dict | None:
    """Ask for the free-text details that Gemini will structure.

    Asks for a description, when and where, then shows the answers back
    for confirmation (y = keep, n = re-enter, b = back). Returns
    {"description", "date_time", "location"}, or None if the user chooses
    to go back to the main menu.
    """
    verb = "lost" if report_type == "lost" else "found"    # used in the question wording
    print(f"(Type '{BACK_COMMAND}' at any prompt to return to the main menu.)\n")

    while True:
        description = prompt_detail(
            f"Describe the item you {verb} (type, colour, brand, unique features): ",
            word_count_between(2, 80),
            "Description is too short or too long. Enter 2 to 80 words."
        )
        if description is None:
            return None

        date_time = prompt_detail(
            f"When was it {verb}? (e.g. 2026-10-08 2.30pm, or 'yesterday afternoon'): ",
            word_count_between(1, 20),
            "Please enter a date/time of up to 20 words."
        )
        if date_time is None:
            return None

        location = prompt_detail(
            f"Where was it {verb}? ",
            word_count_between(1, 30),
            "Please enter a location of up to 30 words."
        )
        if location is None:
            return None

        print("\nPlease confirm your details:")
        print(f"  Description : {description}")
        print(f"  When        : {date_time}")
        print(f"  Where       : {location}")

        choice = confirm_details()    # "yes", "retry" or "back"
        if choice == "yes":
            return {"description": description, "date_time": date_time, "location": location}
        if choice == "back":
            return None
        print("\nOkay, please re-enter the details.\n")


def confirm_details() -> str:
    """Ask whether the entered details are correct.

    Returns "yes" (keep them), "retry" (re-enter them) or "back" (main menu).
    """
    while True:
        answer = input(
            "Is this correct? (y = yes, n = re-enter, b = back to main menu): "
        ).strip().lower()
        if answer in ("y", "yes"):
            return "yes"
        if answer in ("n", "no"):
            return "retry"
        if answer in ("b", BACK_COMMAND):
            return "back"
        print("Please enter y, n or b.")


def confirm(prompt: str) -> bool:
    """Ask a yes/no question. Returns True for y/yes and False for n/no."""
    while True:
        answer = input(f"{prompt} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter y or n.")


def choose_item(items: list[dict], prompt: str) -> dict | None:
    """Pick one entry from a numbered list. Returns None if the user enters 0."""
    while True:
        answer = input(f"{prompt} (1-{len(items)}, or 0 to cancel): ").strip()
        if answer == "0":
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(items):
            return items[int(answer) - 1]
        print("Invalid choice.")


def show_message(message: str) -> None:
    """Print a message. main.py uses this so all screen output stays in this module."""
    print(message)



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

# Friendly names for each field, used in follow-up questions.
FIELD_LABELS = {
    "item_description": "item description",
    "item_type": "item type",
    "item_colour": "colour",
    "item_brand": "brand",
    "item_unique_info": "unique features",
    "datetime": "date and time",
    "location": "location",
}

# The question asked when a required field is missing.
# {verb} is replaced with "lost" or "found".
FIELD_QUESTIONS = {
    "item_description": "Please describe the item (e.g. Samsung Galaxy S25): ",
    "item_type": "What kind of item is it (e.g. phone, wallet, bottle)? ",
    "item_colour": "What colour is it? ",
    "datetime": "When was it {verb}? (e.g. 'yesterday 3pm', '8 Oct around noon'): ",
    "location": "Where was it {verb}? ",
}


# Messages shown when Gemini rejects the item type, keyed by the reason
# returned from logic_manager.get_item_rejection().
ITEM_TYPE_REJECTIONS = {
    "prohibited": (
        "Sorry, living things (people, animals, plants) and food, drinks or fruit "
        "cannot be reported here."
    ),
    "unrecognised": "Sorry, we could not recognise that as an item.",
}


def ask_for_item_type(report_type: str, reason: str = "prohibited") -> dict | None:
    """Re-prompt for the item type after Gemini rejected it.

    reason is "prohibited" (living thing / food) or "unrecognised" (not a
    real object). Returns {"item_type": answer}, or None if the user types
    'back'.
    """
    action = "lose" if report_type == "lost" else "find"    # used in the question wording
    print("\n" + ITEM_TYPE_REJECTIONS[reason])
    answer = prompt_detail(
        f"  What kind of item did you {action}? (e.g. phone, wallet, bottle; "
        f"'{BACK_COMMAND}' for main menu): ",
        word_count_between(1, 30),
        "Please enter the item type (up to 30 words)."
    )
    return None if answer is None else {"item_type": answer}


def ask_for_specific_location(item_data: dict, report_type: str) -> dict | None:
    """Re-prompt when Gemini judged the location too vague to find.

    Pressing Enter cannot skip it. Returns {"location": answer}, or None
    if the user types 'back'.
    """
    verb = "lost" if report_type == "lost" else "found"
    current = item_data["location"]["value"]    # the vague place the user gave
    print(f"\n'{current}' is too vague for someone else to find.")
    answer = prompt_detail(
        f"  Where exactly was it {verb}? (e.g. building and level, mall, MRT station, "
        f"street name; '{BACK_COMMAND}' for main menu): ",
        word_count_between(1, 30),
        "Please enter a location of up to 30 words."
    )
    return None if answer is None else {"location": answer}

def choose_colour(colour_options: list[str]) -> str | None:
    """Ask the user to pick the most noticeable colour from Gemini's options.

    Returns the chosen colour, or None if the user types 'back'.
    """
    print("\nMore than one colour was mentioned. Which is the most noticeable colour?")
    for number, colour in enumerate(colour_options, start=1):
        print(f"  {number}. {colour}")

    while True:
        answer = input(
            f"Enter your choice (1-{len(colour_options)}, or '{BACK_COMMAND}' for main menu): "
        ).strip()
        if answer.lower() == BACK_COMMAND:
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(colour_options):
            return colour_options[int(answer) - 1]
        print("Invalid choice.")


def ask_about_flagged_fields(item_data: dict, flagged_fields: list[str], report_type: str) -> dict | None:
    """Ask follow-up questions for the fields logic_manager flagged.

    If a field already has a value, the user can press Enter to confirm it
    or type a correction; if it is empty, the question in FIELD_QUESTIONS is
    asked. Returns {field: free-text answer} for the AI manager to validate
    and format, or None if the user types 'back'.
    """
    verb = "lost" if report_type == "lost" else "found"
    answers = {}    # field name -> the user's answer, sent to Gemini afterwards

    print(f"\nWe need a few more details (type '{BACK_COMMAND}' for main menu):")

    for field in flagged_fields:
        field_data = item_data.get(field)
        current = field_data.get("value") if isinstance(field_data, dict) else None    # Gemini's current value
        label = FIELD_LABELS[field]

        if current:
            answer = clean_text(input(
                f"  We understood the {label} as '{current}'. "
                f"Press Enter to confirm, or type a correction: "
            ))
            if answer.lower() == BACK_COMMAND:
                return None
            # An empty answer means "keep it", which Gemini is told explicitly.
            answers[field] = answer if answer else f"{current} (confirmed by the user)"
        else:
            answer = prompt_detail(
                "  " + FIELD_QUESTIONS[field].format(verb=verb),
                word_count_between(1, 30),
                f"Please enter the {label} (up to 30 words)."
            )
            if answer is None:
                return None
            answers[field] = answer

    return answers