
"""EmailMessage: One email to send: subject, plain-text body and HTML body. Immutable."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessage:
    """One email to send: subject, plain-text body and HTML body. Immutable."""

    subject: str
    text: str
    html: str
