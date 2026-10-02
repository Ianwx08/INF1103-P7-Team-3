import os
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field
from typing import Optional, Literal

load_dotenv()

# Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# -------------------------
# JSON Structure
# -------------------------
class ExtractedField(BaseModel):
    value: Optional[str] = None
    confidence: float = Field(
        ge=0.0,
        le=1.0
    )

class LostFoundItem(BaseModel):

    report_type: Literal[
        "lost",
        "found",
        "unknown"
    ]

    item_description: ExtractedField
    item_type: ExtractedField
    item_colour: ExtractedField
    item_brand: ExtractedField
    item_unique_info: ExtractedField
    datetime: ExtractedField
    location: ExtractedField

    missing_fields: list[str]

    overall_confidence: float = Field(
        ge=0.0,
        le=1.0
    )

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

def extract_item_information(user_input: str) -> LostFoundItem:

    prompt = f"""{SYSTEM_PROMPT} USER REPORT:{user_input}"""
    interaction = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": LostFoundItem.model_json_schema()
        }
    )
    result = LostFoundItem.model_validate_json(
        interaction.output_text
    )
    return result