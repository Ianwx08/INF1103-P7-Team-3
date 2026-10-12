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
