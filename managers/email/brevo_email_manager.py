
"""BrevoEmailManager: Sends an email to the administrators through the Brevo API."""
from __future__ import annotations

import os
import re
from typing import Callable

import httpx

from managers.base.base_email_manager import BaseEmailManager
from models.email_message import EmailMessage


class BrevoEmailManager(BaseEmailManager):
    """Sends an email to the administrators through the Brevo API.

    Settings are read from the environment (.env) each time an email is sent:
    STARTUP_EMAIL_ENABLED, BREVO_API_KEY, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME,
    BREVO_RECIPIENTS. Sending is off unless STARTUP_EMAIL_ENABLED=true.
    One request, 10-second timeout, no retry: a timed-out request may already have
    been accepted, so retrying could send the email twice.
    """

    API_URL = "https://api.brevo.com/v3/smtp/email"
    TIMEOUT_SECONDS = 10.0
    REQUIRED_SETTINGS = ("BREVO_API_KEY", "BREVO_SENDER_EMAIL", "BREVO_RECIPIENTS")
    DEFAULT_SENDER_NAME = "Lost & Found"

    def __init__(self, notify: Callable[[str], None] = print) -> None:
        """notify shows the result of each send (default: print)."""
        self._notify = notify

    # ---- BaseEmailManager interface ----
    def send(self, message: EmailMessage) -> bool:
        if os.getenv("STARTUP_EMAIL_ENABLED", "false").strip().lower() != "true":
            return False
        settings = {key: os.getenv(key, "").strip() for key in self.REQUIRED_SETTINGS}
        missing = [key for key, value in settings.items() if not value]
        if missing:
            self._notify("Admin email skipped: set " + ", ".join(missing) + " in .env.")
            return False
        recipients = self._recipients(settings["BREVO_RECIPIENTS"])
        if not recipients:
            self._notify("Admin email skipped: BREVO_RECIPIENTS must contain an email address.")
            return False

        api_key = settings["BREVO_API_KEY"]
        payload = {
            "sender": {
                "email": settings["BREVO_SENDER_EMAIL"],
                "name": os.getenv("BREVO_SENDER_NAME", "").strip() or self.DEFAULT_SENDER_NAME,
            },
            "to": [{"email": address} for address in recipients],
            "subject": message.subject,
            "htmlContent": message.html,
            "textContent": message.text,
        }
        try:
            response = httpx.post(self.API_URL, json=payload, timeout=self.TIMEOUT_SECONDS,
                                  headers={"api-key": api_key, "accept": "application/json"})
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            self._notify(
                f"Admin email failed (HTTP {error.response.status_code}). "
                f"Brevo: {self._error_detail(error.response, api_key)} "
                "Check the Brevo API key, verified sender, recipients and account status.")
            return False
        except httpx.RequestError:
            self._notify("Admin email could not be confirmed: network error or timeout. "
                         "Check the Brevo logs.")
            return False
        self._notify("Admin email accepted by Brevo.")
        return True

    # ---- helpers ----
    @staticmethod
    def _recipients(setting: str) -> list[str]:
        """The comma-separated addresses, trimmed, without blanks or repeats (order kept)."""
        return list(dict.fromkeys(a.strip() for a in setting.split(",") if a.strip()))

    @staticmethod
    def _error_detail(response: httpx.Response, api_key: str) -> str:
        """Brevo's own error message, with any API key removed. Never the request headers."""
        detail = "No additional error details returned."
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict) and isinstance(body.get("message"), str):
            detail = body["message"]
        detail = detail.replace(api_key, "[redacted]")
        detail = re.sub(r"xkeysib-[A-Za-z0-9_-]+", "[redacted]", detail)
        return " ".join(detail.split())[:500]
