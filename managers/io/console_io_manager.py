"""ConsoleIOManager: Reads answers from the keyboard and prints to the terminal."""
from __future__ import annotations

from typing import Sequence

from managers.base.base_io_manager import BaseIOManager
from models.found_item import FoundItem
from models.item import Item
from models.item_match import ItemMatch


class ConsoleIOManager(BaseIOManager):
    """Reads answers from the keyboard and prints to the terminal.

    All input and output go through _read() and _write(), so a subclass can redirect
    them (e.g. the scripted IO used in tests) without changing any other method.
    """

    # ---- the two hooks every other method uses ----
    def _read(self, prompt: str) -> str:
        """Read one line from the user."""
        return input(prompt)

    def _write(self, text: str = "") -> None:
        """Print one line."""
        print(text)

    @staticmethod
    def _clean(value: str) -> str:
        """Trim and collapse spaces, e.g. "  black   wallet " -> "black wallet"."""
        return " ".join(value.strip().split())

    # ---- menu ----
    def menu(self) -> str:
        self._write("===============================")
        self._write("Lost and Found Management System")
        self._write("===============================\n")
        self._write("What are you here for?")
        self._write("1. Find a lost item")
        self._write("2. Report a found item")
        self._write("3. Exit\n")
        choices = {"1": ("lost", "\nYou selected: Find a lost item\n"),
                   "2": ("found", "\nYou selected: Report a found item\n")}
        while True:
            answer = self._read("Enter your choice (1-3): ").strip()
            if answer in choices:
                choice, message = choices[answer]
                self._write(message)
                return choice
            if answer == "3":
                return "exit"
            self._write("Invalid choice. Enter 1, 2 or 3.")

    # ---- questions ----
    def ask_detail(self, prompt: str, min_words: int, max_words: int, error: str) -> str | None:
        while True:
            value = self._clean(self._read(prompt))
            if value.lower() == self.BACK_COMMAND:
                return None
            if min_words <= len(value.split()) <= max_words:
                return value
            self._write(error)

    def ask_confirm_or_correct(self, prompt: str) -> str | None:
        answer = self._clean(self._read(prompt))
        return None if answer.lower() == self.BACK_COMMAND else answer

    def get_report_details(self, report_type: str) -> dict[str, str] | None:
        verb = "lost" if report_type == "lost" else "found"
        self._write(f"(Type '{self.BACK_COMMAND}' at any prompt to return to the main menu.)\n")
        while True:
            description = self.ask_detail(
                f"Describe the item you {verb} (type, colour, brand, unique features): ", 2, 80,
                "Description is too short or too long. Enter 2 to 80 words.")
            if description is None:
                return None
            date_time = self.ask_detail(
                f"When was it {verb}? (e.g. 2026-10-08 2.30pm, or 'yesterday afternoon'): ", 1, 20,
                "Please enter a date/time of up to 20 words.")
            if date_time is None:
                return None
            location = self.ask_detail(f"Where was it {verb}? ", 1, 30,
                                       "Please enter a location of up to 30 words.")
            if location is None:
                return None

            self._write("\nPlease confirm your details:")
            self._write(f"  Description : {description}")
            self._write(f"  When        : {date_time}")
            self._write(f"  Where       : {location}")
            choice = self._confirm_details()
            if choice == "yes":
                return {"description": description, "date_time": date_time, "location": location}
            if choice == "back":
                return None
            self._write("\nOkay, please re-enter the details.\n")

    def _confirm_details(self) -> str:
        """"yes", "retry" or "back"."""
        while True:
            answer = self._read("Is this correct? (y = yes, n = re-enter, b = back to main menu): ").strip().lower()
            if answer in ("y", "yes"):
                return "yes"
            if answer in ("n", "no"):
                return "retry"
            if answer in ("b", self.BACK_COMMAND):
                return "back"
            self._write("Please enter y, n or b.")

    def choose_option(self, heading: str, options: Sequence[str]) -> str | None:
        self._write("\n" + heading)
        for number, option in enumerate(options, start=1):
            self._write(f"  {number}. {option}")
        while True:
            answer = self._read(
                f"Enter your choice (1-{len(options)}, or '{self.BACK_COMMAND}' for main menu): ").strip()
            if answer.lower() == self.BACK_COMMAND:
                return None
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return options[int(answer) - 1]
            self._write("Invalid choice.")

    def confirm(self, prompt: str) -> bool:
        while True:
            answer = self._read(f"{prompt} (y/n): ").strip().lower()
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            self._write("Please enter y or n.")

    # ---- output ----
    @staticmethod
    def format_item(item: Item) -> str:
        """The 4-line block shown for an item; missing values show as "-"."""
        def value(field) -> str:
            return field.value if field.value else "-"
        item_id = getattr(item, "item_id", None) or "NEW"
        return "\n".join([
            f"[{item_id}] {value(item.description)}",
            f"    Type: {value(item.item_type)} | Colour: {value(item.colour)} | Brand: {value(item.brand)}",
            f"    Unique features: {value(item.unique_info)}",
            f"    When: {value(item.when)} | Where: {value(item.location)}",
        ])

    def show_item(self, item: Item) -> None:
        self._write(self.format_item(item))

    def show_message(self, message: str) -> None:
        self._write(message)

    def show_not_found(self) -> None:
        self._write("No matching items found. Please try again later or report a found item.")

    def choose_match(self, matches: Sequence[ItemMatch],
                     possible_matches: Sequence[ItemMatch]) -> FoundItem | None:
        everything = list(matches) + list(possible_matches)   # one list so numbering runs on
        lines = [f"{number}. " + self.format_item(match.item) for number, match in enumerate(everything, start=1)]
        if matches:
            self._write("Displaying top five matches...\n")
            for line in lines[:len(matches)]:
                self._write(line)
        if possible_matches:
            self._write("\nPossible matches (less certain)...\n")
            for line in lines[len(matches):]:
                self._write(line)
        while True:
            answer = self._read(f"\nWhich item is yours? (1-{len(everything)}, or 0 to cancel): ").strip()
            if answer == "0":
                return None
            if answer.isdigit() and 1 <= int(answer) <= len(everything):
                return everything[int(answer) - 1].item
            self._write("Invalid choice.")

    def confirm_duplicate(self, duplicates: Sequence[FoundItem]) -> bool:
        self._write("\nThis looks similar to item(s) already reported:")
        for item in duplicates:
            self._write(self.format_item(item))
        return self.confirm("Save as a new report anyway?")