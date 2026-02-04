from buyer_connect_logic import find_matching_buyers
from buyer_connect_models import Buyer, CropInterest


def test_matching_prefers_better_price_and_qty(sample_farmer_listing):
    # Buyer 1: Price 34 (further from farmer's 30), qty range 100-400 (center=250, farmer has 200)
    buyer_good = Buyer(
        id=1,
        name="Good Buyer",
        phone="1",
        location="City",
        interested_crops=[CropInterest(crop="tomato", min_qty=100, max_qty=400, preferred_price=34.0)],
    )
    # Buyer 2: Price 31 (closer to farmer's 30), qty range 50-600 (wider range, includes 200)
    buyer_ok = Buyer(
        id=2,
        name="OK Buyer",
        phone="2",
        location="City",
        interested_crops=[CropInterest(crop="tomato", min_qty=50, max_qty=600, preferred_price=31.0)],
    )

    matched = find_matching_buyers(sample_farmer_listing, [buyer_ok, buyer_good])
    assert len(matched) == 2
    # Buyer 2 should rank higher because price (31) is closer to farmer threshold (30)
    # than buyer 1's price (34)
    assert matched[0].buyer_id == 2
    assert matched[0].match_score >= matched[1].match_score


def test_matching_accepts_smaller_qty_with_flex(sample_farmer_listing):
    # Farmer has 200kg, buyer wants 500-1000kg, should still match via flexible rule
    buyer = Buyer(
        id=3,
        name="Large Buyer",
        phone="3",
        location="City",
        interested_crops=[CropInterest(crop="tomato", min_qty=500, max_qty=1000, preferred_price=35.0)],
    )
    matched = find_matching_buyers(sample_farmer_listing, [buyer])
    assert len(matched) == 1
    assert matched[0].buyer_id == 3
