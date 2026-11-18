"""The four managers and the interfaces they implement, one class per file:

- base/      interfaces (abstract base classes) every manager and pluggable part implements
- ai/        AIManager:    Gemini calls, prompts, schema validation, mock AI for tests
- data/      DataManager:  JSON file and SQLite database storage of found items, factory,
                          JSON import and database column migration
- logic/     LogicManager: matching, decisions, follow-up rules (rules/), stored-items overview (overview/)
- io/        IOManager:    the terminal interface
- email/     admin emails: the Brevo sender and the high-value found-item escalation email text
- samples/   example found items loaded without Gemini
"""