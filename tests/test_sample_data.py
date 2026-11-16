"""Example data: the shipped sample file, the loader's checks and the seeder. No API calls."""
import json
import os
import tempfile
import unittest
from datetime import datetime

from managers.data.sqlite_data_manager import SqliteDataManager
from managers.logic.matching_service import MatchingService
from managers.samples.sample_data_loader import SampleDataLoader
from managers.samples.sample_data_seeder import SampleDataSeeder
from models import FoundItem, Item
from seed_data import SeedDataCommand
from tests.helpers import SampleReplies

NOW = datetime(2026, 11, 4, 12, 30)


class SampleFiles:
    """Writes small sample files into a temporary folder."""

    @staticmethod
    def entry(**changes):
        entry = {"description": "black Samsung phone", "item_type": "phone", "colour": "black",
                 "brand": "Samsung", "unique_info": None, "location": "Punggol MRT station",
                 "found_days_ago": 1, "found_time": "15:00"}
        entry.update(changes)
        return entry

    @staticmethod
    def write(entries) -> str:
        path = os.path.join(tempfile.mkdtemp(), "samples.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(entries, file)
        return path


entry = SampleFiles.entry
write = SampleFiles.write


class TestShippedSamples(unittest.TestCase):
    def setUp(self):
        self.items = SampleDataLoader(clock=lambda: NOW).load()

    def test_every_sample_is_valid_and_varied(self):
        self.assertGreaterEqual(len(self.items), 20)
        self.assertTrue(all(isinstance(item, FoundItem) and item.item_id is None for item in self.items))
        self.assertGreaterEqual(len({item.item_type.text for item in self.items}), 15)

    def test_every_sample_is_recent_and_not_in_the_future(self):
        for item in self.items:
            self.assertLessEqual(item.occurred_at, NOW, item.description.text)
            self.assertLess((NOW - item.occurred_at).days, 7, item.description.text)

    def test_samples_are_unique(self):
        keys = [SampleDataSeeder.key(item) for item in self.items]
        self.assertEqual(len(keys), len(set(keys)))

    def test_a_lost_search_finds_the_right_sample(self):
        stored = [FoundItem(i.fields, i.flags, f"FND-{n:04d}", "2026-11-04T12:00")
                  for n, i in enumerate(self.items, start=1)]
        lost = Item.from_ai_response("lost", SampleReplies.ai_reply(
            "lost", "black Samsung Galaxy S24", "phone", "black", "Samsung", None,
            "2026-11-03T13:00", "SIT Punggol food court"))
        top, _ = MatchingService().find_matches(lost, stored)
        self.assertEqual(top[0].item.description.text, "Samsung Galaxy S24 with cracked screen protector")


class TestSampleDataLoader(unittest.TestCase):
    def load(self, entries):
        return SampleDataLoader(write(entries), clock=lambda: NOW).load()

    def test_relative_dates(self):
        items = self.load([entry(found_days_ago=2, found_time="08:45"), entry(found_days_ago=0, found_time="23:00")])
        self.assertEqual(items[0].when.text, "2026-11-02T08:45")
        self.assertEqual(items[1].when.text, "2026-11-04T12:30")      # later today -> capped at now

    def test_values_and_confidence(self):
        item = self.load([entry()])[0]
        self.assertEqual((item.item_type.text, item.brand.text, item.colour.confidence), ("phone", "Samsung", 0.95))
        self.assertTrue(item.unique_info.is_empty())
        self.assertEqual(item.unique_info.confidence, 0.0)

    def test_bad_entries_name_the_sample(self):
        cases = [
            ([entry(), {"description": "x"}], "Sample #2 is missing"),
            ([entry(item_type="  ")], "item_type must be non-empty text"),
            ([entry(brand=5)], "brand must be text or null"),
            ([entry(found_days_ago=7)], "found_days_ago must be a whole number"),
            ([entry(found_days_ago=True)], "found_days_ago must be a whole number"),
            ([entry(found_time="3pm")], "found_time must look like 15:00"),
            (["not an object"], "Sample #1 must be an object"),
            ({"not": "a list"}, "must contain a list"),
        ]
        for entries, message in cases:
            with self.assertRaises(ValueError) as caught:
                self.load(entries)
            self.assertIn(message, str(caught.exception))

    def test_schema_validator_is_used(self):
        class RejectAll:
            def validate(self, data):
                return ["rejected for the test"]

        loader = SampleDataLoader(write([entry()]), clock=lambda: NOW, validator=RejectAll())
        with self.assertRaises(ValueError) as caught:
            loader.load()
        self.assertIn("does not match the AI schema: rejected for the test", str(caught.exception))


class TestSampleDataSeeder(unittest.TestCase):
    def setUp(self):
        self.data = SqliteDataManager(os.path.join(tempfile.mkdtemp(), "found_items.db"), notify=lambda m: None)
        self.loader = SampleDataLoader(clock=lambda: NOW)

    def test_seed_once_then_skip(self):
        count = len(self.loader.load())
        self.assertEqual(SampleDataSeeder(self.loader, self.data).seed(), (count, 0))
        self.assertEqual(SampleDataSeeder(self.loader, self.data).seed(), (0, count))
        self.assertEqual(len(self.data.load_all()), count)
        self.assertEqual(self.data.get("FND-0001").description.text,
                         "Samsung Galaxy S24 with cracked screen protector")

    def test_archived_samples_are_added_again(self):
        loader = SampleDataLoader(write([entry()]), clock=lambda: NOW)
        SampleDataSeeder(loader, self.data).seed()
        old = self.data.get("FND-0001")
        old.archive()
        self.data.update(old)
        self.assertEqual(SampleDataSeeder(loader, self.data).seed(), (1, 0))

    def test_command_reports_result_and_errors(self):
        notes = []
        self.assertEqual(SeedDataCommand(SampleDataSeeder(self.loader, self.data), notes.append).run(), 0)
        self.assertIn("Added 24 sample found item(s); 0 were already stored.", notes[0])
        broken = SampleDataSeeder(SampleDataLoader(write([{"x": 1}])), self.data)
        self.assertEqual(SeedDataCommand(broken, notes.append).run(), 1)
        self.assertIn("Could not load the sample data", notes[-1])


if __name__ == "__main__":
    unittest.main()
