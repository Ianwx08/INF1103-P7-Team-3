import os
import sys
from dotenv import load_dotenv

load_dotenv()    # read GEMINI_API_KEY (and optional GEMINI_MODEL, DATA_DIR) from .env

# The app cannot work without Gemini, so stop straight away if there is no key.
if not os.getenv("GEMINI_API_KEY"):
    print("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

import ai_manager
import Database_manager
import io_manager
import logic_manager


def archive_expired_items() -> None:
    """Archive found items left unclaimed past the archive period (7 days)."""
    for item_id in logic_manager.get_expired_item_ids(Database_manager.get_all_items()):
        Database_manager.update_item(item_id, {"status": "archived"})
