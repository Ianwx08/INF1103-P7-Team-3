"""ProhibitedItemRule: Living things, food, drinks and fruit cannot be reported."""
from __future__ import annotations
from managers.logic.rules.rejected_item_type_rule import RejectedItemTypeRule
from models.item import Item

class ProhibitedItemRule(RejectedItemTypeRule):
    """Living things, food, drinks and fruit cannot be reported."""

    message = ("Sorry, living things (people, animals, plants) and food, drinks or fruit "
               "cannot be reported here.")

    def applies(self, item: Item) -> bool:
        return item.flags.prohibited_item
