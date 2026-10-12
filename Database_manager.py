import json
import os
from datetime import datetime

# -------------------------
# Flat-file storage settings
# -------------------------
DATA_DIR = os.getenv(
    "DATA_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
)
# Stores every found item as a list of dicts.
FOUND_ITEMS_FILE = os.path.join(DATA_DIR, "found_items.json")
# Every found item ID starts with this, e.g. FND-0001.
ID_PREFIX = "FND-"

def ensure_data_dir() -> None:
    """Create the data folder if it does not exist yet."""
    os.makedirs(DATA_DIR, exist_ok=True)


def backup_corrupt_file() -> None:
    """Rename an unreadable data file so it is kept, not overwritten.

    The copy is named found_items.json.corrupt-<timestamp>.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")    # e.g. 20261011234512
    backup_path = f"{FOUND_ITEMS_FILE}.corrupt-{timestamp}"
    os.replace(FOUND_ITEMS_FILE, backup_path)
    print(f"Warning: found items file was unreadable. Backed up to {backup_path}")

def load_items() -> list[dict]:
    """Load all found items from the JSON flat file.

    Returns an empty list if the file does not exist yet, or if it is
    corrupt (after backing the corrupt file up).
    """
    ensure_data_dir()

    if not os.path.exists(FOUND_ITEMS_FILE):
        return []

    try:
        with open(FOUND_ITEMS_FILE, "r", encoding="utf-8") as file:
            items = json.load(file)    # whatever the file contains
    except (json.JSONDecodeError, UnicodeDecodeError):
        backup_corrupt_file()
        return []

    # The file must hold a list of item dictionaries; anything else is corrupt.
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        backup_corrupt_file()
        return []

    return items

def save_items(items: list[dict]) -> None:
    """Write all found items to the JSON flat file.

    Writes to a temporary file first and then swaps it in, so a crash
    part-way through saving cannot leave a half-written data file.
    """
    ensure_data_dir()
    temp_path = FOUND_ITEMS_FILE + ".tmp"    # written first, then renamed

    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(items, file, indent=2, ensure_ascii=False)

    os.replace(temp_path, FOUND_ITEMS_FILE)

def get_all_items() -> list[dict]:
    """Return every stored item, including archived ones."""
    return load_items()

def generate_item_id() -> str:
    """Return the next sequential ID, e.g. FND-0001, FND-0002, ..."""
    highest = 0    # largest ID number found so far

    for item in load_items():
        item_id = str(item.get("item_id", ""))
        suffix = item_id[len(ID_PREFIX):]    
        if item_id.startswith(ID_PREFIX) and suffix.isdigit():
            highest = max(highest, int(suffix))

    return f"{ID_PREFIX}{highest + 1:04d}"