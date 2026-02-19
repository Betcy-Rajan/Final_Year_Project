
import logging
import json
from typing import Dict, Any, List

from agent_system.llm import AgriMitraLLM
from config import REASONER_SYSTEM_PROMPT, COORDINATOR_SYSTEM_PROMPT, MOCK_PRICE_DATA

logger = logging.getLogger(__name__)

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
