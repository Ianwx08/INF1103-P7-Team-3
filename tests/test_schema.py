"""SchemaValidator: Gemini replies must be checked before being used. Doesn't call API."""
import unittest

from managers.ai.constants import RESPONSE_SCHEMA
from managers.ai.schema_validator import SchemaValidator
from models import FIELD_NAMES
from tests.helpers import SampleReplies

ai_reply = SampleReplies.ai_reply
copy_reply = SampleReplies.copy_reply

class TestSchemaValidator(unittest.TestCase):
    def setUp(self):
        self.validator = SchemaValidator()
        self.good = ai_reply()

    def assert_problem(self, data, text):
        problems = self.validator.validate(data)
        self.assertTrue(any(text in p for p in problems), f"expected {text!r} in {problems}")

    def test_valid_reply_has_no_problems(self):
        self.assertEqual(self.validator.validate(self.good), [])
        self.assertTrue(self.validator.is_valid(self.good))

    def test_null_values_allowed(self):
        self.assertTrue(self.validator.is_valid(ai_reply(colour=None, when=None, brand=None)))

    def test_not_an_object(self):
        for data in ([], "text", None, 42):
            self.assertEqual(self.validator.validate(data), ["Response is not a JSON object."])

    def test_bad_report_type(self):
        self.assert_problem(copy_reply(self.good, report_type="stolen"), "report_type")

    def test_missing_field(self):
        data = copy_reply(self.good)
        del data["location"]
        self.assert_problem(data, "location must be an object")

    def test_value_must_be_text_or_null(self):
        data = copy_reply(self.good, item_type={"value": 123, "confidence": 0.9})
        self.assert_problem(data, "item_type.value")

    def test_confidence_must_be_number_0_to_1(self):
        for bad in (True, 1.5, -0.1, "high", None):
            data = copy_reply(self.good, item_colour={"value": "black", "confidence": bad})
            self.assert_problem(data, "item_colour.confidence")

    def test_datetime_format(self):
        data = copy_reply(self.good, datetime={"value": "10 Oct 3pm", "confidence": 0.9})
        self.assert_problem(data, "YYYY-MM-DDTHH:MM")

    def test_colour_options_must_be_list_of_text(self):
        self.assert_problem(copy_reply(self.good, colour_options="black"), "colour_options")
        self.assert_problem(copy_reply(self.good, colour_options=["black", 3]), "colour_options")

    def test_flags_must_be_booleans(self):
        for flag in ("prohibited_item", "item_recognised", "location_specific"):
            self.assert_problem(copy_reply(self.good, **{flag: "no"}), flag)
            data = copy_reply(self.good)
            del data[flag]
            self.assert_problem(data, flag)

    def test_missing_fields_only_known_names(self):
        self.assert_problem(copy_reply(self.good, missing_fields="item_colour"), "missing_fields must be a list")
        self.assert_problem(copy_reply(self.good, missing_fields=["favourite_food"]), "known field names")

    def test_overall_confidence(self):
        self.assert_problem(copy_reply(self.good, overall_confidence=2), "overall_confidence")

    def test_reports_every_problem_at_once(self):
        data = copy_reply(self.good, report_type="x", overall_confidence="high", prohibited_item=None)
        self.assertGreaterEqual(len(self.validator.validate(data)), 3)

    def test_response_schema_requires_every_key(self):
        required = set(RESPONSE_SCHEMA["required"])
        self.assertTrue(set(FIELD_NAMES) <= required)
        self.assertTrue({"colour_options", "prohibited_item", "item_recognised", "location_specific"} <= required)


if __name__ == "__main__":
    unittest.main()
