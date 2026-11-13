"""Full workflows: LogicManager and LostAndFoundApp with MockAIManager, scripted IO and a temp file.

No live API: every Gemini reply is a hard-coded sample.
"""
import os
import tempfile
import unittest
from datetime import datetime
from unittest import mock
from main import LostAndFoundApp
from managers.ai.mock_ai_manager import MockAIManager
from managers.base.base_data_manager import BaseDataManager
from managers.data.json_data_manager import JsonDataManager
from managers.logic.logic_manager import LogicManager
from models import FoundItem, Item
from tests.helpers import SampleReplies, ScriptedIOManager

ai_reply = SampleReplies.ai_reply

NOW = datetime(2026, 10, 14, 12, 0)
PAST = "2026-10-13T15:00"
FUTURE = "2026-10-21T15:00"
DETAILS = ["black Samsung phone", "yesterday 3pm", "SIT Punggol food court", "y"]

class WorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "found_items.json")
        self.data = JsonDataManager(self.path, notify=lambda m: None)
        self.ai = MockAIManager(notify=self.ai_notes_append)
        self.ai_notes = []
        self.io = ScriptedIOManager()
        self.logic = LogicManager(self.ai, self.data, self.io, clock=lambda: NOW)

    def ai_notes_append(self, message):
        self.ai_notes.append(message)

    def store(self, **changes) -> FoundItem:
        return self.data.add(Item.from_ai_response("found", ai_reply(**changes)))

    def run_report(self, report_type, replies, answers):
        self.ai.queue(*replies)
        self.io.add_answers(*answers)
        return self.logic.process_report(report_type)

class TestProcessReport(WorkflowTestCase):
    def test_clear_report_needs_no_follow_up(self):
        result = self.run_report("found", [ai_reply(when=PAST)], DETAILS)
        self.assertEqual((result.item_type.text, len(self.ai.calls)), ("phone", 1))
        self.assertNotIn("We need a few more details", self.io.text)

    def test_details_can_be_re_entered_and_confirmed(self):
        result = self.run_report("found", [ai_reply(when=PAST)], DETAILS[:3] + ["maybe", "n"] + DETAILS)
        self.assertIsNotNone(result)
        self.assertIn("Please enter y, n or b.", self.io.text)
        self.assertIn("Okay, please re-enter the details.", self.io.text)

    def test_back_at_first_question_makes_no_ai_call(self):
        self.assertIsNone(self.run_report("found", [], ["back"]))
        self.assertEqual(self.ai.calls, [])
        self.assertIn("Returning to the main menu.", self.io.text)

    def test_two_colours_user_picks_one(self):
        result = self.run_report("found", [ai_reply(when=PAST, colours=["black", "red"], colour_conf=0.7)], DETAILS + ["2"])
        self.assertEqual((result.colour.text, result.colour.confidence), ("red", 1.0))
        self.assertEqual(len(self.ai.calls), 1)

    def test_living_thing_then_gibberish_then_real_item(self):
        replies = [ai_reply(when=PAST, prohibited=True), ai_reply(when=PAST, item_type=None, description=None,
                   recognised=False, missing=["item_description", "item_type"]),
                   ai_reply(when=PAST, item_type="wallet", description="brown leather wallet")]
        result = self.run_report("found", replies, DETAILS + ["asdf", "brown leather wallet"])
        self.assertEqual(result.item_type.text, "wallet")
        self.assertIn("cannot be reported here", self.io.text)
        self.assertIn("could not recognise that as an item", self.io.text)
        self.assertEqual(self.ai.calls[1]["answers"], {"item_type": "asdf"})

    def test_item_still_rejected_after_three_rounds(self):
        dog = ai_reply(when=PAST, prohibited=True)
        self.assertIsNone(self.run_report("found", [dog] * 4, DETAILS + ["cat", "kitten", "puppy"]))
        self.assertIn("This item cannot be reported", self.io.text)

    def test_vague_place_future_date_and_missing_colour_in_one_round(self):
        first = ai_reply(when=FUTURE, where="my house", specific=False, colour=None, missing=["item_colour"])
        result = self.run_report("found", [first, ai_reply(when=PAST)],
                                 DETAILS + ["Punggol MRT station", "yesterday 3pm", "black"])
        self.assertEqual(len(self.ai.calls), 2)
        self.assertEqual(self.ai.calls[1]["answers"],
                         {"location": "Punggol MRT station", "datetime": "yesterday 3pm", "item_colour": "black"})
        self.assertIs(self.ai.calls[1]["previous"].__class__, FoundItem)
        self.assertEqual(result.when.text, PAST)

    def test_future_date_still_future_after_three_rounds_is_cleared(self):
        future = ai_reply(when=FUTURE)
        result = self.run_report("found", [future] * 4, DETAILS + ["next week", "tomorrow", "next month"])
        self.assertTrue(result.when.is_empty())
        self.assertIn("still unclear", self.io.text)

    def test_unclear_details_continue_after_three_rounds(self):
        unclear = ai_reply(when=PAST, colour=None, missing=["item_colour"])
        result = self.run_report("found", [unclear] * 4, DETAILS + ["dunno", "no idea", "not sure"])
        self.assertIsNotNone(result)
        self.assertIn("still unclear", self.io.text)

    def test_back_at_follow_up_and_colour_choice(self):
        self.assertIsNone(self.run_report("found", [ai_reply(when=PAST, colour=None)], DETAILS + ["back"]))
        self.assertIsNone(self.run_report("found", [ai_reply(when=PAST, colours=["black", "red"])], DETAILS + ["back"]))

    def test_ai_failure(self):
        self.assertIsNone(self.run_report("found", [ValueError("bad json")], DETAILS))
        self.assertIn("AI processing failed. Please try again later.", self.io.text)

    def test_ai_failure_during_follow_up(self):
        replies = [ai_reply(when=PAST, colour=None), ValueError("down")]
        self.assertIsNone(self.run_report("found", replies, DETAILS + ["black"]))
        self.assertEqual(self.data.load_all(), [])

class TestFoundAndLostWorkflows(WorkflowTestCase):
    def test_found_item_is_saved(self):
        self.ai.queue(ai_reply(when=PAST))
        self.io.add_answers(*DETAILS)
        self.logic.report_found_item()
        self.assertEqual([i.item_id for i in self.data.load_all()], ["FND-0001"])
        self.assertIn("Thank you! Your report has been saved:", self.io.text)
        self.assertIn("[FND-0001]", self.io.text)

    def test_duplicate_declined_then_accepted(self):
        self.store(when=PAST)
        self.ai.queue(ai_reply(when=PAST), ai_reply(when=PAST))
        self.io.add_answers(*DETAILS, "n", *DETAILS, "y")
        self.logic.report_found_item()
        self.assertIn("Report not saved.", self.io.text)
        self.logic.report_found_item()
        self.assertEqual(len(self.data.load_all()), 2)

    def test_lost_search_and_claim(self):
        self.store(when=PAST)
        self.ai.queue(ai_reply("lost", when="2026-10-13T14:00"))
        self.io.add_answers(*DETAILS, "9", "1", "y")
        self.logic.report_lost_item()
        self.assertIn("Displaying top five matches", self.io.text)
        self.assertIn("Invalid choice.", self.io.text)
        self.assertIn("Claimed. Quote reference FND-0001", self.io.text)
        self.assertEqual(self.data.load_all(), [])

    def test_item_claimed_elsewhere_before_confirming(self):
        self.store(when=PAST)
        self.ai.queue(ai_reply("lost", when="2026-10-13T14:00"))
        self.io.add_answers(*DETAILS, "1", "y")
        real_confirm = self.io.confirm

        def claimed_at_another_kiosk(prompt):
            self.data.delete("FND-0001")          # someone else claims it while this user reads
            return real_confirm(prompt)

        self.io.confirm = claimed_at_another_kiosk
        self.logic.report_lost_item()
        self.assertIn("Sorry, this item is no longer available.", self.io.text)
        self.assertNotIn("Claimed. Quote reference", self.io.text)

    def test_item_archived_before_confirming_is_not_claimed(self):
        stored = self.store(when=PAST)
        self.ai.queue(ai_reply("lost", when="2026-10-13T14:00"))
        self.io.add_answers(*DETAILS, "1", "y")
        stored.archive()
        with mock.patch.object(self.data, "get", return_value=stored):
            self.logic.report_lost_item()
        self.assertIn("Sorry, this item is no longer available.", self.io.text)
        self.assertEqual(len(self.data.load_all()), 1)      # archived item kept, not deleted

    def test_cancel_or_decline_keeps_the_item(self):
        self.store(when=PAST)
        self.ai.queue(ai_reply("lost", when=PAST), ai_reply("lost", when=PAST))
        self.io.add_answers(*DETAILS, "0", *DETAILS, "1", "n")
        self.logic.report_lost_item()
        self.logic.report_lost_item()
        self.assertEqual(len(self.data.load_all()), 1)

    def test_far_apart_dates_only_possible_match(self):
        self.store(when="2026-10-21T02:00")       # stored before the future-date check existed
        self.ai.queue(ai_reply("lost", when="2026-10-09T02:00"))
        self.io.add_answers(*DETAILS, "0")
        self.logic.report_lost_item()
        self.assertIn("Possible matches (less certain)", self.io.text)
        self.assertNotIn("Displaying top five matches", self.io.text)

    def test_nothing_matches(self):
        self.ai.queue(ai_reply("lost", "red foldable umbrella", "umbrella", "red", None, None, PAST, "Jurong East MRT station"))
        self.io.add_answers(*DETAILS)
        self.logic.report_lost_item()
        self.assertIn("No matching items found", self.io.text)

    def test_archiving(self):
        old, new = self.store(when=PAST), self.store(when=PAST)
        records = self.data.load_all()
        for record, reported in zip(records, ("2026-10-05T12:00", "2026-10-13T12:00")):
            self.data.update(FoundItem(record.fields, record.flags, record.item_id, reported))
        archived = self.logic.archive_expired()
        self.assertEqual([i.item_id for i in archived], [old.item_id])
        self.assertEqual([i.item_id for i in self.data.get_active()], [new.item_id])
        self.assertEqual(self.logic.archive_expired(), [])     # nothing archived twice

class BrokenDataManager(BaseDataManager):
    """A data manager whose disk always fails, to test error handling."""

    def load_all(self):
        raise OSError("disk unavailable")

    def add(self, item):
        raise OSError("disk unavailable")

    def update(self, item):
        raise OSError("disk unavailable")

    def delete(self, item_id):
        raise OSError("disk unavailable")

class TestApp(WorkflowTestCase):
    def test_menu_loop_found_then_lost_then_exit(self):
        app = LostAndFoundApp(self.io, self.logic)
        self.ai.queue(ai_reply(when=PAST), ai_reply("lost", when="2026-10-13T14:00"))
        self.io.add_answers("5", "2", *DETAILS, "1", *DETAILS, "1", "y", "3")
        app.run()
        self.assertIn("Invalid choice. Enter 1, 2 or 3.", self.io.text)
        self.assertIn("Claimed. Quote reference FND-0001", self.io.text)
        self.assertEqual(self.io.output[-1], "Goodbye!")
        self.assertEqual(self.io.unused_answers, [])

    def test_disk_errors_become_messages(self):
        logic = LogicManager(MockAIManager([ai_reply(when=PAST)], notify=lambda m: None),
                             BrokenDataManager(), self.io, clock=lambda: NOW)
        self.io.add_answers("2", *DETAILS, "3")
        LostAndFoundApp(self.io, logic).run()
        self.assertIn("Could not update the data file: disk unavailable", self.io.text)
        self.assertIn("Could not read or save the data file: disk unavailable. Nothing was saved.", self.io.text)

if __name__ == "__main__":
    unittest.main()