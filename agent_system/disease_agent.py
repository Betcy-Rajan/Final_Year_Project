
import logging
import json
import os
import re
from typing import Dict, Any, Optional

from agent_system.llm import AgriMitraLLM
from agent_system.tools import remedy_tool, find_fertilizer_shops, get_current_location, geocode_location
from config import DISEASE_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Try to import CNN model
try:
    from cnn_model import PlantDiseaseCNN
    CNN_AVAILABLE = True
except ImportError as e:
    CNN_AVAILABLE = False
    error_msg = str(e)
    if "tensorflow" in error_msg.lower() or "keras" in error_msg.lower():
        logger.warning(
            "CNN model module not available: TensorFlow/Keras not installed. "
            "Image-based disease detection is disabled. To enable it, install TensorFlow: pip install tensorflow>=2.13.0"
        )
    else:
        logger.warning(f"CNN model module not available: {error_msg}. Image-based detection disabled.")

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