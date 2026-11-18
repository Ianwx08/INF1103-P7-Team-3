"""Full flow: report a high-value found item -> store -> age -> escalate -> claim; and the start-up check.

No live API: MockAIManager with hard-coded sample replies, a recording email manager, scripted IO,
temporary folders and a clock the test moves forward. Runs on both storage backends.
"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from main import LostAndFoundApp
from managers.ai.mock_ai_manager import MockAIManager
from managers.data.json_data_manager import JsonDataManager
from managers.data.sqlite_data_manager import SqliteDataManager
from managers.logic.escalation_service import EscalationService
from managers.logic.logic_manager import LogicManager
from models.constants import DATETIME_FORMAT
from tests.helpers import RecordingEmailManager, SampleReplies, ScriptedIOManager

DETAILS = ["black Samsung phone", "yesterday 3pm", "SIT Punggol food court", "y"]
UMBRELLA = ["red foldable umbrella", "yesterday 3pm", "Jurong East MRT station", "y"]


class TestFoundEscalationWorkflow(unittest.TestCase):                                  # T55
    BACKENDS = {
        "json": lambda folder: JsonDataManager(os.path.join(folder, "found_items.json"), notify=lambda m: None),
        "sqlite": lambda folder: SqliteDataManager(os.path.join(folder, "found_items.db"), notify=lambda m: None),
    }

    def test_report_store_age_escalate_claim(self):
        for name, make in self.BACKENDS.items():
            with self.subTest(backend=name):
                self.run_flow(make, tempfile.mkdtemp())

    def run_flow(self, make, folder):
        # Storage stamps reported_at with the real clock, so the test clock starts at the real time.
        start = datetime.now().replace(second=0, microsecond=0)
        clock = [start]
        found_at = start - timedelta(days=1)
        data, email, io = make(folder), RecordingEmailManager(), ScriptedIOManager()
        ai = MockAIManager(notify=lambda m: None)
        logic = LogicManager(ai, data, io, clock=lambda: clock[0])

        def service(store):
            return EscalationService(store, email, notify=lambda m: None, clock=lambda: clock[0])

        # 1. A high-value phone and an ordinary umbrella are reported found through the menu.
        ai.queue(SampleReplies.found_reply(2500, when=found_at.strftime(DATETIME_FORMAT)),
                 SampleReplies.found_reply(50, description="red foldable umbrella", item_type="umbrella",
                                           colour="red", brand=None, where="Jurong East MRT station",
                                           when=found_at.strftime(DATETIME_FORMAT)))
        io.add_answers("2", *DETAILS, "2", *UMBRELLA, "4")
        LostAndFoundApp(io, logic).run()
        self.assertIn("Category: HIGH_VALUE. Value: S$2,500.00 (AI estimate).", io.text)
        self.assertIn("Category: ORDINARY. Value: S$50.00 (AI estimate).", io.text)
        phone = make(folder).get("FND-0001")
        self.assertEqual((phone.assessment.estimated_value_sgd, phone.value_category), (2500, "HIGH_VALUE"))

        # 2. Not yet seven days: nothing to email.
        self.assertEqual(service(data).check(), 0)

        # 3. Just over seven days later: only the ordinary item is archived.
        clock[0] = start + timedelta(days=7, minutes=2)
        self.assertEqual([i.item_id for i in logic.archive_expired()], ["FND-0002"])
        self.assertEqual([i.item_id for i in data.get_active()], ["FND-0001"])
        shown_before = len(io.output)
        io.add_answers("1")
        logic.view_stored_items()
        overview = "\n".join(io.output[shown_before:])
        self.assertIn("[FND-0001]", overview)
        self.assertNotIn("[FND-0002]", overview)

        # 4. The admins are emailed about the phone, and the time is stored.
        self.assertEqual(service(data).check(), 1)
        self.assertEqual(len(email.sent), 1)
        self.assertIn("FND-0001", email.sent[0].text)
        self.assertNotIn("FND-0002", email.sent[0].text)
        self.assertEqual(make(folder).get("FND-0001").escalated_at, clock[0].strftime(DATETIME_FORMAT))

        # 5. A restart the same day sends nothing.
        self.assertEqual(service(make(folder)).check(), 0)
        self.assertEqual(len(email.sent), 1)

        # 6. The next day it is reminded again.
        clock[0] += timedelta(days=1)
        self.assertEqual(service(data).check(), 1)
        self.assertEqual(len(email.sent), 2)

        # 7. The owner searches and claims it; nothing about the search is saved.
        calls_before = len(ai.calls)
        ai.queue(SampleReplies.ai_reply("lost", when=(found_at - timedelta(hours=2)).strftime(DATETIME_FORMAT)))
        io.add_answers(*DETAILS, "1", "y")
        logic.report_lost_item()
        self.assertIn("Claimed. Quote reference FND-0001", io.text)
        self.assertIsNone(make(folder).get("FND-0001"))
        self.assertEqual(make(folder).get_active(), [])
        self.assertEqual(len(ai.calls) - calls_before, 1)
        self.assertEqual(len(os.listdir(folder)), 1)               # only the found-items store

        # 8. The claimed item is never emailed again.
        clock[0] += timedelta(days=1)
        self.assertEqual(service(data).check(), 0)
        self.assertEqual(len(email.sent), 2)


class TestStartup(unittest.TestCase):                                                   # T56
    def test_default_app_checks_escalations_once_after_building_managers(self):
        with patch("main.ConsoleIOManager"), patch("main.DataManagerFactory") as factory, \
             patch("main.GeminiAIManager"), patch("main.LogicManager"), \
             patch("main.BrevoEmailManager") as email, patch("main.EscalationService") as service:
            app = LostAndFoundApp.create_default()
            data = factory.return_value.create.return_value
            self.assertEqual(service.call_args.args[:2], (data, email.return_value))
            service.return_value.check.assert_called_once()
            self.assertIsInstance(app, LostAndFoundApp)

    def test_failed_initialization_does_not_send(self):
        with patch("main.ConsoleIOManager"), \
             patch("main.DataManagerFactory", side_effect=ValueError("bad config")), \
             patch("main.BrevoEmailManager") as email:
            with self.assertRaises(ValueError):
                LostAndFoundApp.create_default()
            email.assert_not_called()


if __name__ == "__main__":
    unittest.main()
