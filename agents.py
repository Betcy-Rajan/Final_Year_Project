"""
AgriMitra Agentic Prototype - Agent implementations
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import requests
import re
from config import (
    REASONER_SYSTEM_PROMPT, DISEASE_AGENT_SYSTEM_PROMPT, 
    COORDINATOR_SYSTEM_PROMPT, MOCK_PRICE_DATA, REMEDIES_FILE,
    SCHEME_AGENT_SYSTEM_PROMPT, SCHEME_ELIGIBILITY_PROMPT, SCHEMES_FILE,
    
)
try:
    from cnn_model import PlantDiseaseCNN
    CNN_AVAILABLE = True
except ImportError as e:
    CNN_AVAILABLE = False
    error_msg = str(e)
    if "tensorflow" in error_msg.lower() or "keras" in error_msg.lower():
        logging.warning(
            "CNN model module not available: TensorFlow/Keras not installed. "
            "Image-based disease detection is disabled. To enable it, install TensorFlow: pip install tensorflow>=2.13.0"
        )
    else:
        logging.warning(f"CNN model module not available: {error_msg}. Image-based detection disabled.")

try:
    from scheme_rag_agent import SchemeRAGAgent, UserProfile, QueryParser
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning("RAG agent not available - using fallback scheme search")

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
            price_keywords = ['price', 'market', 'cost', 'value', 'rate', 'mandi']
            sell_keywords = ['sell', 'find buyer', 'looking for buyer', 'want to sell', 'need buyer', 'find buyer for']
            scheme_keywords = ['scheme', 'schemes', 'subsidy', 'subsidies', 'government', 'govt', 'eligible', 'eligibility', 'benefit', 'benefits', 'assistance', 'program', 'programme']
            has_disease = any(keyword in user_lower for keyword in disease_keywords)
            has_price = any(keyword in user_lower for keyword in price_keywords)
            has_sell = any(keyword in user_lower for keyword in sell_keywords)
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
            
            if has_price and not has_sell:  # Don't trigger price_agent if it's a sell request
                intent.append("market")
                agents.append("price_agent")
            
            if has_sell:
                intent.append("sell")
                agents.append("buyer_connect_agent")
            
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
def get_current_location() -> str:
    """Automatically get current location (latitude/longitude) using IP-based geolocation."""
    try:
        # Use ip-api.com free service for IP-based geolocation
        resp = requests.get(
            "http://ip-api.com/json/",
            params={"fields": "status,message,lat,lon,city,region,country"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("status") == "success":
            return json.dumps({
                "lat": float(data.get("lat", 0)),
                "lon": float(data.get("lon", 0)),
                "display_name": f"{data.get('city', '')}, {data.get('region', '')}, {data.get('country', '')}".strip(", "),
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country")
            })
        else:
            return json.dumps({"error": f"IP geolocation failed: {data.get('message', 'Unknown error')}"})
    except Exception as e:
        logger.error(f"Current location error: {e}")
        return json.dumps({"error": f"Failed to get current location: {e}"})

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

# Fertilizer shop tool
def _generate_google_maps_search_urls(lat: float, lon: float, location_name: str = None) -> List[Dict[str, str]]:
    """Generate Google Maps search URLs for fertilizer shops (NO API KEY REQUIRED - FREE)
    
    Returns a list of search URLs that users can open directly in their browser.
    """
    search_queries = [
        "fertilizer shop",
        "agricultural input store",
        "agro shop",
        "pesticide shop",
        "seed store",
        "fertilizer store"
    ]
    
    urls = []
    base_location = location_name if location_name else f"{lat},{lon}"
    
    for query in search_queries:
        # Google Maps search URL format (NO API KEY REQUIRED - FREE)
        # Format 1: Direct search with location
        query_encoded = query.replace(' ', '+')
        search_url = f"https://www.google.com/maps/search/{query_encoded}/@{lat},{lon},15z"
        
        # Alternative format using query parameters (more reliable)
        alt_url = f"https://www.google.com/maps/search/?api=1&query={query_encoded}+near+{lat},{lon}"
        
        urls.append({
            "query": query,
            "url": search_url,
            "alt_url": alt_url,
            "description": f"Search for {query} near this location"
        })
    
    return urls

@tool
def find_fertilizer_shops(lat: float, lon: float, radius_m: int = 20000) -> str:
    """Find nearby fertilizer/agro input shops using Google Maps search URLs.
    
    Uses Google Maps search URLs (FREE, NO API KEY REQUIRED) based on latitude and longitude.
    Users can click the URLs to see shops directly on Google Maps.
    
    Args:
        lat: Latitude of the location
        lon: Longitude of the location
        radius_m: Radius in meters (used for information, Google Maps handles the search)
    
    Returns:
        JSON string with Google Maps search URLs for various fertilizer shop searches
    """
    # Generate Google Maps search URLs (FREE, NO API KEY REQUIRED)
    logger.info("Generating Google Maps search URLs (free, no API key)...")
    google_maps_urls = _generate_google_maps_search_urls(lat, lon)
    
    # Prepare response with Google Maps URLs
    response_data = {
        "count": 0,  # No shop count since we're only providing URLs
        "shops": [],  # No shop data, only URLs
        "google_maps_search_urls": google_maps_urls,
        "location": {
            "lat": lat,
            "lon": lon,
            "radius_meters": radius_m
        },
        "note": "Click the Google Maps URLs above to see shops directly on Google Maps (free, no API key required)"
    }
    
    return json.dumps(response_data, indent=2)
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
        logger.error(f"Overpass error: {e}")
        return json.dumps({"error": f"Overpass query failed: {e}"})



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
def scheme_tool(
    state: str = "",
    category: str = "",
    scheme_name: str = "",
    sub_category: str = "",
    scheme_scope: str = "all",
) -> str:
    """Tool to search and filter agricultural schemes from agri_schemes_cleaned.json.
    
    Args:
        state: State name to filter schemes. If empty string "", returns central schemes.
        category: Optional category filter (e.g., "Agriculture,Rural & Environment")
        scheme_name: Optional scheme name to search for (partial match)
        sub_category: Optional sub-category filter (e.g., "Animal husbandry")
        scheme_scope: "all" (default), "state_only", "central_only", or "both" (alias to all)
    
    Returns:
        JSON string with matching schemes and their eligibility information (limited to top 10)
    """
    try:
        with open(SCHEMES_FILE, 'r', encoding='utf-8') as f:
            all_schemes = json.load(f)
        
        filtered_schemes = []
        
        for scheme in all_schemes:
            scheme_state = scheme.get("state", "")
            
            # Scope filtering
            if scheme_scope == "central_only":
                if scheme_state != "":
                    continue
            elif scheme_scope == "state_only":
                if not state:
                    continue
                if scheme_state.lower() != state.lower():
                    continue
            else:
                # Default behavior: if state provided, include that state + central
                if state:
                    if scheme_state.lower() != state.lower() and scheme_state != "":
                        continue
                else:
                    # No state specified - include all
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
        
        # Limit to top 10 schemes
        return json.dumps({
            "count": len(filtered_schemes),
            "schemes": filtered_schemes[:10]  # Limit to top 10 results
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
            print(f"🎯 REASONER: Intent={parsed_response.get('intent')}, Agents={parsed_response.get('agents_to_trigger')}, Crop={parsed_response.get('crop')}")
            
            # If out_of_scope, ensure no next nodes
            next_nodes = parsed_response.get("agents_to_trigger", [])
            if parsed_response.get("intent") and "out_of_scope" in parsed_response.get("intent"):
                next_nodes = []
            return {
                "intent": parsed_response.get("intent", []),
                "crop": parsed_response.get("crop"),
                "agents_to_trigger": next_nodes,
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
        
        # Simple keyword-based reasoning - expanded keywords
        disease_keywords = ['disease', 'sick', 'infected', 'spots', 'spot', 'mold', 'wilting', 'yellow', 'yellowing', 'brown', 'black', 'leaf', 'leaves', 'blight', 'mildew', 'rot', 'damage', 'problem', 'issue', 'unhealthy', 'weak', 'dying', 'curling', 'curled']
        price_keywords = ['price', 'market', 'cost', 'value', 'rate', 'mandi']
        sell_keywords = ['sell', 'find buyer', 'looking for buyer', 'want to sell', 'need buyer', 'find buyer for']
        scheme_keywords = ['scheme', 'schemes', 'subsidy', 'subsidies', 'government', 'govt', 'eligible', 'eligibility', 'benefit', 'benefits', 'assistance', 'program', 'programme']
        
        has_disease = any(keyword in user_lower for keyword in disease_keywords)
        has_price = any(keyword in user_lower for keyword in price_keywords)
        has_sell = any(keyword in user_lower for keyword in sell_keywords)
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
        
        if has_price and not has_sell:  # Don't trigger price_agent if it's a sell request
            intent.append("market")
            agents.append("price_agent")
        
        if has_sell:
            intent.append("sell")
            agents.append("buyer_connect_agent")
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
        # Initialize CNN model if available
        self.cnn_model = None
        if CNN_AVAILABLE:
            try:
                self.cnn_model = PlantDiseaseCNN()
                if self.cnn_model.is_available():
                    logger.info("CNN model loaded successfully for image-based disease detection")
                else:
                    logger.warning("CNN model file not found or could not be loaded")
            except Exception as e:
                logger.warning(f"Could not initialize CNN model: {e}")
    
    def process(self, user_input: str, crop: Optional[str] = None, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Process disease diagnosis request - handles both image and text inputs"""
        logger.info(f"DiseaseAgent processing: {user_input}, image_path: {image_path}")
        
        # Check if image file exists and CNN model is available
        image_exists = image_path and os.path.exists(image_path)
        cnn_available = self.cnn_model and self.cnn_model.is_available()
        has_image = image_exists and cnn_available
        
        # Check if meaningful text is provided (not just default image query)
        has_text = user_input and user_input.strip() and user_input.strip() != "Analyze this plant image for disease detection"
        
        # If image is provided but CNN is not available, return helpful error
        if image_exists and not cnn_available:
            logger.warning(f"Image provided ({image_path}) but CNN model is not available. TensorFlow required for image-based detection.")
            
            # If meaningful text is provided, still process it
            if has_text:
                logger.info("Processing text-based disease detection as fallback")
                text_result = self._process_text(user_input, crop)
                # Add a note about image processing being unavailable
                text_result["image_processing_note"] = {
                    "image_provided": True,
                    "cnn_unavailable": True,
                    "message": "Image-based disease detection requires TensorFlow. Please install it: pip install tensorflow>=2.13.0",
                    "fallback_to_text": True
                }
                return text_result
            else:
                # No text and no CNN - return error message
                return {
                    "disease_info": {
                        "identified_disease": "Image Analysis Unavailable",
                        "disease": "Image Analysis Unavailable",
                        "confidence": "low",
                        "confidence_score": 0.0,
                        "symptoms": [],
                        "description": "Image-based disease detection is not available. TensorFlow is required to analyze plant images. Please install it: pip install tensorflow>=2.13.0. Alternatively, describe the symptoms in text for diagnosis."
                    },
                    "disease_diagnosis": {
                        "disease": "Image Analysis Unavailable",
                        "confidence": "low",
                        "needs_remedy": False,
                        "explanation": "Image-based disease detection requires TensorFlow. Install it: pip install tensorflow>=2.13.0",
                        "error": "CNN model not available"
                    },
                    "remedy_info": None,
                    "shops_info": None,
                    "detection_method": "error",
                    "agent": "disease_agent",
                    "image_processing_note": {
                        "image_provided": True,
                        "cnn_unavailable": True,
                        "message": "TensorFlow required for image-based detection. Install: pip install tensorflow>=2.13.0"
                    }
                }
        
        # Normal processing when CNN is available or no image
        if has_image and has_text:
            # Process both and compare confidence scores
            logger.info("Processing both image and text inputs, will compare confidence scores")
            image_result = self._process_image(image_path, user_input)
            text_result = self._process_text(user_input, crop)
            
            # Extract confidence scores
            image_confidence = self._get_confidence_score(image_result)
            text_confidence = self._get_confidence_score(text_result)
            
            logger.info(f"Image confidence: {image_confidence}, Text confidence: {text_confidence}")
            
            # Return the result with higher confidence
            if image_confidence >= text_confidence:
                logger.info("Selecting image-based result (higher confidence)")
                return image_result
            else:
                logger.info("Selecting text-based result (higher confidence)")
                return text_result
        elif has_image:
            logger.info("Processing image-based disease detection")
            return self._process_image(image_path, user_input)
        else:
            logger.info("Processing text-based disease detection")
            return self._process_text(user_input, crop)
    
    def _get_confidence_score(self, result: Dict[str, Any]) -> float:
        """Extract confidence score from result (numeric value between 0.0 and 1.0)"""
        diagnosis = result.get("disease_diagnosis", {})
        
        # Check if confidence_score exists (from image processing)
        if "confidence_score" in diagnosis:
            return float(diagnosis["confidence_score"])
        
        # Convert text confidence string to numeric score
        confidence_str = diagnosis.get("confidence", "low").lower()
        if confidence_str == "high":
            return 0.8
        elif confidence_str == "medium":
            return 0.5
        else:  # low or unknown
            return 0.3
    
    def _process_image(self, image_path: str, user_input: str) -> Dict[str, Any]:
        """Process disease diagnosis from image using CNN model"""
        try:
            # Get CNN prediction
            cnn_result = self.cnn_model.predict(image_path)
            
            if "error" in cnn_result:
                logger.error(f"CNN prediction error: {cnn_result['error']}")
                # Fallback to text-based if CNN fails
                return self._process_text(user_input, cnn_result.get("crop"))
            
            disease = cnn_result.get("disease")
            crop = cnn_result.get("crop")
            confidence = cnn_result.get("confidence", 0.0)
            full_class_name = cnn_result.get("full_class_name", "")
            is_healthy = cnn_result.get("is_healthy", False)
            
            # Extract disease name from full_class_name if not provided directly
            if not disease and full_class_name:
                # Full class name format: "Crop___Disease" or "Crop___healthy"
                parts = full_class_name.split("___")
                if len(parts) >= 2 and "healthy" not in parts[1].lower():
                    disease = parts[1].replace("_", " ").strip()
                elif "healthy" in full_class_name.lower():
                    disease = None  # Will be set to "Healthy" below
            
            # Determine the disease name to display
            if is_healthy:
                disease_name = "Healthy"
            elif disease:
                disease_name = disease
            elif full_class_name:
                # Fallback: extract from class name
                parts = full_class_name.split("___")
                if len(parts) >= 2:
                    disease_name = parts[1].replace("_", " ").strip()
                else:
                    disease_name = "Unknown disease"
            else:
                disease_name = "Unknown disease"
            
            # Create diagnosis structure
            diagnosis = {
                "disease": disease_name,
                "crop": crop,
                "confidence": "high" if confidence > 0.8 else "medium" if confidence > 0.5 else "low",
                "confidence_score": confidence,
                "needs_remedy": not is_healthy and disease_name and disease_name != "Healthy",
                "explanation": f"CNN model detected: {full_class_name} with {confidence*100:.1f}% confidence",
                "is_healthy": is_healthy,
                "detection_method": "CNN",
                "top_3_predictions": cnn_result.get("top_3_predictions", [])
            }
            
            # Get remedy if disease detected
            remedy_info = None
            if diagnosis.get("needs_remedy", False) and disease_name and disease_name != "Healthy":
                # Try multiple disease name variations
                remedy_result = remedy_tool.invoke({"disease_name": disease_name})
                remedy_data = json.loads(remedy_result)
                
                # If remedy not found, try with crop name prefix
                if "error" in remedy_data:
                    # Try alternative disease names
                    alternative_names = [
                        f"{crop} {disease_name}" if crop else disease_name,
                        disease_name.replace(" ", "_"),
                        disease_name.lower()
                    ]
                    for alt_name in alternative_names:
                        remedy_result = remedy_tool.invoke({"disease_name": alt_name})
                        remedy_data = json.loads(remedy_result)
                        if "error" not in remedy_data:
                            break
                
                remedy_info = remedy_data if "error" not in remedy_data else None
            
            # Automatically search for nearby fertilizer shops when disease is detected
            shops_info = None
            if diagnosis.get("needs_remedy", False) and disease_name and disease_name != "Healthy":
                logger.info("Disease detected - automatically searching for nearby fertilizer shops")
                shops_info = self._search_shops(user_input, auto_location=True)
            
            # Also check if user explicitly requested shop search
            if not shops_info:
                text_lower = user_input.lower() if user_input else ""
                ask_shop_keywords = [
                    "fertilizer shop", "fertilizer shops", "fertiliser shop", "fertiliser shops",
                    "agro shop", "agro shops", "agri input", "agri store", "agri stores",
                    "buy fertilizer", "where to buy", "shop near", "shops near", "store near"
                ]
                if any(k in text_lower for k in ask_shop_keywords):
                    shops_info = self._search_shops(user_input, auto_location=False)
            
            # Format disease info for consistency with text processing
            disease_name = diagnosis.get("disease", "Unknown disease")
            if disease_name == "Unknown disease (demo mode)":
                disease_name = "Unknown disease"
            
            # Create disease_info structure for frontend compatibility
            disease_info = {
                "identified_disease": disease_name,
                "disease": disease_name,
                "confidence": diagnosis.get("confidence", "low"),
                "confidence_score": diagnosis.get("confidence_score", 0.0),
                "symptoms": [],
                "description": diagnosis.get("explanation", ""),
                "crop": crop,
                "is_healthy": is_healthy
            }
            
            result = {
                "disease_info": disease_info,
                "disease_diagnosis": diagnosis,
                "remedy_info": remedy_info,
                "shops_info": shops_info,
                "cnn_result": cnn_result,
                "detection_method": "CNN",
                "agent": "disease_agent"
            }
            
            logger.info(f"DiseaseAgent (CNN) output: {result}")
            logger.info(f"DiseaseAgent (CNN) identified_disease: {disease_name}")
            return result
            
        except Exception as e:
            logger.error(f"DiseaseAgent (CNN) error: {e}")
            # Fallback to text-based processing
            return self._process_text(user_input, None)
    
    def _process_text(self, user_input: str, crop: Optional[str] = None) -> Dict[str, Any]:
        """Process disease diagnosis from text using LLM"""
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
            
            # Add confidence_score for consistency with image processing
            confidence_str = diagnosis.get("confidence", "low").lower()
            if confidence_str == "high":
                diagnosis["confidence_score"] = 0.8
            elif confidence_str == "medium":
                diagnosis["confidence_score"] = 0.5
            else:  # low or unknown
                diagnosis["confidence_score"] = 0.3
            
            remedy_info = None
            if diagnosis.get("needs_remedy", False):
                remedy_result = remedy_tool.invoke({"disease_name": diagnosis["disease"]})
                remedy_info = json.loads(remedy_result)

            # Automatically search for nearby fertilizer shops when disease is detected
            shops_info = None
            if diagnosis.get("needs_remedy", False) and diagnosis.get("disease") and diagnosis.get("disease") != "Healthy":
                logger.info("Disease detected - automatically searching for nearby fertilizer shops")
                shops_info = self._search_shops(user_input, auto_location=True)
            
            # Also check if user explicitly requested shop search
            if not shops_info:
                shops_info = self._search_shops(user_input, auto_location=False)
            
            # Format disease info for consistency with image processing
            disease_name = diagnosis.get("disease", "Unknown disease")
            if disease_name == "Unknown disease (demo mode)":
                disease_name = "Unknown disease"
            
            disease_info = {
                "identified_disease": disease_name,
                "disease": disease_name,
                "confidence": diagnosis.get("confidence", "low"),
                "confidence_score": diagnosis.get("confidence_score", 0.3),
                "symptoms": [],
                "description": diagnosis.get("explanation", "")
            }
            
            result = {
                "disease_info": disease_info,
                "disease_diagnosis": diagnosis,
                "remedy_info": remedy_info,
                "shops_info": shops_info,
                "detection_method": "LLM",
                "agent": "disease_agent"
            }
            
            logger.info(f"DiseaseAgent (Text) output: {result}")
            return result
            
        except Exception as e:
            logger.error(f"DiseaseAgent error: {e}")
            return {
                "disease_diagnosis": {"error": str(e)},
                "remedy_info": None,
                "agent": "disease_agent"
            }
    
    def _search_shops(self, user_input: str = None, auto_location: bool = False) -> Optional[Dict[str, Any]]:
        """Helper method to search for fertilizer shops.
        
        Args:
            user_input: User query text (optional if auto_location is True)
            auto_location: If True, automatically fetch current location instead of parsing from user_input
        """
        shops_info = None
        
        # If auto_location is True, automatically get current location
        if auto_location:
            logger.info("Automatically fetching current location for shop search")
            geo_raw = get_current_location.invoke({})
            geo = json.loads(geo_raw)
            if not geo.get("error"):
                logger.info(f"Current location detected: {geo.get('display_name', 'Unknown')}")
                shops_raw = find_fertilizer_shops.invoke({
                    "lat": geo["lat"],
                    "lon": geo["lon"],
                    "radius_m": 20000
                })
                shops_info = {
                    "location": geo,
                    "results": json.loads(shops_raw)
                }
            else:
                logger.warning(f"Failed to get current location: {geo.get('error')}")
            return shops_info
        
        # Otherwise, check if user explicitly requested shop search
        if not user_input:
            return None
            
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
                        "radius_m": 20000
                    })
                    shops_info = {
                        "location": geo,
                        "results": json.loads(shops_raw)
                    }
                else:
                    logger.info(f"Geocoding failed for location: {loc} -> {geo}")
            else:
                # If user asked for shops but no location provided, use current location
                logger.info("User requested shops but no location provided, using current location")
                geo_raw = get_current_location.invoke({})
                geo = json.loads(geo_raw)
                if not geo.get("error"):
                    shops_raw = find_fertilizer_shops.invoke({
                        "lat": geo["lat"],
                        "lon": geo["lon"],
                        "radius_m": 20000
                    })
                    shops_info = {
                        "location": geo,
                        "results": json.loads(shops_raw)
                    }
                else:
                    logger.info(f"Failed to get current location: {geo.get('error')}")
        return shops_info
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

class BuyerConnectAgentNode:
    """Buyer Connect Agent - Assists farmers in finding buyers and negotiating fair prices"""
    
    def __init__(self):
        # Import here to avoid circular dependencies
        from buyer_connect_storage import storage
        from buyer_connect_logic import find_matching_buyers, generate_price_suggestion
        from buyer_connect_models import FarmerListing, ListingStatus
        
        self.storage = storage
        self.find_matching_buyers = find_matching_buyers
        self.generate_price_suggestion = generate_price_suggestion
        self.FarmerListing = FarmerListing
        self.ListingStatus = ListingStatus
        self.price_agent = PriceAgentNode()
    
    def process(self, user_input: str, crop: Optional[str] = None, 
                quantity: Optional[float] = None, 
                farmer_threshold_price: Optional[float] = None,
                farmer_id: int = 1) -> Dict[str, Any]:
        """
        Process buyer connect request.
        
        This agent:
        1. Creates a farmer listing (if not exists)
        2. Finds matching buyers
        3. Fetches benchmark price from PriceAgent
        4. Runs negotiation engine for top matches
        5. Returns structured output with buyer matches and price suggestions
        """
        logger.info(f"BuyerConnectAgent processing: crop={crop}, quantity={quantity}, threshold_price={farmer_threshold_price}")
        
        try:
            # If crop, quantity, and price are provided, create/use listing
            listing = None
            if crop and quantity is not None and farmer_threshold_price is not None:
                # Create a listing
                listing = self.FarmerListing(
                    farmer_id=farmer_id,
                    crop=crop,
                    quantity=quantity,
                    unit="kg",
                    farmer_threshold_price=farmer_threshold_price,
                    status=self.ListingStatus.OPEN
                )
                listing = self.storage.create_listing(listing)
                logger.info(f"Created listing {listing.id} for buyer connect")
            
            # Get all buyers from old collection
            all_buyers = self.storage.get_all_buyers()
            
            # Find matching buyers from old buyers collection
            matched_buyers = []
            if listing:
                matched_buyers = self.find_matching_buyers(listing, all_buyers)
            
            # Also check buyer_requirements collection for matches
            if listing:
                try:
                    all_requirements = self.storage.get_buyer_requirements()
                    for requirement in all_requirements:
                        # Check if crop matches
                        if requirement.crop.lower() != listing.crop.lower():
                            continue
                        
                        # Flexible quantity matching - more lenient for smaller quantities
                        qty_match = False
                        # Check if listing quantity is within buyer's acceptable range (50% flexibility)
                        if (requirement.required_quantity * 0.5 <= listing.quantity <= requirement.required_quantity * 1.5):
                            qty_match = True
                        # Check if required quantity is within 50% of listing quantity
                        elif (listing.quantity * 0.5 <= requirement.required_quantity <= listing.quantity * 1.5):
                            qty_match = True
                        # Special case: if farmer has less quantity but buyer can accept smaller lots (at least 30% of requirement)
                        elif listing.quantity < requirement.required_quantity * 0.5 and listing.quantity >= requirement.required_quantity * 0.3:
                            qty_match = True
                        
                        if not qty_match:
                            continue
                        
                        # Flexible price matching
                        price_diff = abs(requirement.max_price - listing.farmer_threshold_price)
                        avg_price = (requirement.max_price + listing.farmer_threshold_price) / 2
                        if avg_price > 0:
                            price_diff_ratio = price_diff / avg_price
                            if price_diff_ratio > 0.20:  # More than 20% difference - skip
                                continue
                        else:
                            continue
                        
                        # Calculate match score
                        qty_diff = abs(requirement.required_quantity - listing.quantity)
                        max_qty = max(requirement.required_quantity, listing.quantity, 1)
                        qty_score = max(0, 1 - (qty_diff / max_qty))
                        price_score = max(0, 1 - price_diff_ratio)
                        match_score = (qty_score * 0.5) + (price_score * 0.5)
                        
                        # Get buyer info if available
                        buyer = None
                        try:
                            buyer_id_int = int(requirement.buyer_id) if isinstance(requirement.buyer_id, str) and requirement.buyer_id.isdigit() else requirement.buyer_id
                            buyer = self.storage.get_buyer(buyer_id_int)
                        except:
                            buyer = self.storage.get_buyer(requirement.buyer_id)
                        
                        buyer_name = buyer.name if buyer else f"Buyer {requirement.buyer_id}"
                        buyer_location = buyer.location if buyer else requirement.location
                        
                        # Convert buyer_id to int if possible
                        try:
                            buyer_id_for_match = int(requirement.buyer_id) if isinstance(requirement.buyer_id, str) and requirement.buyer_id.isdigit() else requirement.buyer_id
                        except:
                            buyer_id_for_match = requirement.buyer_id
                        
                        from buyer_connect_models import MatchedBuyer
                        matched_buyer = MatchedBuyer(
                            buyer_id=buyer_id_for_match,
                            buyer_name=buyer_name,
                            location=buyer_location,
                            preferred_price=requirement.max_price,
                            demand_range={
                                "min_qty": requirement.required_quantity * 0.8,
                                "max_qty": requirement.required_quantity * 1.2
                            },
                            match_score=match_score
                        )
                        matched_buyers.append(matched_buyer)
                    
                    # Sort by match score
                    matched_buyers.sort(key=lambda x: x.match_score or 0, reverse=True)
                except Exception as e:
                    logger.warning(f"Error checking buyer_requirements: {e}")
            
            # Get benchmark price from PriceAgent
            benchmark_price = None
            if crop:
                try:
                    price_result = self.price_agent.process(crop)
                    price_info = price_result.get("price_info", {})
                    if "error" not in price_info:
                        benchmark_price = price_info.get("current_price", 0)
                except Exception as e:
                    logger.warning(f"Failed to get benchmark price: {e}")
            
            # Generate price suggestions for top 3 matches
            price_suggestions = []
            for matched_buyer in matched_buyers[:3]:  # Top 3 matches
                buyer = self.storage.get_buyer(matched_buyer.buyer_id)
                if buyer and listing:
                    # Find buyer's crop interest
                    crop_interest = None
                    for interest in buyer.interested_crops:
                        if interest.crop.lower() == listing.crop.lower():
                            crop_interest = interest
                            break
                    
                    if crop_interest and benchmark_price:
                        suggestion = self.generate_price_suggestion(
                            farmer_threshold_price=listing.farmer_threshold_price,
                            buyer_preferred_price=crop_interest.preferred_price,
                            benchmark_price=benchmark_price
                        )
                        price_suggestions.append({
                            "buyer_id": matched_buyer.buyer_id,
                            "buyer_name": matched_buyer.buyer_name,
                            "suggestion": suggestion.dict()
                        })
            
            result = {
                "listing_id": listing.id if listing else None,
                "matched_buyers": [mb.dict() for mb in matched_buyers],
                "benchmark_price": benchmark_price,
                "price_suggestions": price_suggestions,
                "agent": "buyer_connect_agent"
            }
            
            logger.info(f"BuyerConnectAgent output: {len(matched_buyers)} buyers matched")
            return result
            
        except Exception as e:
            logger.error(f"BuyerConnectAgent error: {e}")
            return {
                "error": str(e),
                "agent": "buyer_connect_agent"
            }
class SchemeAgentNode:
    """Scheme Agent - Checks eligibility and finds relevant agricultural schemes"""
    
    def __init__(self):
        self.llm = AgriMitraLLM()
        self._subcategories_cache = None
        self._rag_agent = None  # Lazy-loaded RAG agent
    
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
            import re
            
            # Check if this is a follow-up selection (number or subcategory name)
            # Extract state from context if present in input
            user_input_clean = user_input
            context_state = None
            if "(selecting from subcategories for" in user_input:
                # Extract state from context
                match = re.search(r"selecting from subcategories for ([^)]+)", user_input)
                if match:
                    context_state = match.group(1).strip()
                    # Clean the input to get the actual selection
                    user_input_clean = re.sub(r"\s*\(selecting from subcategories for[^)]+\)", "", user_input).strip()
                    logger.info(f"Detected follow-up selection: '{user_input_clean}' for state: {context_state}")
            
            # FIRST: Check if user input contains a number in the same query
            # Look for patterns like: "scheme 3", "number 3", "option 3", "3", "I need 3", etc.
            # IMPORTANT: Exclude age patterns like "45 years old", "age 45", etc.
            number_in_query = None
            
            # First check for age patterns and exclude them
            age_patterns = [
                r'\b(\d+)\s+years?\s+old',
                r'\bage\s+(\d+)',
                r'\b(\d+)\s+years?\s+of\s+age',
                r'\b(\d+)\s+years?\s+aged',
            ]
            is_age_mention = False
            for age_pattern in age_patterns:
                if re.search(age_pattern, user_input_clean.lower()):
                    is_age_mention = True
                    break
            
            if not is_age_mention:
                number_patterns = [
                    r'\b(govt|government|gov)\s+scheme\s+(\d+)',  # "govt scheme 3"
                    r'\bscheme\s+(\d+)',  # "scheme 3"
                    r'\bnumber\s+(\d+)',  # "number 3"
                    r'\boption\s+(\d+)',  # "option 3"
                    r'\bcategory\s+(\d+)',  # "category 3"
                    r'\bsubcategory\s+(\d+)',  # "subcategory 3"
                    r'\bsub-category\s+(\d+)',  # "sub-category 3"
                    r'\b(\d+)\s+(?:central|state|union)\s+scheme',  # "1 central scheme", "3 state scheme"
                    r'\b(\d+)\s+scheme',  # "3 scheme"
                    r'\b(\d+)\s+category',  # "3 category"
                    r'\bneed\s+(\d+)',  # "need 3"
                    r'\bwant\s+(\d+)',  # "want 3"
                    r'\bselect\s+(\d+)',  # "select 3"
                    r'\bchoose\s+(\d+)',  # "choose 3"
                    r'^(\d+)$',  # Standalone number only (not in context of age)
                ]
                
                for pattern in number_patterns:
                    match = re.search(pattern, user_input_clean.lower())
                    if match:
                        try:
                            # Handle patterns with 2 groups (like "govt scheme 3")
                            if len(match.groups()) > 1:
                                number_in_query = int(match.group(2))
                            else:
                                number_in_query = int(match.group(1))
                            # Only accept reasonable numbers (1-100)
                            if 1 <= number_in_query <= 100:
                                logger.info(f"Found number {number_in_query} in query: '{user_input_clean}'")
                                break
                            else:
                                number_in_query = None
                        except (ValueError, IndexError):
                            continue
            
            # Detect explicit scheme type preference (central vs state vs both)
            user_lower = user_input.lower()
            scheme_scope_pref = "all"
            mentions_central = any(k in user_lower for k in ["central", "union", "pan india", "all states", "india level"])
            mentions_state_only = any(k in user_lower for k in ["state only", "only state", "state scheme", "state schemes"])
            mentions_both = any(k in user_lower for k in ["both", "state and central", "central and state", "all schemes"])
            if mentions_both:
                scheme_scope_pref = "all"
            elif mentions_central and not mentions_state_only:
                scheme_scope_pref = "central_only"
            elif mentions_state_only and not mentions_central:
                scheme_scope_pref = "state_only"
            
            # CRITICAL: If a number is found in the query, try to map it FIRST before LLM processing
            # This allows users to say "I am from Rajasthan and need scheme 3" in one query
            search_state_prelim = state or context_state or self._extract_state_from_input(user_input)
            number_mapped_successfully = False
            
            if number_in_query and search_state_prelim:
                mapped_subcategory = self._map_number_to_subcategory(number_in_query, search_state_prelim, scheme_scope_pref)
                if mapped_subcategory:
                    logger.info(f"PRE-MAPPED number {number_in_query} from query to subcategory: {mapped_subcategory}")
                    # Use this mapped subcategory directly, skip showing subcategories list
                    search_sub_category = mapped_subcategory
                    search_state = search_state_prelim
                    search_category = category or ""
                    search_scheme_name = ""
                    number_mapped_successfully = True
                    # Skip LLM processing and go directly to scheme search
                else:
                    logger.warning(f"Could not pre-map number {number_in_query} to subcategory for state {search_state_prelim}")
                    search_sub_category = ""
                    # Preserve state even if number mapping fails
                    search_state = search_state_prelim
            else:
                search_sub_category = ""
                search_state = state or context_state or self._extract_state_from_input(user_input)
            
            # Use LLM to extract state, category, sub_category from user input (only if not already mapped)
            if not number_mapped_successfully:
                context = f"User query: {user_input_clean}"
                if state or context_state:
                    context += f"\nUser's state: {state or context_state}"
                
                response = self.llm.chat(SCHEME_AGENT_SYSTEM_PROMPT, context)
                
                # Parse LLM response
                try:
                    parsed_response = json.loads(response)
                    # Preserve state from earlier extraction if LLM doesn't return it or returns empty
                    llm_state = parsed_response.get("state", "")
                    if llm_state:
                        search_state = llm_state
                    elif 'search_state' not in locals():
                        # If search_state wasn't set earlier, extract it now
                        search_state = state or context_state or self._extract_state_from_input(user_input)
                    # Otherwise keep the search_state from earlier
                    search_category = parsed_response.get("category", category or "")
                    search_sub_category = parsed_response.get("sub_category", "")
                    search_scheme_name = parsed_response.get("scheme_name", "")
                    needs_subcategories = parsed_response.get("needs_subcategories", False)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM response, using fallback logic")
                    # Preserve state from earlier extraction
                    if 'search_state' not in locals():
                        search_state = state or context_state or self._extract_state_from_input(user_input)
                    search_category = category or ""
                    search_sub_category = self._extract_subcategory_from_input(user_input_clean)
                    search_scheme_name = ""
                    # If state is specified but no sub-category, show sub-categories
                    needs_subcategories = bool(search_state and not search_sub_category)
                
                # If LLM didn't extract sub-category, try improved extraction
                if not search_sub_category:
                    search_sub_category = self._extract_subcategory_from_input(user_input_clean)
                
                # Also check if input is just a number (for follow-up queries)
                # Handle patterns like "1 central scheme", "3 state scheme", etc.
                if not search_sub_category and search_state:
                    # Check if input is a number (with optional scope keywords)
                    number_match = re.search(r'^(\d+)', user_input_clean.strip())
                    if number_match:
                        number = int(number_match.group(1))
                        # Use the detected scope preference (central_only, state_only, or all)
                        search_sub_category = self._map_number_to_subcategory(number, search_state, scheme_scope_pref)
                        if search_sub_category:
                            logger.info(f"Mapped number {number} to subcategory: {search_sub_category} (scope={scheme_scope_pref})")
            
            # Check if user explicitly asks for sub-categories or state specified without sub-category
            explicit_subcategory_request = any(keyword in user_lower for keyword in [
                "list of", "show categories", "what categories", "available categories",
                "sub-categories", "subcategories", "all categories", "options"
            ])
            
            # IMPORTANT: If sub-category is not found, return sub-categories list
            # This ensures users see available options (Central subcategories by default, or State+Central if state specified)
            # BUT: Skip this if we already successfully mapped a number (go directly to schemes)
            if not search_sub_category and not number_mapped_successfully:
                logger.info(f"State '{search_state}' specified but no sub-category found. Returning sub-categories list.")
                subcategories_result = get_subcategories_tool.invoke({"state": search_state})
                subcategories_info = json.loads(subcategories_result)
                
                # If user explicitly asked for central_only, filter to show only Central subcategories
                if scheme_scope_pref == "central_only":
                    logger.info("User requested central_only schemes - filtering to show only Central subcategories")
                    # Keep only Central Schemes in the response
                    central_schemes = subcategories_info.get("Central Schemes", {})
                    subcategories_info["State Schemes"] = {}  # Clear state schemes
                    subcategories_info["Central Schemes"] = central_schemes
                    # Rebuild sub_categories list with only central schemes
                    subcategories_list = []
                    for sub_cat, count in central_schemes.items():
                        subcategories_list.append({
                            "name": sub_cat,
                            "count": count,
                            "scheme_types": ["Central"]
                        })
                    subcategories_list.sort(key=lambda x: x["count"], reverse=True)
                    subcategories_info["sub_categories"] = subcategories_list
                    subcategories_info["total_subcategories"] = len(subcategories_list)
                
                return {
                    "subcategories_info": subcategories_info,
                    "search_params": {
                        "state": search_state,
                        "category": search_category,
                        "scheme_scope": scheme_scope_pref
                    },
                    "agent": "scheme_agent",
                    "response_type": "subcategories"
                }
            
            # If sub-category is specified, use RAG agent for better retrieval
            if search_sub_category:
                logger.info(f"Searching schemes for state: {search_state}, sub-category: {search_sub_category}")
                
                # Try using RAG agent if available (for semantic search and better matching)
                if RAG_AVAILABLE:
                    try:
                        if self._rag_agent is None:
                            self._rag_agent = SchemeRAGAgent()
                            self._rag_agent.load_schemes()
                        
                        # Build user profile for RAG
                        profile = UserProfile(
                            state=search_state,
                            sub_category=search_sub_category,
                            scheme_scope=scheme_scope_pref
                        )
                        
                        # Retrieve schemes using RAG
                        rag_schemes = self._rag_agent.retrieve_schemes(profile, top_k=10)
                        
                        # Assess eligibility
                        rag_schemes = self._rag_agent.assess_eligibility(profile, rag_schemes)
                        
                        # Convert to expected format
                        formatted_schemes = []
                        for scheme in rag_schemes:
                            scheme_state = scheme.get("state", "")
                            formatted_schemes.append({
                                "scheme_name": scheme.get("scheme_name", ""),
                                "short_name": scheme.get("short_name", ""),
                                "state": scheme_state if scheme_state else "Central",
                                "scheme_type": "Central" if not scheme_state else "State",
                                "scheme_for": scheme.get("scheme_for", ""),
                                "category": scheme.get("category", []),
                                "sub_category": scheme.get("sub_category", []),
                                "brief_description": scheme.get("brief_description", "")[:300] if scheme.get("brief_description") else "",
                                "eligibility": scheme.get("eligibility", [])[:3],
                                "eligibility_summary": " ".join(scheme.get("eligibility", [])[:1])[:200] if scheme.get("eligibility") else "",
                                "benefits": scheme.get("benefits", [])[:2],
                                "references": scheme.get("application_links", []),
                                "eligibility_status": scheme.get("eligibility_status", "unclear"),
                                "eligibility_reasons": scheme.get("eligibility_reasons", [])
                            })
                        
                        # Generate eligibility questions (optional - skip if RAG already provides eligibility assessment)
                        # Since RAG agent already assesses eligibility, we can skip generating questions to save API calls
                        eligibility_questions = []
                        # Only generate if user explicitly asks for eligibility help
                        if any(keyword in user_input.lower() for keyword in ["eligibility", "qualify", "eligible", "questions"]):
                            if formatted_schemes:
                                eligibility_questions = self.generate_eligibility_questions(
                                    user_input, 
                                    formatted_schemes
                                )
                        
                        return {
                            "scheme_info": {
                                "count": len(formatted_schemes),
                                "schemes": formatted_schemes
                            },
                            "eligibility_questions": eligibility_questions,
                            "search_params": {
                                "state": search_state,
                                "category": search_category,
                                "sub_category": search_sub_category,
                                "scheme_name": search_scheme_name,
                                "scheme_scope": scheme_scope_pref
                            },
                            "agent": "scheme_agent",
                            "response_type": "schemes",
                            "rag_used": True
                        }
                    except Exception as e:
                        logger.warning(f"RAG agent failed, falling back to traditional search: {e}")
                        # Fall through to traditional search
                
                # Traditional search (fallback or when RAG not available)
                # Determine if sub-category exists in both state and central
                has_state_subcat = False
                has_central_subcat = False
                state_count = 0
                central_count = 0
                if search_state:
                    try:
                        sub_info_raw = get_subcategories_tool.invoke({"state": search_state})
                        sub_info = json.loads(sub_info_raw)
                        state_dict = sub_info.get("State Schemes", {}) or {}
                        central_dict = sub_info.get("Central Schemes", {}) or {}
                        # case-insensitive lookup
                        for k, v in state_dict.items():
                            if k.lower() == search_sub_category.lower():
                                has_state_subcat = True
                                state_count = v
                                break
                        for k, v in central_dict.items():
                            if k.lower() == search_sub_category.lower():
                                has_central_subcat = True
                                central_count = v
                                break
                    except Exception as e:
                        logger.warning(f"Failed to check subcategory scope: {e}")
                
                # If both exist and no explicit preference, ask user to choose
                if has_state_subcat and has_central_subcat and scheme_scope_pref == "all":
                    logger.info(f"Sub-category '{search_sub_category}' available in both State and Central. Asking user to choose scope.")
                    return {
                        "scheme_type_choice": {
                            "subcategory": search_sub_category,
                            "state": search_state,
                            "options": [
                                {"type": "State", "count": state_count},
                                {"type": "Central", "count": central_count}
                            ]
                        },
                        "search_params": {
                            "state": search_state,
                            "category": search_category,
                            "sub_category": search_sub_category,
                            "scheme_scope": "all",
                            "scheme_name": search_scheme_name
                        },
                        "agent": "scheme_agent",
                        "response_type": "scheme_type_choice"
                    }
                
                # Decide scope based on preference or availability
                scheme_scope = "all"
                if scheme_scope_pref == "central_only":
                    scheme_scope = "central_only"
                elif scheme_scope_pref == "state_only":
                    scheme_scope = "state_only"
                elif has_state_subcat and not has_central_subcat:
                    scheme_scope = "state_only"
                elif has_central_subcat and not has_state_subcat:
                    scheme_scope = "central_only"
                
                # If central_only, we can still pass state for context; scope will filter
                scheme_result = scheme_tool.invoke({
                    "state": search_state,
                    "category": search_category,
                    "sub_category": search_sub_category,
                    "scheme_name": search_scheme_name,
                    "scheme_scope": scheme_scope
                })
                scheme_info = json.loads(scheme_result)
                
                # Generate eligibility questions based on shortlisted schemes (optional - only if user asks)
                eligibility_questions = []
                # Only generate if user explicitly asks for eligibility help to reduce API calls
                if any(keyword in user_input.lower() for keyword in ["eligibility", "qualify", "eligible", "questions"]):
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
    
    def _map_number_to_subcategory(self, number: int, state: str, scope: str = "all") -> str:
        """Map a number selection to a subcategory name based on scope:
        - state_only: use State Schemes list
        - central_only: use Central Schemes list
        - all (default): State list first, then Central (no duplicates)
        """
        try:
            subcategories_result = get_subcategories_tool.invoke({"state": state})
            subcategories_info = json.loads(subcategories_result)
            if subcategories_info.get("error"):
                return ""
            
            state_schemes = subcategories_info.get("State Schemes", {}) or {}
            central_schemes = subcategories_info.get("Central Schemes", {}) or {}
            
            display_list = []
            if scope == "state_only":
                # Sort by count descending (same as displayed to user)
                display_list = sorted(state_schemes.items(), key=lambda x: x[1], reverse=True)
                display_list = [item[0] for item in display_list]
            elif scope == "central_only":
                # Sort by count descending (same as displayed to user)
                display_list = sorted(central_schemes.items(), key=lambda x: x[1], reverse=True)
                display_list = [item[0] for item in display_list]
            else:
                # all / both: state first (sorted), then central (sorted) without duplicates
                state_list = sorted(state_schemes.items(), key=lambda x: x[1], reverse=True)
                display_list = [item[0] for item in state_list]
                central_list = sorted(central_schemes.items(), key=lambda x: x[1], reverse=True)
                for sub_cat, _ in central_list:
                    if sub_cat not in display_list:
                        display_list.append(sub_cat)
            
            if 1 <= number <= len(display_list):
                subcategory_name = display_list[number - 1]
                logger.info(f"Mapped number {number} to subcategory: {subcategory_name} (scope={scope}, list_length={len(display_list)})")
                return subcategory_name
            
            logger.warning(f"Number {number} out of range for scope={scope}. Available: {len(display_list)} subcategories")
            return ""
        except Exception as e:
            logger.error(f"Error mapping number to subcategory: {e}")
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

