"""
Buyer Connect & Fair Negotiation - Business Logic
"""
import logging
from typing import List, Dict, Any, Optional
from buyer_connect_models import (
    Buyer, FarmerListing, BuyerMatch, CropInterest,
    MatchedBuyer, PriceSuggestion
)

logger = logging.getLogger(__name__)


def find_matching_buyers(listing: FarmerListing, buyers: List[Buyer]) -> List[MatchedBuyer]:
    """
    Find buyers matching a farmer's listing.
    
    Matching rules:
    1. Buyer must be interested in the crop
    2. listing.quantity must be within buyer.min_qty and buyer.max_qty
    3. (Optional) Same location or nearby district
    
    Returns a ranked list of matched buyers.
    """
    matched = []
    
    for buyer in buyers:
        # Find buyer's interest in the listing crop
        crop_interest = None
        for interest in buyer.interested_crops:
            if interest.crop.lower() == listing.crop.lower():
                crop_interest = interest
                break
        
        # Rule 1: Buyer must be interested in the crop
        if not crop_interest:
            continue
        
        # Rule 2: Flexible quantity matching - allow if within 50% range or overlapping
        # More flexible for smaller quantities
        qty_match = False
        
        # Check if listing quantity is within buyer's range
        if crop_interest.min_qty <= listing.quantity <= crop_interest.max_qty:
            qty_match = True
        # Check if listing quantity is within 50% of buyer's min (for smaller farmer quantities)
        elif listing.quantity >= crop_interest.min_qty * 0.5 and listing.quantity <= crop_interest.max_qty * 1.5:
            qty_match = True
        # Check if buyer's range overlaps with listing quantity (within 50%)
        elif (listing.quantity * 0.5 <= crop_interest.max_qty and listing.quantity * 1.5 >= crop_interest.min_qty):
            qty_match = True
        # Special case: if farmer has less quantity but buyer can accept smaller lots
        elif listing.quantity < crop_interest.min_qty and listing.quantity >= crop_interest.min_qty * 0.3:
            # Allow if farmer has at least 30% of buyer's minimum
            qty_match = True
        
        if not qty_match:
            continue
        
        # Calculate match score (higher is better)
        # Score based on:
        # - Quantity match (closer to middle of range = better)
        # - Price proximity (closer to farmer threshold = better)
        # Note: Location matching is optional and can be added if listing has location field
        
        # Quantity match score (0-1)
        qty_range = crop_interest.max_qty - crop_interest.min_qty
        if qty_range > 0:
            qty_center = crop_interest.min_qty + (qty_range / 2)
            qty_distance = abs(listing.quantity - qty_center)
            qty_score = max(0, 1 - (qty_distance / qty_range))
        else:
            qty_score = 1.0  # Exact match
        
        # Price proximity score (0-1)
        # Closer buyer price is to farmer threshold = better
        # More flexible: allow up to 15% difference and still give a score
        price_diff = abs(crop_interest.preferred_price - listing.farmer_threshold_price)
        avg_price = (crop_interest.preferred_price + listing.farmer_threshold_price) / 2
        if avg_price > 0:
            price_diff_ratio = price_diff / avg_price
            # If within 15% difference, give a good score
            if price_diff_ratio <= 0.15:
                price_score = 1 - (price_diff_ratio / 0.15) * 0.3  # Score between 0.7 and 1.0
            else:
                # Still give some score if within 30% difference
                price_score = max(0, 0.7 - ((price_diff_ratio - 0.15) / 0.15) * 0.5)
        else:
            price_score = 1.0
        
        # Combined match score (weighted)
        match_score = (qty_score * 0.5) + (price_score * 0.5)
        
        matched_buyer = MatchedBuyer(
            buyer_id=buyer.id or 0,
            buyer_name=buyer.name,
            location=buyer.location,
            preferred_price=crop_interest.preferred_price,
            demand_range={
                "min_qty": crop_interest.min_qty,
                "max_qty": crop_interest.max_qty
            },
            match_score=match_score
        )
        matched.append(matched_buyer)
    
    # Sort by match score (highest first)
    matched.sort(key=lambda x: x.match_score or 0, reverse=True)
    
    logger.info(f"Found {len(matched)} matching buyers for listing {listing.id}")
    return matched


def generate_price_suggestion(
    farmer_threshold_price: float,
    buyer_preferred_price: float,
    benchmark_price: float
) -> PriceSuggestion:
    """
    Generate a fair price suggestion using rule-based logic.
    
    Rules:
    - α = 0.10 (lower bound: 10% below benchmark)
    - β = 0.15 (upper bound: 15% above benchmark)
    
    Steps:
    1) fair_lower = max(farmer_threshold_price, benchmark_price * (1 - α))
    2) fair_upper = min(buyer_preferred_price, benchmark_price * (1 + β))
    
    If fair_lower > fair_upper:
        return "NO_FAIR_MATCH"
    Else:
        suggested_price = average(fair_lower, fair_upper)
    
    Returns PriceSuggestion with explanation.
    """
    # Constants for fair price bounds
    ALPHA = 0.10  # Lower bound: 10% below benchmark
    BETA = 0.15   # Upper bound: 15% above benchmark
    
    # Step 1: Calculate fair lower bound
    # Must be at least farmer's threshold, and at least 10% below benchmark
    benchmark_lower = benchmark_price * (1 - ALPHA)
    fair_lower = max(farmer_threshold_price, benchmark_lower)
    
    # Step 2: Calculate fair upper bound
    # Must be at most buyer's preferred price, and at most 15% above benchmark
    benchmark_upper = benchmark_price * (1 + BETA)
    fair_upper = min(buyer_preferred_price, benchmark_upper)
    
    # Step 3: Check if fair match exists
    if fair_lower > fair_upper:
        # No fair match possible
        explanation = (
            f"Unfortunately, there's no fair price match. "
            f"Your minimum price ({farmer_threshold_price:.2f}) is higher than what the buyer can offer "
            f"({buyer_preferred_price:.2f}), or the market benchmark ({benchmark_price:.2f}) doesn't allow "
            f"a fair range. Consider adjusting your expectations or waiting for better market conditions."
        )
        
        return PriceSuggestion(
            suggested_price=None,
            fair_lower=fair_lower,
            fair_upper=fair_upper,
            explanation=explanation,
            has_fair_match=False
        )
    
    # Step 4: Calculate suggested price (average of fair range)
    suggested_price = (fair_lower + fair_upper) / 2
    
    # Generate farmer-friendly explanation
    explanation = (
        f"Suggested price is {suggested_price:.2f} per unit. "
        f"This is based on current mandi trends (benchmark: {benchmark_price:.2f}), "
        f"your minimum acceptable price ({farmer_threshold_price:.2f}), "
        f"and the buyer's offer ({buyer_preferred_price:.2f}). "
        f"The fair price range is between {fair_lower:.2f} and {fair_upper:.2f}."
    )
    
    logger.info(
        f"Price suggestion: {suggested_price:.2f} "
        f"(range: {fair_lower:.2f} - {fair_upper:.2f}, "
        f"farmer: {farmer_threshold_price:.2f}, buyer: {buyer_preferred_price:.2f}, "
        f"benchmark: {benchmark_price:.2f})"
    )
    
    return PriceSuggestion(
        suggested_price=suggested_price,
        fair_lower=fair_lower,
        fair_upper=fair_upper,
        explanation=explanation,
        has_fair_match=True
    )

