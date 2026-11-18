
"""BrevoEmailManager and EscalationEmailBuilder, tested without network access or real credentials."""
import os
import unittest
from unittest.mock import patch

import httpx

from managers.base.base_email_manager import BaseEmailManager
from managers.email.brevo_email_manager import BrevoEmailManager
from managers.email.escalation_email_builder import EscalationEmailBuilder
from models import EmailMessage, FoundItem, Item
from tests.helpers import RecordingEmailManager, SampleReplies

found_item = SampleReplies.found_item
MESSAGE = EmailMessage(subject="Subject", text="Plain text", html="<p>HTML</p>")
REQUEST = httpx.Request("POST", BrevoEmailManager.API_URL)


class TestBrevoEmailManager(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "STARTUP_EMAIL_ENABLED": "true",
            "BREVO_API_KEY": "test-secret",
            "BREVO_SENDER_EMAIL": "sender@example.com",
            "BREVO_RECIPIENTS": " one@example.com, two@example.com,one@example.com, ",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.post = patch("managers.email.brevo_email_manager.httpx.post").start()
        self.addCleanup(patch.stopall)
        self.notes = []

    def send(self):
        return BrevoEmailManager(self.notes.append).send(MESSAGE)

    def test_is_an_email_manager(self):
        self.assertIsInstance(BrevoEmailManager(), BaseEmailManager)

    def test_payload_and_recipient_parsing(self):
        self.post.return_value = httpx.Response(201, request=REQUEST)
        self.assertTrue(self.send())
        self.post.assert_called_once()
        kwargs = self.post.call_args.kwargs
        self.assertEqual(kwargs["json"]["to"], [{"email": "one@example.com"}, {"email": "two@example.com"}])
        self.assertEqual(kwargs["json"]["sender"], {"email": "sender@example.com", "name": "Lost & Found"})
        self.assertEqual(kwargs["headers"]["api-key"], "test-secret")
        self.assertEqual((kwargs["json"]["subject"], kwargs["json"]["textContent"], kwargs["json"]["htmlContent"]),
                         ("Subject", "Plain text", "<p>HTML</p>"))
        self.assertEqual(kwargs["timeout"], 10.0)
        self.assertIn("accepted by Brevo", self.notes[-1])

    def test_disabled_by_default(self):
        del os.environ["STARTUP_EMAIL_ENABLED"]
        self.assertFalse(self.send())
        self.post.assert_not_called()

    def test_missing_settings_and_empty_recipients_skip_network(self):
        for key, value in (("BREVO_API_KEY", ""), ("BREVO_SENDER_EMAIL", " "), ("BREVO_RECIPIENTS", ", ,")):
            with self.subTest(key=key), patch.dict(os.environ, {key: value}):
                self.assertFalse(self.send())
                self.assertIn("skipped", self.notes[-1])
        self.post.assert_not_called()

    def test_api_rejection_does_not_expose_key(self):
        self.post.return_value = httpx.Response(401, request=REQUEST)
        self.assertFalse(self.send())
        self.assertIn("401", self.notes[-1])
        self.assertNotIn("test-secret", self.notes[-1])

    def test_timeout_is_not_retried(self):
        self.post.side_effect = httpx.ReadTimeout("timeout")
        self.assertFalse(self.send())
        self.post.assert_called_once()

    def test_brevo_error_message_is_shown_with_secrets_redacted(self):
        self.post.return_value = httpx.Response(
            401, json={"message": "Key not found: test-secret xkeysib-other-secret"}, request=REQUEST)
        self.assertFalse(self.send())
        self.assertIn("Key not found", self.notes[-1])
        self.assertNotIn("test-secret", self.notes[-1])
        self.assertNotIn("xkeysib-other-secret", self.notes[-1])

    def test_non_object_error_body_does_not_crash(self):
        self.post.return_value = httpx.Response(401, json=["unexpected"], request=REQUEST)
        self.assertFalse(self.send())
        self.assertIn("No additional error details", self.notes[-1])


class TestRecordingEmailManager(unittest.TestCase):
    def test_stand_in_can_replace_the_real_manager(self):
        email = RecordingEmailManager()
        self.assertIsInstance(email, BaseEmailManager)
        self.assertTrue(email.send(MESSAGE))
        email.accepts = False
        self.assertFalse(email.send(MESSAGE))
        self.assertEqual(email.sent, [MESSAGE])


class TestEscalationEmailBuilder(unittest.TestCase):
    def test_email_lists_every_item_with_its_assessment(self):                          # T44
        items = [found_item(2500, item_id="FND-0001", reported_at="2026-11-01T09:30"),
                 found_item(None, True, item_id="FND-0002", reported_at="2026-11-03T10:00")]
        message = EscalationEmailBuilder().build(items, 7)
        self.assertEqual(message.subject, "Lost & Found: 2 unclaimed high-value found item(s)")
        self.assertIn("more than 7 days", message.text)
        for expected in ("Item: FND-0001", "Item: FND-0002", "S$2,500.00 (AI estimate)",
                         "Unknown / not priced", "Sensitive / invaluable: yes",
                         "Reported found at: 2026-11-01 09:30", "Category: HIGH_VALUE",
                         "item_type: phone", "location: SIT Punggol food court"):
            self.assertIn(expected, message.text)

    def test_html_escapes_item_contents(self):                                          # T45
        reply = SampleReplies.copy_reply(SampleReplies.found_reply(None, True),
                                         valuation_reason='<script>alert("x")</script>')
        base = Item.from_ai_response("found", reply)
        item = FoundItem(base.fields, base.flags, "FND-0001", "2026-11-01T09:30", assessment=base.assessment)
        message = EscalationEmailBuilder().build([item], 7)
        self.assertNotIn("<script>", message.html)
        self.assertIn("&lt;script&gt;", message.html)


if __name__ == "__main__":
    unittest.main()
