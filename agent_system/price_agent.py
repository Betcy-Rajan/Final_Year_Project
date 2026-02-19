
import logging
import json
from typing import Dict, Any

from agent_system.tools import price_tool

logger = logging.getLogger(__name__)

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
