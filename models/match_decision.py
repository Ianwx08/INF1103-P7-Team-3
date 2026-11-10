"""MatchDecision: What to do with a found item for a lost search."""
from __future__ import annotations

from enum import Enum


class MatchDecision(Enum):
    """What to do with a found item for a lost search."""

    DISPLAY = "display"   # confident: shown as a top match
    REVIEW = "review"     # borderline: shown as a possible match
    HIDE = "hide"         # too weak to show
