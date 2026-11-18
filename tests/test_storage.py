"""Advanced deliverable: SQLite database storage, the storage factory and the JSON import.

The same contract tests run against JsonDataManager and SqliteDataManager, showing
either store can replace the other (Liskov Substitution). Temporary folders only; no API calls.
"""
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from unittest import mock

from managers.ai.mock_ai_manager import MockAIManager
from managers.base.base_data_manager import BaseDataManager
from managers.base.sequential_id import SequentialId
from managers.data.data_manager_factory import DataManagerFactory
from managers.data.data_migrator import DataMigrator
from managers.data.found_item_row_mapper import FoundItemRowMapper
from managers.data.json_data_manager import JsonDataManager
from managers.data.sqlite_column_migrator import SqliteColumnMigrator
from managers.data.sqlite_data_manager import SqliteDataManager
from managers.data.sqlite_database import SqliteDatabase
from managers.logic.logic_manager import LogicManager
from models import FoundItem, Item
from tests.helpers import SampleReplies, ScriptedIOManager

ai_reply = SampleReplies.ai_reply
found_reply = SampleReplies.found_reply
found_item = SampleReplies.found_item
VALUATION_KEYS = ("estimated_value_sgd", "sensitive", "valuation_reason", "value_category")
STORAGE_NOW = datetime(2026, 11, 16, 18, 0)


class StorageSamples:
    """New, unsaved found items for the storage tests."""

    @staticmethod
    def found(**changes) -> FoundItem:
        return Item.from_ai_response("found", ai_reply(**changes))


found = StorageSamples.found


class DataContract:
    """Behaviour every BaseDataManager must have. Subclasses say how to build one."""

    def make(self, folder) -> BaseDataManager:
        raise NotImplementedError

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.notes = []
        self.data = self.make(self.folder)

    def test_is_a_base_data_manager(self):
        self.assertIsInstance(self.data, BaseDataManager)

    def test_empty_store(self):
        self.assertEqual((self.data.load_all(), self.data.get_active()), ([], []))

    def test_add_assigns_sequential_ids_and_report_time(self):
        first, second = self.data.add(found()), self.data.add(found(item_type="wallet"))
        self.assertEqual((first.item_id, second.item_id), ("FND-0001", "FND-0002"))
        self.assertIsNotNone(first.reported_datetime())
        self.assertEqual([i.item_id for i in self.data.load_all()], ["FND-0001", "FND-0002"])

    def test_next_id_continues_after_highest(self):
        for _ in range(2):
            self.data.add(found())
        self.data.delete("FND-0001")
        self.assertEqual(self.data.add(found()).item_id, "FND-0003")

    def test_every_value_survives_a_new_manager(self):
        original = self.data.add(found(unique="sticker 'A&B' on back", colours=["black", "grey"],
                                       missing=["item_brand"], specific=False))
        reloaded = self.make(self.folder).load_all()[0]
        self.assertEqual(reloaded.to_dict(), original.to_dict())

    def test_existing_id_is_kept(self):
        item = FoundItem(found().fields, found().flags, "FND-0042", "2026-10-10T10:00", "archived")
        self.data.add(item)
        self.assertEqual(self.data.load_all()[0].to_dict(), item.to_dict())
        self.assertEqual(self.data.add(found()).item_id, "FND-0043")

    def test_get_one_item_by_id(self):
        self.data.add(found())
        wallet = self.data.add(found(item_type="wallet"))
        self.assertEqual(self.data.get("FND-0002").to_dict(), wallet.to_dict())
        self.assertIsNone(self.data.get("FND-9999"))
        wallet.archive()
        self.data.update(wallet)
        self.assertEqual(self.data.get("FND-0002").status, "archived")    # archived items can still be read
        self.data.delete("FND-0002")
        self.assertIsNone(self.data.get("FND-0002"))

    def test_update_archives_and_get_active_excludes_it(self):
        item = self.data.add(found())
        self.data.add(found(item_type="wallet"))
        item.archive()
        self.assertTrue(self.data.update(item))
        self.assertEqual(self.data.load_all()[0].status, "archived")
        self.assertEqual([i.item_id for i in self.data.get_active()], ["FND-0002"])

    def test_update_unknown_item(self):
        self.assertFalse(self.data.update(FoundItem(item_id="FND-9999")))
        self.assertFalse(self.data.update(found()))

    def test_delete(self):
        self.data.add(found())
        self.assertTrue(self.data.delete("FND-0001"))
        self.assertFalse(self.data.delete("FND-0001"))
        self.assertEqual(self.data.load_all(), [])

    def test_value_assessment_survives_a_new_manager(self):                              # T17
        items = [self.data.add(found_item(2500)), self.data.add(found_item(None, True)),
                 self.data.add(found_item(50))]
        reloaded = self.make(self.folder).load_all()
        self.assertEqual([i.to_dict() for i in reloaded], [i.to_dict() for i in items])
        self.assertEqual([(i.assessment, i.value_category) for i in reloaded],
                         [(i.assessment, i.value_category) for i in items])
        self.assertEqual([i.value_category for i in reloaded], ["HIGH_VALUE", "HIGH_VALUE", "ORDINARY"])

    def test_update_keeps_the_assessment_and_saves_the_escalation_time(self):          # T18
        item = self.data.add(found_item(2500))
        item.archive()
        self.data.update(item)
        self.assertEqual(self.make(self.folder).get(item.item_id).assessment, item.assessment)
        item.mark_escalated(STORAGE_NOW)
        self.data.update(item)
        reloaded = self.make(self.folder).get(item.item_id)
        self.assertEqual(reloaded.escalated_at, "2026-11-16T18:00")
        self.assertEqual(reloaded.assessment, item.assessment)

    def test_item_without_assessment_stays_unassessed(self):                           # T19
        plain = Item.from_ai_response("found", {key: value for key, value in ai_reply().items()
                                                if key not in VALUATION_KEYS})
        self.assertIsNone(plain.assessment)
        stored = self.data.add(plain)
        reloaded = self.make(self.folder).get(stored.item_id)
        self.assertIsNone(reloaded.assessment)
        self.assertIsNone(reloaded.escalated_at)
        raw = self.raw_valuation(stored.item_id)
        self.assertTrue(all(value is None for value in raw.values()), raw)

    def test_re_assessed_value_after_a_follow_up_is_saved(self):                       # T20
        ai = MockAIManager([found_reply(300, colour=None, missing=["item_colour"]), found_reply(1500)],
                           notify=lambda m: None)
        io = ScriptedIOManager(["black Samsung phone", "yesterday 3pm", "SIT Punggol food court", "y", "black"])
        LogicManager(ai, self.data, io, clock=lambda: datetime(2026, 10, 14, 12, 0)).report_found_item()
        stored = self.make(self.folder).load_all()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].assessment.estimated_value_sgd, 1500)
        self.assertEqual(stored[0].value_category, "HIGH_VALUE")

    def test_unreadable_store_is_backed_up(self):
        self.data.add(found())
        with open(self.store_path(), "w", encoding="utf-8") as file:
            file.write("this is not valid storage " * 50)
        self.assertEqual(self.data.load_all(), [])
        self.assertTrue(any(".corrupt-" in name for name in os.listdir(self.folder)))
        self.assertIn("unreadable", self.notes[0])
        self.assertEqual(self.data.add(found()).item_id, "FND-0001")    # usable again


class TestJsonContract(DataContract, unittest.TestCase):
    def make(self, folder):
        return JsonDataManager(os.path.join(folder, "found_items.json"), notify=self.notes.append)

    def store_path(self):
        return self.data.file_path
    
    def raw_valuation(self, item_id):
        """The stored record's valuation keys (absent keys read as None)."""
        with open(self.data.file_path, encoding="utf-8") as file:
            record = next(r for r in json.load(file) if r["item_id"] == item_id)
        self.assertFalse(set(VALUATION_KEYS + ("escalated_at",)) & set(record))
        return {key: record.get(key) for key in VALUATION_KEYS + ("escalated_at",)}
    

class TestSqliteContract(DataContract, unittest.TestCase):
    def make(self, folder):
        return SqliteDataManager(os.path.join(folder, "found_items.db"), notify=self.notes.append)

    def store_path(self):
        return self.data.db_path

    def raw_valuation(self, item_id):
        """The row's valuation and escalation columns."""
        db = sqlite3.connect(self.data.db_path)
        try:
            columns = VALUATION_KEYS + ("escalated_at",)
            row = db.execute(f"SELECT {', '.join(columns)} FROM found_items WHERE item_id = ?",
                             (item_id,)).fetchone()
        finally:
            db.close()
        return dict(zip(columns, row))
    

class TestSqliteDataManager(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "found_items.db")
        self.data = SqliteDataManager(self.path, notify=lambda m: None)

    def query(self, sql, params=()):
        db = sqlite3.connect(self.path)
        try:
            return db.execute(sql, params).fetchall()
        finally:
            db.close()

    def test_table_columns_match_the_mapper(self):
        self.data.load_all()     # creates the table
        columns = [row[1] for row in self.query("PRAGMA table_info(found_items)")]
        self.assertEqual(tuple(columns), FoundItemRowMapper.COLUMNS)
        indexes = {row[1] for row in self.query("PRAGMA index_list(found_items)")}
        self.assertTrue({"idx_found_items_status", "idx_found_items_type"} <= indexes)

    def test_fields_are_real_queryable_columns(self):
        self.data.add(found())
        self.data.add(found(item_type="wallet", colour="brown"))
        rows = self.query("SELECT item_id, item_colour, status FROM found_items WHERE item_type = ?", ("wallet",))
        self.assertEqual(rows, [("FND-0002", "brown", "active")])

    def test_get_uses_a_primary_key_lookup_not_load_all(self):
        self.data.add(found())
        with mock.patch.object(SqliteDataManager, "load_all", side_effect=AssertionError("loaded every row")):
            self.assertEqual(self.data.get("FND-0001").item_id, "FND-0001")
        self.assertIsNone(self.data.get("x' OR '1'='1"))      # injection attempt finds nothing

    def test_sql_injection_is_stored_as_plain_text(self):
        attack = "x'); DROP TABLE found_items; --"
        self.data.add(found(description=attack))
        self.assertEqual(self.data.load_all()[0].description.text, attack)
        self.data.delete(attack)
        self.assertEqual(len(self.data.load_all()), 1)

    def test_database_rejects_an_invalid_value_category(self):                           # T25
        self.data.add(found_item(2500))
        with self.assertRaises(sqlite3.IntegrityError):
            db = sqlite3.connect(self.path)
            try:
                db.execute("UPDATE found_items SET value_category = 'x'")
            finally:
                db.close()

    def test_database_rejects_an_invalid_status(self):
        self.data.load_all()
        with self.assertRaises(sqlite3.IntegrityError):
            db = sqlite3.connect(self.path)
            try:
                db.execute("INSERT INTO found_items (item_id, status) VALUES ('X', 'claimed')")
            finally:
                db.close()

    def test_failed_save_is_rolled_back(self):
        self.data.add(found())
        with mock.patch.object(FoundItemRowMapper, "to_row", side_effect=RuntimeError("crash mid-save")):
            with self.assertRaises(RuntimeError):
                self.data.add(found(item_type="wallet"))
        self.assertEqual([i.item_id for i in self.data.load_all()], ["FND-0001"])

    def test_duplicate_id_becomes_os_error(self):
        self.data.add(FoundItem(found().fields, found().flags, "FND-0001", "2026-10-10T10:00"))
        with self.assertRaises(OSError):
            self.data.add(FoundItem(found().fields, found().flags, "FND-0001", "2026-10-10T10:00"))
        self.assertEqual(len(self.data.load_all()), 1)                     # existing data kept
        self.assertFalse(any(".corrupt-" in n for n in os.listdir(os.path.dirname(self.path))))

    def test_database_that_cannot_be_opened_becomes_os_error(self):
        folder = tempfile.mkdtemp()      # a folder, not a file, cannot be opened as a database
        with self.assertRaises(OSError):
            SqliteDataManager(folder, notify=lambda m: None).load_all()
        self.assertTrue(os.path.isdir(folder))     # a real failure is not "repaired" by renaming

    def test_db_path_is_read_only(self):
        with self.assertRaises(AttributeError):
            self.data.db_path = "elsewhere.db"

    def test_default_path_uses_data_dir(self):
        with mock.patch.dict(os.environ, {"DATA_DIR": "/somewhere"}):
            self.assertEqual(SqliteDataManager().db_path, os.path.join("/somewhere", "found_items.db"))


class TestRowMapper(unittest.TestCase):
    def test_round_trip_keeps_values_types_and_flags(self):
        item = FoundItem(found(prohibited=True, recognised=False, colours=["red", "blue"]).fields,
                         found(prohibited=True, recognised=False, colours=["red", "blue"]).flags,
                         "FND-0007", "2026-10-10T10:00", "archived")
        mapper = FoundItemRowMapper()
        row = mapper.to_row(item)
        self.assertEqual((row["prohibited_item"], row["item_recognised"]), (1, 0))
        self.assertEqual(json.loads(row["colour_options"]), ["red", "blue"])
        self.assertEqual(mapper.from_row(row).to_dict(), item.to_dict())

    def test_round_trip_of_the_value_assessment(self):                                  # T26
        mapper = FoundItemRowMapper()
        assessed = found_item(None, True, item_id="FND-0001", reported_at="2026-11-01T09:30")
        assessed.mark_escalated(STORAGE_NOW)
        row = mapper.to_row(assessed)
        self.assertEqual((row["sensitive"], row["value_category"], row["escalated_at"]),
                         (1, "HIGH_VALUE", "2026-11-16T18:00"))
        self.assertEqual(mapper.from_row(row).to_dict(), assessed.to_dict())
        plain = FoundItem(assessed.fields, assessed.flags, "FND-0002", "2026-11-01T09:30")
        row = mapper.to_row(plain)
        self.assertEqual([row[c] for c in FoundItemRowMapper.VALUE_COLUMNS], [None] * 4)
        self.assertEqual(mapper.from_row(row).to_dict(), plain.to_dict())


class TestSqliteMigration(unittest.TestCase):
    """An existing database made before the value columns existed is upgraded in place."""

    OLD_SCHEMA = """
        CREATE TABLE found_items (
            item_id                      TEXT PRIMARY KEY,
            report_type                  TEXT NOT NULL DEFAULT 'found',
            reported_at                  TEXT,
            status                       TEXT NOT NULL DEFAULT 'active'
                                         CHECK (status IN ('active', 'archived')),
            item_description             TEXT,
            item_description_confidence  REAL NOT NULL DEFAULT 0,
            item_type                    TEXT,
            item_type_confidence         REAL NOT NULL DEFAULT 0,
            item_colour                  TEXT,
            item_colour_confidence       REAL NOT NULL DEFAULT 0,
            item_brand                   TEXT,
            item_brand_confidence        REAL NOT NULL DEFAULT 0,
            item_unique_info             TEXT,
            item_unique_info_confidence  REAL NOT NULL DEFAULT 0,
            "datetime"                   TEXT,
            datetime_confidence          REAL NOT NULL DEFAULT 0,
            location                     TEXT,
            location_confidence          REAL NOT NULL DEFAULT 0,
            colour_options               TEXT NOT NULL DEFAULT '[]',
            prohibited_item              INTEGER NOT NULL DEFAULT 0,
            item_recognised              INTEGER NOT NULL DEFAULT 1,
            location_specific            INTEGER NOT NULL DEFAULT 1,
            missing_fields               TEXT NOT NULL DEFAULT '[]',
            overall_confidence           REAL NOT NULL DEFAULT 0
        );
        CREATE INDEX idx_found_items_status ON found_items (status);
        INSERT INTO found_items (item_id, reported_at, status, item_description, item_description_confidence,
                                 item_type, item_type_confidence, "datetime", datetime_confidence,
                                 colour_options, overall_confidence)
            VALUES ('FND-0001', '2026-10-10T10:00', 'active', 'old phone', 0.9, 'phone', 0.9,
                    '2026-10-09T15:00', 0.9, '["black"]', 0.9),
                   ('FND-0002', '2026-10-01T10:00', 'archived', 'old wallet', 0.8, 'wallet', 0.8,
                    NULL, 0.0, '[]', 0.7);
    """

    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "found_items.db")
        db = sqlite3.connect(self.path)
        try:
            db.executescript(self.OLD_SCHEMA)
            db.commit()
        finally:
            db.close()

    def query(self, sql):
        db = sqlite3.connect(self.path)
        try:
            return db.execute(sql).fetchall()
        finally:
            db.close()

    def columns(self):
        return tuple(row[1] for row in self.query("PRAGMA table_info(found_items)"))

    def open(self):
        return SqliteDataManager(self.path, notify=lambda m: None)

    def test_old_rows_keep_every_value_and_gain_the_columns(self):                     # T21
        self.assertEqual(len(self.columns()), 24)
        items = self.open().load_all()
        self.assertEqual([(i.item_id, i.status, i.description.text, i.reported_at) for i in items],
                         [("FND-0001", "active", "old phone", "2026-10-10T10:00"),
                          ("FND-0002", "archived", "old wallet", "2026-10-01T10:00")])
        self.assertEqual(items[0].flags.colour_options, ("black",))
        self.assertTrue(all(i.assessment is None and i.escalated_at is None for i in items))
        self.assertEqual(self.columns(), FoundItemRowMapper.COLUMNS)

    def test_reopening_is_safe_and_new_items_are_assessed(self):                       # T22
        for _ in range(3):
            self.open().load_all()
        self.assertEqual(self.columns(), FoundItemRowMapper.COLUMNS)
        new = self.open().add(found_item(2500))
        items = self.open().load_all()
        self.assertEqual(len(items), 3)
        self.assertEqual(items[-1].item_id, new.item_id)
        self.assertEqual(items[-1].value_category, "HIGH_VALUE")

    def test_migrator_on_an_up_to_date_table_and_rollback_on_failure(self):            # T24
        migrator = SqliteColumnMigrator(SqliteDataManager.TABLE, SqliteDataManager.ADDED_COLUMNS)
        database = SqliteDatabase(self.path, "SELECT 1;", migrator=migrator)

        def fail(db):
            raise RuntimeError("crash after the migration")

        with self.assertRaises(RuntimeError):
            database.run(fail)
        self.assertEqual(len(self.columns()), 24)                      # rolled back with the action
        self.assertEqual(len(self.query("SELECT * FROM found_items")), 2)
        self.assertEqual(database.run(migrator.apply), [])             # the next run migrates...
        self.assertEqual(self.columns(), FoundItemRowMapper.COLUMNS)
        self.assertEqual(database.run(migrator.apply), [])             # ...and up to date adds nothing
        added = SqliteColumnMigrator("found_items", {"extra": "TEXT"})
        self.assertEqual(SqliteDatabase(self.path, "SELECT 1;").run(added.apply), ["extra"])


class TestDataMigrator(unittest.TestCase):
    def setUp(self):
        folder = tempfile.mkdtemp()
        self.source = JsonDataManager(os.path.join(folder, "found_items.json"), notify=lambda m: None)
        self.target = SqliteDataManager(os.path.join(folder, "found_items.db"), notify=lambda m: None)

    def test_copies_items_keeping_ids_and_status(self):
        first = self.source.add(found())
        self.source.add(found(item_type="wallet"))
        first.archive()
        self.source.update(first)
        self.assertEqual(DataMigrator(self.source, self.target).migrate(), 2)
        self.assertEqual([i.to_dict() for i in self.target.load_all()],
                         [i.to_dict() for i in self.source.load_all()])

    def test_assessment_and_escalation_time_are_imported(self):                        # T27
        item = self.source.add(found_item(2500))
        item.mark_escalated(STORAGE_NOW)
        self.source.update(item)
        self.assertEqual(DataMigrator(self.source, self.target).migrate(), 1)
        copied = self.target.get(item.item_id)
        self.assertEqual((copied.assessment, copied.escalated_at), (item.assessment, "2026-11-16T18:00"))

    def test_target_with_items_is_left_alone(self):
        self.source.add(found())
        self.target.add(found(item_type="wallet"))
        self.assertEqual(DataMigrator(self.source, self.target).migrate(), 0)
        self.assertEqual([i.item_type.text for i in self.target.load_all()], ["wallet"])


class TestDataManagerFactory(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.notes = []

    def factory(self, backend=None):
        return DataManagerFactory(backend, self.folder, notify=self.notes.append)

    def test_database_is_the_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(self.factory().create(), SqliteDataManager)

    def test_backend_from_argument_or_setting(self):
        self.assertIsInstance(self.factory("JSON").create(), JsonDataManager)
        with mock.patch.dict(os.environ, {"STORAGE_BACKEND": "json"}):
            self.assertEqual(self.factory().backend, "json")

    def test_unknown_backend(self):
        with self.assertRaises(ValueError):
            self.factory("mongodb")

    def test_old_json_is_imported_once_and_renamed(self):
        JsonDataManager(os.path.join(self.folder, "found_items.json")).add(found())
        database = self.factory().create()
        self.assertEqual([i.item_id for i in database.load_all()], ["FND-0001"])
        self.assertIn("Imported 1 found item(s) into the database", self.notes[0])
        self.assertFalse(os.path.exists(os.path.join(self.folder, "found_items.json")))
        self.assertTrue(any(".imported-" in name for name in os.listdir(self.folder)))
        database.delete("FND-0001")                 # claimed: the database is now empty...
        self.assertEqual(self.factory().create().load_all(), [])    # ...and nothing is re-imported

    def test_json_backend_never_imports(self):
        JsonDataManager(os.path.join(self.folder, "found_items.json")).add(found())
        self.assertEqual(len(self.factory("json").create().load_all()), 1)
        self.assertFalse(os.path.exists(os.path.join(self.folder, "found_items.db")))

    def test_import_failure_is_reported_not_fatal(self):
        JsonDataManager(os.path.join(self.folder, "found_items.json")).add(found())
        with mock.patch.object(DataMigrator, "migrate", side_effect=OSError("disk full")):
            self.assertIsInstance(self.factory().create(), SqliteDataManager)
        self.assertIn("Could not import", self.notes[0])
        self.assertTrue(os.path.exists(os.path.join(self.folder, "found_items.json")))


class TestSequentialId(unittest.TestCase):                                              # T57
    def test_next_number_ignores_other_ids(self):
        ids = SequentialId("FND-")
        self.assertEqual(ids.next_after([]), "FND-0001")
        self.assertEqual(ids.next_after(["FND-0002", "FND-DEMO-001", "ABC-0009", None]), "FND-0003")

    def test_found_items_after_demo_ids(self):
        self.assertEqual(BaseDataManager._next_id_from(["FND-DEMO-001", "FND-DEMO-013"]), "FND-0001")
        self.assertEqual(BaseDataManager._next_id_from(["FND-0003", "XYZ-0008"]), "FND-0004")


if __name__ == "__main__":
    unittest.main()
