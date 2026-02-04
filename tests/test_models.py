import pytest
from buyer_connect_models import (
    FarmerListing,
    Buyer,
    BuyerRequirement,
    Negotiation,
    CropInterest,
    ListingStatus,
    MatchStatus,
)


def test_farmer_listing_accepts_string_id():
    listing = FarmerListing(
        id="abc123",
        farmer_id=1,
        crop="tomato",
        quantity=100,
        unit="kg",
        farmer_threshold_price=25.0,
        status=ListingStatus.OPEN,
    )
    assert listing.id == "abc123"
    assert listing.status == ListingStatus.OPEN


def test_buyer_model_with_interests():
    buyer = Buyer(
        id=1,
        name="Test Buyer",
        phone="000",
        location="City",
        verified=True,
        interested_crops=[CropInterest(crop="tomato", min_qty=50, max_qty=300, preferred_price=32.0)],
    )
    assert buyer.verified is True
    assert buyer.interested_crops[0].crop == "tomato"


def test_buyer_requirement_allows_int_buyer_id():
    req = BuyerRequirement(
        buyer_id=1,
        crop="tomato",
        required_quantity=200,
        max_price=33.0,
        location="Pune",
        valid_till="2026-12-31",
    )
    assert req.buyer_id == 1
    assert req.required_quantity == 200


def test_negotiation_accepts_string_and_range():
    negotiation = Negotiation(
        listing_id="abc",
        buyer_id="1",
        ai_suggested_price=31.0,
        explanation="Test explanation",
        benchmark_price=30.0,
        buyer_offer=32.0,
        farmer_min_price=29.0,
        fair_lower=29.0,
        fair_upper=32.0,
    )
    assert negotiation.listing_id == "abc"
    assert negotiation.fair_lower == 29.0
    assert negotiation.fair_upper == 32.0

