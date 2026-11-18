1. Clone the repository.

2. Install dependencies:
   pip install -r requirements.txt

3. Copy .env.example to .env and add your Gemini API key:
   GEMINI_API_KEY=your_key_here

4. Run locally:
   python main.py

## High-value found items and admin escalation

When a found item is reported, Gemini also estimates its value in Singapore dollars, says
whether it is sensitive, and gives a reason. The category is then worked out in Python (and a
reply that disagrees is rejected):

- `HIGH_VALUE`: estimated value of S$1,000 or more, or sensitive (IDs, passports, bank cards,
  EZ-Link and other stored-value cards, access cards, identifying keys, confidential documents)
  whatever its price.
- `ORDINARY`: everything else. An unknown value stays empty; it is never guessed.

Estimates are rough AI assessments, not verified appraisals. After a found item is saved, the
app shows its category and estimate.

Archiving and escalation both count from the time the item was **reported** (not the date it
was found):

- `ORDINARY` found items are archived once they were reported more than 7 days ago.
- `HIGH_VALUE` found items are never archived. They stay listed, searchable and claimable.
- Each time the app starts, it sends the administrators one email (through Brevo) listing the
  active `HIGH_VALUE` found items reported more than 7 days ago (strictly more: exactly 7 days
  is not yet overdue).
- Each item is included at most once per calendar day. The time of the last successful email is
  stored with the item (`escalated_at`). If the send fails or email is switched off, nothing is
  recorded, so the next start tries again.
- Claiming an item removes it, so it drops out of the next email.

Lost searches are not saved: a search only lists matching found items to claim.

Email settings in `.env` (email is off unless `STARTUP_EMAIL_ENABLED=true`):

```dotenv
STARTUP_EMAIL_ENABLED=true
BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=your_verified_sender@example.edu
BREVO_SENDER_NAME="Lost & Found"
BREVO_RECIPIENTS=admin1@example.com,admin2@example.com
```

The Brevo API key needs the **Transactional email** permission and the sender must be verified
in Brevo. "Accepted by Brevo" means Brevo took the email; check the inbox, spam folder and Brevo
logs for delivery. Requests use a 10-second timeout and are not retried. The email contains the
item details, so only list administrators in `BREVO_RECIPIENTS`.

To change the email's subject or layout, edit `managers/email/escalation_email_builder.py`.
To use another email provider, add a class that implements `BaseEmailManager`.

Demo data for the escalation (no Gemini call, no email):

    python seed_escalation_demo.py

adds 13 example found items (FND-DEMO-001 ...; made-up data), each with an example value
assessment. Seven of them qualify (high value, reported more than 7 days ago). With email
switched on, the first `python main.py` start each day emails those seven, and a second start
the same day sends nothing. Claim one from menu 1 and it is gone from the next day's email.
Three old ordinary items are archived at the first menu; the rest are too recent or ordinary.
Running the script again skips items that are already stored.

## Upgrading from an earlier version

- An existing database gains five columns (`estimated_value_sgd`, `sensitive`, `valuation_reason`,
  `value_category`, `escalated_at`) automatically the first time it is used. All records are kept.
  JSON files need no change.
- Items stored before this version have no value assessment. They are treated as ordinary
  (archived after 7 days) and are never escalated.
- To keep a backup, copy the `data/` folder before the first start.

## Main menu

   1. Find a lost item       describe it; Gemini extracts the details; matching found items are listed
                             to claim. Nothing is saved.
   2. Report a found item    describe it; Gemini extracts the details and estimates the value; it is
                             saved (duplicate warning first)
   3. View stored items      overview of active found items, sorted by date found (newest or oldest first)
                             or by item type (A-Z), with a count per type. Descriptions, unique features
                             and values are hidden so only the real owner can describe them. No AI call.
   4. Exit

Before a claim is confirmed, the item is read again from storage, so an item claimed or archived
in the meantime is not claimed twice ("Sorry, this item is no longer available.").

## Storage (database)

Found items are stored in an SQLite database, data/found_items.db (Python's built-in sqlite3;
nothing extra to install). Each item field is its own column, so the data can be queried with SQL.

To use the JSON flat file instead, add to .env:
   STORAGE_BACKEND=json

The first time the database is used, items from an existing data/found_items.json are imported
automatically and that file is renamed to found_items.json.imported-<time>.

## Example data (saves Gemini API tokens)

   python seed_data.py

Adds 24 example found items (phones, wallets, umbrellas, bottles, earbuds, a laptop, keys, ...)
to the same storage main.py uses. No API key or Gemini call is needed. Dates are relative
("found 2 days ago at 15:00"), so the items are always recent when loaded; running it again
does not create copies. Edit samples/sample_found_items.json to change them. Four samples
carry an example value or sensitive mark (`estimated_value_sgd`, `sensitive`), so they are
`HIGH_VALUE`; the others are ordinary.

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
   seed_escalation_demo.py        SeedEscalationDemoCommand: loads example high-value found items (no API calls)
   samples/                       sample_found_items.json
   .github/workflows/ci.yml       CI: Docker build + offline tests on every push / pull request

   models/                        the data (re-exported: from models import FoundItem)
     item.py, lost_item.py, found_item.py          Item (abstract) and its two subclasses
     value_assessment.py, email_message.py         a found item's value assessment; one email to send
     extracted_field.py, ai_flags.py               the parts an Item is built from
     match_decision.py, item_match.py              match results
     stored_items_overview.py                      result of "View stored items"
     constants.py                                  DATETIME_FORMAT, FIELD_NAMES

   managers/
     base/      interfaces: base_ai_manager.py, base_data_manager.py, base_io_manager.py,
                base_email_manager.py, similarity_strategy.py,
                item_sort_order.py, follow_up_rule.py, item_correction.py; sequential_id.py (shared ID rule)
     ai/        AIManager:   gemini_ai_manager.py, mock_ai_manager.py, schema_validator.py,
                prompt_builder.py, ai_error_translator.py, constants.py (schema + prompt)
     data/      DataManager: sqlite_data_manager.py, found_item_row_mapper.py, json_data_manager.py,
                data_manager_factory.py, data_migrator.py, constants.py,
                sqlite_database.py (file handling and transactions),
                sqlite_column_migrator.py (adds new columns to an existing database)
     logic/     LogicManager: logic_manager.py, matching_service.py, match_scorer.py,
                text_similarity.py, date_similarity.py, decision_engine.py, threshold_config.py,
                colour_choice_correction.py, escalation_service.py
       rules/     one follow-up rule per file (prohibited, unrecognised, vague place, future date, missing fields)
       overview/  found_date_order.py, item_type_order.py, overview_service.py
     io/        IOManager:   console_io_manager.py
     email/     admin email: brevo_email_manager.py, escalation_email_builder.py
     samples/   sample_data_loader.py, sample_data_seeder.py, escalation_demo_seeder.py

   tests/                         offline unit tests (mock AI replies, no API calls)
     helpers/                     scripted_io_manager.py, sample_replies.py, recording_email_manager.py
   docs/phase2/                   step-by-step explanations of every class

## Automated tests

The tests in tests/ cover the models, schema validation, the AI managers (with a
fake Gemini client), both storage backends (the same contract tests run on JSON and
SQLite), matching, follow-up rules, the stored-items overview, the example data, full
workflows, and the high-value feature: the value rule, valuation storage in both backends,
the database migration, 7-day archiving and escalation, the daily reminder limit and the Brevo
email manager. They use hard-coded sample AI replies and a stand-in
email manager, and need no API key or internet connection.

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
   5. checks the escalation demo data loads       docker run --rm --network none -e DATA_DIR=/tmp/data lost-and-found python seed_escalation_demo.py

No API key or GitHub secret is needed: the tests use sample AI replies, and --network none
proves no test can call the live Gemini API. A pull request should only be merged when the
CI check is green. Results: the repository's Actions tab, or the tick / cross next to each commit.

To run the same checks before pushing, run the commands in steps 2-5 locally.
