from __future__ import annotations
import json
from dotenv import load_dotenv
from managers.ai.gemini_ai_manager import GeminiAIManager
from managers.base.base_ai_manager import BaseAIManager

class LiveAICheck:
    """Runs sample reports through any BaseAIManager"""

    SAMPLES = [
        ("lost", "Airpod pro 3 with keychain with logo", "15 July 2026 2.05pm", "Tampines Mall"),
        ("found", "blue wallet", "20 September 2026 at 7pm", "Punggol MRT"),
        ("lost", "black Samsung Galaxy S25", "1 October 2026 3.30pm", "SIT Punggol food court"),
        ("lost", "my AirPods Pro", "not sure", "Tampines Mall"),
    ]

    def __init__(self, ai: BaseAIManager) -> None:
        self._ai = ai

    def run(self) -> None:
        for report_type, description, when, where in self.SAMPLES:
            print("\n====================================")
            print(f"INPUT ({report_type}): {description} | {when} | {where}")
            item = self._ai.analyse(report_type, {"description": description, "date_time": when, "location": where})
            if item is None:
                print("\nAI OUTPUT: none (Gemini failed or the reply did not pass the schema check)")
                continue
            print("\nAI OUTPUT:")
            print(json.dumps(item.ai_record(), indent=4))


if __name__ == "__main__":
    load_dotenv()
    LiveAICheck(GeminiAIManager()).run()
