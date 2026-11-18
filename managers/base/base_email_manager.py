
"""BaseEmailManager: Sends an email to the administrators."""
from __future__ import annotations

from abc import ABC, abstractmethod

from models.email_message import EmailMessage


class BaseEmailManager(ABC):
    """Sends an email to the administrators.

    The app depends on this interface only, so the provider (Brevo today) can be swapped,
    and tests use a recording stand-in instead of a live email API.
    """

    @abstractmethod
    def send(self, message: EmailMessage) -> bool:
        """Send the message. True only if the provider accepted it.

        Never raises for delivery problems (switched off, missing settings, rejected,
        network error): it returns False, so a failed email cannot stop the app.
        """
