"""Advanced deliverable: SQLite database storage, the storage factory and the JSON import.

The same contract tests run against JsonDataManager and SqliteDataManager, showing
either store can replace the other (Liskov Substitution). Temporary folders only; no API calls.
"""
import json
import os
import sqlite3
import tempfile
import unittest
from unittest import mock
from managers.base.base_data_manager import BaseDataManager
from managers.data.found_item_row_mapper import FoundItemRowMapper
from managers.data.json_data_manager import JsonDataManager
from managers.data.sqlite_data_manager import SqliteDataManager
from models import FoundItem, Item
from tests.helpers import SampleReplies
