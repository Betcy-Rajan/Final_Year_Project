import pytest

from buyer_connect_models import (
    FarmerListing,
    Buyer,
    BuyerRequirement,
    CropInterest,
    Negotiation,
    BuyerMatch,
    MatchStatus,
    ListingStatus,
)


@pytest.fixture
def sample_farmer_listing():
    return FarmerListing(
        farmer_id=1,
        crop="tomato",
        quantity=200,
        unit="kg",
        farmer_threshold_price=30.0,
    )


@pytest.fixture
def sample_buyer():
    return Buyer(
        id=1,
        name="GreenGrow Traders",
        phone="+91-9999999999",
        location="Pune",
        interested_crops=[
            CropInterest(crop="tomato", min_qty=100, max_qty=500, preferred_price=35.0)
        ],
        verified=True,
    )


@pytest.fixture
def sample_buyer_requirement():
    return BuyerRequirement(
        buyer_id=1,
        crop="tomato",
        required_quantity=250,
        max_price=34.0,
        location="Pune",
        valid_till="2026-12-31",
    )


@pytest.fixture
def mock_price_agent():
    class MockPriceAgent:
        def process(self, crop: str):
            # Always return a deterministic benchmark price
            return {"price_info": {"current_price": 32.0}}

    return MockPriceAgent()


@pytest.fixture
def mock_storage():
    class MockStorage:
        def __init__(self):
            self.buyers = {}
            self.listings = {}
            self.matches = {}
            self.buyer_requirements = {}
            self.negotiations = {}
            self._id = 0

        def _next_id(self):
            self._id += 1
            return self._id

        # Buyer methods
        def get_all_buyers(self):
            return list(self.buyers.values())

        def get_buyer(self, buyer_id):
            return self.buyers.get(int(buyer_id))

        def create_buyer(self, buyer: Buyer):
            if buyer.id is None:
                buyer.id = self._next_id()
            self.buyers[int(buyer.id)] = buyer
            return buyer

        # Listing methods
        def create_listing(self, listing: FarmerListing):
            if listing.id is None:
                listing.id = str(self._next_id())
            self.listings[str(listing.id)] = listing
            return listing

        def get_listing(self, listing_id):
            return self.listings.get(str(listing_id))

        def update_listing_status(self, listing_id, status: ListingStatus):
            listing = self.get_listing(listing_id)
            if listing:
                listing.status = status
            return listing

        # Buyer requirements
        def create_buyer_requirement(self, requirement: BuyerRequirement):
            if not requirement.id:
                requirement.id = str(self._next_id())
            self.buyer_requirements[str(requirement.id)] = requirement
            return requirement

        def get_buyer_requirements(self, buyer_id=None):
            if buyer_id is None:
                return list(self.buyer_requirements.values())
            return [
                req
                for req in self.buyer_requirements.values()
                if str(req.buyer_id) == str(buyer_id)
            ]

        # Matches
        def create_match(self, match: BuyerMatch):
            if match.id is None:
                match.id = self._next_id()
            self.matches[int(match.id)] = match
            return match

        def get_match(self, match_id):
            return self.matches.get(int(match_id))

        def update_match_status(self, match_id, status: MatchStatus):
            match = self.get_match(match_id)
            if match:
                match.match_status = status
            return match

        def get_matches_for_listing(self, listing_id):
            return [
                m for m in self.matches.values() if str(m.listing_id) == str(listing_id)
            ]

        # Negotiations
        def create_negotiation(self, negotiation: Negotiation):
            if negotiation.id is None:
                negotiation.id = str(self._next_id())
            self.negotiations[str(negotiation.id)] = negotiation
            return negotiation

        def get_negotiation(self, negotiation_id: str):
            return self.negotiations.get(str(negotiation_id))

        def update_negotiation_decision(self, negotiation_id: str, decision: str):
            negotiation = self.get_negotiation(negotiation_id)
            if negotiation:
                negotiation.decision = decision
            return negotiation

        def get_negotiations_for_listing(self, listing_id: str):
            return [
                n
                for n in self.negotiations.values()
                if str(n.listing_id) == str(listing_id)
            ]

        def get_negotiations_for_buyer(self, buyer_id: str):
            return [
                n
                for n in self.negotiations.values()
                if str(n.buyer_id) == str(buyer_id)
            ]

    return MockStorage()
