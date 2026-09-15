Project Initial Details: AI-Powered Campus Lost & Found Matching System
Repository URL: https://github.com/Ianwx08/INF1103-P7-Team-3

1. Problem Statement and Target Users
Problem Statement:
Campus lost and found counters handle a huge volume of missing items every semester. The main issue is a communication gap: a student reporting a lost item and a staff member cataloging a found item often use completely different words for the exact same object (e.g., "black wireless earbud case" vs. "dark audio accessory"). Manual cross-checking is slow, error-prone, and causes many items to remain unclaimed.
Target Users:
Students, Faculty, and Visitors: Anyone who loses or finds personal items on campus.
Campus Desk & Facility Staff: Personnel responsible for logging found items, managing the storage inventory, and returning items to verified owners.


2. User Inputs
The application will prompt users to enter basic details through the terminal interface:
User Information: Student/Staff ID or contact reference.
Report Type: Selecting whether they are logging a Lost Item or a Found Item.
Location & Date: Where the item was lost/found (e.g., Library, Canteen) and the date of the incident.
Item Description: A plain-text description detailing what the item looks like, its color, brand, or any unique features (e.g., "Blue Hydro Flask bottle with a scratch on the cap").





3. Use of AI
How AI is Utilized:
The AI acts as an intelligent translator. Instead of relying on exact keyword matching, the AI reads the free-text description and standardizes it into organized data fields. This ensures that vague or different descriptions can still be compared accurately.
AI Generated Outputs & Insights:
Item Category & Type: Standardizes the object (e.g., Category: Electronics, Type: Water Bottle).
Visual Attributes: Extracts primary colors, detected brand names, and key distinguishing marks.
Value Assessment: Estimates whether the item is high-value (e.g., laptop, wallet) or low-value (e.g., umbrella) to prioritize search urgent cases.


4. Business Rules
Once the AI breaks down the description, the program applies decision-making rules to match lost entries against found items:
Input Validation: Re-prompts the user if mandatory fields are missing or if descriptions are too short to process.
Match Confidence Scoring: Calculates a match score (0–100%) based on overlapping attributes (category, color, location, and date proximity).
High-Confidence Auto-Match: If a lost report and a found item reach a high match score (e.g., >= 85%), the system immediately flags the item for staff to verify.
High-Value Priority Boost: High-value items with unique details (like serial numbers or distinct stickers) automatically receive a priority score boost so staff can act quickly.
Expiration & Archiving: Items that remain unmatched after 30 days are automatically updated to an archived status.
