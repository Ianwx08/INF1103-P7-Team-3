import os
import sys
from dotenv import load_dotenv

load_dotenv()    # read GEMINI_API_KEY (and optional GEMINI_MODEL, DATA_DIR) from .env

# The app cannot work without Gemini, so stop straight away if there is no key.
if not os.getenv("GEMINI_API_KEY"):
    print("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

import ai_manager
import Database_manager
import io_manager
import logic_manager


def archive_expired_items() -> None:
    """Archive found items left unclaimed past the archive period (7 days)."""
    for item_id in logic_manager.get_expired_item_ids(Database_manager.get_all_items()):
        Database_manager.update_item(item_id, {"status": "archived"})

def process_report(report_type: str) -> dict | None:
    """Collect free-text input and let Gemini extract, validate and format it.

    Each round: reject living things / food (re-ask item type), let the user
    pick one colour if several were given, then re-ask any flagged fields.
    Every answer goes back through Gemini, for at most
    logic_manager.MAX_FOLLOW_UP_ROUNDS rounds.

    Returns the finished report dictionary, or None if the user went back
    to the menu, the item cannot be reported, or the AI failed.
    """
    details = io_manager.get_report_details(report_type)    # description, date_time, location
    if details is None:
        io_manager.show_message("\nReturning to the main menu.")
        return None

    io_manager.show_message("\nAnalysing your report with AI...")
    item_data = ai_manager.analyse_user_input(report_type, details)    # Gemini's checked result

    for round_number in range(logic_manager.MAX_FOLLOW_UP_ROUNDS + 1):
        if item_data is None:
            io_manager.show_message("AI processing failed. Please try again later.")
            return None

        last_round = round_number == logic_manager.MAX_FOLLOW_UP_ROUNDS    # no more questions after this

        rejection = logic_manager.get_item_rejection(item_data)    # "prohibited", "unrecognised" or None
        if rejection:
            if last_round:
                io_manager.show_message(
                    "This item cannot be reported. Returning to the main menu."
                )
                return None
            answers = io_manager.ask_for_item_type(report_type, rejection)
        else:
            colour_options = logic_manager.get_colour_options(item_data)
            if len(colour_options) > 1:
                colour = io_manager.choose_colour(colour_options)
                if colour is None:
                    io_manager.show_message("\nReturning to the main menu.")
                    return None
                item_data = logic_manager.apply_colour_choice(item_data, colour)

            flagged = logic_manager.get_flagged_fields(item_data)    # missing or unsure fields
            vague_location = logic_manager.is_vague_location(item_data)
            if not flagged and not vague_location:
                return item_data
            if last_round:
                io_manager.show_message(
                    "Some details are still unclear; continuing with the information provided."
                )
                return item_data

            # Collect every answer for this round, so Gemini is called once.
            answers = {}
            if vague_location:
                answers = io_manager.ask_for_specific_location(item_data, report_type)
                flagged = [field for field in flagged if field != "location"]
            if answers is not None and flagged:
                more = io_manager.ask_about_flagged_fields(item_data, flagged, report_type)
                answers = None if more is None else {**answers, **more}

        # None means the user typed 'back' at one of the questions.
        if answers is None:
            io_manager.show_message("\nReturning to the main menu.")
            return None

        io_manager.show_message("\nUpdating your report with AI...")
        item_data = ai_manager.analyse_user_input(report_type, answers, item_data)
