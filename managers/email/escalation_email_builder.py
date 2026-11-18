
"""EscalationEmailBuilder: Writes the admin email that lists unclaimed high-value found items."""
from __future__ import annotations

from html import escape
from typing import Sequence

from models.constants import FIELD_NAMES
from models.email_message import EmailMessage
from models.found_item import FoundItem


class EscalationEmailBuilder:
    """Writes the admin email that lists unclaimed high-value found items.

    Single responsibility: this class decides what the email says; a BaseEmailManager
    decides how it is sent. Change the subject or layout here.
    """

    HEADING = "Unclaimed HIGH_VALUE found items held for more than {days} days"

    def build(self, items: Sequence[FoundItem], days: int) -> EmailMessage:
        """One email covering every item. Item text is escaped in the HTML version."""
        heading = self.HEADING.format(days=days)
        sections = [self._section(item) for item in items]
        text = heading + "\n\n" + "\n\n".join(sections)
        blocks = "".join(
            '<pre style="white-space:pre-wrap;background:#f1f5f9;padding:20px">'
            f"{escape(section)}</pre>" for section in sections)
        html = ('<html><body style="font-family:Arial,sans-serif;color:#1e293b">'
                f"<h1>High-value found item escalation</h1><p>{escape(heading)}</p>{blocks}"
                "</body></html>")
        subject = f"Lost & Found: {len(items)} unclaimed high-value found item(s)"
        return EmailMessage(subject=subject, text=text, html=html)

    @staticmethod
    def _section(item: FoundItem) -> str:
        """The lines for one item: reference, report time, value assessment, then the item details."""
        assessment = item.assessment
        value = ("Unknown / not priced" if assessment is None or assessment.estimated_value_sgd is None
                 else f"S${assessment.estimated_value_sgd:,.2f} (AI estimate)")
        sensitive = assessment is not None and assessment.sensitive
        lines = [
            f"Item: {item.item_id}",
            f"Reported found at: {(item.reported_at or '-').replace('T', ' ')}",
            f"Category: {item.value_category or '-'}",
            f"Estimated value: {value}",
            f"Sensitive / invaluable: {'yes' if sensitive else 'no'}",
            f"Assessment: {assessment.reason if assessment is not None else '-'}",
        ]
        lines.extend(f"{name}: {item.field(name).text or '-'}" for name in FIELD_NAMES)
        return "\n".join(lines)
