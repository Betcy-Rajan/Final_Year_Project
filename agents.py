"""
AgriMitra Agentic Prototype - Agent implementations
"""
import json
import logging
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import requests
import re
from config import (
    REASONER_SYSTEM_PROMPT, DISEASE_AGENT_SYSTEM_PROMPT, 
    COORDINATOR_SYSTEM_PROMPT, MOCK_PRICE_DATA, REMEDIES_FILE,
    SCHEME_AGENT_SYSTEM_PROMPT, SCHEME_ELIGIBILITY_PROMPT, SCHEMES_FILE
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgriMitraLLM:
    """Base LLM class for all agents"""
    def __init__(self, model_name: str = "openai/gpt-oss-20b"):
        from config import GROQ_API_KEY, GROQ_API_BASE
        
        self.llm = None
        self.api_available = False
        
        if GROQ_API_KEY:
            try:
                self.llm = ChatOpenAI(
                    model=model_name,
                    temperature=0.1,
                    api_key=GROQ_API_KEY,
                    base_url=GROQ_API_BASE
                )
                self.api_available = True
                logger.info("Groq API configured successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq API: {e}")
                self.api_available = False
        else:
            logger.info("No Groq API key provided, using fallback logic")
    
    def chat(self, system_prompt: str, user_input: str) -> str:
        """Generic chat method for all agents"""
        if not self.api_available or not self.llm:
            logger.info("Using fallback logic - no API available")
            return self._fallback_response(system_prompt, user_input)
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input)
            ]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return self._fallback_response(system_prompt, user_input)
    
    def _fallback_response(self, system_prompt: str, user_input: str) -> str:
        """Fallback response when API is not available"""
        # Simple keyword-based fallback logic
        user_lower = user_input.lower()
        
        # Check if this is the reasoner system prompt
        if "AI coordinator" in system_prompt and "intent" in system_prompt:
            # Fallback reasoning logic
            disease_keywords = ['disease', 'sick', 'infected', 'spots', 'mold', 'wilting', 'yellow', 'blight', 'mildew', 'rust', 'leaf', 'stem', 'root']
            price_keywords = ['price', 'market', 'sell', 'cost', 'value', 'rate', 'mandi']
            scheme_keywords = ['scheme', 'schemes', 'subsidy', 'subsidies', 'government', 'govt', 'eligible', 'eligibility', 'benefit', 'benefits', 'assistance', 'program', 'programme']
            
            has_disease = any(keyword in user_lower for keyword in disease_keywords)
            has_price = any(keyword in user_lower for keyword in price_keywords)
            has_scheme = any(keyword in user_lower for keyword in scheme_keywords)
            
            crop = None
            for crop_name in MOCK_PRICE_DATA.keys():
                if crop_name in user_lower:
                    crop = crop_name
                    break
            
            # Extract state if mentioned
            states = [
                "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
                "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
                "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
                "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
                "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
                "delhi", "jammu and kashmir", "ladakh", "puducherry"
            ]
            state = None
            for s in states:
                if s in user_lower:
                    state = s.title()
                    break
            
            intent = []
            agents = []
            
            if has_disease:
                intent.append("disease")
                agents.append("disease_agent")
            
            if has_price:
                intent.append("market")
                agents.append("price_agent")
            
            if has_scheme:
                intent.append("scheme")
                agents.append("scheme_agent")
            
            # If neither disease nor price signals appear and no known crop found, treat as out_of_scope
            if not intent and crop is None:
                return json.dumps({
                    "intent": ["out_of_scope"],
                    "crop": None,
                    "state": None,
                    "agents_to_trigger": []
                })
            
            if not intent:
                intent = ["disease"]
                agents = ["disease_agent"]
            
            return json.dumps({
                "intent": intent,
                "crop": crop,
                "state": state,
                "agents_to_trigger": agents
            })
        
        # Check if this is the disease agent system prompt
        elif "plant disease diagnosis expert" in system_prompt:
            # Fallback disease diagnosis
            return json.dumps({
                "disease": "Unknown disease (demo mode)",
                "confidence": "low",
                "needs_remedy": True,
                "explanation": "Running in demo mode - please provide more specific symptoms for accurate diagnosis"
            })
        
        # Check if this is the scheme agent system prompt
        elif "agricultural scheme eligibility expert" in system_prompt:
            # Fallback scheme agent response
            return json.dumps({
                "state": "",
                "category": "",
                "sub_category": "",
                "scheme_name": "",
                "needs_subcategories": False
            })
        
        # Check if this is the coordinator system prompt
        elif "synthesizes information from multiple agricultural agents" in system_prompt:
            # Fallback coordinator response
            return "I'm running in demo mode without API access. For full functionality, please configure your Groq API key. The system can still provide basic disease and price information using local data."
        
        else:
            return "Demo mode response - API not configured"

# Tools
@tool
def remedy_tool(disease_name: str) -> str:
    """Tool to get remedy information for a specific disease"""
    try:
        with open(REMEDIES_FILE, 'r') as f:
            remedies = json.load(f)
        
        for remedy in remedies:
            if remedy['disease_name'].lower() == disease_name.lower():
                return json.dumps(remedy, indent=2)
        
        return json.dumps({
            "error": f"No remedy found for disease: {disease_name}",
            "suggestion": "Please consult with a local agricultural expert"
        })
    except Exception as e:
        logger.error(f"Remedy tool error: {e}")
        return json.dumps({"error": f"Failed to load remedies: {e}"})

@tool
def price_tool(crop_name: str) -> str:
    """Tool to get current market price information for a crop"""
    try:
        crop_lower = crop_name.lower()
        if crop_lower in MOCK_PRICE_DATA:
            price_info = MOCK_PRICE_DATA[crop_lower]
            return json.dumps(price_info, indent=2)
        else:
            return json.dumps({
                "error": f"No price data available for: {crop_name}",
                "available_crops": list(MOCK_PRICE_DATA.keys())
            })
    except Exception as e:
        logger.error(f"Price tool error: {e}")
        return json.dumps({"error": f"Failed to get price data: {e}"})

@tool
def geocode_location(query: str) -> str:
    """Geocode a free-form location string to latitude/longitude using OpenStreetMap Nominatim."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "AgriMitra/1.0 (educational)"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return json.dumps({"error": f"No results for location: {query}"})
        top = data[0]
        return json.dumps({
            "lat": float(top.get("lat")),
            "lon": float(top.get("lon")),
            "display_name": top.get("display_name")
        })
    except Exception as e:
        logger.error(f"Geocode error: {e}")
        return json.dumps({"error": f"Geocoding failed: {e}"})

@tool
def find_fertilizer_shops(lat: float, lon: float, radius_m: int = 5000) -> str:
    """Find nearby fertilizer/agro input shops around a location using Overpass API."""
    try:
        # Overpass query: search for shops that likely sell agro inputs/fertilizers
        # We search for nodes/ways with shop=agrarian OR name tags containing 'fertilizer'/'agro'
        overpass_url = "https://overpass-api.de/api/interpreter"
        query = f"""
        [out:json][timeout:25];
        (
          node["shop"="agrarian"](around:{radius_m},{lat},{lon});
          node["shop"="farm"](around:{radius_m},{lat},{lon});
          node["name"~"fertilizer|fertiliser|agro", i](around:{radius_m},{lat},{lon});
          way["shop"="agrarian"](around:{radius_m},{lat},{lon});
          way["shop"="farm"](around:{radius_m},{lat},{lon});
          way["name"~"fertilizer|fertiliser|agro", i](around:{radius_m},{lat},{lon});
        );
        out center 20;
        """
        resp = requests.post(overpass_url, data={"data": query}, headers={"User-Agent": "AgriMitra/1.0 (educational)"}, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        elements = data.get("elements", [])
        results = []
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("brand") or "Unknown"
            shop = tags.get("shop")
            addr = ", ".join(filter(None, [
                tags.get("addr:street"), tags.get("addr:city"), tags.get("addr:state"), tags.get("addr:postcode")
            ])) or None
            center = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
            results.append({
                "name": name,
                "shop": shop,
                "address": addr,
                "lat": center.get("lat"),
                "lon": center.get("lon")
            })
        return json.dumps({"count": len(results), "shops": results[:20]}, indent=2)
    except Exception as e:
        logger.error(f"Overpass error: {e}")
        return json.dumps({"error": f"Overpass query failed: {e}"})

def _truncate_text(text: str, max_chars: int = 200) -> str:
    """Helper function to truncate text to max_chars"""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + "..."

def _truncate_list(items: list, max_items: int = 3, max_chars_per_item: int = 200) -> list:
    """Helper function to truncate list items"""
    if not items:
        return []
    truncated = []
    for item in items[:max_items]:
        if isinstance(item, str):
            truncated.append(_truncate_text(item, max_chars_per_item))
        else:
            truncated.append(str(item)[:max_chars_per_item])
    return truncated

@tool
def get_subcategories_tool(state: str = "") -> str:
    """Tool to extract all unique sub-categories from schemes for a given state.
    
    Args:
        state: State name to filter schemes. If empty string "", returns sub-categories from central schemes only.
              If state is provided, returns sub-categories from both state schemes and central schemes.
    
    Returns:
        JSON string with unique sub-categories and their counts
    """
    try:
        with open(SCHEMES_FILE, 'r', encoding='utf-8') as f:
            all_schemes = json.load(f)
        
        subcategory_counts = {}
        
        for scheme in all_schemes:
            scheme_state = scheme.get("state", "")
            scheme_sub_categories = scheme.get("sub_category", [])
            
            # Filter by state: if state is empty string, it's a central scheme
            if state:
                # User specified a state - include schemes for that state OR central schemes
                if scheme_state.lower() != state.lower() and scheme_state != "":
                    continue
            else:
                # No state specified - show all schemes (both state and central)
                pass
            
            # Process each sub-category
            for sub_cat in scheme_sub_categories:
                if not sub_cat or sub_cat.strip() == "":
                    continue
                
                sub_cat_lower = sub_cat.lower()
                
                if sub_cat_lower not in subcategory_counts:
                    subcategory_counts[sub_cat_lower] = {
                        "name": sub_cat,
                        "count": 0,
                        "scheme_types": set()
                    }
                
                subcategory_counts[sub_cat_lower]["count"] += 1
                
                # Track scheme types
                if scheme_state == "":
                    subcategory_counts[sub_cat_lower]["scheme_types"].add("Central")
                else:
                    subcategory_counts[sub_cat_lower]["scheme_types"].add("State")
        
        # Convert to list format and sort by count (descending)
        subcategories_list = []
        for sub_cat_data in subcategory_counts.values():
            subcategories_list.append({
                "name": sub_cat_data["name"],
                "count": sub_cat_data["count"],
                "scheme_types": sorted(list(sub_cat_data["scheme_types"]))
            })
        
        # Sort by count descending
        subcategories_list.sort(key=lambda x: x["count"], reverse=True)
        
        return json.dumps({
            "state": state if state else "All",
            "total_subcategories": len(subcategories_list),
            "sub_categories": subcategories_list
        }, indent=2, ensure_ascii=False)
        
    except FileNotFoundError:
        logger.error(f"Schemes file not found: {SCHEMES_FILE}")
        return json.dumps({"error": f"Schemes file not found: {SCHEMES_FILE}"})
    except Exception as e:
        logger.error(f"Subcategories tool error: {e}")
        return json.dumps({"error": f"Failed to load schemes: {e}"})

@tool
def scheme_tool(state: str = "", category: str = "", scheme_name: str = "", sub_category: str = "") -> str:
    """Tool to search and filter agricultural schemes from agri_schemes_cleaned.json.
    
    Args:
        state: State name to filter schemes. If empty string "", returns central schemes.
        category: Optional category filter (e.g., "Agriculture,Rural & Environment")
        scheme_name: Optional scheme name to search for (partial match)
        sub_category: Optional sub-category filter (e.g., "Animal husbandry")
    
    Returns:
        JSON string with matching schemes and their eligibility information (limited to top 3)
    """
    try:
        with open(SCHEMES_FILE, 'r', encoding='utf-8') as f:
            all_schemes = json.load(f)
        
        filtered_schemes = []
        
        for scheme in all_schemes:
            scheme_state = scheme.get("state", "")
            
            # Filter by state: if state is empty string, it's a central scheme
            if state:
                # User specified a state - show schemes for that state OR central schemes
                if scheme_state.lower() != state.lower() and scheme_state != "":
                    continue
            else:
                # No state specified - show all schemes (both state and central)
                pass
            
            # Filter by category if provided
            if category:
                scheme_categories = scheme.get("category", [])
                if not any(cat.lower() == category.lower() for cat in scheme_categories):
                    continue
            
            # Filter by sub_category if provided
            if sub_category:
                scheme_sub_categories = scheme.get("sub_category", [])
                sub_category_lower = sub_category.lower()
                # Try exact match first
                exact_match = any(sub_cat.lower() == sub_category_lower for sub_cat in scheme_sub_categories)
                # If no exact match, try partial match (search term in scheme sub-category or vice versa)
                partial_match = False
                if not exact_match:
                    for sub_cat in scheme_sub_categories:
                        sub_cat_lower = sub_cat.lower()
                        # Check if search term is contained in scheme sub-category
                        if sub_category_lower in sub_cat_lower:
                            partial_match = True
                            break
                        # Check if scheme sub-category is contained in search term
                        if sub_cat_lower in sub_category_lower:
                            partial_match = True
                            break
                        # Check if significant words match (for cases like "Agricultural Inputs" vs "Agricultural Inputs- seeds, fertilizer etc.")
                        search_words = [w for w in sub_category_lower.split() if len(w) > 3]
                        scheme_words = [w for w in sub_cat_lower.split() if len(w) > 3]
                        if search_words and scheme_words:
                            # If all significant words from search are in scheme sub-category
                            if all(word in sub_cat_lower for word in search_words):
                                partial_match = True
                                break
                
                if not exact_match and not partial_match:
                    continue
            
            # Filter by scheme name if provided
            if scheme_name:
                name = scheme.get("scheme_name", "").lower()
                if scheme_name.lower() not in name:
                    continue
            
            # Get eligibility and benefits for truncation
            eligibility = scheme.get("eligibility", [])
            benefits = scheme.get("benefits", [])
            
            # Truncate eligibility (keep first 3 items, max 200 chars each)
            eligibility_truncated = _truncate_list(eligibility, max_items=3, max_chars_per_item=200)
            
            # Truncate benefits (keep first 2 items, max 200 chars each)
            benefits_truncated = _truncate_list(benefits, max_items=2, max_chars_per_item=200)
            
            # Create eligibility summary (first item or first 200 chars)
            eligibility_summary = ""
            if eligibility:
                first_eligibility = eligibility[0] if isinstance(eligibility, list) else str(eligibility)
                eligibility_summary = _truncate_text(str(first_eligibility), max_chars=200)
            
            # Include scheme in results with truncated data
            filtered_schemes.append({
                "scheme_name": scheme.get("scheme_name", ""),
                "short_name": scheme.get("short_name", ""),
                "state": scheme_state if scheme_state else "Central",
                "scheme_type": "Central" if scheme_state == "" else "State",
                "scheme_for": scheme.get("scheme_for", ""),
                "category": scheme.get("category", []),
                "sub_category": scheme.get("sub_category", []),
                "brief_description": _truncate_text(scheme.get("brief_description", ""), max_chars=300),
                "eligibility": eligibility_truncated,
                "eligibility_summary": eligibility_summary,
                "benefits": benefits_truncated,
                "references": scheme.get("references", [])
            })
        
        # Limit to top 3 schemes
        return json.dumps({
            "count": len(filtered_schemes),
            "schemes": filtered_schemes[:3]  # Limit to top 3 results
        }, indent=2, ensure_ascii=False)
        
    except FileNotFoundError:
        logger.error(f"Schemes file not found: {SCHEMES_FILE}")
        return json.dumps({"error": f"Schemes file not found: {SCHEMES_FILE}"})
    except Exception as e:
        logger.error(f"Scheme tool error: {e}")
        return json.dumps({"error": f"Failed to load schemes: {e}"})

class ReasonerNode:
    """Reasoner Node - Analyzes user input and determines which agents to trigger"""
    
    def __init__(self):
        self.llm = AgriMitraLLM()
    
    def process(self, user_input: str) -> Dict[str, Any]:
        """Process user input and determine agent routing"""
        logger.info(f"Reasoner processing: {user_input}")
        
        try:
            response = self.llm.chat(REASONER_SYSTEM_PROMPT, user_input)
            
            # Try to parse JSON response
            try:
                parsed_response = json.loads(response)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                logger.warning("Failed to parse JSON, using fallback logic")
                parsed_response = self._fallback_reasoning(user_input)
            
            logger.info(f"Reasoner output: {parsed_response}")
            # If out_of_scope, ensure no next nodes
            next_nodes = parsed_response.get("agents_to_trigger", [])
            if parsed_response.get("intent") and "out_of_scope" in parsed_response.get("intent"):
                next_nodes = []
            return {
                "reasoner_output": parsed_response,
                "user_input": user_input,
                "next_nodes": next_nodes
            }
            
        except Exception as e:
            logger.error(f"Reasoner error: {e}")
            return {
                "reasoner_output": {"error": str(e)},
                "user_input": user_input,
                "next_nodes": []
            }
    
    def _fallback_reasoning(self, user_input: str) -> Dict[str, Any]:
        """Fallback reasoning when JSON parsing fails"""
        user_lower = user_input.lower()
        
        # Simple keyword-based reasoning
        disease_keywords = ['disease', 'sick', 'infected', 'spots', 'mold', 'wilting', 'yellow']
        price_keywords = ['price', 'market', 'sell', 'cost', 'value']
        scheme_keywords = ['scheme', 'schemes', 'subsidy', 'subsidies', 'government', 'govt', 'eligible', 'eligibility', 'benefit', 'benefits', 'assistance', 'program', 'programme']
        
        has_disease = any(keyword in user_lower for keyword in disease_keywords)
        has_price = any(keyword in user_lower for keyword in price_keywords)
        has_scheme = any(keyword in user_lower for keyword in scheme_keywords)
        
        crop = None
        for crop_name in MOCK_PRICE_DATA.keys():
            if crop_name in user_lower:
                crop = crop_name
                break
        
        # Extract state if mentioned
        states = [
            "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
            "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
            "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
            "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
            "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
            "delhi", "jammu and kashmir", "ladakh", "puducherry"
        ]
        state = None
        for s in states:
            if s in user_lower:
                state = s.title()
                break
        
        intent = []
        agents = []
        
        if has_disease:
            intent.append("disease")
            agents.append("disease_agent")
        
        if has_price:
            intent.append("market")
            agents.append("price_agent")
        
        if has_scheme:
            intent.append("scheme")
            agents.append("scheme_agent")
        
        if not intent:  # Default to disease if unclear
            intent = ["disease"]
            agents = ["disease_agent"]
        
        return {
            "intent": intent,
            "crop": crop,
            "state": state,
            "agents_to_trigger": agents
        }

class DiseaseAgentNode:
    """Disease Agent - Diagnoses plant diseases and provides remedies"""
    
    def __init__(self):
        self.llm = AgriMitraLLM()
    
    def process(self, user_input: str, crop: Optional[str] = None) -> Dict[str, Any]:
        """Process disease diagnosis request"""
        logger.info(f"DiseaseAgent processing: {user_input}")
        
        # Prepare context with crop information
        context = user_input
        if crop:
            context = f"Crop: {crop}. Symptoms: {user_input}"
        
        try:
            response = self.llm.chat(DISEASE_AGENT_SYSTEM_PROMPT, context)
            
            # Parse response
            try:
                diagnosis = json.loads(response)
            except json.JSONDecodeError:
                # Fallback diagnosis
                diagnosis = {
                    "disease": "Unknown disease",
                    "confidence": "low",
                    "needs_remedy": False,
                    "explanation": "Unable to parse diagnosis, please provide more specific symptoms"
                }
            
            remedy_info = None
            if diagnosis.get("needs_remedy", False):
                remedy_result = remedy_tool.invoke({"disease_name": diagnosis["disease"]})
                remedy_info = json.loads(remedy_result)

            # Detect if user asked for nearby shops and try to fetch using tools
            shops_info = None
            text_lower = user_input.lower()
            ask_shop_keywords = [
                "fertilizer shop", "fertilizer shops", "fertiliser shop", "fertiliser shops",
                "agro shop", "agro shops", "agri input", "agri store", "agri stores",
                "buy fertilizer", "where to buy", "shop near", "shops near", "store near"
            ]
            if any(k in text_lower for k in ask_shop_keywords):
                logger.info("Shop search requested by user query")
                # Extract location after 'in|at|near <location>' up to a stop token
                loc = None
                m = re.search(r"\b(?:in|at|near)\s+([a-zA-Z\s,]+?)\b(?:to|for|\.|,|$)", user_input, re.IGNORECASE)
                if m:
                    loc = m.group(1).strip()
                # If still no loc, try shorter cleanup by trimming trailing purpose phrases
                if not loc:
                    maybe_loc = re.sub(r"\b(to|for)\b.*$", "", user_input, flags=re.IGNORECASE).strip()
                    # Heuristic: if contains at least one space and not too long, attempt
                    if 2 <= len(maybe_loc.split()) <= 6:
                        loc = maybe_loc
                # Final fallback: try just the last proper noun token if present
                if not loc:
                    toks = re.findall(r"[A-Z][a-z]+", user_input)
                    if toks:
                        loc = toks[-1]
                if loc:
                    logger.info(f"Geocoding location for shop search: {loc}")
                    geo_raw = geocode_location.invoke({"query": loc})
                    geo = json.loads(geo_raw)
                    if not geo.get("error"):
                        shops_raw = find_fertilizer_shops.invoke({
                            "lat": geo["lat"],
                            "lon": geo["lon"],
                            "radius_m": 10000
                        })
                        shops_info = {
                            "location": geo,
                            "results": json.loads(shops_raw)
                        }
                    else:
                        logger.info(f"Geocoding failed for location: {loc} -> {geo}")
                else:
                    logger.info("No location detected for shop search request")
            
            result = {
                "disease_diagnosis": diagnosis,
                "remedy_info": remedy_info,
                "shops_info": shops_info,
                "agent": "disease_agent"
            }
            
            logger.info(f"DiseaseAgent output: {result}")
            return result
            
        except Exception as e:
            logger.error(f"DiseaseAgent error: {e}")
            return {
                "disease_diagnosis": {"error": str(e)},
                "remedy_info": None,
                "agent": "disease_agent"
            }

class PriceAgentNode:
    """Price Agent - Provides market price information and selling advice"""
    
    def __init__(self):
        pass  # No LLM needed for this agent
    
    def process(self, crop: str) -> Dict[str, Any]:
        """Process price information request"""
        logger.info(f"PriceAgent processing crop: {crop}")
        
        try:
            price_result = price_tool.invoke({"crop_name": crop})
            price_info = json.loads(price_result)
            
            result = {
                "price_info": price_info,
                "agent": "price_agent"
            }
            
            logger.info(f"PriceAgent output: {result}")
            return result
            
        except Exception as e:
            logger.error(f"PriceAgent error: {e}")
            return {
                "price_info": {"error": str(e)},
                "agent": "price_agent"
            }

class SchemeAgentNode:
    """Scheme Agent - Checks eligibility and finds relevant agricultural schemes"""
    
    def __init__(self):
        self.llm = AgriMitraLLM()
        self._subcategories_cache = None
    
    def _load_all_subcategories(self) -> List[str]:
        """Load all unique sub-categories from schemes file for better matching"""
        if self._subcategories_cache is not None:
            return self._subcategories_cache
        
        try:
            with open(SCHEMES_FILE, 'r', encoding='utf-8') as f:
                all_schemes = json.load(f)
            
            subcategories_set = set()
            for scheme in all_schemes:
                sub_categories = scheme.get("sub_category", [])
                for sub_cat in sub_categories:
                    if sub_cat and sub_cat.strip():
                        subcategories_set.add(sub_cat.strip())
            
            self._subcategories_cache = sorted(list(subcategories_set))
            logger.info(f"Loaded {len(self._subcategories_cache)} unique sub-categories")
            return self._subcategories_cache
        except Exception as e:
            logger.error(f"Error loading sub-categories: {e}")
            return []
    
    def process(self, user_input: str, state: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        """Process scheme eligibility check request"""
        logger.info(f"SchemeAgent processing: {user_input}")
        
        try:
            # Use LLM to extract state, category, sub_category from user input
            context = f"User query: {user_input}"
            if state:
                context += f"\nUser's state: {state}"
            
            response = self.llm.chat(SCHEME_AGENT_SYSTEM_PROMPT, context)
            
            # Parse LLM response
            try:
                parsed_response = json.loads(response)
                search_state = parsed_response.get("state", state or "")
                search_category = parsed_response.get("category", category or "")
                search_sub_category = parsed_response.get("sub_category", "")
                search_scheme_name = parsed_response.get("scheme_name", "")
                needs_subcategories = parsed_response.get("needs_subcategories", False)
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM response, using fallback logic")
                search_state = state or self._extract_state_from_input(user_input)
                search_category = category or ""
                search_sub_category = self._extract_subcategory_from_input(user_input)
                search_scheme_name = ""
                # If state is specified but no sub-category, show sub-categories
                needs_subcategories = bool(search_state and not search_sub_category)
            
            # If LLM didn't extract sub-category, try improved extraction
            if not search_sub_category:
                search_sub_category = self._extract_subcategory_from_input(user_input)
            
            # Check if user explicitly asks for sub-categories or state specified without sub-category
            user_lower = user_input.lower()
            explicit_subcategory_request = any(keyword in user_lower for keyword in [
                "list of", "show categories", "what categories", "available categories",
                "sub-categories", "subcategories", "all categories", "options"
            ])
            
            # If state is specified but no sub-category found, return sub-categories list
            if (explicit_subcategory_request or needs_subcategories) and search_state and not search_sub_category:
                logger.info("Returning sub-categories list for state: " + search_state)
                subcategories_result = get_subcategories_tool.invoke({"state": search_state})
                subcategories_info = json.loads(subcategories_result)
                
                return {
                    "subcategories_info": subcategories_info,
                    "search_params": {
                        "state": search_state,
                        "category": search_category
                    },
                    "agent": "scheme_agent",
                    "response_type": "subcategories"
                }
            
            # If sub-category is specified, get schemes filtered by state + sub-category
            if search_sub_category:
                logger.info(f"Searching schemes for state: {search_state}, sub-category: {search_sub_category}")
                scheme_result = scheme_tool.invoke({
                    "state": search_state,
                    "category": search_category,
                    "sub_category": search_sub_category,
                    "scheme_name": search_scheme_name
                })
                scheme_info = json.loads(scheme_result)
                
                # Generate eligibility questions based on shortlisted schemes
                eligibility_questions = []
                if scheme_info.get("schemes") and len(scheme_info["schemes"]) > 0:
                    eligibility_questions = self.generate_eligibility_questions(
                        user_input, 
                        scheme_info["schemes"]
                    )
                
                return {
                    "scheme_info": scheme_info,
                    "eligibility_questions": eligibility_questions,
                    "search_params": {
                        "state": search_state,
                        "category": search_category,
                        "sub_category": search_sub_category,
                        "scheme_name": search_scheme_name
                    },
                    "agent": "scheme_agent",
                    "response_type": "schemes"
                }
            else:
                # No sub-category and no state - return all schemes or error
                return {
                    "scheme_info": {"error": "Please specify a state or sub-category"},
                    "agent": "scheme_agent"
                }
            
        except Exception as e:
            logger.error(f"SchemeAgent error: {e}")
            return {
                "scheme_info": {"error": str(e)},
                "agent": "scheme_agent"
            }
    
    def generate_eligibility_questions(self, user_query: str, schemes: List[Dict[str, Any]]) -> List[str]:
        """Generate eligibility questions based on scheme eligibility criteria"""
        try:
            eligibility_criteria = []
            for scheme in schemes:
                scheme_name = scheme.get("scheme_name", "")
                eligibility = scheme.get("eligibility", [])
                eligibility_summary = scheme.get("eligibility_summary", "")
                
                if eligibility_summary:
                    eligibility_criteria.append(f"Scheme: {scheme_name}\nCriteria: {eligibility_summary}")
                elif eligibility:
                    criteria_text = "\n".join(eligibility[:3])
                    eligibility_criteria.append(f"Scheme: {scheme_name}\nCriteria: {criteria_text}")
            
            if not eligibility_criteria:
                return []
            
            context = f"User query: {user_query}\n\n"
            context += "Eligibility criteria from schemes:\n"
            context += "\n\n".join(eligibility_criteria)
            context += "\n\nGenerate 3-5 key eligibility questions that will help determine if the user qualifies for these schemes."
            
            response = self.llm.chat(SCHEME_ELIGIBILITY_PROMPT, context)
            
            # Try to parse as JSON first
            try:
                parsed = json.loads(response)
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, dict) and "questions" in parsed:
                    return parsed["questions"]
            except json.JSONDecodeError:
                pass
            
            # Extract questions from text
            questions = []
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                line = re.sub(r'^[\d\.\-\*\)]\s*', '', line)
                if line and len(line) > 10 and '?' in line:
                    questions.append(line)
            
            return questions[:5]
            
        except Exception as e:
            logger.error(f"Error generating eligibility questions: {e}")
            return []
    
    def _extract_state_from_input(self, user_input: str) -> str:
        """Extract state from user input"""
        states = [
            "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
            "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
            "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
            "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
            "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
            "Delhi", "Jammu and Kashmir", "Ladakh", "Puducherry"
        ]
        
        user_lower = user_input.lower()
        for state in states:
            if state.lower() in user_lower:
                return state
        
        return ""
    
    def _extract_subcategory_from_input(self, user_input: str) -> str:
        """Extract sub-category from user input"""
        user_lower = user_input.lower()
        all_subcategories = self._load_all_subcategories()
        
        # First, try exact phrase match (prioritize longer/more specific matches)
        # Sort by length descending to match more specific sub-categories first
        sorted_subcategories = sorted(all_subcategories, key=len, reverse=True)
        for sub_cat in sorted_subcategories:
            sub_cat_lower = sub_cat.lower()
            # Check if the entire sub-category phrase is in the user input
            if sub_cat_lower in user_lower:
                logger.info(f"Found exact sub-category match: {sub_cat}")
                return sub_cat
        
        # Second, try word-by-word match (all words must be present)
        best_exact_match = ""
        best_exact_score = 0
        for sub_cat in sorted_subcategories:
            sub_cat_words = [w for w in sub_cat.lower().split() if len(w) > 2]  # Words longer than 2 chars
            if not sub_cat_words:
                continue
            # Check if all significant words are present
            all_words_present = all(word in user_lower for word in sub_cat_words)
            if all_words_present:
                score = len(sub_cat_words)  # Prefer matches with more words (more specific)
                if score > best_exact_score:
                    best_exact_match = sub_cat
                    best_exact_score = score
        
        if best_exact_match:
            logger.info(f"Found word-by-word sub-category match: {best_exact_match}")
            return best_exact_match
        
        # Third, try partial match (50%+ words match)
        best_match = ""
        best_score = 0
        for sub_cat in sorted_subcategories:
            sub_cat_words = [w for w in sub_cat.lower().split() if len(w) > 3]
            if not sub_cat_words:
                continue
            matches = sum(1 for word in sub_cat_words if word in user_lower)
            score = matches / len(sub_cat_words)
            if score > 0.5 and score > best_score:
                best_match = sub_cat
                best_score = score
        
        if best_match:
            logger.info(f"Found partial sub-category match: {best_match} (score: {best_score:.2f})")
            return best_match
        
        # Fourth, keyword mapping (for common terms)
        keyword_mapping = {
            "soil health": "Soil health",
            "soil": "Soil health",
            "animal": "Animal husbandry", "husbandry": "Animal husbandry",
            "dairy": "Animal husbandry", "poultry": "Animal husbandry",
            "livestock": "Animal husbandry",
            "financial": "Financial assistance", "loan": "Financial assistance",
            "subsidy": "Financial assistance", "fishing": "Fishing and hunting",
            "fisheries": "Fishing and hunting",
            "seeds": "Agricultural Inputs- seeds, fertilizer etc.",
            "fertilizer": "Agricultural Inputs- seeds, fertilizer etc.",
            "fertiliser": "Agricultural Inputs- seeds, fertilizer etc.",
            "insurance": "Crop insurance", "irrigation": "Irrigation",
            "organic": "Organic farming", "compost": "Soil health",
            "vermicompost": "Soil health", "vermi-compost": "Soil health"
        }
        
        # Check keyword mapping (prioritize longer keywords first)
        for keyword in sorted(keyword_mapping.keys(), key=len, reverse=True):
            if keyword in user_lower:
                sub_cat = keyword_mapping[keyword]
                if sub_cat in all_subcategories:
                    logger.info(f"Found sub-category via keyword mapping: {sub_cat} (keyword: {keyword})")
                    return sub_cat
        
        return ""

class CoordinatorNode:
    """Coordinator Node - Synthesizes outputs from all agents"""
    
    def __init__(self):
        self.llm = AgriMitraLLM()
    
    def process(self, user_input: str, agent_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process and synthesize all agent outputs"""
        logger.info(f"Coordinator processing {len(agent_outputs)} agent outputs")
        
        # Prepare context for synthesis
        context = f"Original farmer query: {user_input}\n\n"
        context += "Agent outputs:\n"
        
        for output in agent_outputs:
            context += f"- {output.get('agent', 'unknown')}: {json.dumps(output, indent=2)}\n"
        
        try:
            # If reasoner marked out_of_scope, bypass LLM and return refusal
            try:
                # Attempt to detect out_of_scope from agent_outputs context
                # The reasoner output is added to workflow state, but not passed here directly
                # We infer out_of_scope if there are no agent outputs and the query seems non-agri
                non_agri_clues = [
                    'who is ', 'what is ', 'when was ', 'biography', 'president', 'movie', 'capital of', 'history', 'celebrity'
                ]
                u_lower = user_input.lower()
                if len(agent_outputs) == 0 and any(k in u_lower for k in non_agri_clues):
                    refusal = (
                        "This system only answers agriculture-focused questions (crops, plant diseases, farm practices, "
                        "and market prices). Your query appears to be outside this scope. Please ask something related to "
                        "plants or agriculture."
                    )
                    return {
                        "final_response": refusal,
                        "agent_outputs": agent_outputs,
                        "agent": "coordinator"
                    }
            except Exception:
                pass

            response = self.llm.chat(COORDINATOR_SYSTEM_PROMPT, context)
            
            result = {
                "final_response": response,
                "agent_outputs": agent_outputs,
                "agent": "coordinator"
            }
            
            logger.info("Coordinator synthesis completed")
            return result
            
        except Exception as e:
            logger.error(f"Coordinator error: {e}")
            return {
                "final_response": f"Error in coordination: {e}",
                "agent_outputs": agent_outputs,
                "agent": "coordinator"
            }

