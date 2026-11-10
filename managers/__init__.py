"""The four managers and the interfaces they implement, one class per file:

- base/      interfaces (abstract base classes) every manager and pluggable part implements
- ai/        AIManager:    Gemini calls, prompts, schema validation, mock AI for tests
- data/      DataManager:  the found-items JSON file
- logic/     LogicManager: matching, decisions, follow-up rules (rules/)
- io/        IOManager:    the terminal interface
- samples/   example found items loaded without Gemini
"""
