"""Domain models: the items people report and the matches between them. One class per file.

OOP concepts shown here:
- Abstract base class: Item cannot be created directly; LostItem / FoundItem must say which they are.
- Inheritance + polymorphism: both subclasses share Item's behaviour and answer report_type differently.
- Encapsulation: fields live in protected attributes and are read through properties; a found
  item's status can only change through archive().
- Composition: an Item is built from ExtractedField objects and one AIFlags object that it owns.

Everything is re-exported here, so callers can write `from models import FoundItem`.
"""
from models.ai_flags import AIFlags
from models.constants import DATETIME_FORMAT, FIELD_NAMES
from models.extracted_field import ExtractedField
from models.found_item import FoundItem
from models.item import Item
from models.item_match import ItemMatch
from models.lost_item import LostItem
from models.match_decision import MatchDecision

__all__ = [
    "DATETIME_FORMAT",
    "FIELD_NAMES",
    "AIFlags",
    "ExtractedField",
    "FoundItem",
    "Item",
    "ItemMatch",
    "LostItem",
    "MatchDecision",

]
