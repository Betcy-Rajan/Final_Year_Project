"""
Government Scheme RAG Agent - Retrieval-Augmented Generation for Scheme Discovery
"""
import json
import logging
import re
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np

logger = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available - RAG features will be limited")

from config import SCHEMES_FILE

@dataclass
class UserProfile:
    """User profile extracted from query"""
    state: Optional[str] = None
    crops: List[str] = None
    land_size: Optional[float] = None  # in acres
    farmer_type: Optional[str] = None  # small, marginal, large
    age: Optional[int] = None
    income: Optional[float] = None
    target_group: Optional[str] = None  # SC, ST, BPL, Women, etc.
    sub_category: Optional[str] = None
    scheme_scope: str = "all"  # "all", "state_only", "central_only"
    
    def __post_init__(self):
        if self.crops is None:
            self.crops = []

@dataclass
class EligibilityHints:
    """Structured eligibility hints extracted from scheme"""
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    land_size_min: Optional[float] = None
    land_size_max: Optional[float] = None
    income_max: Optional[float] = None
    target_groups: List[str] = None
    crops: List[str] = None
    states: List[str] = None
    
    def __post_init__(self):
        if self.target_groups is None:
            self.target_groups = []
        if self.crops is None:
            self.crops = []
        if self.states is None:
            self.states = []

class SchemeDataNormalizer:
    """Normalizes and enriches scheme data for RAG"""
    
    @staticmethod
    def normalize_scheme(scheme: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single scheme and add RAG fields"""
        # Create RAG text for embedding
        rag_parts = []
        
        # Add scheme name
        if scheme.get("scheme_name"):
            rag_parts.append(scheme["scheme_name"])
        
        # Add brief description
        if scheme.get("brief_description"):
            rag_parts.append(scheme["brief_description"])
        
        # Add full description (first 500 chars to avoid too long)
        if scheme.get("full_description"):
            desc = scheme["full_description"][:500]
            rag_parts.append(desc)
        
        # Add sub-categories
        if scheme.get("sub_category"):
            rag_parts.append(" ".join(scheme["sub_category"]))
        
        # Add categories
        if scheme.get("category"):
            rag_parts.append(" ".join(scheme["category"]))
        
        # Add eligibility keywords
        if scheme.get("eligibility"):
            eligibility_text = " ".join(str(e) for e in scheme["eligibility"][:3])
            rag_parts.append(eligibility_text[:300])
        
        # Add benefits keywords
        if scheme.get("benefits"):
            benefits_text = " ".join(str(b) for b in scheme["benefits"][:2])
            rag_parts.append(benefits_text[:200])
        
        # Combine into RAG text
        rag_text = " ".join(rag_parts)
        
        # Extract eligibility hints
        eligibility_hints = SchemeDataNormalizer._extract_eligibility_hints(scheme)
        
        # Extract crop tags from description and eligibility
        crop_tags = SchemeDataNormalizer._extract_crop_tags(scheme)
        
        # Extract application links
        application_links = []
        if scheme.get("references"):
            for ref in scheme["references"]:
                if isinstance(ref, dict) and ref.get("url"):
                    application_links.append({
                        "title": ref.get("title", "Application Link"),
                        "url": ref.get("url")
                    })
        
        # Add enriched fields
        enriched_scheme = scheme.copy()
        enriched_scheme["rag_text"] = rag_text
        enriched_scheme["eligibility_hints"] = eligibility_hints.__dict__
        enriched_scheme["crop_tags"] = crop_tags
        enriched_scheme["application_links"] = application_links
        
        return enriched_scheme
    
    @staticmethod
    def _extract_eligibility_hints(scheme: Dict[str, Any]) -> EligibilityHints:
        """Extract structured eligibility hints from scheme text"""
        hints = EligibilityHints()
        eligibility_text = ""
        
        if scheme.get("eligibility"):
            eligibility_text = " ".join(str(e) for e in scheme["eligibility"]).lower()
        
        # Extract age range
        age_patterns = [
            r'age.*?(\d+).*?(\d+)',
            r'between\s+(\d+)\s+and\s+(\d+)\s+years',
            r'(\d+)\s+to\s+(\d+)\s+years',
            r'above\s+(\d+)\s+years?',
            r'below\s+(\d+)\s+years?',
            r'minimum\s+age\s+(\d+)',
            r'maximum\s+age\s+(\d+)',
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, eligibility_text)
            if match:
                if len(match.groups()) == 2:
                    hints.age_min = int(match.group(1))
                    hints.age_max = int(match.group(2))
                elif 'above' in pattern or 'minimum' in pattern:
                    hints.age_min = int(match.group(1))
                elif 'below' in pattern or 'maximum' in pattern:
                    hints.age_max = int(match.group(1))
                break
        
        # Extract land size
        land_patterns = [
            r'land.*?(\d+(?:\.\d+)?)\s*(?:acres?|hectares?|bighas?)',
            r'(\d+(?:\.\d+)?)\s*(?:acres?|hectares?|bighas?).*?land',
            r'minimum\s+(\d+(?:\.\d+)?)\s*(?:acres?|hectares?|bighas?)',
            r'maximum\s+(\d+(?:\.\d+)?)\s*(?:acres?|hectares?|bighas?)',
        ]
        
        for pattern in land_patterns:
            matches = re.findall(pattern, eligibility_text)
            if matches:
                values = [float(m) for m in matches]
                if 'minimum' in pattern:
                    hints.land_size_min = min(values)
                elif 'maximum' in pattern:
                    hints.land_size_max = max(values)
                else:
                    hints.land_size_min = min(values)
                    hints.land_size_max = max(values) if len(values) > 1 else None
        
        # Extract income limits
        income_patterns = [
            r'income.*?(\d+(?:\.\d+)?)\s*(?:lakhs?|lakh|rupees?|rs\.?)',
            r'(\d+(?:\.\d+)?)\s*(?:lakhs?|lakh).*?income',
            r'not\s+exceed.*?(\d+(?:\.\d+)?)\s*(?:lakhs?|lakh)',
        ]
        
        for pattern in income_patterns:
            match = re.search(pattern, eligibility_text)
            if match:
                value = float(match.group(1))
                # Convert lakhs to rupees if needed
                if 'lakh' in match.group(0):
                    value = value * 100000
                hints.income_max = value
                break
        
        # Extract target groups
        target_keywords = {
            'sc': 'SC', 'scheduled caste': 'SC',
            'st': 'ST', 'scheduled tribe': 'ST',
            'bpl': 'BPL', 'below poverty line': 'BPL',
            'women': 'Women', 'female': 'Women',
            'small farmer': 'Small Farmer',
            'marginal farmer': 'Marginal Farmer',
            'landless': 'Landless',
            'pwd': 'PWD', 'disabled': 'PWD',
        }
        
        for keyword, group in target_keywords.items():
            if keyword in eligibility_text:
                hints.target_groups.append(group)
        
        # Extract state
        if scheme.get("state"):
            hints.states = [scheme["state"]]
        else:
            hints.states = ["Central"]  # Central schemes apply to all states
        
        return hints
    
    @staticmethod
    def _extract_crop_tags(scheme: Dict[str, Any]) -> List[str]:
        """Extract crop-related keywords from scheme"""
        crops = []
        text = ""
        
        if scheme.get("brief_description"):
            text += " " + scheme["brief_description"].lower()
        if scheme.get("full_description"):
            text += " " + scheme["full_description"].lower()
        if scheme.get("eligibility"):
            text += " " + " ".join(str(e) for e in scheme["eligibility"]).lower()
        
        # Common crop keywords
        crop_keywords = [
            'rice', 'wheat', 'maize', 'corn', 'sugarcane', 'cotton', 'jute',
            'pulses', 'oilseeds', 'soybean', 'groundnut', 'mustard', 'sunflower',
            'tomato', 'potato', 'onion', 'chilli', 'vegetables', 'fruits',
            'mango', 'banana', 'apple', 'orange', 'grapes', 'pomegranate',
            'dairy', 'milk', 'cattle', 'buffalo', 'goat', 'sheep', 'poultry',
            'chicken', 'fish', 'fishing', 'aquaculture', 'prawn', 'shrimp',
            'spices', 'turmeric', 'ginger', 'pepper', 'cardamom',
            'tea', 'coffee', 'rubber', 'coconut', 'cashew', 'arecanut',
        ]
        
        for keyword in crop_keywords:
            if keyword in text:
                crops.append(keyword.title())
        
        return list(set(crops))  # Remove duplicates


class SchemeVectorStore:
    """Simple in-memory vector store using TF-IDF"""
    
    def __init__(self):
        self.schemes: List[Dict[str, Any]] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.vectors: Optional[np.ndarray] = None
        self._is_built = False
    
    def add_schemes(self, schemes: List[Dict[str, Any]]):
        """Add schemes to the vector store"""
        self.schemes = schemes
        self._is_built = False
    
    def build_index(self):
        """Build TF-IDF index from schemes"""
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn not available - cannot build vector index")
            return
        
        if not self.schemes:
            logger.warning("No schemes to index")
            return
        
        # Extract RAG text from all schemes
        rag_texts = []
        for scheme in self.schemes:
            rag_text = scheme.get("rag_text", "")
            if not rag_text:
                # Fallback: create rag_text from available fields
                parts = []
                if scheme.get("scheme_name"):
                    parts.append(scheme["scheme_name"])
                if scheme.get("brief_description"):
                    parts.append(scheme["brief_description"])
                if scheme.get("sub_category"):
                    parts.append(" ".join(scheme["sub_category"]))
                rag_text = " ".join(parts)
            rag_texts.append(rag_text)
        
        # Build TF-IDF vectors
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2
        )
        self.vectors = self.vectorizer.fit_transform(rag_texts).toarray()
        self._is_built = True
        logger.info(f"Built vector index for {len(self.schemes)} schemes")
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """Search for similar schemes"""
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn not available - using simple keyword matching")
            # Fallback: simple keyword matching
            query_words = set(query.lower().split())
            results = []
            for scheme in self.schemes:
                rag_text = scheme.get("rag_text", "").lower()
                matches = sum(1 for word in query_words if word in rag_text)
                if matches > 0:
                    score = matches / len(query_words) if query_words else 0
                    results.append((scheme, score))
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
        
        if not self._is_built:
            self.build_index()
        
        if not self.vectors.size:
            return []
        
        # Vectorize query
        query_vector = self.vectorizer.transform([query]).toarray()
        
        # Compute cosine similarity
        similarities = cosine_similarity(query_vector, self.vectors)[0]
        
        # Get top K indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Return schemes with scores
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:  # Only return non-zero similarity
                results.append((self.schemes[idx], float(similarities[idx])))
        
        return results


class QueryParser:
    """Parse user queries to extract profile information"""
    
    @staticmethod
    def parse(user_input: str, context_state: Optional[str] = None) -> UserProfile:
        """Parse user input to extract profile"""
        profile = UserProfile()
        user_lower = user_input.lower()
        
        # Extract state (from context or query)
        if context_state:
            profile.state = context_state
        else:
            profile.state = QueryParser._extract_state(user_input)
        
        # Extract crops
        profile.crops = QueryParser._extract_crops(user_input)
        
        # Extract land size
        profile.land_size = QueryParser._extract_land_size(user_input)
        
        # Extract farmer type
        profile.farmer_type = QueryParser._extract_farmer_type(user_input)
        
        # Extract age
        profile.age = QueryParser._extract_age(user_input)
        
        # Extract income
        profile.income = QueryParser._extract_income(user_input)
        
        # Extract target group
        profile.target_group = QueryParser._extract_target_group(user_input)
        
        # Extract sub-category
        profile.sub_category = QueryParser._extract_sub_category(user_input)
        
        # Extract scheme scope
        profile.scheme_scope = QueryParser._extract_scheme_scope(user_input)
        
        return profile
    
    @staticmethod
    def _extract_state(user_input: str) -> Optional[str]:
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
        return None
    
    @staticmethod
    def _extract_crops(user_input: str) -> List[str]:
        """Extract crop mentions from user input"""
        crops = []
        user_lower = user_input.lower()
        
        crop_keywords = {
            'rice', 'wheat', 'maize', 'corn', 'sugarcane', 'cotton', 'jute',
            'pulses', 'oilseeds', 'soybean', 'groundnut', 'mustard', 'sunflower',
            'tomato', 'potato', 'onion', 'chilli', 'vegetables', 'fruits',
            'mango', 'banana', 'apple', 'orange', 'grapes', 'pomegranate',
            'dairy', 'milk', 'cattle', 'buffalo', 'goat', 'sheep', 'poultry',
            'chicken', 'fish', 'fishing', 'aquaculture', 'prawn', 'shrimp',
        }
        
        for keyword in crop_keywords:
            if keyword in user_lower:
                crops.append(keyword.title())
        
        return crops
    
    @staticmethod
    def _extract_land_size(user_input: str) -> Optional[float]:
        """Extract land size from user input"""
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:acres?|hectares?|bighas?)',
            r'land.*?(\d+(?:\.\d+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                return float(match.group(1))
        return None
    
    @staticmethod
    def _extract_farmer_type(user_input: str) -> Optional[str]:
        """Extract farmer type"""
        user_lower = user_input.lower()
        if 'small farmer' in user_lower or 'small and marginal' in user_lower:
            return 'small'
        elif 'marginal farmer' in user_lower:
            return 'marginal'
        elif 'large farmer' in user_lower:
            return 'large'
        return None
    
    @staticmethod
    def _extract_age(user_input: str) -> Optional[int]:
        """Extract age from user input"""
        patterns = [
            r'age\s+(\d+)',
            r'(\d+)\s+years?\s+old',
            r'i\s+am\s+(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                return int(match.group(1))
        return None
    
    @staticmethod
    def _extract_income(user_input: str) -> Optional[float]:
        """Extract income from user input"""
        patterns = [
            r'income.*?(\d+(?:\.\d+)?)\s*(?:lakhs?|lakh)',
            r'(\d+(?:\.\d+)?)\s*(?:lakhs?|lakh).*?income',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                value = float(match.group(1))
                return value * 100000  # Convert lakhs to rupees
        return None
    
    @staticmethod
    def _extract_target_group(user_input: str) -> Optional[str]:
        """Extract target group"""
        user_lower = user_input.lower()
        if 'sc' in user_lower or 'scheduled caste' in user_lower:
            return 'SC'
        elif 'st' in user_lower or 'scheduled tribe' in user_lower:
            return 'ST'
        elif 'bpl' in user_lower or 'below poverty line' in user_lower:
            return 'BPL'
        elif 'women' in user_lower or 'female' in user_lower:
            return 'Women'
        return None
    
    @staticmethod
    def _extract_sub_category(user_input: str) -> Optional[str]:
        """Extract sub-category from user input"""
        # This will be handled by the main scheme agent
        # Just return None here, let the scheme agent handle it
        return None
    
    @staticmethod
    def _extract_scheme_scope(user_input: str) -> str:
        """Extract scheme scope preference"""
        user_lower = user_input.lower()
        if 'state scheme' in user_lower or 'state only' in user_lower:
            return 'state_only'
        elif 'central scheme' in user_lower or 'central only' in user_lower or 'union' in user_lower:
            return 'central_only'
        elif 'both' in user_lower or 'all' in user_lower:
            return 'all'
        return 'all'  # Default to all


class EligibilityChecker:
    """Check eligibility based on user profile and scheme hints"""
    
    @staticmethod
    def check_eligibility(profile: UserProfile, scheme: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Check eligibility and return status with reasons
        Returns: (status, reasons)
        status: "likely_eligible", "possibly_eligible", "unclear", "unlikely"
        """
        reasons = []
        hints_dict = scheme.get("eligibility_hints", {})
        if not hints_dict:
            return "unclear", ["No eligibility information available"]
        
        hints = EligibilityHints(**hints_dict)
        score = 0
        max_score = 0
        
        # Check age
        if hints.age_min or hints.age_max:
            max_score += 1
            if profile.age:
                if hints.age_min and profile.age < hints.age_min:
                    reasons.append(f"Age {profile.age} is below minimum {hints.age_min}")
                    return "unlikely", reasons
                elif hints.age_max and profile.age > hints.age_max:
                    reasons.append(f"Age {profile.age} is above maximum {hints.age_max}")
                    return "unlikely", reasons
                else:
                    score += 1
                    reasons.append(f"Age {profile.age} meets requirements")
            else:
                reasons.append("Age information not provided")
        
        # Check land size
        if hints.land_size_min or hints.land_size_max:
            max_score += 1
            if profile.land_size:
                if hints.land_size_min and profile.land_size < hints.land_size_min:
                    reasons.append(f"Land size {profile.land_size} acres is below minimum {hints.land_size_min}")
                    return "unlikely", reasons
                elif hints.land_size_max and profile.land_size > hints.land_size_max:
                    reasons.append(f"Land size {profile.land_size} acres exceeds maximum {hints.land_size_max}")
                    return "unlikely", reasons
                else:
                    score += 1
                    reasons.append(f"Land size {profile.land_size} acres meets requirements")
        
        # Check income
        if hints.income_max:
            max_score += 1
            if profile.income:
                if profile.income > hints.income_max:
                    reasons.append(f"Income exceeds maximum limit")
                    return "unlikely", reasons
                else:
                    score += 1
                    reasons.append(f"Income within acceptable range")
        
        # Check target groups
        if hints.target_groups:
            max_score += 1
            if profile.target_group and profile.target_group in hints.target_groups:
                score += 1
                reasons.append(f"Target group {profile.target_group} matches")
            elif not profile.target_group:
                reasons.append("Target group not specified")
        
        # Check state
        if hints.states:
            max_score += 1
            scheme_state = scheme.get("state", "")
            if scheme_state:
                if profile.state and profile.state.lower() == scheme_state.lower():
                    score += 1
                    reasons.append(f"State {profile.state} matches")
                elif not profile.state:
                    reasons.append("State not specified")
            else:  # Central scheme
                score += 1
                reasons.append("Central scheme - applies to all states")
        
        # Determine status
        if max_score == 0:
            return "unclear", ["No eligibility criteria available"]
        
        ratio = score / max_score
        if ratio >= 0.8:
            return "likely_eligible", reasons
        elif ratio >= 0.5:
            return "possibly_eligible", reasons
        elif ratio > 0:
            return "unclear", reasons
        else:
            return "unlikely", reasons


class SchemeRAGAgent:
    """Main RAG Agent for scheme discovery"""
    
    def __init__(self, schemes_file: str = SCHEMES_FILE):
        self.schemes_file = schemes_file
        self.schemes: List[Dict[str, Any]] = []
        self.vector_store = SchemeVectorStore()
        self._loaded = False
    
    def load_schemes(self):
        """Load and normalize schemes"""
        if self._loaded:
            return
        
        logger.info(f"Loading schemes from {self.schemes_file}")
        try:
            with open(self.schemes_file, 'r', encoding='utf-8') as f:
                raw_schemes = json.load(f)
            
            # Normalize all schemes
            self.schemes = []
            for scheme in raw_schemes:
                normalized = SchemeDataNormalizer.normalize_scheme(scheme)
                self.schemes.append(normalized)
            
            # Build vector index
            self.vector_store.add_schemes(self.schemes)
            self.vector_store.build_index()
            
            self._loaded = True
            logger.info(f"Loaded and indexed {len(self.schemes)} schemes")
        except Exception as e:
            logger.error(f"Error loading schemes: {e}")
            raise
    
    def retrieve_schemes(self, profile: UserProfile, top_k: int = 10) -> List[Dict[str, Any]]:
        """Retrieve relevant schemes based on user profile"""
        if not self._loaded:
            self.load_schemes()
        
        # Build query text for vector search
        query_parts = []
        
        if profile.state:
            query_parts.append(f"schemes for {profile.state}")
        
        if profile.crops:
            query_parts.append(f"for {', '.join(profile.crops)}")
        
        if profile.sub_category:
            query_parts.append(profile.sub_category)
        
        if profile.land_size:
            query_parts.append(f"land size {profile.land_size} acres")
        
        if profile.farmer_type:
            query_parts.append(f"{profile.farmer_type} farmer")
        
        query_text = " ".join(query_parts) if query_parts else "government agricultural schemes"
        
        # Vector search
        vector_results = self.vector_store.search(query_text, top_k=top_k * 2)  # Get more for filtering
        
        # Filter by metadata
        filtered_schemes = []
        for scheme, score in vector_results:
            # Filter by state/central scope
            scheme_state = scheme.get("state", "")
            if profile.scheme_scope == "state_only":
                if not scheme_state or scheme_state.lower() != (profile.state or "").lower():
                    continue
            elif profile.scheme_scope == "central_only":
                if scheme_state:  # Not a central scheme
                    continue
            elif profile.scheme_scope == "all":
                # When scope is "all" but a state is specified, show that state's schemes + central schemes
                if profile.state:
                    # Only include schemes for the specified state OR central schemes
                    if scheme_state and scheme_state.lower() != profile.state.lower():
                        continue  # Skip schemes from other states
                # If no state specified, include all schemes (both state and central)
            
            # Filter by sub-category if specified
            if profile.sub_category:
                scheme_subcats = scheme.get("sub_category", [])
                if not any(profile.sub_category.lower() in str(sc).lower() for sc in scheme_subcats):
                    # Check if subcategory matches via fuzzy matching
                    if not self._fuzzy_match_subcategory(profile.sub_category, scheme_subcats):
                        continue
            
            # Add boosted score based on metadata matches
            boosted_score = score
            
            # Boost for exact state match
            if profile.state and scheme_state and profile.state.lower() == scheme_state.lower():
                boosted_score += 0.2
            
            # Boost for crop matches
            scheme_crops = scheme.get("crop_tags", [])
            if profile.crops and scheme_crops:
                matches = set(c.lower() for c in profile.crops) & set(c.lower() for c in scheme_crops)
                if matches:
                    boosted_score += 0.15 * len(matches)
            
            filtered_schemes.append((scheme, boosted_score))
        
        # Sort by boosted score and return top K
        filtered_schemes.sort(key=lambda x: x[1], reverse=True)
        return [scheme for scheme, _ in filtered_schemes[:top_k]]
    
    def _fuzzy_match_subcategory(self, query_subcat: str, scheme_subcats: List[str]) -> bool:
        """Fuzzy match subcategory"""
        query_lower = query_subcat.lower()
        for sc in scheme_subcats:
            sc_lower = str(sc).lower()
            if query_lower in sc_lower or sc_lower in query_lower:
                return True
            # Check word overlap
            query_words = set(query_lower.split())
            sc_words = set(sc_lower.split())
            if len(query_words & sc_words) >= 2:  # At least 2 words match
                return True
        return False
    
    def assess_eligibility(self, profile: UserProfile, schemes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Assess eligibility for each scheme"""
        assessed_schemes = []
        for scheme in schemes:
            status, reasons = EligibilityChecker.check_eligibility(profile, scheme)
            scheme_copy = scheme.copy()
            scheme_copy["eligibility_status"] = status
            scheme_copy["eligibility_reasons"] = reasons
            assessed_schemes.append(scheme_copy)
        
        return assessed_schemes
    
    def format_response(self, profile: UserProfile, schemes: List[Dict[str, Any]]) -> str:
        """Format schemes into a readable response"""
        if not schemes:
            return "No matching schemes found. Please try adjusting your search criteria."
        
        lines = []
        lines.append(f"**Top {len(schemes)} Relevant Schemes")
        if profile.state:
            lines.append(f" for {profile.state}**")
        else:
            lines.append("**")
        lines.append("\n\n")
        
        for i, scheme in enumerate(schemes, 1):
            scheme_name = scheme.get("scheme_name", "Unknown Scheme")
            scheme_state = scheme.get("state", "")
            scheme_type = "Central Scheme" if not scheme_state else f"State Scheme ({scheme_state})"
            
            lines.append(f"### {i}. {scheme_name}\n")
            lines.append(f"**Type:** {scheme_type}\n\n")
            
            # Brief description
            brief_desc = scheme.get("brief_description", "")
            if brief_desc:
                lines.append(f"**Description:** {brief_desc[:200]}...\n\n")
            
            # Eligibility status
            eligibility_status = scheme.get("eligibility_status", "unclear")
            if eligibility_status != "unclear":
                status_emoji = {
                    "likely_eligible": "✅",
                    "possibly_eligible": "⚠️",
                    "unlikely": "❌"
                }.get(eligibility_status, "❓")
                lines.append(f"**Eligibility:** {status_emoji} {eligibility_status.replace('_', ' ').title()}\n\n")
            
            # Key eligibility requirements
            eligibility = scheme.get("eligibility", [])
            if eligibility:
                lines.append("**Key Requirements:**\n")
                for req in eligibility[:3]:
                    # Clean HTML entities
                    req_clean = req.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                    lines.append(f"- {req_clean[:150]}\n")
                lines.append("\n")
            
            # Benefits
            benefits = scheme.get("benefits", [])
            if benefits:
                lines.append("**Benefits:**\n")
                for benefit in benefits[:2]:
                    if benefit and benefit.strip() and benefit != "<br>":
                        benefit_clean = benefit.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                        lines.append(f"- {benefit_clean[:150]}\n")
                lines.append("\n")
            
            # Application links
            application_links = scheme.get("application_links", [])
            if application_links:
                lines.append("**Application Links:**\n")
                for link in application_links[:2]:
                    title = link.get("title", "Application Link")
                    url = link.get("url", "")
                    if url:
                        lines.append(f"- [{title}]({url})\n")
                lines.append("\n")
            
            lines.append("---\n\n")
        
        return "".join(lines)
    
    def process_query(self, user_input: str, context_state: Optional[str] = None) -> str:
        """Process a user query and return formatted response"""
        # Parse user profile
        profile = QueryParser.parse(user_input, context_state)
        
        # Retrieve schemes
        schemes = self.retrieve_schemes(profile, top_k=10)
        
        # Assess eligibility
        schemes = self.assess_eligibility(profile, schemes)
        
        # Format response
        response = self.format_response(profile, schemes)
        
        return response


