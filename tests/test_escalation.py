"""EscalationService: the 7-day rule for HIGH_VALUE found items, the daily limit and the email gating.

Runs on both storage backends. No live API: emails go to a recording stand-in; the clock is fixed.
"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from managers.data.json_data_manager import JsonDataManager
from managers.data.sqlite_data_manager import SqliteDataManager
from managers.logic.escalation_service import EscalationService
from models import FoundItem
from models.constants import DATETIME_FORMAT
from tests.helpers import RecordingEmailManager, SampleReplies

found_item = SampleReplies.found_item
NOW = datetime(2026, 11, 16, 18, 0)


class FailingUpdateJsonDataManager(JsonDataManager):
    """A JSON store that reads fine but cannot save changes."""

    def update(self, item):
        raise OSError("disk full")


class FailingReadJsonDataManager(JsonDataManager):
    """A JSON store whose disk has failed."""

    def get_active(self):
        raise OSError("disk unavailable")


class EscalationContract:
    """The escalation behaviour, run against each storage backend."""

    def make(self):
        raise NotImplementedError

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.data = self.make()
        self.email = RecordingEmailManager()
        self.notes = []
        self.now = NOW
        self.service = self.new_service(self.data)

    def new_service(self, data):
        return EscalationService(data, self.email, self.notes.append, clock=lambda: self.now)

    def add(self, days_ago=None, value=1000, sensitive=False, *, reported_at=None, status=FoundItem.ACTIVE):
        """Store a found item reported days_ago before NOW (or at reported_at)."""
        if reported_at is None and days_ago is not None:
            reported_at = (NOW - timedelta(days=days_ago)).strftime(DATETIME_FORMAT)
        number = len(self.data.load_all()) + 1
        return self.data.add(found_item(value, sensitive, item_id=f"FND-{number:04d}",
                                        reported_at=reported_at, status=status))

    def ids(self, items):
        return [item.item_id for item in items]

    def stored_escalation(self, item):
        return self.make().get(item.item_id).escalated_at

    def test_only_active_old_high_value_items_are_due(self):                            # T32
        high = self.add(8)
        sensitive = self.add(8, None, True)
        self.add(8, 50)                                         # ordinary
        self.add(6)                                             # too recent
        plain = self.add(8)
        self.data.update(FoundItem(plain.fields, plain.flags, plain.item_id, plain.reported_at))   # not assessed
        self.add(8, status=FoundItem.ARCHIVED)                  # archived
        self.assertEqual(self.ids(self.service.due(NOW)), [high.item_id, sensitive.item_id])

    def test_exactly_seven_days_is_not_yet_due(self):                                   # T33
        self.add(reported_at="2026-11-09T18:00")
        self.assertEqual(self.service.due(NOW), [])
        self.assertEqual(len(self.service.due(NOW + timedelta(seconds=1))), 1)

    def test_one_minute_more_is_due(self):                                              # T34
        self.add(reported_at="2026-11-09T17:59")
        self.assertEqual(len(self.service.due(NOW)), 1)

    def test_missing_or_unreadable_report_time_is_never_due(self):                     # T35
        self.add(reported_at=None)
        self.add(reported_at="not a date")
        self.assertEqual(self.service.due(NOW + timedelta(days=365)), [])
        self.assertEqual(self.service.check(), 0)

    def test_nothing_due_sends_no_email(self):                                          # T36
        self.add(8, 50)
        self.assertEqual(self.service.check(), 0)
        self.assertEqual(self.email.sent, [])

    def test_one_email_covers_every_due_item_and_marks_them(self):                     # T37
        first, second = self.add(9), self.add(8, None, True)
        self.assertEqual(self.service.check(), 2)
        self.assertEqual(len(self.email.sent), 1)
        self.assertIn("2 unclaimed", self.email.sent[0].subject)
        for item in (first, second):
            self.assertIn(item.item_id, self.email.sent[0].text)
            self.assertEqual(self.stored_escalation(item), "2026-11-16T18:00")

    def test_at_most_one_reminder_per_day_even_after_a_restart(self):                  # T38
        self.add(9)
        self.add(8, None, True)
        self.assertEqual(self.service.check(), 2)
        self.assertEqual(self.service.check(), 0)
        self.assertEqual(self.new_service(self.make()).check(), 0)      # app restarted
        self.now = NOW.replace(hour=23, minute=59)
        self.assertEqual(self.service.check(), 0)
        self.assertEqual(len(self.email.sent), 1)

    def test_next_calendar_day_reminds_again(self):                                     # T39
        item = self.add(9)
        self.add(8, None, True)
        self.service.check()
        self.now = datetime(2026, 11, 17, 0, 1)
        self.assertEqual(self.service.check(), 2)
        self.assertEqual(len(self.email.sent), 2)
        self.assertEqual(self.stored_escalation(item), "2026-11-17T00:01")

    def test_item_due_later_the_same_day_is_sent_alone(self):                          # T40
        first = self.add(8)
        later = self.add(reported_at=(NOW - timedelta(days=7) + timedelta(hours=1)).strftime(DATETIME_FORMAT))
        self.assertEqual(self.service.check(), 1)
        self.now = NOW + timedelta(hours=2)
        self.assertEqual(self.service.check(), 1)
        self.assertIn(later.item_id, self.email.sent[1].text)
        self.assertNotIn(first.item_id, self.email.sent[1].text)

    def test_claimed_item_drops_out(self):                                              # T41
        claimed, kept = self.add(9), self.add(8)
        self.service.check()
        self.data.delete(claimed.item_id)                       # a claim deletes the record
        self.now = NOW + timedelta(days=1)
        self.assertEqual(self.ids(self.service.due(self.now)), [kept.item_id])
        self.assertEqual(self.service.check(), 1)
        self.assertNotIn(claimed.item_id, self.email.sent[1].text)

    def test_failed_send_records_nothing_and_is_tried_again(self):                     # T42
        item = self.add(9)
        self.email.accepts = False
        self.assertEqual(self.service.check(), 0)
        self.assertIsNone(self.stored_escalation(item))
        self.email.accepts = True
        self.assertEqual(self.service.check(), 1)


class TestEscalationJson(EscalationContract, unittest.TestCase):
    def make(self):
        return JsonDataManager(os.path.join(self.folder, "found_items.json"), notify=lambda m: None)


class TestEscalationSqlite(EscalationContract, unittest.TestCase):
    def make(self):
        return SqliteDataManager(os.path.join(self.folder, "found_items.db"), notify=lambda m: None)


class TestEscalationStorageErrors(unittest.TestCase):                                   # T43
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "found_items.json")
        self.email = RecordingEmailManager()
        self.notes = []

    def test_read_error_becomes_a_message(self):
        service = EscalationService(FailingReadJsonDataManager(self.path), self.email, self.notes.append,
                                    clock=lambda: NOW)
        self.assertEqual(service.check(), 0)
        self.assertIn("disk unavailable", self.notes[-1])
        self.assertEqual(self.email.sent, [])

    def test_save_error_after_sending_becomes_a_message(self):
        data = FailingUpdateJsonDataManager(self.path, notify=lambda m: None)
        data.add(found_item(2500, item_id="FND-0001", reported_at="2026-11-01T09:30"))
        service = EscalationService(data, self.email, self.notes.append, clock=lambda: NOW)
        self.assertEqual(service.check(), 0)
        self.assertEqual(len(self.email.sent), 1)
        self.assertIn("Could not check or record found-item escalations: disk full", self.notes[-1])


if __name__ == "__main__":
    unittest.main()
