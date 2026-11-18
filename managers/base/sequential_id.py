"""SequentialId: Makes the next reference number for a prefix, e.g. FND-0004."""
from __future__ import annotations

from typing import Iterable


class SequentialId:
    """Makes the next reference number for a prefix, e.g. FND-0004.

    One rule shared by every store, so JSON and the database number items the same way.
    IDs with another prefix or a non-numeric suffix (e.g. FND-DEMO-001) are ignored.
    """

    def __init__(self, prefix: str) -> None:
        """prefix starts every ID, e.g. "FND-"."""
        self._prefix = prefix

    def next_after(self, existing_ids: Iterable[str | None]) -> str:
        """The ID after the highest numbered one in existing_ids. Other IDs are ignored."""
        highest = 0
        for existing in existing_ids:
            existing = str(existing or "")
            suffix = existing[len(self._prefix):]
            if existing.startswith(self._prefix) and suffix.isdigit():
                highest = max(highest, int(suffix))
        return f"{self._prefix}{highest + 1:04d}"
