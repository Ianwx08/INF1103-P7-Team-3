
"""RecordingEmailManager: A stand-in email manager for offline tests: keeps the messages, sends nothing."""
from __future__ import annotations

from managers.base.base_email_manager import BaseEmailManager
from models.email_message import EmailMessage


class RecordingEmailManager(BaseEmailManager):
    """A stand-in email manager for offline tests: keeps the messages, sends nothing."""

    def __init__(self, accepts: bool = True) -> None:
        """accepts=False simulates a provider that rejects every email."""
        self.accepts = accepts
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> bool:
        if self.accepts:
            self.sent.append(message)
        return self.accepts
