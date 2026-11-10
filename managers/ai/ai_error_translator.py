"""AIErrorTranslator: Turns API, network and reply errors into plain messages for better user experience."""
from __future__ import annotations

import httpx
from google.genai import errors

class AIErrorTranslator:
    # Errors a failed attempt can raise; anything else is a real bug and isn't hidden.
    HANDLED_ERRORS: tuple[type[Exception], ...] = (ValueError, TypeError, errors.APIError, httpx.HTTPError)

    def describe(self, error: Exception) -> str:
        if isinstance(error, errors.APIError):
            code = getattr(error, "code", None)
            if code == 400 and "api key" in str(error).lower():
                return "Your Gemini API key is not valid. Check GEMINI_API_KEY in your .env file."
            if code in (401, 403):
                return "Gemini refused access. Check that your API key is valid and allowed to use this model."
            if code == 404:
                return "The AI model could not be found. Check GEMINI_MODEL in your .env file."
            if code == 429:
                return "Too many requests to Gemini. Please wait a minute and try again."
            if isinstance(code, int) and code >= 500:
                return "Gemini is busy or temporarily unavailable."
            return f"Gemini returned an error (code {code})."
        if isinstance(error, httpx.TimeoutException):
            return "Gemini took too long to respond."
        if isinstance(error, httpx.HTTPError):
            return "Could not connect to Gemini. Check your internet connection."
        return "Gemini's reply was not in the expected format."
