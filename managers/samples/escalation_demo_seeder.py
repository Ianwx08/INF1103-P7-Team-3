"""EscalationDemoSeeder: Adds example found items, with value assessments, for the escalation demo."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from managers.base.base_data_manager import BaseDataManager
from models.constants import DATETIME_FORMAT
from models.extracted_field import ExtractedField
from models.found_item import FoundItem
from models.value_assessment import ValueAssessment


class EscalationDemoSeeder:
    """Adds example found items, with value assessments, for the escalation demo.

    No Gemini call and no email. Works with any data manager (association). The records read
    like real reports but are made up; each has a fixed FND-DEMO- reference, which is how they
    are told apart from real ones. Existing references are skipped, so running it twice adds
    nothing and never resets an item's escalation time. A demo item that was claimed (and so
    deleted) is added again by a later run.
    """

    # description, type, brand, colour, unique feature, place, value in SGD, sensitive, days since reported
    CASES = (
        ("MacBook Pro 14-inch laptop", "laptop", "Apple", "space grey",
         "SIT sticker on the lid", "SIT Punggol library level 3", 2800, False, 10),
        ("Gold chain necklace with a heart pendant", "necklace", None, "gold",
         "initials engraved on the clasp", "SIT Punggol sports hall changing room", 1800, False, 9),
        ("SIT student ID card (fictional student)", "student ID", None, "white",
         "red lanyard", "SIT Punggol food court", None, True, 12),
        ("DBS debit card (fictional, no real number)", "bank card", "DBS", "black",
         "small crack on one corner", "Punggol MRT station", None, True, 8),
        ("Office keys on a ring with a name tag", "keys", None, "silver",
         "tag reads Room E2-05-11", "SIT Punggol block E2 level 5", 20, True, 11),
        ("Seiko Presage automatic watch", "watch", "Seiko", "silver",
         "brown leather strap", "SIT Punggol gym", 1000, False, 8),
        ("Envelope containing S$1,200 in cash", "cash", None, "brown",
         "sealed, tuition fee written on the front", "SIT Punggol student services counter", 1200, False, 10),
        ("Foldable umbrella", "umbrella", None, "navy blue",
         "wooden handle", "Bus 84 towards Punggol interchange", 15, False, 15),
        ("Wireless earbuds in a charging case", "earphones", "Soundcore", "white",
         "scratch on the case lid", "SIT Punggol lecture theatre 2A", 50, False, 9),
        ("Canon EOS R50 camera with kit lens", "camera", "Canon", "black",
         "grey neck strap", "Waterway Point level 2", 999.99, False, 10),
        ("Coach leather handbag", "handbag", "Coach", "tan",
         "gold zip pull", "Waterway Point food court", 2200, False, 2),
        ("Singapore passport (fictional holder)", "passport", None, "red",
         "clear plastic cover", "Punggol Coast MRT station", None, True, 6),
        ("Bunch of three plain keys", "keys", None, "silver",
         "no tag or keychain", "SIT Punggol bicycle parking", 10, False, 3),
    )

    def __init__(self, data: BaseDataManager, clock: Callable[[], datetime] = datetime.now) -> None:
        """data is where the found items are stored; clock gives "now" (tests pass a fixed one)."""
        self._data = data
        self._clock = clock

    def seed(self) -> int:
        """Store the example found items; returns how many were added."""
        now = self._clock()
        added = 0
        for number, case in enumerate(self.CASES, 1):
            item_id = f"{BaseDataManager.ID_PREFIX}DEMO-{number:03d}"
            if self._data.get(item_id) is not None:
                continue
            value, sensitive, days = case[6:]
            reported_at = now - timedelta(days=days)
            reason = ("Example assessment: sensitive item, escalated whatever its price." if sensitive
                      else "Example estimate for demonstration; not a real appraisal.")
            self._data.add(FoundItem(self._fields(case, reported_at - timedelta(hours=2)),
                                     item_id=item_id, reported_at=reported_at.strftime(DATETIME_FORMAT),
                                     assessment=ValueAssessment(value, sensitive, reason)))
            added += 1
        return added

    @staticmethod
    def _fields(case: tuple, when: datetime) -> dict[str, ExtractedField]:
        """The seven item fields for one example case."""
        description, kind, brand, colour, unique, place = case[:6]
        return {
            "item_description": ExtractedField(description, 1),
            "item_type": ExtractedField(kind, 1),
            "item_brand": ExtractedField(brand, 1 if brand else 0),
            "item_colour": ExtractedField(colour, 1),
            "item_unique_info": ExtractedField(unique, 1),
            "datetime": ExtractedField(when.strftime(DATETIME_FORMAT), 1),
            "location": ExtractedField(place, 1),
        }
