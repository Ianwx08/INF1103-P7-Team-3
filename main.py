import os
import sys
from dotenv import load_dotenv

load_dotenv()    # read GEMINI_API_KEY (and optional GEMINI_MODEL, DATA_DIR) from .env

# The app cannot work without Gemini, so stop straight away if there is no key.
if not os.getenv("GEMINI_API_KEY"):
    print("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

import ai_manager
import database_manager
import io_manager
import logic_manager


def archive_expired_items() -> None:
    """Archive found items left unclaimed past the archive period (7 days)."""
    for item_id in logic_manager.get_expired_item_ids(database_manager.get_all_items()):
        database_manager.update_item(item_id, {"status": "archived"})

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
            future_date = logic_manager.is_future_datetime(item_data)
            if not flagged and not vague_location and not future_date:
                return item_data
            if last_round:
                if future_date:
                    # A future date is wrong, so keep no date rather than a misleading one.
                    item_data["datetime"] = {"value": None, "confidence": 0.0}
                io_manager.show_message(
                    "Some details are still unclear; continuing with the information provided."
                )
                return item_data

            # Collect every answer for this round, so Gemini is called once.
            answers = {}
            if vague_location:
                answers = io_manager.ask_for_specific_location(item_data, report_type)
                flagged = [field for field in flagged if field != "location"]
            if answers is not None and future_date:
                when = io_manager.ask_for_past_datetime(item_data, report_type)
                answers = None if when is None else {**answers, **when}
                flagged = [field for field in flagged if field != "datetime"]
            if answers is not None and flagged:
                more = io_manager.ask_about_flagged_fields(item_data, flagged, report_type)
                answers = None if more is None else {**answers, **more}

        # None means the user typed 'back' at one of the questions.
        if answers is None:
            io_manager.show_message("\nReturning to the main menu.")
            return None

        io_manager.show_message("\nUpdating your report with AI...")
        item_data = ai_manager.analyse_user_input(report_type, answers, item_data)


def handle_lost_item() -> None:
    """Menu option 1: build a lost report, show matching found items and let the user claim one."""
    lost_data = process_report("lost")    # the lost report; never saved
    if lost_data is None:
        return

    results = logic_manager.find_matches(lost_data, database_manager.get_active_items())
    matches = results["matches"]                     # confident matches
    possible_matches = results["possible_matches"]   # less certain matches
    if not matches and not possible_matches:
        io_manager.items_not_found()
        return

    chosen = io_manager.show_matches_and_choose(matches, possible_matches)    # the found item picked
    if chosen is None:
        return

    io_manager.show_message("\n" + io_manager.format_item(chosen))
    if io_manager.confirm("Confirm this is your item and claim it?"):
        database_manager.delete_item(chosen["item_id"])
        io_manager.show_message(
            f"Claimed. Quote reference {chosen['item_id']} at the Lost & Found counter."
        )


def handle_found_item() -> None:
    """Menu option 2: build a found report, check for duplicates and save it."""
    found_data = process_report("found")
    if found_data is None:
        return

    duplicates = logic_manager.find_duplicates(found_data, database_manager.get_active_items())
    if duplicates and not io_manager.confirm_duplicate(duplicates):
        io_manager.show_message("Report not saved.")
        return

    stored = database_manager.add_item(found_data)    # the item as saved, with its new ID
    io_manager.show_message("\nThank you! Your report has been saved:")
    io_manager.show_message(io_manager.format_item(stored))


def main() -> None:
    """Run the menu loop until the user chooses Exit.

    Archives old items before every menu, and turns file errors into a
    message instead of a crash.
    """
    handlers = {    # menu choice -> function that handles it
        "lost": handle_lost_item,
        "found": handle_found_item,
    }

    while True:
        try:
            archive_expired_items()
        except OSError as error:
            io_manager.show_message(f"Could not update the data file: {error}")

        choice = io_manager.menu()
        if choice == "exit":
            io_manager.show_message("Goodbye!")
            break

        try:
            handlers[choice]()
        except OSError as error:
            io_manager.show_message(
                f"Could not read or save the data file: {error}. Nothing was saved."
            )
        print()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):    # Ctrl+C or closed input
        print("\nGoodbye!")