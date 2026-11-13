"""Lost & Found CLI: entry point that builds the four managers and runs the menu loop."""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from managers.ai.gemini_ai_manager import GeminiAIManager
from managers.base.base_io_manager import BaseIOManager
from managers.data.json_data_manager import JsonDataManager
from managers.io.console_io_manager import ConsoleIOManager
from managers.logic.logic_manager import LogicManager


class LostAndFoundApp:
    """The application: the menu loop and file-error handling.

    Composition root: create_default() builds the real managers; tests build the app
    with a mock AI and scripted IO instead (the same code runs either way).
    """

    def __init__(self, io: BaseIOManager, logic: LogicManager) -> None:
        self._io = io
        self._logic = logic
        self._handlers = {
            "lost": self._logic.report_lost_item,
            "found": self._logic.report_found_item,
        }

    @classmethod
    def create_default(cls) -> "LostAndFoundApp":
        """The real app: Gemini AI, JSON storage, console IO."""
        io = ConsoleIOManager()
        logic = LogicManager(ai=GeminiAIManager(), data=JsonDataManager(), io=io)
        return cls(io, logic)

    def run(self) -> None:
        """Show the menu until the user chooses Exit. File errors become messages, not crashes."""
        while True:
            try:
                self._logic.archive_expired()
            except OSError as error:
                self._io.show_message(f"Could not update the data file: {error}")

            choice = self._io.menu()
            if choice == "exit":
                self._io.show_message("Goodbye!")
                break

            try:
                self._handlers[choice]()
            except OSError as error:
                self._io.show_message(f"Could not read or save the data file: {error}. Nothing was saved.")
            self._io.show_message("")


if __name__ == "__main__":
    load_dotenv()    # GEMINI_API_KEY, and optional GEMINI_MODEL / DATA_DIR, from .env
    # The app cannot work without Gemini, so stop straight away if there is no key.
    if not os.getenv("GEMINI_API_KEY"):
        print("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
        sys.exit(1)
    try:
        LostAndFoundApp.create_default().run()
    except (KeyboardInterrupt, EOFError):    # Ctrl+C or closed input
        print("\nGoodbye!")