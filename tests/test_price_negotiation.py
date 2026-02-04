from buyer_connect_logic import generate_price_suggestion


def test_fair_price_within_range():
    suggestion = generate_price_suggestion(
        farmer_threshold_price=30.0,
        buyer_preferred_price=34.0,
        benchmark_price=32.0,
    )
    assert suggestion.has_fair_match is True
    assert suggestion.fair_lower <= suggestion.suggested_price <= suggestion.fair_upper
    assert "benchmark" in suggestion.explanation.lower()


def test_no_fair_match_returns_none_price():
    suggestion = generate_price_suggestion(
        farmer_threshold_price=40.0,
        buyer_preferred_price=30.0,
        benchmark_price=32.0,
    )
    assert suggestion.has_fair_match is False
    assert suggestion.suggested_price is None
    assert "no fair price match" in suggestion.explanation.lower()
