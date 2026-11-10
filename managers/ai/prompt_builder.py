"""PromptBuilder: Builds the text sent to Gemini for a report and follow-up answers."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Callable, Mapping
from managers.ai.constants import SYSTEM_PROMPT
from models.item import Item

class PromptBuilder:
    DATE_RULES = (
        "Resolve relative dates such as 'yesterday' or 'last Friday' against the "
        "current date and time. If only a date is given without a time, use 12:00 "
        "and a confidence between 0.60 and 0.70. If no usable date is given, the "
        "datetime value must be null."
    )

    def __init__(self, system_prompt: str = SYSTEM_PROMPT,
                 clock: Callable[[], datetime] = datetime.now) -> None:
        """clock gives "now"; tests can pass a fixed one."""
        self._system_prompt = system_prompt
        self._clock = clock

    def build(self, report_type: str, answers: Mapping[str, str], previous: Item | None = None) -> str:
        """The full prompt: extraction rules + the user's report or follow-up answers."""
        report = self._first_report(report_type, answers) if previous is None \
            else self._follow_up(report_type, answers, previous)
        return f"{self._system_prompt} USER REPORT:{report}"

    def _today(self) -> str:
        return self._clock().strftime("%Y-%m-%dT%H:%M (%A)")    # e.g. 2026-10-11T23:00 (Sunday)

    def _first_report(self, report_type: str, answers: Mapping[str, str]) -> str:
        return (
            f"Current date and time: {self._today()}. {self.DATE_RULES}\n"
            f"Report type: {report_type}\n"
            f"Item description: {answers['description']}\n"
            f"Date/time: {answers['date_time']}\n"
            f"Location: {answers['location']}"
        )

    def _follow_up(self, report_type: str, answers: Mapping[str, str], previous: Item) -> str:
        answer_lines = "\n".join(f"- {field}: {answer}" for field, answer in answers.items())
        return (
            f"Current date and time: {self._today()}. {self.DATE_RULES}\n"
            f"Report type: {report_type}\n"
            f"This report was already extracted as:\n"
            f"{json.dumps(previous.ai_record(), ensure_ascii=False)}\n"
            f"The user has now answered follow-up questions about these fields:\n"
            f"{answer_lines}\n"
            f"Update those fields from the user's answers. Information the user "
            f"states or confirms directly is explicit. If an answer contains no "
            f"usable information for its field, set that value to null. If the "
            f"item type changes, update item_description to match. Keep all "
            f"other fields unchanged, then re-evaluate colour_options, "
            f"prohibited_item, item_recognised and location_specific and "
            f"recompute missing_fields and overall_confidence."
        )
