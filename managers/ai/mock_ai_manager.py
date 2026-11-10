"""MockAIManager: Stand-in AI for offline tests: returns queued sample replies instead of calling Gemini."""
from __future__ import annotations
import json
from typing import Any, Callable, Mapping, Sequence
from managers.ai.ai_error_translator import AIErrorTranslator
from managers.ai.schema_validator import SchemaValidator
from managers.base.base_ai_manager import BaseAIManager
from models.item import Item

class MockAIManager(BaseAIManager):
    """Replies still passes through the real SchemaValidator, so invalid samples fail the same
       way a bad Gemini reply would. An Exception in the queue simulates a failed call."""

    def __init__(self, replies: Sequence[Mapping[str, Any] | Exception] = (),
                 notify: Callable[[str], None] = print) -> None:
        self._replies: list[Mapping[str, Any] | Exception] = list(replies)
        self._validator = SchemaValidator()
        self._notify = notify
        self.calls: list[dict[str, Any]] = []

    def queue(self, *replies: Mapping[str, Any] | Exception) -> None:
        """Add more replies to return, in order."""
        self._replies.extend(replies)

    @property
    def remaining(self) -> int:
        """How many queued replies have not been used."""
        return len(self._replies)

    def analyse(self, report_type: str, answers: Mapping[str, str],
                previous: Item | None = None) -> Item | None:
        self.calls.append({"report_type": report_type, "answers": dict(answers), "previous": previous})
        if not self._replies:
            self._notify("AI processing failed: no mock reply queued.")
            return None
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            self._notify(f"AI processing failed: {AIErrorTranslator().describe(reply)}")
            return None
        if not self._validator.is_valid(reply):
            self._notify("AI processing failed: Gemini's reply was not in the expected format.")
            return None
        return Item.from_ai_response(report_type, json.loads(json.dumps(reply)))