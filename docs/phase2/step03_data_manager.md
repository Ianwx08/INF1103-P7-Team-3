# Step 3 — Data manager (`managers/data/json_data_manager.py`)

**Commits:** #9 (Ruyu); `get(item_id)` in #27 (Ruyu)   **Tests:** `tests/test_data_manager.py`

## What it does
`JsonDataManager(BaseDataManager)` replaces Phase 1's `database_manager.py`. It stores found items
in `data/found_items.json` (or `DATA_DIR/found_items.json`), with the same safety features:

| Method | Behaviour |
|---|---|
| `load_all()` | Every stored `FoundItem`. Missing file → `[]`. Unreadable file → renamed to `found_items.json.corrupt-<time>`, then `[]`. |
| `add(item)` | Gives the item the next ID (`FND-0001`, ...) and report time via `item.assign_id()`, then saves. |
| `update(item)` | Saves changes to an existing item (used for archiving). |
| `delete(item_id)` | Removes a claimed item. |
| `get(item_id)` | Inherited from `BaseDataManager` (added in #27): one item by ID, or `None`; used to re-check an item before it is claimed. |
| `get_active()` | Inherited from `BaseDataManager`. |

Saving writes `found_items.json.tmp` first and swaps it in with `os.replace`, so a crash mid-save
cannot leave a half-written file.

## OOP concepts
- **Inheritance:** implements `BaseDataManager`.
- **Encapsulation:** the file path is private (`__file_path`) with a read-only `file_path` property. File handling (`_read_records`, `_write_records`, `_backup_corrupt_file`, `_next_id`) is protected — only this class uses it.
- **Polymorphism:** `LogicManager` only knows it has *a* `BaseDataManager`; the workflow tests even pass a `BrokenDataManager` to test disk errors.

## SOLID
- **SRP:** only storage. It never matches, asks questions or calls the AI.
- **OCP / LSP:** a different store (e.g. a database) could implement `BaseDataManager` and replace it without changing `LogicManager`; the workflow tests already swap in a `BrokenDataManager`.

## Tests prove
Sequential IDs, data surviving a new manager, archive saved, delete, corrupt file backed up, wrong-shape file treated as corrupt, simulated power cut leaves the old file intact, Phase 1 records load, `file_path` read-only.
