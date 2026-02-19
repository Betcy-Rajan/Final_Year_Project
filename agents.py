
"""
AgriMitra Agentic Prototype - Agent implementations
This file now serves as a facade/adapter for the modularized agent system.
"""
import logging
import json
from langchain_core.tools import tool

# Re-export key components from the modular system
from agent_system.llm import AgriMitraLLM
from agent_system.tools import (
    remedy_tool, 
    price_tool, 
    get_current_location, 
    geocode_location, 
    find_fertilizer_shops, 
    get_subcategories_tool, 
    scheme_tool
)
from agent_system.disease_agent import DiseaseAgentNode
from agent_system.price_agent import PriceAgentNode
from agent_system.buyer_agent import BuyerConnectAgentNode
from agent_system.scheme_agent import SchemeAgentNode
from agent_system.reasoner_coordinator import ReasonerNode, CoordinatorNode

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Maintain backward compatibility for availability flags
try:
    from cnn_model import PlantDiseaseCNN
    CNN_AVAILABLE = True
except ImportError:
    CNN_AVAILABLE = False

try:
    from scheme_rag_agent import SchemeRAGAgent
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# Re-export flags from agent modules if they are exposed there
from agent_system.disease_agent import CNN_AVAILABLE as DISEASE_AGENT_CNN_AVAILABLE
from agent_system.scheme_agent import RAG_AVAILABLE as SCHEME_AGENT_RAG_AVAILABLE

# Ensure consistency - though mainly used locally in modules
CNN_AVAILABLE = DISEASE_AGENT_CNN_AVAILABLE
RAG_AVAILABLE = SCHEME_AGENT_RAG_AVAILABLE
