1. Clone the repository.

2. Install dependencies:
   pip install -r requirements.txt

3. Copy .env.example to .env and add your Gemini API key:
   GEMINI_API_KEY=your_key_here

4. Run locally:
   python main.py

## Main menu

   1. Find a lost item       describe it; Gemini extracts the details; matching found items are listed to claim
   2. Report a found item    describe it; Gemini extracts the details; it is saved (duplicate warning first)
   3. View stored items      overview of active found items, sorted by date found (newest or oldest first)
                             or by item type (A-Z), with a count per type. Descriptions and unique features
                             are hidden so only the real owner can describe them. No AI call.
   4. Exit

Before a claim is confirmed, the item is read again from storage, so an item claimed or archived
in the meantime is not claimed twice ("Sorry, this item is no longer available.").

## Storage

Found items are stored in a JSON flat file, data/found_items.json (or DATA_DIR/found_items.json).
Saves go through a temporary file so a crash cannot corrupt it; an unreadable file is kept as
found_items.json.corrupt-<time>. Items are archived 7 days after they were reported.

## Example data (saves Gemini API tokens)

   python seed_data.py

Adds 24 example found items (phones, wallets, umbrellas, bottles, earbuds, a laptop, keys, ...)
to the same JSON file main.py uses. No API key or Gemini call is needed. Dates are relative
("found 2 days ago at 15:00"), so the items are always recent when loaded; running it again
does not create copies. Edit samples/sample_found_items.json to change them.

Sample data is demo/test data: it skips Gemini to save tokens, but every sample is checked
against the same JSON schema as Gemini's replies. Reports typed into the app always go
through Gemini. Searching for a lost item still uses one Gemini call per search.

In Docker:
   docker run --rm -v "$(pwd)/data:/app/data" lost-and-found python seed_data.py

## Docker

Build:
   docker build -t lost-and-found .

Run (interactive; found items persist in ./data between runs):
   docker run -it --env-file .env -v "$(pwd)/data:/app/data" lost-and-found

On Windows PowerShell use `-v "${PWD}/data:/app/data"`.

## Project structure (Phase 2, object-oriented, one class per file)

   main.py                        LostAndFoundApp: builds the managers and runs the menu
   seed_data.py                   SeedDataCommand: loads the example found items (no API calls)
   samples/                       sample_found_items.json
   .github/workflows/ci.yml       CI: Docker build + offline tests on every push / pull request

   models/                        the data (re-exported: from models import FoundItem)
     item.py, lost_item.py, found_item.py          Item (abstract) and its two subclasses
     extracted_field.py, ai_flags.py               the parts an Item is built from
     match_decision.py, item_match.py              match results
     stored_items_overview.py                      result of "View stored items"
     constants.py                                  DATETIME_FORMAT, FIELD_NAMES

   managers/
     base/      interfaces: base_ai_manager.py, base_data_manager.py, base_io_manager.py,
                similarity_strategy.py, item_sort_order.py, follow_up_rule.py, item_correction.py
     ai/        AIManager:   gemini_ai_manager.py, mock_ai_manager.py, schema_validator.py,
                prompt_builder.py, ai_error_translator.py, constants.py (schema + prompt)
     data/      DataManager: json_data_manager.py, constants.py
     logic/     LogicManager: logic_manager.py, matching_service.py, match_scorer.py,
                text_similarity.py, date_similarity.py, decision_engine.py, threshold_config.py,
                colour_choice_correction.py
       rules/     one follow-up rule per file (prohibited, unrecognised, vague place, future date, missing fields)
       overview/  found_date_order.py, item_type_order.py, overview_service.py
     io/        IOManager:   console_io_manager.py
     samples/   sample_data_loader.py, sample_data_seeder.py

   tests/                         offline unit tests (mock AI replies, no API calls)
     helpers/                     scripted_io_manager.py, sample_replies.py

## Automated tests

The tests in tests/ cover the models, schema validation, the AI managers (with a
fake Gemini client), JSON storage, matching, follow-up rules, the claim check, the
example data and full workflows. They use hard-coded sample AI replies and need no API key or internet connection.

Locally:
   python -m unittest discover tests

Inside the Docker container (no API key, networking switched off):
   docker run --rm --network none lost-and-found python -m unittest discover tests

## Continuous Integration (CI)

The GitHub Actions workflow .github/workflows/ci.yml runs automatically on every push and
every pull request (and can be started by hand from the Actions tab). It:

   1. checks out the code
   2. builds the Docker image                     docker build -t lost-and-found .
   3. runs all unit tests inside the container    docker run --rm --network none lost-and-found python -m unittest discover tests -v
   4. checks the example data loads               docker run --rm --network none -e DATA_DIR=/tmp/data lost-and-found python seed_data.py

No API key or GitHub secret is needed: the tests use sample AI replies, and --network none
proves no test can call the live Gemini API. A pull request should only be merged when the
CI check is green. Results: the repository's Actions tab, or the tick / cross next to each commit.

To run the same checks before pushing, run the commands in steps 2-4 locally.
