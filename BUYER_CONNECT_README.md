# Buyer Connect & Fair Negotiation Module

## Overview

The Buyer Connect & Fair Negotiation module assists farmers in finding buyers and negotiating fair prices for their crops. This module is designed to be **explainable, deterministic, and farmer-controlled** - no autonomous deal finalization without explicit farmer confirmation.

## Features

- **Buyer Discovery**: Automatically finds buyers matching farmer's crop, quantity, and price requirements
- **Fair Price Negotiation**: Rule-based price suggestion engine that ensures fair deals
- **Transparency**: All price suggestions include clear explanations
- **Farmer Control**: No deals are finalized without explicit farmer acceptance

## Architecture

### Components

1. **Data Models** (`buyer_connect_models.py`)
   - `Buyer`: Buyer information with crop interests
   - `FarmerListing`: Farmer's crop listing
   - `BuyerMatch`: Match between listing and buyer
   - `PriceSuggestion`: Result from negotiation engine

2. **Business Logic** (`buyer_connect_logic.py`)
   - `find_matching_buyers()`: Finds and ranks matching buyers
   - `generate_price_suggestion()`: Rule-based fair price calculation

3. **Storage** (`buyer_connect_storage.py`)
   - In-memory storage (demo-ready)
   - Can be replaced with SQLAlchemy + database in production

4. **API Endpoints** (`buyer_connect_api.py`)
   - FastAPI REST API for buyer connect operations

5. **LangGraph Integration** (`agents.py`, `workflow.py`)
   - `BuyerConnectAgentNode`: Agent that processes sell/find buyer requests
   - Integrated into main workflow

## Fair Negotiation Rules

The price suggestion engine uses deterministic, rule-based logic:

- **α = 0.10** (lower bound: 10% below benchmark)
- **β = 0.15** (upper bound: 15% above benchmark)

**Algorithm:**
1. `fair_lower = max(farmer_threshold_price, benchmark_price * (1 - α))`
2. `fair_upper = min(buyer_preferred_price, benchmark_price * (1 + β))`
3. If `fair_lower > fair_upper`: No fair match exists
4. Else: `suggested_price = average(fair_lower, fair_upper)`

## API Endpoints

### Create Listing
```bash
POST /listings
{
  "farmer_id": 1,
  "crop": "tomato",
  "quantity": 500,
  "unit": "kg",
  "farmer_threshold_price": 30.0
}
```

### Get Matched Buyers
```bash
GET /buyers/match/{listing_id}
```

### Negotiate Price
```bash
POST /negotiate/{listing_id}/{buyer_id}
```

### Accept Match
```bash
POST /negotiate/{match_id}/accept
```

### Reject Match
```bash
POST /negotiate/{match_id}/reject
```

## Usage in LangGraph Workflow

The BuyerConnectAgent is automatically triggered when the Reasoner detects:
- Intent: "sell" or "find buyer"
- Keywords: "sell", "find buyer", "looking for buyer", etc.

**Example Query:**
```
"I want to sell my tomato crop, 500 kg, minimum price 30 per kg"
```

**Workflow:**
1. Reasoner detects "sell" intent
2. Routes to BuyerConnectAgent
3. Agent creates listing, finds buyers, generates price suggestions
4. Coordinator synthesizes output for farmer

## Example Output

```json
{
  "buyer": "GreenGrow Traders",
  "benchmark_price": 29,
  "buyer_offer": 32,
  "farmer_min_price": 30,
  "suggested_price": 31,
  "explanation": "Suggested price is 31.00 per unit. This is based on current mandi trends (benchmark: 29.00), your minimum acceptable price (30.00), and the buyer's offer (32.00). The fair price range is between 30.00 and 32.00."
}
```

## Safety & Explainability

✅ **No Auto-Finalization**: All deals require explicit farmer acceptance via `/negotiate/{match_id}/accept`

✅ **Deterministic Logic**: All price calculations use rule-based algorithms (no black-box LLM negotiation)

✅ **Clear Explanations**: Every price suggestion includes a farmer-friendly explanation

✅ **Transparent Matching**: Buyers are ranked with clear match scores and criteria

## Running the Demo

```bash
python buyer_connect_demo.py
```

## Running the API

```bash
uvicorn buyer_connect_api:app --reload
```

Then visit: `http://localhost:8000/docs` for interactive API documentation

## Integration with Existing System

The module integrates seamlessly with:
- **PriceAgent**: Fetches benchmark prices for negotiation
- **Coordinator**: Synthesizes buyer connect results with other agent outputs
- **Reasoner**: Detects sell/find buyer intent automatically

## Future Enhancements

- Location-based matching (same district/city)
- Buyer verification system
- Historical transaction data
- Multi-crop negotiations
- Automated buyer notifications

