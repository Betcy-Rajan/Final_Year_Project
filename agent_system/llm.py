
import logging
import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from config import GROQ_API_KEY, GROQ_API_BASE, REASONER_SYSTEM_PROMPT, MOCK_PRICE_DATA

logger = logging.getLogger(__name__)

class AgriMitraLLM:
    """Base LLM class for all agents"""
    def __init__(self, model_name: str = "openai/gpt-oss-20b"):
        
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
