from buyer_connect_models import Negotiation, FarmerListing


def test_accept_decision_closes_listing(mock_storage):
    # Create listing and negotiation
    listing = mock_storage.create_listing(
        FarmerListing(
            farmer_id=1,
            crop="tomato",
            quantity=200,
            unit="kg",
            farmer_threshold_price=30.0,
        )
    )

    negotiation = Negotiation(
        listing_id=str(listing.id),
        buyer_id="1",
        ai_suggested_price=31.0,
        explanation="fair price",
        benchmark_price=30.0,
        buyer_offer=32.0,
        farmer_min_price=29.0,
        fair_lower=29.0,
        fair_upper=32.0,
    )
    created = mock_storage.create_negotiation(negotiation)
    mock_storage.update_negotiation_decision(created.id, "accept")
    assert mock_storage.get_negotiation(created.id).decision == "accept"


def test_reject_decision(mock_storage):
    negotiation = Negotiation(
        listing_id="1",
        buyer_id="1",
        ai_suggested_price=31.0,
        explanation="fair price",
        benchmark_price=30.0,
        buyer_offer=32.0,
        farmer_min_price=29.0,
        fair_lower=29.0,
        fair_upper=32.0,
    )
    created = mock_storage.create_negotiation(negotiation)
    mock_storage.update_negotiation_decision(created.id, "reject")
    assert mock_storage.get_negotiation(created.id).decision == "reject"
