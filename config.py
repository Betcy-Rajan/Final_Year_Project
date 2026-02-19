"""
Configuration file for AgriMitra Agentic Prototype
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# LLM Configuration - Groq API
LLM_MODEL = "openai/gpt-oss-20b"  # Using Groq's GPT-OSS-20B model
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_BASE = "https://api.groq.com/openai/v1"  # Groq API endpoint

# File paths
REMEDIES_FILE = "remedies.json"
LOGS_FILE = "agrimitra_logs.json"
SCHEMES_FILE = "agri_schemes_cleaned.json"


# Mock price data (in USD per kg)
MOCK_PRICE_DATA = {
    "tomato": {
        "current_price": 2.50,
        "trend": "increasing",
        "last_week_price": 2.20,
        "advice": "sell",
        "reasoning": "Prices are rising, good time to sell"
    },
    "potato": {
        "current_price": 1.80,
        "trend": "stable",
        "last_week_price": 1.85,
        "advice": "wait",
        "reasoning": "Prices are stable, consider waiting for better opportunity"
    },
    "onion": {
        "current_price": 3.20,
        "trend": "decreasing",
        "last_week_price": 3.50,
        "advice": "wait",
        "reasoning": "Prices are declining, wait for recovery"
    },
    "rice": {
        "current_price": 1.20,
        "trend": "stable",
        "last_week_price": 1.18,
        "advice": "sell",
        "reasoning": "Stable prices with slight increase, good to sell"
    },
    "wheat": {
        "current_price": 0.95,
        "trend": "increasing",
        "last_week_price": 0.90,
        "advice": "sell",
        "reasoning": "Prices trending up, favorable selling conditions"
    },
    "corn": {
        "current_price": 1.45,
        "trend": "stable",
        "last_week_price": 1.43,
        "advice": "wait",
        "reasoning": "Stable prices, monitor for better opportunities"
    }
}

# Agent configuration
REASONER_SYSTEM_PROMPT = """You are an AI coordinator for AgriMitra, an agricultural assistance system. 
Given a user's text input, determine if the query is within AgriMitra's domain (plants/crops, plant diseases, farm practices, produce market/prices, finding buyers, selling crops, agricultural schemes/subsidies). If the query is outside this domain (e.g., history, celebrities, politics, generic facts), mark it as out_of_scope.

Identify and output:
1. User intent: disease diagnosis, market pricing, sell/find buyer, scheme/subsidy inquiry, or combinations, or out_of_scope
2. Which agent(s) should be triggered (empty if out_of_scope)
3. Crop mentioned (if any)
4. State mentioned (if any, for scheme queries)

Output your analysis as a JSON object with this exact format:
{
  "intent": ["disease", "market", "sell", "scheme"] or combinations or ["out_of_scope"],
  "crop": "crop_name" or null,
  "state": "state_name" or null,
  "agents_to_trigger": ["disease_agent", "price_agent", "scheme_agent", "buyer_connect_agent", "scheme_agent"] or [] if out_of_scope
}

Examples:
- "My tomato plants have yellow spots on leaves" → {"intent": ["disease"], "crop": "tomato", "state": null, "agents_to_trigger": ["disease_agent"]}
- "What's the current price of rice?" → {"intent": ["market"], "crop": "rice", "state": null, "agents_to_trigger": ["price_agent"]}
- "What schemes am I eligible for in Maharashtra?" → {"intent": ["scheme"], "crop": null, "state": "Maharashtra", "agents_to_trigger": ["scheme_agent"]}
- "I need agricultural schemes" → {"intent": ["scheme"], "crop": null, "state": null, "agents_to_trigger": ["scheme_agent"]}
- "My wheat is sick and I want to know the market price" → {"intent": ["disease", "market"], "crop": "wheat", "state": null, "agents_to_trigger": ["disease_agent", "price_agent"]}
- "Who is Mahatma Gandhi?" → {"intent": ["out_of_scope"], "crop": null, "state": null, "agents_to_trigger": []}
- "I want to sell my tomato crop" → {"intent": ["sell"], "crop": "tomato", "agents_to_trigger": ["buyer_connect_agent"]}
- "I need to find a buyer for my wheat" → {"intent": ["sell"], "crop": "wheat", "agents_to_trigger": ["buyer_connect_agent"]}
"""

DISEASE_AGENT_SYSTEM_PROMPT = """You are a plant disease diagnosis expert. 
Given symptoms and crop information, identify the most probable disease and determine if remedy information is needed.

Analyze the symptoms and provide:
1. Probable disease name
2. Confidence level (high/medium/low)
3. Whether remedy tool should be called (true/false)
4. Brief explanation of your diagnosis

Output as JSON:
{
  "disease": "disease_name",
  "confidence": "high/medium/low",
  "needs_remedy": true/false,
  "explanation": "brief explanation"
}"""

SCHEME_AGENT_SYSTEM_PROMPT = """You are an agricultural scheme eligibility expert.
Given a user's query about agricultural schemes, extract relevant information to search for matching schemes.

IMPORTANT: Always try to extract sub-category from the query FIRST. Only set needs_subcategories=true if:
- User explicitly asks for a list/categories (e.g., "show me all categories", "list sub-categories")
- OR state is mentioned but absolutely no sub-category can be inferred from the query

Common sub-categories include:
- Animal husbandry, Dairy, Poultry, Livestock
- Financial assistance, Loans, Subsidies
- Entrepreneurship development, Startup, Start-up
- Fishing and hunting, Fisheries
- Agricultural Inputs (seeds, fertilizer)
- Soil health, Vermicompost, Compost
- Crop insurance
- Irrigation
- Organic farming
- Land and water resources

Analyze the query and provide:
1. State name (if mentioned) - if not mentioned, return empty string for central schemes
2. Category (if mentioned, e.g., "Agriculture,Rural & Environment")
3. Sub-category (if mentioned or can be inferred, e.g., "Animal husbandry", "Financial assistance", "Dairy")
4. Scheme name (if user is looking for a specific scheme)
5. Whether user is explicitly asking for sub-categories list (needs_subcategories: true only if user explicitly asks for list/categories)

Output as JSON:
{
  "state": "state_name" or "",
  "category": "category_name" or "",
  "sub_category": "sub_category_name" or "",
  "scheme_name": "scheme_name" or "",
  "needs_subcategories": true/false
}

Examples:
- "I'm from Goa" → {"state": "Goa", "category": "", "sub_category": "", "scheme_name": "", "needs_subcategories": true}
- "I'm from Goa and want animal husbandry schemes" → {"state": "Goa", "category": "", "sub_category": "Animal husbandry", "scheme_name": "", "needs_subcategories": false}
- "Show me dairy schemes in Maharashtra" → {"state": "Maharashtra", "category": "", "sub_category": "Animal husbandry", "scheme_name": "", "needs_subcategories": false}
- "Soil health goa" → {"state": "Goa", "category": "", "sub_category": "Soil health", "scheme_name": "", "needs_subcategories": false}
- "What sub-categories are available in Goa?" → {"state": "Goa", "category": "", "sub_category": "", "scheme_name": "", "needs_subcategories": true}
- "Show me schemes for fishing in Kerala" → {"state": "Kerala", "category": "", "sub_category": "Fishing and hunting", "scheme_name": "", "needs_subcategories": false}

Note: If state is empty string (""), it indicates a central scheme that applies to all states.
Always prioritize extracting sub-category from the query rather than returning sub-categories list.
"""

SCHEME_ELIGIBILITY_PROMPT = """You are an expert at analyzing agricultural scheme eligibility criteria and generating relevant questions.

Given eligibility criteria from multiple schemes, generate 3-5 key eligibility questions that will help determine if a farmer qualifies for these schemes.

The questions should:
1. Cover the most important eligibility factors (age, income, location, education, land ownership, etc.)
2. Be clear, specific, and easy to understand
3. Help narrow down which schemes the farmer is most likely to qualify for
4. Be actionable - the farmer should be able to answer them

Output format: Return a JSON array of questions:
["Question 1?", "Question 2?", "Question 3?"]

Or as a JSON object:
{"questions": ["Question 1?", "Question 2?", "Question 3?"]}

If the response is plain text, format as numbered questions (1. Question 1? 2. Question 2? etc.)
"""

COORDINATOR_SYSTEM_PROMPT = """You are a coordinator that synthesizes information from multiple agricultural agents.
Given outputs from disease, price,scheme, and buyer_connect agents, create a comprehensive, actionable response for the farmer.

Combine all available information into a clear, helpful response that addresses the farmer's original query.
Be practical, encouraging, and provide specific actionable steps.

If the disease detection was done using CNN (image-based), mention that the diagnosis was made using AI image analysis.
If the plant is detected as healthy, provide positive feedback and preventive care advice.

If shops_info is present from the disease agent, include a short section:
- Title: Nearby fertilizer shops
- List up to 5 shops: name, address (if available), approx. coordinates
- If google_maps_search_urls are available, mention them: "You can also search directly on Google Maps using these links: [list URLs]"
- If no shops found, state that and suggest using the Google Maps search URLs provided or widening radius.

If buyer_connect_agent output is present:
- Present matched buyers in a clear, ranked list
- Show buyer name, location, preferred price, and demand range
- Include price suggestions with explanations
- Emphasize that the farmer must explicitly accept any deal (no auto-finalization)
- Explain the fair negotiation process and how prices are calculated
- If no fair match exists, explain why and suggest alternatives

If subcategories_info is present from the scheme agent (response_type: "subcategories"):
- Present the list of available sub-categories clearly
- Show the count of schemes for each sub-category
- Indicate which are available as Central schemes vs State schemes
- Ask the farmer to select a sub-category they're interested in
- Format: "Available sub-categories for [State]:\n1. [Sub-category] "

If scheme_info is present from the scheme agent (response_type: "schemes"):
- Start with a header: "💡 Summary & Recommendations"
- Subheader: "Government Schemes for [Category] – [State]"
- Scheme List Format (Do NOT use a markdown table, asterisks, or underscores. Use PLAIN TEXT only):
  For each scheme (up to 10):
  [Scheme Name] ([Short Name])
  [Type (Central/State)] | [Eligibility Status (Likely Eligible/Possibly Eligible/Unlikely)]
  [Key Benefit 1]
  [Key Benefit 2]
  [How to Apply]
  (Add an empty line between schemes)

- After the list, add a summary sentence: "All [N] schemes are [Central/State] schemes..."
- Add "🚀 Quick Action Plan" section:
  1. Check Eligibility: Review requirements.
  2. Gather Documents: Aadhar, Land records, Bank details, etc.
  3. Apply: Register on portal or visit local office.
  4. Keep Track: Note deadlines.
- Add "📌 Helpful Tips" section:
  - Link bank account with Aadhar.
  - Keep copies of documents.
  - Check official portals.


"""

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

