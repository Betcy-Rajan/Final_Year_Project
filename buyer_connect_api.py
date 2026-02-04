"""
FastAPI endpoints for Buyer Connect & Fair Negotiation module
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import logging
from buyer_connect_models import (
    FarmerListing, BuyerMatch, NegotiationResponse, MatchedBuyer,
    MatchStatus, ListingStatus, BuyerRequirement, Negotiation
)
from buyer_connect_storage import storage
from buyer_connect_logic import find_matching_buyers, generate_price_suggestion
from agents import PriceAgentNode, BuyerConnectAgentNode
from workflow import AgriMitraWorkflow

logger = logging.getLogger(__name__)

# Create APIRouter instead of FastAPI app
router = APIRouter(prefix="/buyer-connect", tags=["buyer-connect"])

# For backward compatibility, create app if needed
try:
    from fastapi import FastAPI
    app = FastAPI(title="Buyer Connect & Fair Negotiation API", version="1.0.0")
    app.include_router(router)
except:
    app = None

# Initialize PriceAgent for benchmark price fetching
price_agent = PriceAgentNode()
buyer_connect_agent = BuyerConnectAgentNode()
workflow = AgriMitraWorkflow()


@router.post("/listings", response_model=FarmerListing)
async def create_listing(listing: FarmerListing):
    """
    Create a new farmer listing.
    
    Example:
    {
        "farmer_id": 1,
        "crop": "tomato",
        "quantity": 500,
        "unit": "kg",
        "farmer_threshold_price": 30.0
    }
    """
    try:
        created_listing = storage.create_listing(listing)
        return created_listing
    except Exception as e:
        logger.error(f"Error creating listing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/listings/{listing_id}", response_model=FarmerListing)
async def get_listing(listing_id: str):
    """Get a listing by ID (accepts string IDs from Firestore)"""
    # Try to convert to int if possible, otherwise use as string
    try:
        listing_id_int = int(listing_id)
        listing = storage.get_listing(listing_id_int)
    except ValueError:
        listing = storage.get_listing(listing_id)
    
    if not listing:
        raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")
    return listing


@router.get("/buyers/match/{listing_id}", response_model=List[MatchedBuyer])
async def get_matched_buyers(listing_id: str):
    """
    Get matched buyers for a listing.
    
    Returns ranked list of buyers matching the listing criteria.
    Supports flexible matching for similar price and quantity ranges.
    """
    # Try to convert to int if possible, otherwise use as string
    try:
        listing_id_int = int(listing_id)
        listing = storage.get_listing(listing_id_int)
    except ValueError:
        listing = storage.get_listing(listing_id)
    
    if not listing:
        raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")
    
    # Get all buyers (from old buyers collection)
    all_buyers = storage.get_all_buyers()
    
    # Find matching buyers from buyers collection
    matched = find_matching_buyers(listing, all_buyers)
    
    # Also check buyer_requirements collection for matches
    all_requirements = storage.get_buyer_requirements()
    for requirement in all_requirements:
        # Check if crop matches
        if requirement.crop.lower() != listing.crop.lower():
            continue
        
        # Flexible quantity matching: allow if within 50% range or overlapping
        # More flexible for smaller quantities like 200 kg
        qty_match = False
        # Check if listing quantity is within buyer's acceptable range (50% flexibility)
        if (requirement.required_quantity * 0.5 <= listing.quantity <= requirement.required_quantity * 1.5):
            qty_match = True
        # Check if required quantity is within 50% of listing quantity
        elif (listing.quantity * 0.5 <= requirement.required_quantity <= listing.quantity * 1.5):
            qty_match = True
        # Special case: if farmer has less quantity but buyer can accept smaller lots (at least 30% of requirement)
        elif listing.quantity < requirement.required_quantity * 0.5 and listing.quantity >= requirement.required_quantity * 0.3:
            qty_match = True
        
        if not qty_match:
            continue
        
        # Flexible price matching: allow if buyer max price is within 20% of farmer threshold
        # This allows for negotiation even if prices are slightly different
        price_diff = abs(requirement.max_price - listing.farmer_threshold_price)
        avg_price = (requirement.max_price + listing.farmer_threshold_price) / 2
        if avg_price > 0:
            price_diff_ratio = price_diff / avg_price
            if price_diff_ratio > 0.20:  # More than 20% difference - skip
                continue
        else:
            continue
        
        # Calculate match score
        qty_diff = abs(requirement.required_quantity - listing.quantity)
        max_qty = max(requirement.required_quantity, listing.quantity, 1)
        qty_score = max(0, 1 - (qty_diff / max_qty))
        price_score = max(0, 1 - price_diff_ratio)
        match_score = (qty_score * 0.5) + (price_score * 0.5)
        
        # Get buyer info if available (try both int and string)
        buyer = None
        try:
            buyer_id_int = int(requirement.buyer_id) if isinstance(requirement.buyer_id, str) and requirement.buyer_id.isdigit() else requirement.buyer_id
            buyer = storage.get_buyer(buyer_id_int)
        except:
            buyer = storage.get_buyer(requirement.buyer_id)
        
        buyer_name = buyer.name if buyer else f"Buyer {requirement.buyer_id}"
        buyer_location = buyer.location if buyer else requirement.location
        
        # Convert buyer_id to int if possible for MatchedBuyer model
        try:
            buyer_id_for_match = int(requirement.buyer_id) if isinstance(requirement.buyer_id, str) and requirement.buyer_id.isdigit() else requirement.buyer_id
        except:
            buyer_id_for_match = requirement.buyer_id
        
        matched_buyer = MatchedBuyer(
            buyer_id=buyer_id_for_match,
            buyer_name=buyer_name,
            location=buyer_location,
            preferred_price=requirement.max_price,
            demand_range={
                "min_qty": requirement.required_quantity * 0.8,  # Approximate range
                "max_qty": requirement.required_quantity * 1.2
            },
            match_score=match_score
        )
        matched.append(matched_buyer)
    
    # Sort by match score (highest first)
    matched.sort(key=lambda x: x.match_score or 0, reverse=True)
    
    logger.info(f"Found {len(matched)} matching buyers for listing {listing_id}")
    return matched


@router.post("/negotiate/{listing_id}/{buyer_id}", response_model=NegotiationResponse)
async def negotiate_price(listing_id: str, buyer_id: str):
    """
    Initiate price negotiation for a listing and buyer.
    
    This endpoint:
    1. Fetches benchmark price from PriceAgent
    2. Runs fair negotiation engine
    3. Creates a BuyerMatch record
    4. Returns suggested price + explanation
    """
    # Get listing (handle both int and string IDs)
    try:
        listing_id_int = int(listing_id)
        listing = storage.get_listing(listing_id_int)
    except ValueError:
        listing = storage.get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")
    
    # Get buyer (handle both int and string IDs)
    try:
        buyer_id_int = int(buyer_id)
        buyer = storage.get_buyer(buyer_id_int)
    except ValueError:
        buyer = storage.get_buyer(buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail=f"Buyer {buyer_id} not found")
    
    # Find buyer's interest in the crop
    crop_interest = None
    for interest in buyer.interested_crops:
        if interest.crop.lower() == listing.crop.lower():
            crop_interest = interest
            break
    
    if not crop_interest:
        raise HTTPException(
            status_code=400,
            detail=f"Buyer {buyer_id} is not interested in crop {listing.crop}"
        )
    
    # Step 1: Fetch benchmark price from PriceAgent
    try:
        price_result = price_agent.process(listing.crop)
        price_info = price_result.get("price_info", {})
        
        if "error" in price_info:
            # Fallback to a default benchmark if PriceAgent fails
            benchmark_price = (listing.farmer_threshold_price + crop_interest.preferred_price) / 2
            logger.warning(f"PriceAgent failed, using fallback benchmark: {benchmark_price}")
        else:
            benchmark_price = price_info.get("current_price", 0)
            if benchmark_price <= 0:
                # Fallback
                benchmark_price = (listing.farmer_threshold_price + crop_interest.preferred_price) / 2
    except Exception as e:
        logger.error(f"Error fetching benchmark price: {e}")
        # Fallback
        benchmark_price = (listing.farmer_threshold_price + crop_interest.preferred_price) / 2
    
    # Step 2: Run fair negotiation engine
    price_suggestion = generate_price_suggestion(
        farmer_threshold_price=listing.farmer_threshold_price,
        buyer_preferred_price=crop_interest.preferred_price,
        benchmark_price=benchmark_price
    )
    
    # Step 3: Create BuyerMatch record (convert IDs to int if possible)
    try:
        listing_id_int = int(listing_id) if isinstance(listing_id, str) else listing_id
    except ValueError:
        listing_id_int = listing_id
    try:
        buyer_id_int = int(buyer_id) if isinstance(buyer_id, str) else buyer_id
    except ValueError:
        buyer_id_int = buyer_id
    
    buyer_match = BuyerMatch(
        listing_id=listing_id_int,
        buyer_id=buyer_id_int,
        buyer_preferred_price=crop_interest.preferred_price,
        benchmark_price=benchmark_price,
        suggested_price=price_suggestion.suggested_price,
        match_status=MatchStatus.NEGOTIATING if price_suggestion.has_fair_match else MatchStatus.OPEN
    )
    
    created_match = storage.create_match(buyer_match)
    
    # Step 4: Update listing status to negotiating if fair match exists
    if price_suggestion.has_fair_match:
        storage.update_listing_status(listing_id, ListingStatus.NEGOTIATING)
    
    # Step 5: Return response
    return NegotiationResponse(
        buyer=buyer.name,
        benchmark_price=benchmark_price,
        buyer_offer=crop_interest.preferred_price,
        farmer_min_price=listing.farmer_threshold_price,
        suggested_price=price_suggestion.suggested_price,
        explanation=price_suggestion.explanation,
        match_id=created_match.id
    )


@router.post("/negotiate/{match_id}/accept")
async def accept_match(match_id: str):
    """
    Farmer accepts the suggested price.
    
    This marks the match as accepted and closes the listing.
    NO autonomous deal finalization - farmer must explicitly accept.
    """
    # Handle both int and string IDs
    try:
        match_id_int = int(match_id)
        match = storage.get_match(match_id_int)
    except ValueError:
        match = storage.get_match(match_id)
    
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    
    if match.match_status == MatchStatus.ACCEPTED:
        return {"message": "Match already accepted", "match_id": match_id}
    
    if match.match_status == MatchStatus.REJECTED:
        raise HTTPException(status_code=400, detail="Cannot accept a rejected match")
    
    # Update match status (handle both int and string IDs)
    try:
        match_id_int = int(match_id)
        storage.update_match_status(match_id_int, MatchStatus.ACCEPTED)
    except ValueError:
        storage.update_match_status(match_id, MatchStatus.ACCEPTED)
    
    # Close the listing
    storage.update_listing_status(match.listing_id, ListingStatus.CLOSED)
    
    # Reject other matches for the same listing
    other_matches = storage.get_matches_for_listing(match.listing_id)
    for other_match in other_matches:
        if other_match.id != match_id and other_match.match_status == MatchStatus.NEGOTIATING:
            storage.update_match_status(other_match.id, MatchStatus.REJECTED)
    
    logger.info(f"Match {match_id} accepted by farmer")
    return {
        "message": "Match accepted successfully",
        "match_id": match_id,
        "listing_id": match.listing_id,
        "status": "accepted"
    }


@router.post("/negotiate/{match_id}/reject")
async def reject_match(match_id: str):
    """
    Farmer rejects the suggested price.
    
    This marks the match as rejected.
    """
    # Handle both int and string IDs
    try:
        match_id_int = int(match_id)
        match = storage.get_match(match_id_int)
    except ValueError:
        match = storage.get_match(match_id)
    
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    
    if match.match_status == MatchStatus.REJECTED:
        return {"message": "Match already rejected", "match_id": match_id}
    
    if match.match_status == MatchStatus.ACCEPTED:
        raise HTTPException(status_code=400, detail="Cannot reject an accepted match")
    
    # Update match status (handle both int and string IDs)
    try:
        match_id_int = int(match_id)
        storage.update_match_status(match_id_int, MatchStatus.REJECTED)
    except ValueError:
        storage.update_match_status(match_id, MatchStatus.REJECTED)
    
    logger.info(f"Match {match_id} rejected by farmer")
    return {
        "message": "Match rejected",
        "match_id": match_id,
        "status": "rejected"
    }


# Buyer Requirements Endpoints
@router.post("/buyer-requirements", response_model=BuyerRequirement)
async def create_buyer_requirement(requirement: BuyerRequirement):
    """Create or update a buyer requirement"""
    try:
        if requirement.id:
            # Update existing requirement
            updated = storage.update_buyer_requirement(requirement.id, requirement)
            if not updated:
                raise HTTPException(status_code=404, detail=f"Requirement {requirement.id} not found")
            return updated
        else:
            # Create new requirement
            created = storage.create_buyer_requirement(requirement)
            return created
    except Exception as e:
        logger.error(f"Error creating/updating buyer requirement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyer-requirements", response_model=List[BuyerRequirement])
async def get_buyer_requirements(buyer_id: Optional[str] = None):
    """Get buyer requirements, optionally filtered by buyer_id"""
    try:
        requirements = storage.get_buyer_requirements(buyer_id)
        return requirements
    except Exception as e:
        logger.error(f"Error getting buyer requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyer-requirements/{requirement_id}", response_model=BuyerRequirement)
async def get_buyer_requirement(requirement_id: str):
    """Get a specific buyer requirement by ID"""
    requirement = storage.get_buyer_requirement(requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail=f"Requirement {requirement_id} not found")
    return requirement


@router.delete("/buyer-requirements/{requirement_id}")
async def delete_buyer_requirement(requirement_id: str):
    """Delete a buyer requirement"""
    success = storage.delete_buyer_requirement(requirement_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Requirement {requirement_id} not found")
    return {"message": "Requirement deleted successfully", "requirement_id": requirement_id}


# Natural Language Query Endpoint
class NLQueryRequest(BaseModel):
    query: str
    farmer_id: int = 1


@router.post("/query")
async def process_nl_query(request: NLQueryRequest):
    """
    Process natural language query for buyer connect.
    Routes to BuyerConnectAgent and returns matched buyers.
    """
    try:
        logger.info(f"Processing NL query: {request.query}")
        
        # Use the workflow to process the query
        result = workflow.run(user_input=request.query)
        
        # Extract buyer connect agent output
        buyer_connect_output = result.get("buyer_connect_agent_output", {})
        
        logger.info(f"Buyer connect output: {buyer_connect_output}")
        
        if "error" in buyer_connect_output:
            raise HTTPException(status_code=500, detail=buyer_connect_output["error"])
        
        matched_buyers = buyer_connect_output.get("matched_buyers", [])
        logger.info(f"Found {len(matched_buyers)} matched buyers")
        
        # If no matches found, log why
        if len(matched_buyers) == 0:
            listing_id = buyer_connect_output.get("listing_id")
            if listing_id:
                listing = storage.get_listing(listing_id)
                if listing:
                    logger.warning(f"No matches found for listing: crop={listing.crop}, qty={listing.quantity}, price={listing.farmer_threshold_price}")
                    # Check if there are any buyers/requirements at all
                    all_buyers = storage.get_all_buyers()
                    all_requirements = storage.get_buyer_requirements()
                    logger.info(f"Total buyers in system: {len(all_buyers)}, Total requirements: {len(all_requirements)}")
        
        return {
            "listing_id": buyer_connect_output.get("listing_id"),
            "matched_buyers": matched_buyers,
            "benchmark_price": buyer_connect_output.get("benchmark_price"),
            "price_suggestions": buyer_connect_output.get("price_suggestions", []),
            "final_response": result.get("final_response", "")
        }
    except Exception as e:
        logger.error(f"Error processing NL query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Negotiation Endpoints (using new Negotiation model)
@router.post("/negotiations", response_model=Negotiation)
async def create_negotiation(negotiation: Negotiation):
    """Create a new negotiation record"""
    try:
        created = storage.create_negotiation(negotiation)
        return created
    except Exception as e:
        logger.error(f"Error creating negotiation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/negotiations/listing/{listing_id}", response_model=List[Negotiation])
async def get_negotiations_for_listing(listing_id: str):
    """Get all negotiations for a listing"""
    try:
        negotiations = storage.get_negotiations_for_listing(listing_id)
        return negotiations
    except Exception as e:
        logger.error(f"Error getting negotiations for listing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/negotiations/buyer/{buyer_id}", response_model=List[Negotiation])
async def get_negotiations_for_buyer(buyer_id: str):
    """Get all negotiations for a buyer"""
    try:
        negotiations = storage.get_negotiations_for_buyer(buyer_id)
        return negotiations
    except Exception as e:
        logger.error(f"Error getting negotiations for buyer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class NegotiationDecisionRequest(BaseModel):
    decision: str  # "accept", "counter", or "reject"


@router.post("/negotiations/{negotiation_id}/decision", response_model=Negotiation)
async def update_negotiation_decision(negotiation_id: str, request: NegotiationDecisionRequest):
    """
    Update negotiation decision (accept, counter, or reject).
    
    When accepted:
    - Fair price is finalized and sent to buyer
    - Listing status is updated to CLOSED
    - Other negotiations for the same listing are rejected
    """
    if request.decision not in ["accept", "counter", "reject"]:
        raise HTTPException(status_code=400, detail="Decision must be 'accept', 'counter', or 'reject'")
    
    negotiation = storage.update_negotiation_decision(negotiation_id, request.decision)
    if not negotiation:
        raise HTTPException(status_code=404, detail=f"Negotiation {negotiation_id} not found")
    
    # If accepted, update listing status and reject other negotiations
    if request.decision == "accept":
        # Update listing status to CLOSED
        try:
            storage.update_listing_status(negotiation.listing_id, ListingStatus.CLOSED)
        except Exception as e:
            logger.warning(f"Could not update listing status: {e}")
        
        # Reject other negotiations for the same listing
        try:
            other_negotiations = storage.get_negotiations_for_listing(str(negotiation.listing_id))
            for other_neg in other_negotiations:
                if other_neg.id != negotiation_id and other_neg.decision != "reject":
                    storage.update_negotiation_decision(other_neg.id, "reject")
        except Exception as e:
            logger.warning(f"Could not reject other negotiations: {e}")
        
        logger.info(f"Negotiation {negotiation_id} accepted. Fair price ₹{negotiation.ai_suggested_price}/kg sent to buyer {negotiation.buyer_id}")
    
    return negotiation


# Enhanced negotiate endpoint that creates negotiation record
@router.post("/negotiate/{listing_id}/{buyer_id}/enhanced", response_model=Negotiation)
async def negotiate_price_enhanced(listing_id: str, buyer_id: str):
    """
    Enhanced negotiation endpoint that creates a negotiation record.
    Works with buyer requirements instead of just buyer interests.
    """
    # Get listing (handle both int and string IDs)
    try:
        listing_id_int = int(listing_id)
        listing = storage.get_listing(listing_id_int)
    except ValueError:
        listing = storage.get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")
    
    # Try to get buyer requirement first, then fall back to buyer from old collection
    buyer_requirements = storage.get_buyer_requirements(buyer_id)
    matching_requirement = None
    buyer_max_price = None
    
    for req in buyer_requirements:
        if req.crop.lower() == listing.crop.lower():
            matching_requirement = req
            buyer_max_price = req.max_price
            break
    
    # If no requirement found, try to get from old buyers collection
    if not matching_requirement:
        try:
            buyer_id_int = int(buyer_id) if isinstance(buyer_id, str) and buyer_id.isdigit() else buyer_id
            buyer = storage.get_buyer(buyer_id_int)
        except:
            buyer = storage.get_buyer(buyer_id)
        
        if buyer:
            # Find buyer's interest in the crop
            crop_interest = None
            for interest in buyer.interested_crops:
                if interest.crop.lower() == listing.crop.lower():
                    crop_interest = interest
                    buyer_max_price = interest.preferred_price
                    break
            
            if not crop_interest:
                raise HTTPException(
                    status_code=400,
                    detail=f"Buyer {buyer_id} has no requirement or interest for crop {listing.crop}"
                )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Buyer {buyer_id} not found"
            )
    
    # Fetch benchmark price
    try:
        price_result = price_agent.process(listing.crop)
        price_info = price_result.get("price_info", {})
        benchmark_price = price_info.get("current_price", 0)
        
        # Convert USD to INR if price seems too low (mock data is in USD)
        # USD to INR conversion rate: ~83, but for realistic prices, if price < 10, it's likely USD
        if benchmark_price > 0 and benchmark_price < 10:
            # Convert USD to INR (multiply by ~83)
            # But for realistic Indian market prices, use a more reasonable conversion
            # Tomato: 2.50 USD should be ~25-30 INR (not 208 INR)
            # Use a factor of 10-12 for more realistic prices
            benchmark_price = benchmark_price * 12  # Convert to realistic INR prices
            logger.info(f"Converted benchmark price from USD to INR: {benchmark_price}")
        
        if benchmark_price <= 0:
            # Fallback: use average of farmer and buyer prices
            benchmark_price = (listing.farmer_threshold_price + buyer_max_price) / 2
            logger.warning(f"Using fallback benchmark price: {benchmark_price}")
    except Exception as e:
        logger.error(f"Error fetching benchmark price: {e}")
        # Fallback: use average of farmer and buyer prices
        benchmark_price = (listing.farmer_threshold_price + buyer_max_price) / 2
        logger.warning(f"Using fallback benchmark price after error: {benchmark_price}")
    
    # Generate price suggestion
    price_suggestion = generate_price_suggestion(
        farmer_threshold_price=listing.farmer_threshold_price,
        buyer_preferred_price=buyer_max_price,
        benchmark_price=benchmark_price
    )
    
    # Create negotiation record with fair price range info
    negotiation = Negotiation(
        listing_id=str(listing_id),
        buyer_id=str(buyer_id),
        ai_suggested_price=price_suggestion.suggested_price,
        explanation=price_suggestion.explanation,
        decision=None,
        benchmark_price=benchmark_price,
        buyer_offer=buyer_max_price,
        farmer_min_price=listing.farmer_threshold_price,
        fair_lower=price_suggestion.fair_lower,
        fair_upper=price_suggestion.fair_upper
    )
    
    created_negotiation = storage.create_negotiation(negotiation)
    
    # Log for debugging
    logger.info(f"Created negotiation {created_negotiation.id} for listing {listing_id} and buyer {buyer_id}")
    logger.info(f"Suggested price: {created_negotiation.ai_suggested_price}, Has fair match: {price_suggestion.has_fair_match}")
    
    return created_negotiation


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        buyers_count = len(storage.get_all_buyers())
        requirements_count = len(storage.get_buyer_requirements())
        return {
            "status": "healthy",
            "buyers_count": buyers_count,
            "requirements_count": requirements_count
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }

