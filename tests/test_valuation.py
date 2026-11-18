"""Value assessment of found items: the HIGH_VALUE / ORDINARY rule and its schema checks. No API calls."""
import unittest
from datetime import datetime

from managers.ai.schema_validator import SchemaValidator
from managers.logic.colour_choice_correction import ColourChoiceCorrection
from managers.logic.rules.future_date_rule import FutureDateRule
from models import FoundItem, Item, ValueAssessment
from tests.helpers import SampleReplies, ScriptedIOManager

ai_reply = SampleReplies.ai_reply
found_reply = SampleReplies.found_reply
found_item = SampleReplies.found_item

VALUATION_KEYS = ("estimated_value_sgd", "sensitive", "valuation_reason", "value_category")


class TestValueAssessment(unittest.TestCase):
    def test_category_follows_the_threshold_and_sensitivity(self):                      # T1
        for value, sensitive, expected in [(999.99, False, "ORDINARY"), (1000, False, "HIGH_VALUE"),
                                           (None, True, "HIGH_VALUE"), (20, True, "HIGH_VALUE"),
                                           (None, False, "ORDINARY")]:
            with self.subTest(value=value, sensitive=sensitive):
                assessment = ValueAssessment(value, sensitive, "reason")
                self.assertEqual(assessment.category, expected)
                self.assertEqual(ValueAssessment.category_for(value, sensitive), expected)
                self.assertEqual(assessment.is_high_value, expected == "HIGH_VALUE")

    def test_missing_or_bad_sensitive_means_not_assessed(self):                        # T2
        for record in ({"estimated_value_sgd": 2000}, {"sensitive": "yes"}, {"sensitive": None}):
            with self.subTest(record=record):
                self.assertIsNone(ValueAssessment.from_dict(record))

    def test_bad_values_become_unknown_and_category_is_recomputed(self):               # T3
        for value in (-1, float("nan"), True, "1000"):
            with self.subTest(value=value):
                assessment = ValueAssessment.from_dict({"estimated_value_sgd": value, "sensitive": False})
                self.assertIsNone(assessment.estimated_value_sgd)
                self.assertEqual(assessment.category, "ORDINARY")
        stored = ValueAssessment.from_dict({"estimated_value_sgd": 50, "sensitive": False,
                                            "value_category": "HIGH_VALUE", "valuation_reason": "r"})
        self.assertEqual(stored.category, "ORDINARY")
        self.assertEqual(stored.to_dict()["value_category"], "ORDINARY")
        with self.assertRaises(AttributeError):
            stored.sensitive = True


class TestFoundItemValuation(unittest.TestCase):
    def test_found_reply_gives_an_assessed_item(self):                                  # T4
        item = Item.from_ai_response("found", found_reply(2500))
        self.assertIsInstance(item, FoundItem)
        self.assertEqual(item.assessment.estimated_value_sgd, 2500)
        self.assertEqual(item.value_category, "HIGH_VALUE")
        self.assertTrue(item.is_high_value)
        self.assertEqual(item.assessment.reason, "Rough model-based estimate for offline testing.")

    def test_category_is_computed_not_taken_from_the_reply(self):                       # T5
        data = ai_reply("found")
        data.update(estimated_value_sgd=50, value_category="HIGH_VALUE")
        item = Item.from_ai_response("found", data)
        self.assertEqual(item.value_category, "ORDINARY")
        self.assertFalse(item.is_high_value)

    def test_copies_keep_the_assessment_and_escalation_time(self):                      # T6
        item = found_item(2500, True, item_id="FND-0001", reported_at="2026-11-01T09:30",
                          colours=["black", "red"])
        item.mark_escalated(datetime(2026, 11, 16, 18, 0))
        io = ScriptedIOManager(["1"])
        copies = [item.with_field("item_colour", item.colour), item.with_flags(item.flags),
                  ColourChoiceCorrection().correct(io, item), FutureDateRule().give_up(item)]
        for copy in copies:
            with self.subTest(copy=copy):
                self.assertEqual(copy.assessment, item.assessment)
                self.assertEqual(copy.escalated_at, "2026-11-16T18:00")
                self.assertEqual(copy.item_id, "FND-0001")

    def test_round_trip_assessed_and_not_assessed(self):                                # T7
        assessed = found_item(2500, item_id="FND-0001", reported_at="2026-11-01T09:30")
        self.assertEqual(FoundItem.from_dict(assessed.to_dict()).to_dict(), assessed.to_dict())
        plain = FoundItem.from_dict({key: value for key, value in assessed.to_dict().items()
                                     if key not in VALUATION_KEYS})
        record = plain.to_dict()
        self.assertEqual(FoundItem.from_dict(record).to_dict(), record)
        for key in VALUATION_KEYS:
            self.assertNotIn(key, record)

    def test_ai_record_carries_the_assessment_but_no_storage_keys(self):               # T8
        item = found_item(2500, item_id="FND-0001", reported_at="2026-11-01T09:30")
        item.mark_escalated(datetime(2026, 11, 16, 18, 0))
        record = item.ai_record()
        for key in VALUATION_KEYS:
            self.assertIn(key, record)
        for key in ("item_id", "reported_at", "status", "escalated_at"):
            self.assertNotIn(key, record)


class TestValuationSchema(unittest.TestCase):
    def test_valid_assessments(self):                                                   # T11
        for reply in (found_reply(), found_reply(None), found_reply(None, True), found_reply(0),
                      found_reply(999.99)):
            self.assertEqual(SchemaValidator().validate(reply), [])

    def test_invalid_values_are_rejected_for_every_report_type(self):                  # T12
        for report_type in ("found", "lost", "unknown"):
            for value in (-1, float("nan"), float("inf"), True, "1000"):
                with self.subTest(report_type=report_type, value=value):
                    reply = found_reply()
                    reply.update(report_type=report_type, estimated_value_sgd=value)
                    self.assertFalse(SchemaValidator().is_valid(reply))

    def test_category_must_agree_with_the_rule(self):                                   # T12
        for report_type in ("found", "lost", "unknown"):
            for changes in ({"sensitive": True}, {"estimated_value_sgd": 5000}, {"value_category": "HIGH_VALUE"}):
                with self.subTest(report_type=report_type, changes=changes):
                    reply = ai_reply(report_type)              # S$800, not sensitive, ORDINARY
                    reply.update(changes)
                    self.assertFalse(SchemaValidator().is_valid(reply))

    def test_missing_or_blank_assessment_is_rejected_for_every_report_type(self):      # T12
        for report_type in ("found", "lost", "unknown"):
            for key in VALUATION_KEYS:
                with self.subTest(report_type=report_type, key=key):
                    reply = found_reply()
                    reply["report_type"] = report_type
                    del reply[key]
                    self.assertFalse(SchemaValidator().is_valid(reply))
            reply = found_reply()
            reply.update(report_type=report_type, valuation_reason="   ")
            self.assertFalse(SchemaValidator().is_valid(reply))


if __name__ == "__main__":
    unittest.main()
