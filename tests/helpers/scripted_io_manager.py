
"""ScriptedIOManager: ConsoleIOManager that reads answers from a list and records everything shown."""
from __future__ import annotations

from typing import Iterable

from managers.io.console_io_manager import ConsoleIOManager


class ScriptedIOManager(ConsoleIOManager):
    """ConsoleIOManager that reads answers from a list and records everything shown.

    Inherits every question and display method; only the two hooks change (polymorphism).
    """

    def __init__(self, answers: Iterable[str] = ()) -> None:
        self._answers = list(answers)
        self.output: list[str] = []      # every line written
        self.prompts: list[str] = []     # every question asked

    def add_answers(self, *answers: str) -> None:
        self._answers.extend(answers)

    def _read(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self._answers:
            raise AssertionError(f"No scripted answer left for question: {prompt.strip()!r}")
        return self._answers.pop(0)

    def _write(self, text: str = "") -> None:
        self.output.append(text)

    @property
    def text(self) -> str:
        """Everything shown, as one string."""
        return "\n".join(self.output)

    @property
    def unused_answers(self) -> list[str]:
        return list(self._answers)
