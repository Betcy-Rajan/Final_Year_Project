from buyer_connect_models import ListingStatus, MatchStatus, Negotiation, BuyerMatch


def test_storage_create_and_get_listing(mock_storage, sample_farmer_listing):
    created = mock_storage.create_listing(sample_farmer_listing)
    fetched = mock_storage.get_listing(created.id)
    assert fetched.id == created.id
    assert fetched.crop == "tomato"


def test_storage_buyer_requirement_crud(mock_storage, sample_buyer_requirement):
    created = mock_storage.create_buyer_requirement(sample_buyer_requirement)
    fetched = mock_storage.get_buyer_requirements(sample_buyer_requirement.buyer_id)[0]
    assert fetched.id == created.id
    assert fetched.crop == "tomato"


def test_storage_match_update(mock_storage):
    match = mock_storage.create_match(
        BuyerMatch(
            id=None,
            listing_id="1",
            buyer_id=1,
            buyer_preferred_price=32.0,
            benchmark_price=31.0,
            suggested_price=31.5,
            match_status=MatchStatus.OPEN,
        )
    )
    updated = mock_storage.update_match_status(match.id, MatchStatus.ACCEPTED)
    assert updated.match_status == MatchStatus.ACCEPTED


def test_storage_negotiation_flow(mock_storage):
    negotiation = Negotiation(
        listing_id="1",
        buyer_id="1",
        ai_suggested_price=31.0,
        explanation="test",
        benchmark_price=30.0,
        buyer_offer=32.0,
        farmer_min_price=29.0,
        fair_lower=29.0,
        fair_upper=32.0,
    )
    created = mock_storage.create_negotiation(negotiation)
    fetched = mock_storage.get_negotiation(created.id)
    assert fetched.ai_suggested_price == 31.0
    mock_storage.update_negotiation_decision(created.id, "accept")
    assert mock_storage.get_negotiation(created.id).decision == "accept"

