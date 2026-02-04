"""
CNN Model Loader and Predictor for Plant Disease Detection
"""
import os
import numpy as np
import cv2
import logging
from typing import Dict, Any, Tuple, Optional
from tensorflow.keras.models import load_model

logger = logging.getLogger(__name__)

# Class names from PlantVillage dataset (38 classes)
CLASS_NAMES = [
    'Apple___Apple_scab', 'Apple___Black_rot', 'Apple___Cedar_apple_rust', 'Apple___healthy',
    'Blueberry___healthy', 'Cherry_(including_sour)___Powdery_mildew', 'Cherry_(including_sour)___healthy',
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot', 'Corn_(maize)___Common_rust_',
    'Corn_(maize)___Northern_Leaf_Blight', 'Corn_(maize)___healthy',
    'Grape___Black_rot', 'Grape___Esca_(Black_Measles)', 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)',
    'Grape___healthy', 'Orange___Haunglongbing_(Citrus_greening)',
    'Peach___Bacterial_spot', 'Peach___healthy',
    'Pepper,_bell___Bacterial_spot', 'Pepper,_bell___healthy',
    'Potato___Early_blight', 'Potato___Late_blight', 'Potato___healthy',
    'Raspberry___healthy', 'Soybean___healthy', 'Squash___Powdery_mildew',
    'Strawberry___Leaf_scorch', 'Strawberry___healthy',
    'Tomato___Bacterial_spot', 'Tomato___Early_blight', 'Tomato___Late_blight',
    'Tomato___Leaf_Mold', 'Tomato___Septoria_leaf_spot', 'Tomato___Spider_mites Two-spotted_spider_mite',
    'Tomato___Target_Spot', 'Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Tomato___Tomato_mosaic_virus',
    'Tomato___healthy'
]

IMG_SIZE = (128, 128)
MODEL_PATH = "plantvillage_cnn_model.h5"


class PlantDiseaseCNN:
    """CNN Model for Plant Disease Prediction"""
    
    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = model_path
        self.model = None
        self.class_names = CLASS_NAMES
        self.img_size = IMG_SIZE
        self._load_model()
    
    def _load_model(self):
        """Load the trained CNN model"""
        try:
            if not os.path.exists(self.model_path):
                logger.warning(f"Model file not found: {self.model_path}")
                return
            
            logger.info(f"Loading CNN model from {self.model_path}")
            self.model = load_model(self.model_path)
            logger.info("CNN model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading CNN model: {e}")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if model is loaded and available"""
        return self.model is not None
    
    def preprocess_image(self, image_path: str) -> Optional[np.ndarray]:
        """Preprocess image for model prediction"""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Could not read image: {image_path}")
                return None
            
            # Convert BGR to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Resize to model input size
            img_resized = cv2.resize(img_rgb, self.img_size)
            
            # Normalize pixel values to [0, 1]
            img_array = img_resized / 255.0
            
            # Add batch dimension
            img_array = np.expand_dims(img_array, axis=0)
            
            return img_array
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return None
    
    def predict(self, image_path: str) -> Dict[str, Any]:
        """Predict disease from image"""
        if not self.is_available():
            return {
                "error": "CNN model not available",
                "disease": None,
                "confidence": 0.0
            }
        
        # Preprocess image
        img_array = self.preprocess_image(image_path)
        if img_array is None:
            return {
                "error": "Failed to preprocess image",
                "disease": None,
                "confidence": 0.0
            }
        
        try:
            # Get predictions
            predictions = self.model.predict(img_array, verbose=0)[0]
            
            # Get top prediction
            predicted_idx = np.argmax(predictions)
            confidence = float(predictions[predicted_idx])
            predicted_class = self.class_names[predicted_idx]
            
            # Get top 3 predictions
            top_3_indices = np.argsort(predictions)[-3:][::-1]
            top_3_predictions = [
                {
                    "class": self.class_names[idx],
                    "confidence": float(predictions[idx])
                }
                for idx in top_3_indices
            ]
            
            # Parse crop and disease from class name
            crop, disease = self._parse_class_name(predicted_class)
            
            return {
                "disease": disease,
                "crop": crop,
                "full_class_name": predicted_class,
                "confidence": confidence,
                "top_3_predictions": top_3_predictions,
                "is_healthy": "healthy" in predicted_class.lower(),
                "all_predictions": {
                    self.class_names[i]: float(predictions[i])
                    for i in range(len(self.class_names))
                }
            }
            
        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            return {
                "error": str(e),
                "disease": None,
                "confidence": 0.0
            }
    
    def _parse_class_name(self, class_name: str) -> Tuple[str, str]:
        """Parse class name to extract crop and disease"""
        # Format: "Crop___Disease" or "Crop___healthy"
        if "___" in class_name:
            parts = class_name.split("___")
            crop = parts[0].strip()
            disease = parts[1].strip() if len(parts) > 1 else "Unknown"
            
            # Clean up crop name
            crop = crop.replace("(including_sour)", "").replace("(maize)", "").strip()
            crop = crop.replace(",", "").strip()
            
            # Map disease names to match remedies.json format
            disease = self._map_disease_name(disease)
            
            return crop, disease
        else:
            return "Unknown", class_name
    
    def _map_disease_name(self, disease: str) -> str:
        """Map CNN disease names to remedy database names"""
        # Mapping dictionary for common disease name variations
        disease_mapping = {
            "Late blight": "Late Blight",
            "Early blight": "Early Blight",
            "Bacterial spot": "Bacterial Leaf Spot",
            "Powdery mildew": "Powdery Mildew",
            "Black rot": "Black Rot",
            "Leaf blight (Isariopsis_Leaf_Spot)": "Leaf Blight",
            "Cercospora_leaf_spot Gray_leaf_spot": "Cercospora Leaf Spot",
            "Common_rust_": "Rust",
            "Northern_Leaf_Blight": "Northern Leaf Blight",
            "Esca_(Black_Measles)": "Black Measles",
            "Haunglongbing_(Citrus_greening)": "Citrus Greening",
            "Leaf_Mold": "Leaf Mold",
            "Septoria_leaf_spot": "Septoria Leaf Spot",
            "Spider_mites Two-spotted_spider_mite": "Spider Mites",
            "Target_Spot": "Target Spot",
            "Tomato_Yellow_Leaf_Curl_Virus": "Yellow Leaf Curl Virus",
            "Tomato_mosaic_virus": "Mosaic Virus",
            "Apple_scab": "Apple Scab",
            "Cedar_apple_rust": "Cedar Apple Rust"
        }
        
        # Check for exact match
        if disease in disease_mapping:
            return disease_mapping[disease]
        
        # Check for partial match
        disease_lower = disease.lower()
        for key, value in disease_mapping.items():
            if key.lower() in disease_lower or disease_lower in key.lower():
                return value
        
        # Return cleaned disease name
        return disease.replace("_", " ").title()

