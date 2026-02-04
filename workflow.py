"""
AgriMitra Agentic Prototype - LangGraph Workflow
"""
import json
import logging
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from agents import ReasonerNode, DiseaseAgentNode, PriceAgentNode, SchemeAgentNode, CoordinatorNode, BuyerConnectAgentNode,SchemeAgentNode

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkflowState(TypedDict):
    """State schema for the LangGraph workflow"""
    user_input: str
    image_path: Optional[str]  # Path to image file if provided
    reasoner_output: Optional[Dict[str, Any]]
    disease_agent_output: Optional[Dict[str, Any]]
    price_agent_output: Optional[Dict[str, Any]]
    scheme_agent_output: Optional[Dict[str, Any]]
    buyer_connect_agent_output: Optional[Dict[str, Any]]
    coordinator_output: Optional[Dict[str, Any]]
    final_response: Optional[str]
    next_nodes: List[str]
    execution_log: List[Dict[str, Any]]

class AgriMitraWorkflow:
    """Main workflow class that orchestrates the entire agentic system"""
    
    def __init__(self):
        # Initialize all nodes
        self.reasoner = ReasonerNode()
        self.disease_agent = DiseaseAgentNode()
        self.price_agent = PriceAgentNode()
        self.scheme_agent = SchemeAgentNode()
        self.buyer_connect_agent = BuyerConnectAgentNode()
        self.coordinator = CoordinatorNode()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("reasoner", self._reasoner_node)
        workflow.add_node("disease_agent", self._disease_agent_node)
        workflow.add_node("price_agent", self._price_agent_node)
        workflow.add_node("scheme_agent", self._scheme_agent_node)
        workflow.add_node("buyer_connect_agent", self._buyer_connect_agent_node)
        workflow.add_node("coordinator", self._coordinator_node)
        
        # Define the flow
        workflow.set_entry_point("reasoner")
        
        # Conditional edges from reasoner
        workflow.add_conditional_edges(
            "reasoner",
            self._route_after_reasoner,
            {
                "disease_agent": "disease_agent",
                "price_agent": "price_agent",
                "scheme_agent": "scheme_agent",
                "buyer_connect_agent": "buyer_connect_agent",
                "both_agents": "disease_agent",  # Start with disease agent, then price
                "coordinator": "coordinator",
                END: END
            }
        )
        
        # From disease agent
        workflow.add_conditional_edges(
            "disease_agent",
            self._route_after_disease_agent,
            {
                "price_agent": "price_agent",
                "coordinator": "coordinator",
                END: END
            }
        )
        
        # From price agent to coordinator
        workflow.add_edge("price_agent", "coordinator")
        # From scheme agent to coordinator
        workflow.add_edge("scheme_agent", "coordinator")
        
        # From buyer connect agent to coordinator
        workflow.add_edge("buyer_connect_agent", "coordinator")
        
        # From coordinator to end
        workflow.add_edge("coordinator", END)
        
        return workflow.compile()
    
    def _reasoner_node(self, state: WorkflowState) -> WorkflowState:
        """Reasoner node execution"""
        logger.info("Executing Reasoner Node")
        
        try:
            # If image is provided, automatically route to disease agent
            image_path = state.get("image_path")
            if image_path:
                logger.info(f"Image detected in reasoner: {image_path}, routing to disease agent")
                result = {
                    "reasoner_output": {
                        "intent": ["disease"],
                        "crop": None,  # Will be detected by CNN
                        "agents_to_trigger": ["disease_agent"]
                    },
                    "user_input": state["user_input"],
                    "next_nodes": ["disease_agent"]
                }
            else:
                result = self.reasoner.process(state["user_input"])
            
            # Extract intent and agents from reasoner output
            reasoner_output = result.get("reasoner_output", {})
            intent = result.get("intent", reasoner_output.get("intent", []))
            next_nodes = result.get("next_nodes", result.get("agents_to_trigger", []))
            
            # Log execution
            execution_log = state.get("execution_log", [])
            execution_log.append({
                "node": "reasoner",
                "input": {"user_input": state["user_input"], "image_path": image_path},
                "output": result,
                "timestamp": self._get_timestamp()
            })
            
            return {
                **state,
                "reasoner_output": {
                    "intent": intent,
                    "crop": result.get("crop"),
                    "agents_to_trigger": next_nodes,
                    **reasoner_output
                },
                "next_nodes": next_nodes,
                "execution_log": execution_log
            }
            
        except Exception as e:
            logger.error(f"Reasoner node error: {e}")
            execution_log = state.get("execution_log", [])
            execution_log.append({
                "node": "reasoner",
                "error": str(e),
                "timestamp": self._get_timestamp()
            })
            
            return {
                **state,
                "reasoner_output": {"error": str(e)},
                "next_nodes": [],
                "execution_log": execution_log
            }
    
    # def _disease_agent_node(self, state: WorkflowState) -> WorkflowState:
    #     """Disease agent node execution"""
    #     logger.info("Executing Disease Agent Node")
        
    #     try:
    #         reasoner_data = state.get("reasoner_output", {})
    #         # Extract crop - handle both nested and direct structures
    #         if isinstance(reasoner_data, dict):
    #             crop = reasoner_data.get("crop") or reasoner_data.get("reasoner_output", {}).get("crop")
    #         else:
    #             crop = None
    #         image_path = state.get("image_path")
            
    #         print(f"🦠 DISEASE AGENT NODE: crop={crop}, image_path={image_path}")
    #         result = self.disease_agent.process(state["user_input"], crop, image_path)
    #         print(f"✅ DISEASE AGENT NODE: result keys = {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
            
    #         # Log execution
    #         execution_log = state.get("execution_log", [])
    #         execution_log.append({
    #             "node": "disease_agent",
    #             "input": {"user_input": state["user_input"], "crop": crop, "image_path": image_path},
    #             "output": result,
    #             "timestamp": self._get_timestamp()
    #         })
            
    #         # Debug: Verify result structure
    #         if isinstance(result, dict):
    #             print(f"✅ DISEASE AGENT: Returning result with keys: {list(result.keys())}")
            
    #         return {
    #             **state,
    #             "disease_agent_output": result,
    #             "execution_log": execution_log
    #         }
            
    #     except Exception as e:
    #         logger.error(f"Disease agent node error: {e}")
    #         execution_log = state.get("execution_log", [])
    #         execution_log.append({
    #             "node": "disease_agent",
    #             "error": str(e),
    #             "timestamp": self._get_timestamp()
    #         })
            
    #         return {
    #             **state,
    #             "disease_agent_output": {"error": str(e)},
    #             "execution_log": execution_log
    #         }
    def _disease_agent_node(self, state: WorkflowState) -> WorkflowState:
        """Disease agent node execution"""
        logger.info("Executing Disease Agent Node")
        
        try:
            reasoner_data = state.get("reasoner_output", {})
            # Extract crop - handle both nested and direct structures
            if isinstance(reasoner_data, dict):
                crop = reasoner_data.get("crop") or reasoner_data.get("reasoner_output", {}).get("crop")
            else:
                crop = None
            image_path = state.get("image_path")
            
            print(f"🦠 DISEASE AGENT NODE: crop={crop}, image_path={image_path}")
            result = self.disease_agent.process(state["user_input"], crop, image_path)
            print(f"✅ DISEASE AGENT NODE: result keys = {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
            
            # Log execution
            execution_log = state.get("execution_log", [])
            execution_log.append({
                "node": "disease_agent",
                "input": {"user_input": state["user_input"], "crop": crop, "image_path": image_path},
                "output": result,
                "timestamp": self._get_timestamp()
            })
            
            # Debug: Verify result structure
            if isinstance(result, dict):
                print(f"✅ DISEASE AGENT: Returning result with keys: {list(result.keys())}")
            
            return {
                **state,
                "disease_agent_output": result,
                "execution_log": execution_log
            }
            
        except Exception as e:
            logger.error(f"Disease agent node error: {e}")
            execution_log = state.get("execution_log", [])
            execution_log.append({
                "node": "disease_agent",
                "error": str(e),
                "timestamp": self._get_timestamp()
            })
            
            return {
                **state,
                "disease_agent_output": {"error": str(e)},
                "execution_log": execution_log
            }
    def _price_agent_node(self, state: WorkflowState) -> WorkflowState:
        """Price agent node execution"""
        logger.info("Executing Price Agent Node")
        
        try:
            user_input = state.get("user_input", "").lower()
            reasoner_data = state.get("reasoner_output", {})
            
            # Extract crop from user input first (for price queries, user specifies the crop)
            # Look for price-related queries with crop names
            crop = None
            from config import MOCK_PRICE_DATA
            for crop_name in MOCK_PRICE_DATA.keys():
                # Check if crop is mentioned near price-related keywords
                crop_lower = crop_name.lower()
                price_keywords = ['price', 'cost', 'rate', 'market', 'value', 'mandi']
                
                # Find position of crop and price keywords
                crop_pos = user_input.find(crop_lower)
                if crop_pos != -1:
                    # Check if there's a price keyword nearby (within 30 chars)
                    for keyword in price_keywords:
                        keyword_pos = user_input.find(keyword)
                        if keyword_pos != -1:
                            # If crop appears near price keyword, use it
                            if abs(crop_pos - keyword_pos) < 50:
                                crop = crop_name
                                break
                    if crop:
                        break
            
            # Fallback to reasoner's crop if not found in user input
            if not crop:
                if isinstance(reasoner_data, dict):
                    crop = reasoner_data.get("crop") or reasoner_data.get("reasoner_output", {}).get("crop")
                else:
                    crop = None
            
            if not crop:
                crop = "unknown"
            
            print(f"💰 PRICE AGENT NODE: crop={crop} (extracted from user_input)")
            result = self.price_agent.process(crop)
            print(f"✅ PRICE AGENT NODE: result keys = {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
            
            # Log execution
            execution_log = state.get("execution_log", [])
            execution_log.append({
                "node": "price_agent",
                "input": {"crop": crop},
                "output": result,
                "timestamp": self._get_timestamp()
            })
            
            # Debug: Verify result structure
            if isinstance(result, dict):
                print(f"✅ PRICE AGENT: Returning result with keys: {list(result.keys())}")
            
            return {
                **state,
                "price_agent_output": result,
                "execution_log": execution_log
            }
            
        except Exception as e:
            logger.error(f"Price agent node error: {e}")
            execution_log = state.get("execution_log", [])
            execution_log.append({
                "node": "price_agent",
                "error": str(e),
                "timestamp": self._get_timestamp()
            })
            
            return {
                **state,
                "price_agent_output": {"error": str(e)},
                "execution_log": execution_log
            }
    
    def _scheme_agent_node(self, state: WorkflowState) -> WorkflowState:
        """Scheme agent node execution"""
        logger.info("Executing Scheme Agent Node")
        
        try:
            reasoner_data = state.get("reasoner_output", {})
            reasoner_output = reasoner_data.get("reasoner_output", {})
            user_state = reasoner_output.get("state")
            
            result = self.scheme_agent.process(state["user_input"], state=user_state)
            
            # Log execution
            execution_log = state.get("execution_log", [])
            execution_log.append({
                "node": "scheme_agent",
                "input": {"user_input": state["user_input"], "state": user_state},
                "output": result,
                "timestamp": self._get_timestamp()
            })
            
            return {
                **state,
                "scheme_agent_output": result,
                "execution_log": execution_log
            }
            
        except Exception as e:
            logger.error(f"Scheme agent node error: {e}")
            execution_log = state.get("execution_log", [])
            execution_log.append({
                "node": "scheme_agent",
                "error": str(e),
                "timestamp": self._get_timestamp()
            })
            
            return {
                **state,
                "scheme_agent_output": {"error": str(e)},
                "execution_log": execution_log
            }
    
    def _buyer_connect_agent_node(self, state: WorkflowState) -> WorkflowState:
        """Buyer Connect agent node execution"""
        logger.info("Executing Buyer Connect Agent Node")
        
        try:
            reasoner_data = state.get("reasoner_output", {})
            # Extract crop - handle both nested and direct structures
            if isinstance(reasoner_data, dict):
                crop = reasoner_data.get("crop") or reasoner_data.get("reasoner_output", {}).get("crop")
            else:
                crop = None
            user_input = state.get("user_input", "")
            
            # If crop not found in reasoner, try to extract from user input directly
            if not crop:
                import re
                from config import MOCK_PRICE_DATA
                user_lower = user_input.lower()
                # Check for crop names (handle plurals)
                for crop_name in MOCK_PRICE_DATA.keys():
                    if crop_name in user_lower or crop_name + 's' in user_lower or crop_name + 'es' in user_lower:
                        crop = crop_name
                        break
            
            print(f"🤝 BUYER CONNECT AGENT NODE: crop={crop}, user_input={user_input}")
            
            # Try to extract quantity and price from user input
            # Improved extraction patterns
            quantity = None
            farmer_threshold_price = None
            
            import re
            # Improved quantity extraction - look for numbers before "kg" or standalone numbers
            qty_patterns = [
                r'(\d+)\s*(?:kg|kilograms?|quintals?|kgs?)',  # "200 kg", "500 kilograms"
                r'(\d+)\s+(?:kg|kilograms?|quintals?)',        # "200  kg" (with space)
                r'(?:sell|selling|have|want to sell)\s+(\d+)', # "sell 200" or "selling 200"
            ]
            for pattern in qty_patterns:
                qty_match = re.search(pattern, user_input.lower())
                if qty_match:
                    quantity = float(qty_match.group(1))
                    break
            
            # Improved price extraction - look for price-related keywords
            price_patterns = [
                r'(?:price|at|for|minimum|min|rupees?|rs|₹)\s*(?:of|is|:)?\s*(\d+(?:\.\d+)?)',  # "price 30", "minimum 30", "30 rupees"
                r'(\d+(?:\.\d+)?)\s*(?:rupees?|rs|₹|per\s*kg)',  # "30 rupees", "30 per kg"
                r'(?:minimum|min)\s*(?:price|of)?\s*(\d+(?:\.\d+)?)',  # "minimum price 30"
            ]
            for pattern in price_patterns:
                price_match = re.search(pattern, user_input.lower())
                if price_match:
                    farmer_threshold_price = float(price_match.group(1))
                    break
            
            # If not extracted, use defaults for demo
            if quantity is None:
                quantity = 500  # Default demo quantity
            if farmer_threshold_price is None and crop:
                # Use benchmark price as fallback
                try:
                    price_result = self.price_agent.process(crop)
                    price_info = price_result.get("price_info", {})
                    if "error" not in price_info:
                        farmer_threshold_price = price_info.get("current_price", 0) * 0.9  # 10% below benchmark
                except:
                    farmer_threshold_price = 25.0  # Default fallback
            
            result = self.buyer_connect_agent.process(
                user_input=user_input,
                crop=crop,
                quantity=quantity,
                farmer_threshold_price=farmer_threshold_price,
                farmer_id=1  # Default farmer ID for demo
            )
            
            # Log execution
            execution_log = state.get("execution_log", [])
            execution_log.append({
                "node": "buyer_connect_agent",
                "input": {
                    "user_input": user_input,
                    "crop": crop,
                    "quantity": quantity,
                    "farmer_threshold_price": farmer_threshold_price
                },
                "output": result,
                "timestamp": self._get_timestamp()
            })
            
            return {
                **state,
                "buyer_connect_agent_output": result,
                "execution_log": execution_log
            }
            
        except Exception as e:
            logger.error(f"Buyer Connect agent node error: {e}")
            execution_log = state.get("execution_log", [])
            execution_log.append({
                "node": "buyer_connect_agent",
                "error": str(e),
                "timestamp": self._get_timestamp()
            })
            
            return {
                **state,
                "buyer_connect_agent_output": {"error": str(e)},
                "execution_log": execution_log
            }
    
    def _coordinator_node(self, state: WorkflowState) -> WorkflowState:
        """Coordinator node execution"""
        logger.info("Executing Coordinator Node")
        
        try:
            # Collect all agent outputs
            agent_outputs = []
            
            if state.get("disease_agent_output"):
                agent_outputs.append(state["disease_agent_output"])
            
            if state.get("price_agent_output"):
                agent_outputs.append(state["price_agent_output"])
            
            if state.get("buyer_connect_agent_output"):
                agent_outputs.append(state["buyer_connect_agent_output"])
            
            if state.get("scheme_agent_output"):
                agent_outputs.append(state["scheme_agent_output"])
            
            result = self.coordinator.process(state["user_input"], agent_outputs)
            
            # Log execution
            execution_log = state.get("execution_log", [])
            execution_log.append({
                "node": "coordinator",
                "input": {"user_input": state["user_input"], "agent_outputs": agent_outputs},
                "output": result,
                "timestamp": self._get_timestamp()
            })
            
            return {
                **state,
                "coordinator_output": result,
                "final_response": result.get("final_response", "No response generated"),
                "execution_log": execution_log
            }
            
        except Exception as e:
            logger.error(f"Coordinator node error: {e}")
            execution_log = state.get("execution_log", [])
            execution_log.append({
                "node": "coordinator",
                "error": str(e),
                "timestamp": self._get_timestamp()
            })
            
            return {
                **state,
                "coordinator_output": {"error": str(e)},
                "final_response": f"Error in coordination: {e}",
                "execution_log": execution_log
            }
    
    def _route_after_reasoner(self, state: WorkflowState) -> str:
        """Route after reasoner based on next_nodes"""
        next_nodes = state.get("next_nodes", [])
        # If reasoner flagged out_of_scope, go straight to coordinator
        try:
            ro = state.get("reasoner_output", {})
            inner = ro.get("reasoner_output", ro)
            if inner.get("intent") and "out_of_scope" in inner.get("intent"):
                return "coordinator"
        except Exception:
            pass
        if "scheme_agent" in next_nodes:
            return "scheme_agent"
        # Prioritize scheme_agent if present
        
        if "disease_agent" in next_nodes and "price_agent" in next_nodes:
            return "both_agents"
        elif "buyer_connect_agent" in next_nodes:
            return "buyer_connect_agent"
        elif "disease_agent" in next_nodes:
            return "disease_agent"
        elif "price_agent" in next_nodes:
            return "price_agent"
        else:
            return "coordinator"  # Default to coordinator if no specific agents
    
    def _route_after_disease_agent(self, state: WorkflowState) -> str:
        """Route after disease agent"""
        next_nodes = state.get("next_nodes", [])
        
        if "price_agent" in next_nodes:
            return "price_agent"
        else:
            return "coordinator"
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def run(self, user_input: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Run the complete workflow"""
        logger.info(f"Starting workflow with input: {user_input}, image_path: {image_path}")
        
        # Initialize state
        initial_state = WorkflowState(
            user_input=user_input,
            image_path=image_path,
            reasoner_output=None,
            disease_agent_output=None,
            price_agent_output=None,
            scheme_agent_output=None,
            buyer_connect_agent_output=None,
            coordinator_output=None,
            final_response=None,
            next_nodes=[],
            execution_log=[]
        )
        
        try:
            # Run the workflow
            final_state = self.graph.invoke(initial_state)
            
            logger.info("Workflow completed successfully")
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return {
                "error": str(e),
                "final_response": f"Workflow error: {e}",
                "execution_log": []
            }
    
    def get_execution_summary(self, final_state: Dict[str, Any]) -> str:
        """Get a summary of the execution for debugging/demonstration"""
        summary = []
        summary.append("=== AgriMitra Workflow Execution Summary ===")
        summary.append(f"User Input: {final_state.get('user_input', 'N/A')}")
        summary.append("")
        
        # Log execution steps
        execution_log = final_state.get("execution_log", [])
        for i, log_entry in enumerate(execution_log, 1):
            summary.append(f"Step {i}: {log_entry.get('node', 'unknown')}")
            if "error" in log_entry:
                summary.append(f"  Error: {log_entry['error']}")
            else:
                summary.append(f"  Input: {log_entry.get('input', 'N/A')}")
                summary.append(f"  Output: {json.dumps(log_entry.get('output', {}), indent=2)}")
            summary.append("")
        
        summary.append("=== Final Response ===")
        summary.append(final_state.get("final_response", "No response generated"))
        
        return "\n".join(summary)
