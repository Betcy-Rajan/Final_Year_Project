
import logging
import json
from typing import Dict, Any, Optional

from agent_system.price_agent import PriceAgentNode

logger = logging.getLogger(__name__)

class BuyerConnectAgentNode:
    """Buyer Connect Agent - Assists farmers in finding buyers and negotiating fair prices"""
    
    def __init__(self):
        # Import here to avoid circular dependencies
        try:
            from buyer_connect_storage import storage
            from buyer_connect_logic import find_matching_buyers, generate_price_suggestion
            from buyer_connect_models import FarmerListing, ListingStatus
            
            self.storage = storage
            self.find_matching_buyers = find_matching_buyers
            self.generate_price_suggestion = generate_price_suggestion
            self.FarmerListing = FarmerListing
            self.ListingStatus = ListingStatus
        except ImportError as e:
            logger.error(f"Failed to import buyer connect modules: {e}")
            self.storage = None
            
        self.price_agent = PriceAgentNode()
    
    def process(self, user_input: str, crop: Optional[str] = None, 
                quantity: Optional[float] = None, 
                farmer_threshold_price: Optional[float] = None,
                farmer_id: int = 1) -> Dict[str, Any]:
        """
        Process buyer connect request.
        
        This agent:
        1. Creates a farmer listing (if not exists)
        2. Finds matching buyers
        3. Fetches benchmark price from PriceAgent
        4. Runs negotiation engine for top matches
        5. Returns structured output with buyer matches and price suggestions
        """
        logger.info(f"BuyerConnectAgent processing: crop={crop}, quantity={quantity}, threshold_price={farmer_threshold_price}")
        
        if not self.storage:
             return {
                "error": "Buyer connect modules not available",
                "agent": "buyer_connect_agent"
            }

        try:
            # If crop, quantity, and price are provided, create/use listing
            listing = None
            if crop and quantity is not None and farmer_threshold_price is not None:
                # Create a listing
                listing = self.FarmerListing(
                    farmer_id=farmer_id,
                    crop=crop,
                    quantity=quantity,
                    unit="kg",
                    farmer_threshold_price=farmer_threshold_price,
                    status=self.ListingStatus.OPEN
                )
                listing = self.storage.create_listing(listing)
                logger.info(f"Created listing {listing.id} for buyer connect")
            
            # Get all buyers from old collection
            all_buyers = self.storage.get_all_buyers()
            
            # Find matching buyers from old buyers collection
            matched_buyers = []
            if listing:
                matched_buyers = self.find_matching_buyers(listing, all_buyers)
            
            # Also check buyer_requirements collection for matches
            if listing:
                try:
                    all_requirements = self.storage.get_buyer_requirements()
                    for requirement in all_requirements:
                        # Check if crop matches
                        if requirement.crop.lower() != listing.crop.lower():
                            continue
                        
                        # Flexible quantity matching - more lenient for smaller quantities
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
                        
                        # Flexible price matching
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
                        
                        # Get buyer info if available
                        buyer = None
                        try:
                            buyer_id_int = int(requirement.buyer_id) if isinstance(requirement.buyer_id, str) and requirement.buyer_id.isdigit() else requirement.buyer_id
                            buyer = self.storage.get_buyer(buyer_id_int)
                        except:
                            buyer = self.storage.get_buyer(requirement.buyer_id)
                        
                        buyer_name = buyer.name if buyer else f"Buyer {requirement.buyer_id}"
                        buyer_location = buyer.location if buyer else requirement.location
                        
                        # Convert buyer_id to int if possible
                        try:
                            buyer_id_for_match = int(requirement.buyer_id) if isinstance(requirement.buyer_id, str) and requirement.buyer_id.isdigit() else requirement.buyer_id
                        except:
                            buyer_id_for_match = requirement.buyer_id
                        
                        from buyer_connect_models import MatchedBuyer
                        matched_buyer = MatchedBuyer(
                            buyer_id=buyer_id_for_match,
                            buyer_name=buyer_name,
                            location=buyer_location,
                            preferred_price=requirement.max_price,
                            demand_range={
                                "min_qty": requirement.required_quantity * 0.8,
                                "max_qty": requirement.required_quantity * 1.2
                            },
                            match_score=match_score
                        )
                        matched_buyers.append(matched_buyer)
                    
                    # Sort by match score
                    matched_buyers.sort(key=lambda x: x.match_score or 0, reverse=True)
                except Exception as e:
                    logger.warning(f"Error checking buyer_requirements: {e}")
            
            # Get benchmark price from PriceAgent
            benchmark_price = None
            if crop:
                try:
                    price_result = self.price_agent.process(crop)
                    price_info = price_result.get("price_info", {})
                    if "error" not in price_info:
                        benchmark_price = price_info.get("current_price", 0)
                except Exception as e:
                    logger.warning(f"Failed to get benchmark price: {e}")
            
            # Generate price suggestions for top 3 matches
            price_suggestions = []
            for matched_buyer in matched_buyers[:3]:  # Top 3 matches
                buyer = self.storage.get_buyer(matched_buyer.buyer_id)
                if buyer and listing:
                    # Find buyer's crop interest
                    crop_interest = None
                    for interest in buyer.interested_crops:
                        if interest.crop.lower() == listing.crop.lower():
                            crop_interest = interest
                            break
                    
                    if crop_interest and benchmark_price:
                        suggestion = self.generate_price_suggestion(
                            farmer_threshold_price=listing.farmer_threshold_price,
                            buyer_preferred_price=crop_interest.preferred_price,
                            benchmark_price=benchmark_price
                        )
                        price_suggestions.append({
                            "buyer_id": matched_buyer.buyer_id,
                            "buyer_name": matched_buyer.buyer_name,
                            "suggestion": suggestion.dict()
                        })
            
            result = {
                "listing_id": listing.id if listing else None,
                "matched_buyers": [mb.dict() for mb in matched_buyers],
                "benchmark_price": benchmark_price,
                "price_suggestions": price_suggestions,
                "agent": "buyer_connect_agent"
            }
            
            logger.info(f"BuyerConnectAgent output: {len(matched_buyers)} buyers matched")
            return result
            
        except Exception as e:
            logger.error(f"BuyerConnectAgent error: {e}")
            return {
                "error": str(e),
                "agent": "buyer_connect_agent"
            }
