"""JsonDataManager: storage in a temporary folder. No API calls."""
import json
import os
import tempfile
import unittest

from managers.base.base_data_manager import BaseDataManager
from managers.data.json_data_manager import JsonDataManager
from models import FoundItem, Item
from tests.helpers import SampleReplies

ai_reply = SampleReplies.ai_reply


class TestJsonDataManager(unittest.TestCase):
    @staticmethod
    def found(**changes) -> FoundItem:
        """A new, unsaved found item from a sample reply."""
        return Item.from_ai_response("found", ai_reply(**changes))

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "found_items.json")
        self.notes = []
        self.data = JsonDataManager(self.path, notify=self.notes.append)

    def test_is_a_base_data_manager(self):
        self.assertIsInstance(self.data, BaseDataManager)

    def test_missing_file_means_no_items(self):
        self.assertEqual(self.data.load_all(), [])

    def test_add_assigns_sequential_ids(self):
        first, second = self.data.add(self.found()), self.data.add(self.found(item_type="wallet"))
        self.assertEqual((first.item_id, second.item_id), ("FND-0001", "FND-0002"))
        self.assertIsNotNone(first.reported_at)
        self.assertEqual([i.item_id for i in self.data.load_all()], ["FND-0001", "FND-0002"])

    def test_next_id_continues_after_highest(self):
        self.data.add(self.found())
        self.data.add(self.found())
        self.data.delete("FND-0001")
        self.assertEqual(self.data.add(self.found()).item_id, "FND-0003")

    def test_data_survives_a_new_manager(self):
        self.data.add(self.found())
        reloaded = JsonDataManager(self.path).load_all()
        self.assertEqual((reloaded[0].item_id, reloaded[0].item_type.text), ("FND-0001", "phone"))

    def test_get_one_item_by_id(self):
        self.data.add(self.found())
        wallet = self.data.add(self.found(item_type="wallet"))
        self.assertEqual(self.data.get("FND-0002").to_dict(), wallet.to_dict())
        self.assertIsNone(self.data.get("FND-9999"))
        wallet.archive()
        self.data.update(wallet)
        self.assertEqual(self.data.get("FND-0002").status, "archived")    # archived items can still be read
        self.data.delete("FND-0002")
        self.assertIsNone(self.data.get("FND-0002"))

    def test_update_saves_archived_status(self):
        item = self.data.add(self.found())
        item.archive()
        self.assertTrue(self.data.update(item))
        self.assertEqual(self.data.load_all()[0].status, "archived")
        self.assertEqual(self.data.get_active(), [])

    def test_update_unknown_item(self):
        self.assertFalse(self.data.update(FoundItem(item_id="FND-9999")))

    def test_delete(self):
        self.data.add(self.found())
        self.assertTrue(self.data.delete("FND-0001"))
        self.assertFalse(self.data.delete("FND-0001"))
        self.assertEqual(self.data.load_all(), [])

    def test_corrupt_file_is_backed_up_not_overwritten(self):
        with open(self.path, "w", encoding="utf-8") as file:
            file.write('[{"item_id": "FND-0001", "item_type": {"value": "pho')
        self.assertEqual(self.data.load_all(), [])
        backups = [n for n in os.listdir(self.folder) if ".corrupt-" in n]
        self.assertEqual(len(backups), 1)
        self.assertFalse(os.path.exists(self.path))
        self.assertIn("unreadable", self.notes[0])

    def test_wrong_shape_counts_as_corrupt(self):
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump({"not": "a list"}, file)
        self.assertEqual(self.data.load_all(), [])
        self.assertTrue(any(".corrupt-" in n for n in os.listdir(self.folder)))

    def test_crash_during_save_leaves_old_file_intact(self):
        self.data.add(self.found())
        real_replace = os.replace

        def power_cut(src, dst):
            if src.endswith(".tmp"):
                raise OSError("simulated power loss")
            real_replace(src, dst)

        os.replace = power_cut
        try:
            with self.assertRaises(OSError):
                self.data.add(self.found(item_type="wallet"))
        finally:
            os.replace = real_replace
        self.assertEqual([i.item_id for i in self.data.load_all()], ["FND-0001"])

    def test_reads_phase1_records(self):
        record = {**ai_reply(), "item_id": "FND-0007", "reported_at": "2026-10-10T01:39", "status": "active"}
        del record["location_specific"]
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump([record], file)
        item = self.data.load_all()[0]
        self.assertEqual((item.item_id, item.flags.location_specific), ("FND-0007", True))

    def test_file_path_is_read_only(self):
        with self.assertRaises(AttributeError):
            self.data.file_path = "elsewhere.json"


if __name__ == "__main__":
    unittest.main()
