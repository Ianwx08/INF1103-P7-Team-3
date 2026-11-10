"""Unit tests for models/item.py. No API calls."""
import unittest
from datetime import datetime

from models import AIFlags, ExtractedField, FoundItem, Item, LostItem

# A validated Gemini reply, as ai_manager will hand it over.
SAMPLE_AI_REPLY = {
    "report_type": "found",
    "item_description": {"value": "Samsung Galaxy S25", "confidence": 0.98},
    "item_type": {"value": "phone", "confidence": 0.95},
    "item_colour": {"value": "black", "confidence": 1.0},
    "item_brand": {"value": "Samsung", "confidence": 1.0},
    "item_unique_info": {"value": None, "confidence": 0.0},
    "datetime": {"value": "2026-10-10T15:00", "confidence": 0.95},
    "location": {"value": "SIT Punggol food court", "confidence": 0.95},
    "colour_options": ["black"],
    "prohibited_item": False,
    "item_recognised": True,
    "location_specific": True,
    "missing_fields": [],
    "overall_confidence": 0.95,
}

# A record exactly as the Phase 1 app stored it, before the newer flags existed.
PHASE1_RECORD = {
    "report_type": "found",
    "item_description": {"value": "iPhone 17 Pro Max", "confidence": 0.95},
    "item_type": {"value": "phone", "confidence": 0.95},
    "item_colour": {"value": "black", "confidence": 0.95},
    "item_brand": {"value": "Apple", "confidence": 0.85},
    "item_unique_info": {"value": None, "confidence": 0.0},
    "datetime": {"value": "2026-10-10T00:00", "confidence": 0.9},
    "location": {"value": "AMK Hub", "confidence": 0.95},
    "colour_options": ["black"],
    "prohibited_item": False,
    "item_recognised": True,
    "missing_fields": [],
    "overall_confidence": 0.9,
    "item_id": "FND-0002",
    "reported_at": "2026-10-10T01:39",
    "status": "active",
}


class TestExtractedField(unittest.TestCase):
    def test_text_trims_and_handles_none(self):
        self.assertEqual(ExtractedField("  black ", 1.0).text, "black")
        self.assertEqual(ExtractedField(None, 0.0).text, "")
        self.assertTrue(ExtractedField().is_empty())

    def test_from_dict_tolerates_bad_input(self):
        self.assertEqual(ExtractedField.from_dict(None), ExtractedField())
        self.assertEqual(ExtractedField.from_dict({"value": "x", "confidence": True}).confidence, 0.0)
        self.assertEqual(ExtractedField.from_dict({"value": "x", "confidence": "high"}).confidence, 0.0)

    def test_is_immutable(self):
        field = ExtractedField("black", 1.0)
        with self.assertRaises(Exception):
            field.value = "red"


class TestItemHierarchy(unittest.TestCase):
    def test_item_is_abstract(self):
        with self.assertRaises(TypeError):
            Item()

    def test_polymorphic_report_type(self):
        items = [LostItem(), FoundItem()]
        self.assertEqual([item.report_type for item in items], ["lost", "found"])

    def test_factory_picks_the_subclass_from_the_menu_choice(self):
        self.assertIsInstance(Item.from_ai_response("lost", SAMPLE_AI_REPLY), LostItem)
        self.assertIsInstance(Item.from_ai_response("found", SAMPLE_AI_REPLY), FoundItem)
        with self.assertRaises(ValueError):
            Item.from_ai_response("stolen", SAMPLE_AI_REPLY)

    def test_fields_are_read_through_properties(self):
        item = Item.from_ai_response("lost", SAMPLE_AI_REPLY)
        self.assertEqual(item.item_type.text, "phone")
        self.assertEqual(item.colour.confidence, 1.0)
        self.assertEqual(item.occurred_at, datetime(2026, 10, 10, 15, 0))
        self.assertTrue(item.unique_info.is_empty())

    def test_unknown_field_rejected(self):
        with self.assertRaises(ValueError):
            LostItem({"favourite_food": ExtractedField("rice", 1.0)})

    def test_fields_copy_cannot_change_the_item(self):
        item = Item.from_ai_response("lost", SAMPLE_AI_REPLY)
        copy = item.fields
        copy["item_colour"] = ExtractedField("red", 1.0)
        self.assertEqual(item.colour.text, "black")

    def test_with_field_returns_new_item_and_keeps_original(self):
        item = Item.from_ai_response("lost", SAMPLE_AI_REPLY)
        changed = item.with_field("item_colour", ExtractedField("red", 1.0))
        self.assertIsInstance(changed, LostItem)
        self.assertEqual((item.colour.text, changed.colour.text), ("black", "red"))

    def test_missing_or_unreadable_date(self):
        self.assertIsNone(LostItem().occurred_at)
        self.assertIsNone(LostItem({"datetime": ExtractedField("10 Oct 3pm", 0.5)}).occurred_at)


class TestAIFlags(unittest.TestCase):
    def test_reads_gemini_flags(self):
        flags = AIFlags.from_dict({**SAMPLE_AI_REPLY, "prohibited_item": True, "colour_options": ["black", "red"]})
        self.assertTrue(flags.prohibited_item)
        self.assertEqual(flags.colour_options, ("black", "red"))

    def test_older_records_without_flags_use_safe_defaults(self):
        flags = AIFlags.from_dict({})
        self.assertFalse(flags.prohibited_item)
        self.assertTrue(flags.item_recognised)
        self.assertTrue(flags.location_specific)


class TestFoundItem(unittest.TestCase):
    def test_loads_a_phase1_record_and_saves_the_same_data(self):
        item = FoundItem.from_dict(PHASE1_RECORD)
        self.assertEqual((item.item_id, item.status), ("FND-0002", "active"))
        saved = item.to_dict()
        for key, value in PHASE1_RECORD.items():
            self.assertEqual(saved[key], value, key)
        self.assertTrue(saved["location_specific"])     # missing flag filled with the safe default

    def test_status_changes_only_through_archive(self):
        item = FoundItem.from_dict(PHASE1_RECORD)
        self.assertTrue(item.is_active())
        item.archive()
        self.assertFalse(item.is_active())
        with self.assertRaises(AttributeError):
            item.status = "active"

    def test_private_attributes_are_not_directly_reachable(self):
        item = FoundItem.from_dict(PHASE1_RECORD)
        self.assertFalse(hasattr(item, "__status"))
        self.assertFalse(hasattr(item, "status_"))

    def test_id_assigned_only_once(self):
        item = FoundItem()
        item.assign_id("FND-0009", "2026-10-14T10:00")
        self.assertEqual(item.reported_datetime(), datetime(2026, 10, 14, 10, 0))
        with self.assertRaises(ValueError):
            item.assign_id("FND-0010", "2026-10-14T10:05")

    def test_copies_keep_id_and_status(self):
        item = FoundItem.from_dict(PHASE1_RECORD)
        item.archive()
        changed = item.with_field("item_colour", ExtractedField("silver", 1.0))
        self.assertEqual((changed.item_id, changed.status, changed.colour.text), ("FND-0002", "archived", "silver"))

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            FoundItem(status="lost")


if __name__ == "__main__":
    unittest.main()
