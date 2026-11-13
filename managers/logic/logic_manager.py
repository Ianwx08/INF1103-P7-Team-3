"""LogicManager: Runs the report, search and archiving workflows."""
from __future__ import annotations
from datetime import datetime
from typing import Callable, Sequence
from managers.base.base_ai_manager import BaseAIManager
from managers.base.base_data_manager import BaseDataManager
from managers.base.base_io_manager import BaseIOManager
from managers.base.follow_up_rule import FollowUpRule
from managers.base.item_correction import ItemCorrection
from managers.logic.colour_choice_correction import ColourChoiceCorrection
from managers.logic.matching_service import MatchingService
from managers.logic.rules.future_date_rule import FutureDateRule
from managers.logic.rules.missing_fields_rule import MissingFieldsRule
from managers.logic.rules.prohibited_item_rule import ProhibitedItemRule
from managers.logic.rules.unrecognised_item_rule import UnrecognisedItemRule
from managers.logic.rules.vague_location_rule import VagueLocationRule
from models.found_item import FoundItem
from models.item import Item

class LogicManager:
    """Runs the report, search and archiving workflows.

    Association: uses the AI, data and IO managers it is given (any implementation).
    Composition: owns its MatchingService. Aggregation: holds the rules and corrections
    it is given, so new checks are added without changing this class.
    """

    MAX_FOLLOW_UP_ROUNDS = 3

    def __init__(self, ai: BaseAIManager, data: BaseDataManager, io: BaseIOManager,
                 matching: MatchingService | None = None,
                 rules: Sequence[FollowUpRule] | None = None,
                 corrections: Sequence[ItemCorrection] | None = None,
                 clock: Callable[[], datetime] = datetime.now) -> None:
        self._ai, self._data, self._io = ai, data, io
        self._matching = matching or MatchingService()
        self._rules = list(rules) if rules is not None else self.default_rules(clock)
        self._corrections = list(corrections) if corrections is not None else [ColourChoiceCorrection()]
        self._clock = clock

    @staticmethod
    def default_rules(clock: Callable[[], datetime] = datetime.now) -> list[FollowUpRule]:
        """The checks, in the order they are asked."""
        return [ProhibitedItemRule(), UnrecognisedItemRule(), VagueLocationRule(),
                FutureDateRule(clock), MissingFieldsRule()]

    # ---- one report, from first answer to finished Item ----
    def process_report(self, report_type: str) -> Item | None:
        """Ask, send to the AI, then up to 3 follow-up rounds. None if the user went back or it failed."""
        details = self._io.get_report_details(report_type)
        if details is None:
            self._io.show_message("\nReturning to the main menu.")
            return None
        self._io.show_message("\nAnalysing your report with AI...")
        item = self._ai.analyse(report_type, details)

        for round_number in range(self.MAX_FOLLOW_UP_ROUNDS + 1):
            if item is None:
                self._io.show_message("AI processing failed. Please try again later.")
                return None
            last_round = round_number == self.MAX_FOLLOW_UP_ROUNDS

            blocking = next((r for r in self._rules if r.blocking and r.applies(item)), None)
            if blocking is not None:
                if last_round:
                    self._io.show_message("This item cannot be reported. Returning to the main menu.")
                    return None
                answers = blocking.ask(self._io, item, report_type)
            else:
                for correction in self._corrections:
                    if correction.applies(item):
                        item = correction.correct(self._io, item)
                        if item is None:
                            self._io.show_message("\nReturning to the main menu.")
                            return None
                pending = [r for r in self._rules if not r.blocking and r.applies(item)]
                if not pending:
                    return item
                if last_round:
                    for rule in pending:
                        item = rule.give_up(item)
                    self._io.show_message(
                        "Some details are still unclear; continuing with the information provided.")
                    return item
                answers = self._ask_round(pending, item, report_type)

            if answers is None:
                self._io.show_message("\nReturning to the main menu.")
                return None
            self._io.show_message("\nUpdating your report with AI...")
            item = self._ai.analyse(report_type, answers, item)
        return item

    def _ask_round(self, rules: Sequence[FollowUpRule], item: Item, report_type: str) -> dict[str, str] | None:
        """Ask every pending rule once, combining the answers for a single AI call."""
        answers: dict[str, str] = {}
        asked: list[str] = []
        for rule in rules:
            more = rule.ask(self._io, item, report_type, skip_fields=tuple(asked))
            if more is None:
                return None
            answers.update(more)
            asked.extend(rule.handled_fields)
        return answers

    # ---- menu option 1 ----
    def report_lost_item(self) -> None:
        """Search for a lost item and let the user claim a match."""
        lost = self.process_report("lost")
        if lost is None:
            return
        matches, possible = self._matching.find_matches(lost, self._data.get_active())
        if not matches and not possible:
            self._io.show_not_found()
            return
        chosen = self._io.choose_match(matches, possible)
        if chosen is None:
            return
        self._io.show_message("")
        self._io.show_item(chosen)
        if self._io.confirm("Confirm this is your item and claim it?"):
            # The list may be out of date: the item could have been claimed elsewhere or
            # archived since the matches were shown, so check it again before claiming.
            current = self._data.get(chosen.item_id)
            if current is None or not current.is_active() or not self._data.delete(chosen.item_id):
                self._io.show_message("Sorry, this item is no longer available. "
                                      "It may have just been claimed or archived.")
                return
            self._io.show_message(f"Claimed. Quote reference {chosen.item_id} at the Lost & Found counter.")

    # ---- menu option 2 ----
    def report_found_item(self) -> None:
        """Report a found item, warn about duplicates, and save it."""
        found = self.process_report("found")
        if found is None:
            return
        duplicates = self._matching.find_duplicates(found, self._data.get_active())
        if duplicates and not self._io.confirm_duplicate(duplicates):
            self._io.show_message("Report not saved.")
            return
        stored = self._data.add(found)
        self._io.show_message("\nThank you! Your report has been saved:")
        self._io.show_item(stored)

    # ---- before every menu ----
    def archive_expired(self) -> list[FoundItem]:
        """Archive active found items older than 7 days; returns the ones archived."""
        expired = self._matching.expired(self._data.load_all(), now=self._clock())
        for item in expired:
            item.archive()
            self._data.update(item)
        return expired