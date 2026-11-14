# Step 2 — Interfaces (`managers/base/`)

**Commits:** #3 Ian (`BaseAIManager`), #4 Ruyu (`BaseDataManager`), #5 Peter (`BaseIOManager`),
#6 Markus (`FollowUpRule`, `ItemCorrection`), #7 Jun Wei (`SimilarityStrategy`)

## What it does
Every class in this file is an **abstract base class**: it lists the methods a part must have,
without saying how they work. The rest of the app only depends on these interfaces, so the real
implementations can be swapped for others (e.g. a mock AI in tests) without changing any caller.

| Interface | Methods | Implemented by |
|---|---|---|
| `BaseAIManager` | `analyse(report_type, answers, previous=None) -> Item | None` | `GeminiAIManager`, `MockAIManager` |
| `BaseDataManager` | `load_all`, `add`, `update`, `delete`; shared `get_active()` | `JsonDataManager` |
| `BaseIOManager` | `menu`, `get_report_details`, `ask_detail`, `ask_confirm_or_correct`, `choose_option`, `choose_match`, `confirm`, `confirm_duplicate`, `show_item`, `show_not_found`, `show_message` | `ConsoleIOManager` (and `ScriptedIOManager` in tests) |
| `SimilarityStrategy` | `compare(first, second, directional=True)` | `TextSimilarity`, `DateSimilarity` |
| `FollowUpRule` | `applies(item)`, `ask(io, item, report_type, skip_fields)`, `give_up(item)`; flags `blocking`, `handled_fields` | the five follow-up rules |
| `ItemCorrection` | `applies(item)`, `correct(io, item)` | `ColourChoiceCorrection` |

`ItemCorrection` was added during the build: picking one of several colours is fixed by the user
directly (no Gemini call), which is a different contract from a follow-up question.

## OOP concepts
- **Abstract classes / interfaces:** none of these can be created directly.
- **Polymorphism:** callers call `ai.analyse()`, `rule.applies()`, `strategy.compare()` without knowing which class is behind them.
- `BaseDataManager.get_active()` is a concrete method shared by every subclass (inheritance of behaviour, not only of a contract).

## SOLID
- **OCP:** new storage, AI providers, rules or similarity measures are new subclasses; existing code is not edited.
- **LSP:** anything typed as a base class must work wherever that base class is expected — proven by the contract tests in step 4.
- **DIP (bonus):** high-level code (`LogicManager`) depends on these abstractions, not on Gemini or JSON.

## Added later
- **#27 (Ruyu):** `BaseDataManager.get(item_id)` — read one stored item by ID (or `None`). Concrete, so every store has it without changes; used by the claim re-check (#28).
