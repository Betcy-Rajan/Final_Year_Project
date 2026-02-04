# Tests for Buyer Connect & Fair Negotiation

## How to run
```bash
# from repo root
pytest --maxfail=1 --disable-warnings -q --json-report --json-report-file=test_results.json | tee test_logs.txt

# with coverage
pytest --maxfail=1 --disable-warnings -q --cov=buyer_connect_models --cov=buyer_connect_logic --cov=buyer_connect_storage --cov=agents --cov-report=term > test_logs.txt
coverage report > coverage_report.txt
```

## What is validated
- **Models**: Pydantic models accept string/int IDs, required fields, fair range fields.
- **Matching logic**: Crop match, flexible quantity tolerance, price proximity, ranking.
- **Price negotiation**: Fair range computation, no-fair-match path, explanation text.
- **Storage**: In-memory CRUD for listings, buyers, requirements, matches, negotiations.
- **BuyerConnectAgent**: Creates listing, finds matches, produces suggestions with mocked price agent.
- **Negotiation flow**: Accept/reject decisions update negotiation state.

## Reliability
- External calls (PriceAgent, Firestore) are mocked for determinism.
- Tests are isolated via pytest fixtures.
- One assertion goal per test keeps intent clear and failures easy to trace.
