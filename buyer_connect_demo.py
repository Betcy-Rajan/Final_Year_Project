"""
Demo script for Buyer Connect & Fair Negotiation module
"""
import json
from buyer_connect_models import FarmerListing, CropInterest
from buyer_connect_storage import storage
from buyer_connect_logic import find_matching_buyers, generate_price_suggestion
from agents import PriceAgentNode

def demo_buyer_discovery():
    """Demo: Find matching buyers for a listing"""
    print("=" * 60)
    print("DEMO 1: Buyer Discovery")
    print("=" * 60)
    
    # Create a sample listing
    listing = FarmerListing(
        farmer_id=1,
        crop="tomato",
        quantity=500,
        unit="kg",
        farmer_threshold_price=30.0
    )
    
    listing = storage.create_listing(listing)
    print(f"\nCreated listing:")
    print(f"  Crop: {listing.crop}")
    print(f"  Quantity: {listing.quantity} {listing.unit}")
    print(f"  Minimum Price: {listing.farmer_threshold_price} per {listing.unit}")
    
    # Find matching buyers
    all_buyers = storage.get_all_buyers()
    matched = find_matching_buyers(listing, all_buyers)
    
    print(f"\nFound {len(matched)} matching buyers:")
    for i, buyer in enumerate(matched, 1):
        print(f"\n{i}. {buyer.buyer_name}")
        print(f"   Location: {buyer.location}")
        print(f"   Preferred Price: {buyer.preferred_price} per kg")
        print(f"   Demand Range: {buyer.demand_range['min_qty']} - {buyer.demand_range['max_qty']} kg")
        print(f"   Match Score: {buyer.match_score:.2f}")


def demo_price_negotiation():
    """Demo: Fair price negotiation"""
    print("\n" + "=" * 60)
    print("DEMO 2: Fair Price Negotiation")
    print("=" * 60)
    
    # Example scenario
    farmer_threshold = 30.0
    buyer_preferred = 32.0
    benchmark_price = 29.0
    
    print(f"\nScenario:")
    print(f"  Farmer's minimum price: {farmer_threshold} per kg")
    print(f"  Buyer's preferred price: {buyer_preferred} per kg")
    print(f"  Market benchmark price: {benchmark_price} per kg")
    
    # Generate price suggestion
    suggestion = generate_price_suggestion(
        farmer_threshold_price=farmer_threshold,
        buyer_preferred_price=buyer_preferred,
        benchmark_price=benchmark_price
    )
    
    print(f"\nPrice Suggestion Result:")
    print(f"  Has Fair Match: {suggestion.has_fair_match}")
    if suggestion.has_fair_match:
        print(f"  Suggested Price: {suggestion.suggested_price:.2f} per kg")
        print(f"  Fair Range: {suggestion.fair_lower:.2f} - {suggestion.fair_upper:.2f} per kg")
    print(f"  Explanation: {suggestion.explanation}")


def demo_no_fair_match():
    """Demo: When no fair match exists"""
    print("\n" + "=" * 60)
    print("DEMO 3: No Fair Match Scenario")
    print("=" * 60)
    
    # Scenario where farmer's threshold is too high
    farmer_threshold = 35.0
    buyer_preferred = 32.0
    benchmark_price = 29.0
    
    print(f"\nScenario:")
    print(f"  Farmer's minimum price: {farmer_threshold} per kg")
    print(f"  Buyer's preferred price: {buyer_preferred} per kg")
    print(f"  Market benchmark price: {benchmark_price} per kg")
    
    suggestion = generate_price_suggestion(
        farmer_threshold_price=farmer_threshold,
        buyer_preferred_price=buyer_preferred,
        benchmark_price=benchmark_price
    )
    
    print(f"\nPrice Suggestion Result:")
    print(f"  Has Fair Match: {suggestion.has_fair_match}")
    print(f"  Explanation: {suggestion.explanation}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Buyer Connect & Fair Negotiation Module - Demo")
    print("=" * 60)
    
    demo_buyer_discovery()
    demo_price_negotiation()
    demo_no_fair_match()
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)

