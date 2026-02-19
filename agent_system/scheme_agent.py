
import logging
import json
import re
from typing import Dict, Any, List, Optional

from agent_system.llm import AgriMitraLLM
from agent_system.tools import get_subcategories_tool, scheme_tool
from config import SCHEME_AGENT_SYSTEM_PROMPT, SCHEME_ELIGIBILITY_PROMPT, SCHEMES_FILE

logger = logging.getLogger(__name__)

# Try to import RAG agent
try:
    from scheme_rag_agent import SchemeRAGAgent, UserProfile
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning("RAG agent not available - using fallback scheme search")

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

    def _generate_ui_content(self, schemes: List[Dict[str, Any]], search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured UI content for card-based display"""
        count = len(schemes)
        state = search_params.get("state") or "All States"
        category = search_params.get("sub_category") or search_params.get("category") or "General"
        
        return {
            "summary_card": {
                "title": f"Government Schemes for {category}",
                "subtitle": f"Location: {state}",
                "overview": f"We found {count} relevant financial assistance schemes matching your profile. These schemes offer subsidies, loans, or direct benefits."
            },
            "next_steps": [
                {"step": 1, "title": "Check Eligibility", "text": "Review the age, land, and income requirements for each scheme."},
                {"step": 2, "title": "Prepare Documents", "text": "Gather Aadhar, Land Records (7/12), and Bank Passbook."},
                {"step": 3, "title": "Apply", "text": "Visit the official website link or your local Agriculture Office."}
            ],
            "tips_card": [
                 "Ensure your bank account is linked with Aadhar for Direct Benefit Transfer (DBT).",
                 "Keep a set of passport-sized photos and self-attested document copies ready.",
                 "Check for application deadlines to avoid missing out."
            ],
            "footer_card": "Take advantage of these benefits to reduce cultivation costs and improve yield!"
        }
    
    def process(self, user_input: str, state: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        """Process scheme eligibility check request"""
        logger.info(f"SchemeAgent processing: {user_input}")
        
        try:
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
                        if search_sub_category:
                            logger.info(f"Mapped number {number} to subcategory: {search_sub_category} (scope={scheme_scope_pref})")
            
            # Enforce Case 3: If no state specified and no explicit scope, default to Central schemes
            if not search_state and scheme_scope_pref == "all" and not mentions_both:
                logger.info("No state specified - defaulting scope to 'central_only'")
                scheme_scope_pref = "central_only"
            
            # Check if user explicitly asks for sub-categories or state specified without sub-category
            explicit_subcategory_request = any(keyword in user_lower for keyword in [
                "list of", "show categories", "what categories", "available categories",
                "sub-categories", "subcategories", "all categories", "options"
            ])

            # Extract hints for RAG Profile
            crops_found = []
            common_crops = ["rice", "wheat", "cotton", "sugarcane", "maize", "pulse", "soybean", "groundnut", "vegetable", "fruit", "mango", "banana", "paddy"]
            for crop in common_crops:
                if crop in user_lower:
                    crops_found.append(crop)
            
            farmer_type = None
            if "small" in user_lower: farmer_type = "small"
            elif "marginal" in user_lower: farmer_type = "marginal"
            elif "large" in user_lower: farmer_type = "large"
            
            target_group = None
            if "sc" in user_lower.split() or "scheduled caste" in user_lower: target_group = "SC"
            elif "st" in user_lower.split() or "scheduled tribe" in user_lower: target_group = "ST"
            elif "woman" in user_lower or "women" in user_lower or "female" in user_lower: target_group = "Women"
            elif "obc" in user_lower: target_group = "OBC"
            
            land_size = None
            land_match = re.search(r'(\d+(\.\d+)?)\s*(acre|hectare)', user_lower)
            if land_match:
                try:
                    land_size = float(land_match.group(1))
                except: pass

            has_contextual_hints = bool(crops_found or farmer_type or target_group or land_size or "subsidy" in user_lower or "loan" in user_lower or "insurance" in user_lower)
            
            # Decision: Show sub-categories list OR Search Schemes?
            # Show list ONLY if:
            # 1. No sub-category found
            # 2. No number mapped
            # 3. No explicit search intent/hints that allow a good search
            # 4. OR explicit request for list ("show categories")
            
            should_show_list = (not search_sub_category and not number_mapped_successfully)
            if has_contextual_hints and not explicit_subcategory_request:
                should_show_list = False
                logger.info(f"Contextual hints found (crops={crops_found}, type={farmer_type}), proceeding to RAG search despite no sub-category.")
            
            # Case 2 & 3: Return sub-categories list if no specific search intent
            if should_show_list:
                logger.info(f"State '{search_state}' specified but no sub-category/hints found. Returning sub-categories list.")
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
                    "response_type": "subcategories",
                    "original_query": user_input
                }
            
            # Case 1 & 4: Search schemes using RAG (State + Sub-category OR State + Hints)
            if search_sub_category or has_contextual_hints:
                logger.info(f"Searching schemes for state: {search_state}, sub-category: {search_sub_category}, hints: {has_contextual_hints}")
                
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
                            scheme_scope=scheme_scope_pref,
                            crops=crops_found,
                            farmer_type=farmer_type,
                            target_group=target_group,
                            land_size=land_size
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
                        
                        # Prepare search params for UI generation
                        search_params = {
                            "state": search_state,
                            "category": search_category,
                            "sub_category": search_sub_category,
                            "scheme_name": search_scheme_name,
                            "scheme_scope": scheme_scope_pref
                        }

                        return {
                            "scheme_info": {
                                "count": len(formatted_schemes),
                                "schemes": formatted_schemes
                            },
                            "ui_content": self._generate_ui_content(formatted_schemes, search_params),
                            "eligibility_questions": eligibility_questions,
                            "search_params": search_params,
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
                
                # Prepare search params for UI generation
                search_params = {
                    "state": search_state,
                    "category": search_category,
                    "sub_category": search_sub_category,
                    "scheme_name": search_scheme_name
                }
                
                return {
                    "scheme_info": scheme_info,
                    "ui_content": self._generate_ui_content(scheme_info.get("schemes", []), search_params),
                    "eligibility_questions": eligibility_questions,
                    "search_params": search_params,
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
