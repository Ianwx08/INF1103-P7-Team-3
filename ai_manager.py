import os
import json
from datetime import datetime
import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

# Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)
# Gemini Model used
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# -------------------------
# JSON Structure
# -------------------------
REPORT_TYPES = ("lost", "found", "unknown")

# Item fields to be extracted by gemini
FIELD_NAMES = (
    "item_description",
    "item_type",
    "item_colour",
    "item_brand",
    "item_unique_info",
    "datetime",
    "location",
)

# Schema for each field in the JSON output
_FIELD_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "value": {"type": "STRING", "nullable": True},
        "confidence": {"type": "NUMBER"},
    },
    "required": ["value", "confidence"],
}

# Full JSON gemini is to return
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "report_type": {"type": "STRING", "enum": list(REPORT_TYPES)},
        **{name: _FIELD_SCHEMA for name in FIELD_NAMES},
        "colour_options": {"type": "ARRAY", "items": {"type": "STRING"}},
        "prohibited_item": {"type": "BOOLEAN"},
        "item_recognised": {"type": "BOOLEAN"},
        "location_specific": {"type": "BOOLEAN"},
        "missing_fields": {"type": "ARRAY", "items": {"type": "STRING"}},
        "overall_confidence": {"type": "NUMBER"},
    },
    "required": [
        "report_type",
        *FIELD_NAMES,
        "colour_options",
        "prohibited_item",
        "item_recognised",
        "location_specific",
        "missing_fields",
        "overall_confidence",
    ],
}

# -------------------------
# AI Prompt
# -------------------------
SYSTEM_PROMPT = """
You are an information extraction system for a Lost and Found
CLI application.

Your task is to extract information from a user's natural-language
lost/found item report.

Extract these fields:

1. report_type
   - "lost"
   - "found"
   - "unknown"

2. item_description
   - Specific description/model of the item.
   - Example: "AirPods Pro 3"

3. item_type
   - General category.
   - Example:
       AirPods Pro -> earphones
       iPhone 15 -> phone
       blue wallet -> wallet
       MacBook Air -> laptop

4. item_colour
   - Colour explicitly provided by the user.
   - NEVER assume a colour.

5. item_brand
   - Brand explicitly stated or very strongly implied.
   - Example:
       AirPods -> Apple
       Galaxy Buds -> Samsung
       Air Force 1 -> Nike

6. item_unique_info
   - Any identifying characteristic.
   - Examples:
       "keychain with logo"
       "scratch on the side"
       "name written inside"
       "red sticker"
   - If none is given, value should be null.

7. datetime
   - Convert dates and times to:
       YYYY-MM-DDTHH:MM
   - Example:
       15 July 2026 2.05pm
       becomes
       2026-07-15T14:05

8. location
   - Location where the item was lost or found.

9. colour_options
   - Every distinct colour the user mentions for the item.
   - Example:
       "black and red backpack" -> ["black", "red"]
       "dark blue phone"        -> ["dark blue"]
       no colour given          -> []
   - If more than one colour is listed, item_colour should hold the
     colour that seems most dominant, with confidence no higher than 0.70.

10. prohibited_item
   - true if the item is a living thing (person, animal, pet, insect,
     plant) or food, drink or fruit.
   - Containers and accessories are NOT prohibited, e.g. a water bottle,
     lunch box, pet collar or plant pot is false.
   - Otherwise false.

11. item_recognised
   - true only if item_type names a real, physical, non-living object
     that a person could lose or find (e.g. phone, wallet, umbrella,
     water bottle, pet carrier bag).
   - false if item_type is missing, gibberish, a command or ordinary
     word that is not an object (e.g. "back", "asdf", "nothing", "yes",
     "idk"), or a body part.
   - When false, set item_type and item_description values to null.

12. location_specific
   - true if a stranger could go to the location from the words alone:
     a named building, block, level or room, campus area, mall, shop,
     MRT/bus station, bus service number, park or street name
     (e.g. "SIT Punggol food court", "Tampines Mall Starbucks",
     "Punggol MRT station", "bus 858", "Block 123 Punggol Road void deck").
   - false if it is vague, personal or relative, e.g. "outside my house",
     "my garage", "home", "my room", "my car", "outside", "somewhere",
     "around here", "the toilet", "the road", "not sure".
   - false if location value is null. Keep the user's words in location
     even when false.

IMPORTANT RULES:

- NEVER invent information.
- NEVER fill a missing field just because it is common or likely.
- If information is not provided, value must be null.
- Normalisation is allowed.
- Strong brand inference is allowed when the product uniquely implies
  the brand, but confidence should be lower than an explicitly
  stated brand.

CONFIDENCE SCORES:

0.95 - 1.00:
Information was explicitly stated and is very clear.

0.80 - 0.94:
Information was explicit but required minor interpretation or
normalisation.

0.60 - 0.79:
Information was reasonably inferred.

0.40 - 0.59:
Information is uncertain or ambiguous.

0.00:
No value could be extracted.

MISSING FIELDS:

The following are considered important fields:

- item_description
- item_type
- item_colour
- datetime
- location

If one of these cannot be extracted, put its exact field name in
missing_fields.

item_brand and item_unique_info are optional because some items may
not have a known brand or unique identifying feature.

Do not place optional fields into missing_fields.

overall_confidence should represent your confidence in the entire
extraction.

Return only information matching the supplied JSON schema.
"""

DATETIME_FORMAT = "%Y-%m-%dT%H:%M"

def validate_ai_response(data) -> list[str]:
    """Check keys, types and formats of a Gemini response.

    Returns a list of problems; an empty list means the response is valid.
    """
    if not isinstance(data, dict):
        return ["Response is not a JSON object."]

    def is_confidence(value) -> bool:
        """True if value is a number (not True/False) between 0 and 1."""
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and 0.0 <= value <= 1.0
        )

    problems = []    # every problem found, so all of them are reported at once

    if data.get("report_type") not in REPORT_TYPES:
        problems.append(f"report_type must be one of {REPORT_TYPES}.")

    for name in FIELD_NAMES:
        field = data.get(name)
        if not isinstance(field, dict):
            problems.append(f"{name} must be an object with value and confidence.")
            continue
        if "value" not in field or not (field["value"] is None or isinstance(field["value"], str)):
            problems.append(f"{name}.value must be a string or null.")
        if not is_confidence(field.get("confidence")):
            problems.append(f"{name}.confidence must be a number between 0 and 1.")

    date_field = data.get("datetime")
    if isinstance(date_field, dict) and isinstance(date_field.get("value"), str):
        try:
            datetime.strptime(date_field["value"], DATETIME_FORMAT)
        except ValueError:
            problems.append("datetime.value must use the format YYYY-MM-DDTHH:MM.")

    colour_options = data.get("colour_options")
    if not isinstance(colour_options, list) or not all(isinstance(c, str) for c in colour_options):
        problems.append("colour_options must be a list of strings.")

    if not isinstance(data.get("prohibited_item"), bool):
        problems.append("prohibited_item must be true or false.")

    if not isinstance(data.get("item_recognised"), bool):
        problems.append("item_recognised must be true or false.")

    if not isinstance(data.get("location_specific"), bool):
        problems.append("location_specific must be true or false.")

    missing_fields = data.get("missing_fields")
    if not isinstance(missing_fields, list):
        problems.append("missing_fields must be a list.")
    elif not all(isinstance(name, str) and name in FIELD_NAMES for name in missing_fields):
        problems.append("missing_fields may only contain known field names.")

    if not is_confidence(data.get("overall_confidence")):
        problems.append("overall_confidence must be a number between 0 and 1.")

    return problems

_DATE_RULES = (
    "Resolve relative dates such as 'yesterday' or 'last Friday' against the "
    "current date and time. If only a date is given without a time, use 12:00 "
    "and a confidence between 0.60 and 0.70. If no usable date is given, the "
    "datetime value must be null."
)

def build_item_prompt(report_type: str, description: str, date_time: str, location: str) -> str:
    """Combine the user's raw answers into one report for Gemini.

    Includes today's date so Gemini can turn "yesterday" into a real date.
    """
    today = datetime.now().strftime("%Y-%m-%dT%H:%M (%A)")    # e.g. 2026-10-11T23:00 (Sunday)
    return (
        f"Current date and time: {today}. {_DATE_RULES}\n"
        f"Report type: {report_type}\n"
        f"Item description: {description}\n"
        f"Date/time: {date_time}\n"
        f"Location: {location}"
    )

def extract_item_information(user_input: str) -> dict:
    """Make one Gemini call and return its checked JSON reply as a dict.

    Forces a JSON reply in the RESPONSE_SCHEMA shape. Raises ValueError if
    the reply is not valid JSON or fails validate_ai_response(); API and
    network errors are raised as they are.
    """
    prompt = f"""{SYSTEM_PROMPT} USER REPORT:{user_input}"""    # rules + the user's report
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        ),
    )
    data = json.loads(response.text)    # the reply as a Python dict
    problems = validate_ai_response(data)
    if problems:
        raise ValueError("Invalid AI response: " + "; ".join(problems))
    return data

def describe_ai_error(error: Exception) -> str:
    """Turn a Gemini / network / response error into a plain message for the user."""
    if isinstance(error, errors.APIError):
        code = getattr(error, "code", None)    # HTTP status code from Gemini
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

def extract_with_retry(user_input: str, attempts: int = 3) -> dict | None:
    """Call Gemini until a valid response arrives. Returns None if all attempts fail.

    Prints a plain reason after each failed attempt.
    """
    for attempt in range(1, attempts + 1):
        try:
            return extract_item_information(user_input)
        except (ValueError, TypeError, errors.APIError, httpx.HTTPError) as error:
            print(f"AI processing attempt {attempt}/{attempts} failed: {describe_ai_error(error)}")
    return None

def analyse_user_input(
    report_type: str,
    user_answers: dict,
    previous_data: dict | None = None,
) -> dict | None:
    """Single entry point for all user input: Gemini extracts, validates and
    formats the information, then the response is schema-checked.

    First call: user_answers = {"description", "date_time", "location"}.
    Follow-up call: user_answers = {field_name: free-text answer} together
    with previous_data, so Gemini can update just those fields.
    """
    if previous_data is None:
        prompt = build_item_prompt(
            report_type,
            user_answers["description"],
            user_answers["date_time"],
            user_answers["location"],
        )
    else:
        today = datetime.now().strftime("%Y-%m-%dT%H:%M (%A)")
        answer_lines = "\n".join(
            f"- {field}: {answer}" for field, answer in user_answers.items()
        )
        prompt = (
            f"Current date and time: {today}. {_DATE_RULES}\n"
            f"Report type: {report_type}\n"
            f"This report was already extracted as:\n"
            f"{json.dumps(previous_data, ensure_ascii=False)}\n"
            f"The user has now answered follow-up questions about these fields:\n"
            f"{answer_lines}\n"
            f"Update those fields from the user's answers. Information the user "
            f"states or confirms directly is explicit. If an answer contains no "
            f"usable information for its field, set that value to null. If the "
            f"item type changes, update item_description to match. Keep all "
            f"other fields unchanged, then re-evaluate colour_options, "
            f"prohibited_item, item_recognised and location_specific and "
            f"recompute missing_fields and overall_confidence."
        )

    data = extract_with_retry(prompt)    # check reply, else none if gemini failed
    if data is not None:
        data["report_type"] = report_type
    return data
