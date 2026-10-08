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


def _prompt_valid(prompt, validator, error_message, optional=False):
    while True:
        value = _clean_text(input(prompt))

        if optional and not value:
            return ""

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

    item_brand = input("Enter the item brand: ").strip()
    item_description = input("Enter the item unique description: ").strip()

    return item_type, item_color, item_brand, item_description

def get_datetimelocation():
    datetime = input("Enter the date and time: ")
    location = input("Enter the location: ")

    return datetime, location

def invalid_inputs(item_data):
    if not item_data["item_type"]["value"]:
        item_data["item_type"]["value"] = input("Enter the item type: ") 
    if not item_data["item_colour"]["value"]:
        item_data["item_colour"]["value"] = input("Enter the item color: ")
    if not item_data["item_brand"]["value"]:
        item_data["item_brand"]["value"] = input("Enter the item brand: ")
    if not item_data["item_unique_info"]["value"]:
        item_data["item_unique_info"]["value"] = input("Enter the item unique description: ")
    if not item_data["datetime"]["value"]:
        item_data["datetime"]["value"] = input("Enter the date and time: ")
    if not item_data["location"]["value"]:
        item_data["location"]["value"] = input("Enter the location: ")
    return item_data


def display_matches(top_matches):
    print("Displaying top five matches...\n")
    for lines in top_matches:
        print(lines)

def items_not_found():
    print("No matching items found. Please try again later or report a found item.")

