"""
Data models for Buyer Connect & Fair Negotiation module
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime


class CropInterest(BaseModel):
    """Buyer's interest in a specific crop"""
    crop: str = Field(..., description="Crop name")
    min_qty: float = Field(..., description="Minimum quantity buyer wants (in kg)")
    max_qty: float = Field(..., description="Maximum quantity buyer wants (in kg)")
    preferred_price: float = Field(..., description="Buyer's preferred price per unit")


class Buyer(BaseModel):
    """Buyer model"""
    id: Optional[int] = Field(None, description="Buyer ID")
    name: str = Field(..., description="Buyer name")
    phone: str = Field(..., description="Buyer phone number")
    location: str = Field(..., description="Buyer location (city/district)")
    interested_crops: List[CropInterest] = Field(..., description="List of crops buyer is interested in")
    verified: bool = Field(False, description="Whether buyer is verified")


class ListingStatus(str, Enum):
    """Farmer listing status"""
    OPEN = "open"
    NEGOTIATING = "negotiating"
    CLOSED = "closed"


class FarmerListing(BaseModel):
    """Farmer listing model"""
    id: Optional[Union[int, str]] = Field(None, description="Listing ID (int or string for Firestore)")
    farmer_id: int = Field(..., description="Farmer ID")
    crop: str = Field(..., description="Crop name")
    quantity: float = Field(..., description="Quantity available (in kg)")
    unit: str = Field("kg", description="Unit of measurement")
    farmer_threshold_price: float = Field(..., description="Farmer's minimum acceptable price per unit")
    status: ListingStatus = Field(ListingStatus.OPEN, description="Listing status")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="Creation timestamp")
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v):
        """Accept both int and string IDs"""
        if v is None:
            return v
        # If it's already an int or string, return as-is
        if isinstance(v, (int, str)):
            return v
        # Try to convert to int if it's a numeric string
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return str(v)


class MatchStatus(str, Enum):
    """Buyer match status"""
    OPEN = "open"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class BuyerMatch(BaseModel):
    """Buyer match model"""
    id: Optional[Union[int, str]] = Field(None, description="Match ID (int or string for Firestore)")
    listing_id: Union[int, str] = Field(..., description="Associated listing ID")
    buyer_id: Union[int, str] = Field(..., description="Associated buyer ID")
    buyer_preferred_price: float = Field(..., description="Buyer's preferred price per unit")
    benchmark_price: float = Field(..., description="Market benchmark price per unit")
    suggested_price: Optional[float] = Field(None, description="System-suggested fair price per unit")
    match_status: MatchStatus = Field(MatchStatus.OPEN, description="Match status")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="Creation timestamp")


class PriceSuggestion(BaseModel):
    """Price suggestion result from negotiation engine"""
    suggested_price: Optional[float] = Field(None, description="Suggested fair price (None if no fair match)")
    fair_lower: float = Field(..., description="Lower bound of fair price range")
    fair_upper: float = Field(..., description="Upper bound of fair price range")
    explanation: str = Field(..., description="Farmer-friendly explanation of the price suggestion")
    has_fair_match: bool = Field(..., description="Whether a fair price match exists")


class MatchedBuyer(BaseModel):
    """Matched buyer information for farmer"""
    buyer_id: Union[int, str]
    buyer_name: str
    location: str
    preferred_price: float
    demand_range: Dict[str, float] = Field(..., description="min_qty and max_qty")
    match_score: Optional[float] = Field(None, description="Match quality score (0-1)")


class NegotiationResponse(BaseModel):
    """Response from negotiation endpoint"""
    buyer: str
    benchmark_price: float
    buyer_offer: float
    farmer_min_price: float
    suggested_price: Optional[float]
    explanation: str
    match_id: Optional[int] = None


class BuyerRequirement(BaseModel):
    """Buyer requirement model for Firestore"""
    id: Optional[str] = Field(None, description="Requirement ID (Firestore document ID)")
    buyer_id: Union[int, str] = Field(..., description="Buyer ID (integer preferred, e.g., 1 instead of 'buyer1')")
    crop: str = Field(..., description="Crop name")
    required_quantity: float = Field(..., description="Required quantity in kg")
    max_price: float = Field(..., description="Maximum price per kg")
    location: str = Field(..., description="Buyer location")
    valid_till: str = Field(..., description="Validity period (ISO date string)")
    updated_at: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat(), description="Last update timestamp")


class Negotiation(BaseModel):
    """Negotiation record model for Firestore"""
    id: Optional[str] = Field(None, description="Negotiation ID (Firestore document ID)")
    listing_id: Union[int, str] = Field(..., description="Farmer listing ID")
    buyer_id: Union[int, str] = Field(..., description="Buyer ID (integer preferred)")
    ai_suggested_price: Optional[float] = Field(None, description="AI suggested fair price")
    explanation: str = Field(..., description="Explanation of price suggestion")
    decision: Optional[str] = Field(None, description="Decision: accept, counter, reject, or null")
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp")
    benchmark_price: Optional[float] = Field(None, description="Market benchmark price")
    buyer_offer: Optional[float] = Field(None, description="Buyer's offer price")
    farmer_min_price: Optional[float] = Field(None, description="Farmer's minimum price")
    fair_lower: Optional[float] = Field(None, description="Lower bound of fair price range")
    fair_upper: Optional[float] = Field(None, description="Upper bound of fair price range")
