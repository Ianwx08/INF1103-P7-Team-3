"""UnrecognisedItemRule: The item type is not a real object (e.g. "asdf", "back")."""
from __future__ import annotations
from managers.logic.rules.rejected_item_type_rule import RejectedItemTypeRule
from models.item import Item

class UnrecognisedItemRule(RejectedItemTypeRule):
    """The item type is not a real object (e.g. "asdf", "back")."""

    message = "Sorry, we could not recognise that as an item."

    def applies(self, item: Item) -> bool:
        return not item.flags.item_recognised