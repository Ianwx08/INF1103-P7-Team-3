"""Load example high-value found items for the escalation demo, without any Gemini call or email.

    python seed_escalation_demo.py

Uses the same storage as main.py (STORAGE_BACKEND / DATA_DIR from .env). No API key needed.
Run python main.py afterwards: the high-value found items unclaimed for more than 7 days are
emailed to the admins at start (at most once per item per day).
"""
from __future__ import annotations

import sys
from typing import Callable

from dotenv import load_dotenv

from managers.data.data_manager_factory import DataManagerFactory
from managers.samples.escalation_demo_seeder import EscalationDemoSeeder


class SeedEscalationDemoCommand:
    """Runs the seeder and reports the result. Errors become messages and exit code 1."""

    def __init__(self, seeder: EscalationDemoSeeder, notify: Callable[[str], None] = print) -> None:
        """seeder adds the demo items; notify shows the result (default: print)."""
        self._seeder = seeder
        self._notify = notify

    def run(self) -> int:
        """Seed once; returns the process exit code (0 = success, 1 = error)."""
        try:
            found = self._seeder.seed()
        except (OSError, ValueError) as error:
            self._notify(f"Could not load the demo data: {error}")
            return 1
        self._notify(f"Added {found} example found item(s). Existing ones were skipped.")
        self._notify("No email or AI request was made. Run python main.py to test the escalation email.")
        return 0


if __name__ == "__main__":
    load_dotenv()    # STORAGE_BACKEND / DATA_DIR, same as main.py
    try:
        seeder = EscalationDemoSeeder(DataManagerFactory().create())
    except ValueError as error:
        print(error)
        sys.exit(1)
    sys.exit(SeedEscalationDemoCommand(seeder).run())
