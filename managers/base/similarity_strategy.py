"""SimilarityStrategy: How alike two values of one field are, from 0 to 1."""
from __future__ import annotations

from abc import ABC, abstractmethod


class SimilarityStrategy(ABC):
    """How alike two values of one field are, from 0 to 1."""

    @abstractmethod
    def compare(self, first: str, second: str, *, directional: bool = True) -> float | None:
        """Similarity from 0 to 1, or None when either side is empty (the field is then skipped).

        directional=True means first is the lost report and second the found item;
        strategies that do not depend on order may ignore it.
        """
