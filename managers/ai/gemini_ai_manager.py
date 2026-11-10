"""GeminiAIManager: The main AI manager. Calls Gemini with a JSON schema, validates the reply, retries on failure."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Callable, Mapping
from google.genai import types
from managers.ai.ai_error_translator import AIErrorTranslator
from managers.ai.constants import RESPONSE_SCHEMA
from managers.ai.prompt_builder import PromptBuilder
from managers.ai.schema_validator import SchemaValidator
from managers.base.base_ai_manager import BaseAIManager
from models.item import Item

class GeminiAIManager(BaseAIManager):
    """Composition: it creates and owns its SchemaValidator, PromptBuilder and AIErrorTranslator.
       Encapsulation: the API key and the Gemini client are private."""

    DEFAULT_MODEL = "gemini-3.5-flash-lite"

    def __init__(self, api_key: str | None = None, model: str | None = None, attempts: int = 3,
                 client: Any = None, notify: Callable[[str], None] = print,
                 clock: Callable[[], datetime] = datetime.now) -> None:
        """api_key / model default to GEMINI_API_KEY / GEMINI_MODEL. client can be injected (tests)."""
        self._api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY")
        self._model = model or os.getenv("GEMINI_MODEL") or self.DEFAULT_MODEL
        if attempts < 1:
            raise ValueError("attempts must be at least 1")
        self._attempts = attempts
        self.__client = client
        self._notify = notify
        self._validator = SchemaValidator()
        self._prompts = PromptBuilder(clock=clock)
        self._errors = AIErrorTranslator()

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, name: str) -> None:
        """Switch model; name can't be empty."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("model name must be a non-empty string")
        self._model = name.strip()

    @property
    def has_api_key(self) -> bool:
        """Whether a key is configured."""
        return bool(self._api_key)

    def _client(self) -> Any:
        """Create Gemini client the first time it is needed."""
        if self.__client is None:
            from google import genai
            self.__client = genai.Client(api_key=self._api_key)
        return self.__client

    def analyse(self, report_type: str, answers: Mapping[str, str],
                previous: Item | None = None) -> Item | None:
        prompt = self._prompts.build(report_type, answers, previous)
        for attempt in range(1, self._attempts + 1):
            try:
                return Item.from_ai_response(report_type, self._request(prompt))
            except AIErrorTranslator.HANDLED_ERRORS as error:
                self._notify(f"AI processing attempt {attempt}/{self._attempts} failed: "
                             f"{self._errors.describe(error)}")
        return None

    def _request(self, prompt: str) -> dict[str, Any]:
        """One Gemini call that must return schema-valid JSON; raises ValueError otherwise."""
        response = self._client().models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
        data = json.loads(response.text)
        problems = self._validator.validate(data)
        if problems:
            raise ValueError("Invalid AI response: " + "; ".join(problems))
        return data
