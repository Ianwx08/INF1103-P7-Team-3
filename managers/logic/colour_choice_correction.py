"""ColourChoiceCorrection: Several colours were mentioned: the user picks the most noticeable one."""
from __future__ import annotations
from dataclasses import replace
from managers.base.base_io_manager import BaseIOManager
from managers.base.item_correction import ItemCorrection
from models.extracted_field import ExtractedField
from models.item import Item

class ColourChoiceCorrection(ItemCorrection):
    """Several colours were mentioned: the user picks the most noticeable one."""

    @staticmethod
    def options(item: Item) -> list[str]:
        """Distinct colours, in order, ignoring case and blanks."""
        result: list[str] = []
        for colour in item.flags.colour_options:
            colour = colour.strip()
            if colour and colour.lower() not in [option.lower() for option in result]:
                result.append(colour)
        return result

    def applies(self, item: Item) -> bool:
        return len(self.options(item)) > 1

    def correct(self, io: BaseIOManager, item: Item) -> Item | None:
        colour = io.choose_option(
            "More than one colour was mentioned. Which is the most noticeable colour?", self.options(item))
        if colour is None:
            return None
        flags = replace(item.flags, colour_options=(colour,),
                        missing_fields=tuple(f for f in item.flags.missing_fields if f != "item_colour"))
        return item.with_field("item_colour", ExtractedField(colour, 1.0)).with_flags(flags)