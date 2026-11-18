"""EscalationDemoSeeder: the example found items load into either store and give the expected email."""
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from managers.ai.mock_ai_manager import MockAIManager
from managers.data.json_data_manager import JsonDataManager
from managers.data.sqlite_data_manager import SqliteDataManager
from managers.logic.escalation_service import EscalationService
from managers.logic.logic_manager import LogicManager
from managers.samples.escalation_demo_seeder import EscalationDemoSeeder
from seed_escalation_demo import SeedEscalationDemoCommand
from tests.helpers import RecordingEmailManager, ScriptedIOManager

NOW = datetime(2026, 11, 16, 18, 0)
EMAILED = [f"FND-DEMO-{n:03d}" for n in range(1, 8)]
NOT_EMAILED = [f"FND-DEMO-{n:03d}" for n in range(8, 14)]


class TestEscalationDemoSeeder(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def store(self, kind):
        if kind == "json":
            return JsonDataManager(os.path.join(self.temp.name, "found.json"), notify=lambda m: None)
        return SqliteDataManager(os.path.join(self.temp.name, "found_items.db"), notify=lambda m: None)

    def test_seeds_any_store_once_and_gives_the_expected_escalation(self):              # T46
        for kind in ("sqlite", "json"):
            with self.subTest(kind=kind):
                data = self.store(kind)
                seeder = EscalationDemoSeeder(data, clock=lambda: NOW)
                self.assertEqual(seeder.seed(), 13)
                self.assertEqual(seeder.seed(), 0)
                logic = LogicManager(MockAIManager(notify=lambda m: None), data, ScriptedIOManager(),
                                     clock=lambda: NOW)
                archived = logic.archive_expired()
                self.assertEqual(sorted(i.item_id for i in archived),
                                 ["FND-DEMO-008", "FND-DEMO-009", "FND-DEMO-010"])
                self.assertEqual(len(data.get_active()), 10)

                email, clock = RecordingEmailManager(), [NOW]
                service = EscalationService(data, email, clock=lambda: clock[0])
                self.assertEqual(service.check(), 7)
                self.assertEqual(service.check(), 0)                  # at most once per day
                for reference in EMAILED:
                    self.assertIn(reference, email.sent[0].text)
                for reference in NOT_EMAILED:
                    self.assertNotIn(reference, email.sent[0].text)
                self.assertEqual(seeder.seed(), 0)                    # rerun never resets escalated items
                self.assertEqual(data.get("FND-DEMO-001").escalated_at, "2026-11-16T18:00")
                clock[0] = NOW + timedelta(days=1)
                self.assertEqual(service.check(), 7)                  # the passport is exactly 7 days old
                self.assertNotIn("FND-DEMO-012", email.sent[1].text)

    def test_command_reports_the_result_and_turns_errors_into_messages(self):          # T47
        data = self.store("json")
        notes = []
        self.assertEqual(SeedEscalationDemoCommand(EscalationDemoSeeder(data), notes.append).run(), 0)
        self.assertIn("Added 13 example found item(s). Existing ones were skipped.", notes[0])

        class BrokenSeeder(EscalationDemoSeeder):
            def seed(self):
                raise OSError("disk unavailable")

        notes.clear()
        self.assertEqual(SeedEscalationDemoCommand(BrokenSeeder(data), notes.append).run(), 1)
        self.assertEqual(notes, ["Could not load the demo data: disk unavailable"])


if __name__ == "__main__":
    unittest.main()
