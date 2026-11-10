"""AI managers: GeminiAIManager with a fake client (no network) and MockAIManager.
   The same contract tests run against both, showing either can replace the other."""

import json
import unittest
from datetime import datetime
from types import SimpleNamespace
import httpx
from google.genai import errors
from managers.ai.ai_error_translator import AIErrorTranslator
from managers.ai.gemini_ai_manager import GeminiAIManager
from managers.ai.mock_ai_manager import MockAIManager
from managers.ai.prompt_builder import PromptBuilder
from managers.base.base_ai_manager import BaseAIManager
from models import FoundItem, LostItem
from tests.helpers import SampleReplies

ai_reply = SampleReplies.ai_reply

NOW = datetime(2026, 10, 14, 12, 0)
ANSWERS = {"description": "black Samsung phone", "date_time": "yesterday 3pm", "location": "SIT Punggol food court"}


class FakeGeminiClient:
    """Stands in for google.genai.Client: returns queued texts or raises queued errors."""

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.requests = []
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, **kwargs):
        self.requests.append(kwargs)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome if isinstance(outcome, str) else json.dumps(outcome))


class GeminiFixtures:
    """Builds fake API errors and Gemini managers are wired to a fake client."""

    @staticmethod
    def api_error(code, status, message="error"):
        cls = errors.ServerError if code >= 500 else errors.ClientError
        return cls(code, {"error": {"code": code, "status": status, "message": message}})

    @staticmethod
    def gemini(outcomes, notes=None):
        notes = [] if notes is None else notes
        client = FakeGeminiClient(outcomes)
        manager = GeminiAIManager(api_key="test-key", model="test-model", client=client,
                                  notify=notes.append, clock=lambda: NOW)
        return manager, client, notes


api_error = GeminiFixtures.api_error
gemini = GeminiFixtures.gemini


class AIContract:
    """Behaviour every BaseAIManager must have. Subclasses says how to build one."""

    def make(self, replies):
        raise NotImplementedError

    def test_is_a_base_ai_manager(self):
        self.assertIsInstance(self.make([ai_reply()]), BaseAIManager)

    def test_valid_reply_becomes_the_right_item_type(self):
        self.assertIsInstance(self.make([ai_reply()]).analyse("lost", ANSWERS), LostItem)
        found = self.make([ai_reply()]).analyse("found", ANSWERS)
        self.assertIsInstance(found, FoundItem)
        self.assertEqual((found.item_type.text, found.colour.text), ("phone", "black"))

    def test_menu_choice_wins_over_ai_report_type(self):
        self.assertEqual(self.make([ai_reply(report_type="found")]).analyse("lost", ANSWERS).report_type, "lost")

    def test_invalid_reply_gives_none(self):
        bad = ai_reply()
        bad["overall_confidence"] = "high"
        self.assertIsNone(self.make([bad, bad, bad]).analyse("found", ANSWERS))


class TestGeminiContract(AIContract, unittest.TestCase):
    def make(self, replies):
        return gemini(replies)[0]


class TestMockContract(AIContract, unittest.TestCase):
    def make(self, replies):
        return MockAIManager(replies, notify=lambda m: None)


class TestGeminiAIManager(unittest.TestCase):
    def test_request_forces_json_schema_and_disables_function_calling(self):
        manager, client, _ = gemini([ai_reply()])
        manager.analyse("found", ANSWERS)
        config = client.requests[0]["config"]
        self.assertEqual(config.response_mime_type, "application/json")
        self.assertIsNotNone(config.response_schema)
        self.assertTrue(config.automatic_function_calling.disable)
        self.assertEqual(client.requests[0]["model"], "test-model")

    def test_retries_then_succeeds(self):
        manager, client, notes = gemini([api_error(503, "UNAVAILABLE"), "{broken", ai_reply()])
        self.assertIsNotNone(manager.analyse("found", ANSWERS))
        self.assertEqual(len(client.requests), 3)
        self.assertEqual(len(notes), 2)

    def test_gives_up_after_three_attempts(self):
        manager, client, notes = gemini([api_error(503, "UNAVAILABLE")] * 3)
        self.assertIsNone(manager.analyse("found", ANSWERS))
        self.assertEqual(len(client.requests), 3)
        self.assertIn("AI processing attempt 3/3 failed: Gemini is busy", notes[-1])

    def test_network_errors_are_handled(self):
        for error in (httpx.ConnectError("refused"), httpx.ReadTimeout("slow")):
            manager, _, notes = gemini([error] * 3)
            self.assertIsNone(manager.analyse("found", ANSWERS))
            self.assertEqual(len(notes), 3)

    def test_empty_reply_is_handled(self):
        manager, client, _ = gemini([ai_reply()])
        client._outcomes = [None, None, None]
        client.models = SimpleNamespace(generate_content=lambda **k: SimpleNamespace(text=None))
        self.assertIsNone(manager.analyse("found", ANSWERS))

    def test_follow_up_prompt_sends_previous_record_and_answers(self):
        manager, client, _ = gemini([ai_reply(colour=None), ai_reply(colour="dark grey")])
        first = manager.analyse("found", ANSWERS)
        manager.analyse("found", {"item_colour": "dark grey"}, first)
        prompt = client.requests[1]["contents"]
        self.assertIn("- item_colour: dark grey", prompt)
        self.assertIn('"item_type": {"value": "phone"', prompt)
        self.assertNotIn('"status"', prompt)

    def test_api_key_and_client_are_encapsulated(self):
        manager, _, _ = gemini([ai_reply()])
        self.assertTrue(manager.has_api_key)
        self.assertFalse(hasattr(manager, "client"))
        self.assertFalse(hasattr(manager, "__client"))

    def test_model_setter_validates(self):
        manager, _, _ = gemini([ai_reply()])
        manager.model = "gemini-3.1-flash-lite"
        self.assertEqual(manager.model, "gemini-3.1-flash-lite")
        with self.assertRaises(ValueError):
            manager.model = "  "


class TestPromptBuilder(unittest.TestCase):
    def test_first_prompt_has_rules_date_and_answers(self):
        prompt = PromptBuilder(clock=lambda: NOW).build("found", ANSWERS)
        self.assertIn("You are an information extraction system", prompt)
        self.assertIn("Current date and time: 2026-10-14T12:00 (Wednesday)", prompt)
        self.assertIn("use 12:00", prompt)
        self.assertIn("Item description: black Samsung phone", prompt)


class TestErrorTranslator(unittest.TestCase):
    def test_plain_messages(self):
        describe = AIErrorTranslator().describe
        cases = [
            (api_error(400, "INVALID_ARGUMENT", "API key not valid"), "API key is not valid"),
            (api_error(403, "PERMISSION_DENIED"), "refused access"),
            (api_error(404, "NOT_FOUND"), "model could not be found"),
            (api_error(429, "RESOURCE_EXHAUSTED"), "Too many requests"),
            (api_error(503, "UNAVAILABLE"), "busy or temporarily unavailable"),
            (httpx.ReadTimeout("slow"), "took too long"),
            (httpx.ConnectError("refused"), "Could not connect"),
            (ValueError("bad json"), "not in the expected format"),
        ]
        for error, text in cases:
            self.assertIn(text, describe(error))


class TestMockAIManager(unittest.TestCase):
    def test_records_calls_and_simulates_failures(self):
        notes = []
        mock = MockAIManager([api_error(503, "UNAVAILABLE"), ai_reply()], notify=notes.append)
        self.assertIsNone(mock.analyse("found", ANSWERS))
        self.assertIsNotNone(mock.analyse("found", ANSWERS))
        self.assertEqual((len(mock.calls), mock.remaining), (2, 0))
        self.assertIn("busy", notes[0])

    def test_empty_queue_gives_none(self):
        self.assertIsNone(MockAIManager([], notify=lambda m: None).analyse("found", ANSWERS))


if __name__ == "__main__":
    unittest.main()