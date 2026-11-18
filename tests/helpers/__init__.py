"""Shared test helpers, one class per file: scripted IO, hard-coded sample AI replies and a
recording email manager. No API calls."""

from tests.helpers.recording_email_manager import RecordingEmailManager
from tests.helpers.sample_replies import SampleReplies
from tests.helpers.scripted_io_manager import ScriptedIOManager

__all__ = ["RecordingEmailManager", "SampleReplies", "ScriptedIOManager"]
