from agents import BuyerConnectAgentNode
from buyer_connect_models import ListingStatus


def test_agent_creates_listing_and_matches(mock_storage, sample_farmer_listing, sample_buyer, mock_price_agent):
    # Prepare storage with a buyer
    mock_storage.create_buyer(sample_buyer)

    agent = BuyerConnectAgentNode()
    # Inject mocks
    agent.storage = mock_storage
    agent.price_agent = mock_price_agent

    result = agent.process(
        user_input="I want to sell 200 kg tomato at 30 rupees",
        crop="tomato",
        quantity=sample_farmer_listing.quantity,
        farmer_threshold_price=sample_farmer_listing.farmer_threshold_price,
        farmer_id=1,
    )

    assert result["listing_id"] is not None
    assert len(result["matched_buyers"]) >= 1
    # Listing should remain open or negotiating based on suggestion; ensure created
    created_listing = mock_storage.get_listing(result["listing_id"])
    assert created_listing is not None
    assert created_listing.status in (ListingStatus.OPEN, ListingStatus.NEGOTIATING)
