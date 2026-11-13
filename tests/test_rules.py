"""Follow-up rules and the colour correction, with scripted IO. No API calls."""
import unittest
from datetime import datetime
from managers.base.follow_up_rule import FollowUpRule
from managers.base.item_correction import ItemCorrection
from managers.logic.colour_choice_correction import ColourChoiceCorrection
from managers.logic.rules.future_date_rule import FutureDateRule
from managers.logic.rules.missing_fields_rule import MissingFieldsRule
from managers.logic.rules.prohibited_item_rule import ProhibitedItemRule
from managers.logic.rules.rejected_item_type_rule import RejectedItemTypeRule
from managers.logic.rules.unrecognised_item_rule import UnrecognisedItemRule
from managers.logic.rules.vague_location_rule import VagueLocationRule
from models import ExtractedField, Item
from tests.helpers import SampleReplies, ScriptedIOManager

ai_reply = SampleReplies.ai_reply

NOW = datetime(2026, 10, 14, 12, 0)

class RuleSamples:
    """Builds found items from sample replies for the rule tests."""

    @staticmethod
    def item(**changes) -> Item:
        return Item.from_ai_response("found", ai_reply(**changes))

item = RuleSamples.item

class TestRejectedItemTypes(unittest.TestCase):
    def test_inheritance(self):
        for rule in (ProhibitedItemRule(), UnrecognisedItemRule()):
            self.assertIsInstance(rule, RejectedItemTypeRule)
            self.assertIsInstance(rule, FollowUpRule)
            self.assertTrue(rule.blocking)

    def test_applies(self):
        self.assertTrue(ProhibitedItemRule().applies(item(prohibited=True)))
        self.assertFalse(ProhibitedItemRule().applies(item()))
        self.assertTrue(UnrecognisedItemRule().applies(item(recognised=False)))
        self.assertFalse(UnrecognisedItemRule().applies(item()))

    def test_each_rule_shows_its_own_message(self):
        io = ScriptedIOManager(["dog leash", "wallet"])
        self.assertEqual(ProhibitedItemRule().ask(io, item(), "found"), {"item_type": "dog leash"})
        self.assertEqual(UnrecognisedItemRule().ask(io, item(), "lost"), {"item_type": "wallet"})
        self.assertIn("cannot be reported here", io.text)
        self.assertIn("could not recognise that as an item", io.text)
        self.assertIn("What kind of item did you lose?", io.prompts[1])

    def test_back(self):
        self.assertIsNone(ProhibitedItemRule().ask(ScriptedIOManager(["back"]), item(), "found"))

class TestVagueLocationRule(unittest.TestCase):
    def test_applies_only_with_a_vague_place(self):
        rule = VagueLocationRule()
        self.assertTrue(rule.applies(item(where="outside my house", specific=False)))
        self.assertFalse(rule.applies(item()))
        self.assertFalse(rule.applies(item(where=None, specific=False)))

    def test_enter_cannot_skip(self):
        io = ScriptedIOManager(["", "Punggol MRT station"])
        answers = VagueLocationRule().ask(io, item(where="outside my house", specific=False), "found")
        self.assertEqual(answers, {"location": "Punggol MRT station"})
        self.assertIn("'outside my house' is too vague", io.text)
        self.assertIn("Please enter a location of up to 30 words.", io.text)

class TestFutureDateRule(unittest.TestCase):
    def setUp(self):
        self.rule = FutureDateRule(clock=lambda: NOW)

    def test_applies(self):
        self.assertTrue(self.rule.applies(item(when="2026-10-14T14:00")))
        self.assertFalse(self.rule.applies(item(when="2026-10-14T12:30")))   # within 1 hour
        self.assertFalse(self.rule.applies(item(when="2026-10-13T15:00")))
        self.assertFalse(self.rule.applies(item(when=None)))

    def test_ask_and_give_up(self):
        io = ScriptedIOManager(["yesterday 3pm"])
        future = item(when="2026-10-21T15:00")
        self.assertEqual(self.rule.ask(io, future, "found"), {"datetime": "yesterday 3pm"})
        self.assertIn("'2026-10-21T15:00' is in the future", io.text)
        self.assertTrue(self.rule.give_up(future).when.is_empty())

class TestMissingFieldsRule(unittest.TestCase):
    def setUp(self):
        self.rule = MissingFieldsRule()

    def test_flagged_fields(self):
        self.assertEqual(self.rule.flagged(item()), [])
        unsure = item(colour=None, missing=["item_colour"]).with_field(
            "datetime", ExtractedField("2026-10-10T12:00", 0.45))
        self.assertEqual(self.rule.flagged(unsure), ["item_colour", "datetime"])

    def test_asks_missing_and_confirms_unsure(self):
        io = ScriptedIOManager(["dark grey", ""])
        target = item(colour=None, missing=["item_colour"], colour_conf=0.95).with_field(
            "location", ExtractedField("SIT library", 0.4))
        answers = self.rule.ask(io, target, "found")
        self.assertEqual(answers, {"item_colour": "dark grey", "location": "SIT library (confirmed by the user)"})

    def test_skips_fields_other_rules_asked(self):
        io = ScriptedIOManager([])
        target = item(where="my house", specific=False).with_field(
            "location", ExtractedField("my house", 0.3))
        self.assertEqual(self.rule.ask(io, target, "found", skip_fields=("location",)), {})
        self.assertEqual(io.output, [])

    def test_back(self):
        self.assertIsNone(self.rule.ask(ScriptedIOManager(["back"]), item(colour=None), "found"))

class TestColourChoiceCorrection(unittest.TestCase):
    def setUp(self):
        self.correction = ColourChoiceCorrection()

    def test_is_an_item_correction(self):
        self.assertIsInstance(self.correction, ItemCorrection)

    def test_options_deduplicated(self):
        target = item(colours=["black", "Red", "BLACK", " "])
        self.assertEqual(self.correction.options(target), ["black", "Red"])
        self.assertTrue(self.correction.applies(target))
        self.assertFalse(self.correction.applies(item()))

    def test_choice_is_stored_with_full_confidence(self):
        io = ScriptedIOManager(["7", "2"])
        target = item(colours=["black", "red"], colour_conf=0.7, missing=["item_colour"])
        fixed = self.correction.correct(io, target)
        self.assertEqual((fixed.colour.text, fixed.colour.confidence), ("red", 1.0))
        self.assertEqual(fixed.flags.colour_options, ("red",))
        self.assertNotIn("item_colour", fixed.flags.missing_fields)
        self.assertIn("Invalid choice.", io.text)
        self.assertEqual(target.colour.text, "black")    # original unchanged

    def test_back(self):
        self.assertIsNone(self.correction.correct(ScriptedIOManager(["back"]), item(colours=["black", "red"])))

if __name__ == "__main__":
    unittest.main()