"""Load the example found items into the app's storage, without using any Gemini API tokens.

    python seed_data.py

Uses the same JSON file as main.py (DATA_DIR from .env, else data/found_items.json). No API key needed.
"""
from __future__ import annotations

import sys

from dotenv import load_dotenv

from managers.data.json_data_manager import JsonDataManager
from managers.samples.sample_data_loader import SampleDataLoader
from managers.samples.sample_data_seeder import SampleDataSeeder


class SeedDataCommand:
    """Runs the seeder and reports the result. Errors become messages and exit code 1."""

    def __init__(self, seeder: SampleDataSeeder, notify=print) -> None:
        self._seeder = seeder
        self._notify = notify

    def run(self) -> int:
        try:
            added, skipped = self._seeder.seed()
        except (OSError, ValueError) as error:
            self._notify(f"Could not load the sample data: {error}")
            return 1
        self._notify(f"Added {added} sample found item(s); {skipped} were already stored.")
        self._notify("Run python main.py and choose 1 (Find a lost item) to search for one of them.")
        return 0


if __name__ == "__main__":
    load_dotenv()    # DATA_DIR, same as main.py
    sys.exit(SeedDataCommand(SampleDataSeeder(SampleDataLoader(), JsonDataManager())).run())
