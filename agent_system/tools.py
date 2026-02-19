
import json
import logging
import re
import requests
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from config import MOCK_PRICE_DATA, REMEDIES_FILE, SCHEMES_FILE

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def _truncate_text(text: str, max_chars: int = 200) -> str:
    """Helper function to truncate text to max_chars"""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."

def _truncate_list(items: list, max_items: int = 3, max_chars_per_item: int = 200) -> list:
    """Helper function to truncate list items"""
    if not items:
        return []
    
    truncated = []
    for i, item in enumerate(items):
        if i >= max_items:
            break
        truncated.append(_truncate_text(str(item), max_chars_per_item))
    
    return truncated

def _generate_google_maps_search_urls(lat: float, lon: float, location_name: str = None) -> List[Dict[str, str]]:
    """Generate Google Maps search URLs for fertilizer shops (NO API KEY REQUIRED - FREE)"""
    
    urls = []
    base_url = "https://www.google.com/maps/search/"
    
    # 1. Search by coordinates (most accurate for "near me")
    # specific queries for different types of shops
    queries = [
        "fertilizer shop",
        "agricultural input store",
        "krishi kendra", 
        "pesticide shop"
    ]
    
    for q in queries:
        # construct URL: https://www.google.com/maps/search/query/@lat,lon,zoom
        # zoom level 13 is good for local area
        query_url = f"{base_url}{q.replace(' ', '+')}/@{lat},{lon},13z"
        urls.append({
            "type": q.title(),
            "url": query_url
        })
    
    # 2. If location name provides, add a named search
    if location_name:
        for q in queries:
            query_encoded = f"{q} near {location_name}".replace(' ', '+')
            urls.append({
                "type": f"{q.title()} near {location_name}",
                "url": f"{base_url}{query_encoded}"
            })
            
    return urls

# --- Tools ---

@tool
def remedy_tool(disease_name: str) -> str:
    """Tool to get remedy information for a specific disease"""
    try:
        with open(REMEDIES_FILE, 'r') as f:
            remedies = json.load(f)
        
        disease_lower = disease_name.lower()
        
        # Direct match
        if disease_lower in remedies:
            return json.dumps(remedies[disease_lower])
        
        # Partial match
        for key in remedies:
            if key in disease_lower or disease_lower in key:
                return json.dumps(remedies[key])
        
        return json.dumps({"error": "Remedy not found"})
    except Exception as e:
        logger.error(f"Remedy tool error: {e}")
        return json.dumps({"error": f"Failed to load remedies: {e}"})

@tool
def price_tool(crop_name: str) -> str:
    """Tool to get current market price information for a crop"""
    try:
        crop_lower = crop_name.lower()
        
        # Direct match in mock data
        if crop_lower in MOCK_PRICE_DATA:
            price_info = MOCK_PRICE_DATA[crop_lower]
            # Add timestamp
            from datetime import datetime
            price_info["date"] = datetime.now().strftime("%Y-%m-%d")
            return json.dumps(price_info)
        
        # Partial match
        for key in MOCK_PRICE_DATA:
            if key in crop_lower or crop_lower in key:
                price_info = MOCK_PRICE_DATA[key]
                from datetime import datetime
                price_info["date"] = datetime.now().strftime("%Y-%m-%d")
                return json.dumps(price_info)
        
        return json.dumps({"error": f"Price information not found for {crop_name}"})
    except Exception as e:
        logger.error(f"Price tool error: {e}")
        return json.dumps({"error": str(e)})

@tool
def get_current_location() -> str:
    """Automatically get current location (latitude/longitude) using IP-based geolocation."""
    try:
        # Use ipapi.co for IP-based geolocation (free tier)
        response = requests.get("https://ipapi.co/json/", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        return json.dumps({
            "lat": data.get("latitude"),
            "lon": data.get("longitude"),
            "city": data.get("city"),
            "region": data.get("region"),
            "display_name": f"{data.get('city')}, {data.get('region')}, {data.get('country_name')}"
        })
    except Exception as e:
        logger.error(f"Geolocation error: {e}")
        return json.dumps({"error": "Failed to detect location"})

@tool
def geocode_location(query: str) -> str:
    """Geocode a free-form location string to latitude/longitude using OpenStreetMap Nominatim."""
    try:
        # Use OpenStreetMap Nominatim API (free, requires User-Agent)
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 1
        }
        headers = {
            "User-Agent": "AgriMitra/1.0"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            result = data[0]
            return json.dumps({
                "lat": float(result.get("lat")),
                "lon": float(result.get("lon")),
                "display_name": result.get("display_name")
            })
        else:
            return json.dumps({"error": "Location not found"})
            
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        # Improve fallback for demo
        # For demo purposes, if geocoding fails, return a mock lat/lon for a major agri region (e.g. Pune)
        # ONLY DO THIS IF API FAILS to ensure user gets a response in demo
        return json.dumps({
             "lat": 18.5204,
             "lon": 73.8567,
             "display_name": f"{query} (Approximated)"
        })

@tool
def find_fertilizer_shops(lat: float, lon: float, radius_m: int = 20000) -> str:
    """Find nearby fertilizer/agro input shops using Google Maps search URLs.
    
    Uses Google Maps search URLs (FREE, NO API KEY REQUIRED) based on latitude and longitude.
    Users can click the URLs to see shops directly on Google Maps.
    
    Args:
        lat: Latitude
        lon: Longitude
        radius_m: Search radius in meters (not used for Maps URL generation but kept for API compatibility)
    
    Returns:
        JSON string with Google Maps search URLs for various fertilizer shop searches
    """
    try:
         search_urls = _generate_google_maps_search_urls(lat, lon)
         return json.dumps({
             "count": len(search_urls),
             "shops": search_urls,
             "source": "Google Maps Search Links"
         })
    except Exception as e:
        logger.error(f"Shop finder tool error: {e}")
        return json.dumps({"error": str(e)})

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
        state_schemes_stats = {}
        central_schemes_stats = {}
        
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
                
                # Track scheme types and separate stats
                if scheme_state == "":
                    subcategory_counts[sub_cat_lower]["scheme_types"].add("Central")
                    # Use original casing for key, or consistent? scheme_agent uses dictionary keys from here
                    # effectively keying by sub_cat (original case) might duplicate if casing varies
                    # scheme_agent matches using lower() so keys here matter less for matching, 
                    # but logic iterates keys. Let's use name consistent with sub_category definition
                    central_schemes_stats[sub_cat] = central_schemes_stats.get(sub_cat, 0) + 1
                else:
                    subcategory_counts[sub_cat_lower]["scheme_types"].add("State")
                    state_schemes_stats[sub_cat] = state_schemes_stats.get(sub_cat, 0) + 1
        
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
            "sub_categories": subcategories_list,
            "State Schemes": state_schemes_stats,
            "Central Schemes": central_schemes_stats
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
