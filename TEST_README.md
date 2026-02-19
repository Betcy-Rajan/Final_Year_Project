# Government Scheme Agent - Unit Tests

This document describes the unit tests for the Government Scheme Agent module.

## Overview

The test suite (`test_scheme_agent.py`) provides comprehensive coverage for:

1. **Helper Functions**: Text truncation utilities
2. **SchemeAgentNode**: Core agent logic including state extraction, subcategory mapping, and scheme processing
3. **Tools**: `get_subcategories_tool` and `scheme_tool`
4. **RAG Agent Components**: Query parsing, eligibility checking, and vector search (if available)
5. **Edge Cases**: Error handling and boundary conditions

## Test Structure

### TestHelperFunctions
Tests for utility functions:
- `_truncate_text()`: Text truncation with length limits
- `_truncate_list()`: List truncation with item limits

### TestSchemeAgentNode
Tests for the main SchemeAgentNode class:
- State extraction from user input
- Subcategory loading and caching
- Number-to-subcategory mapping (with different scopes: all, state_only, central_only)
- Process method with various input scenarios
- Eligibility question generation

### TestSubcategoriesTool
Tests for the `get_subcategories_tool`:
- State-specific subcategory retrieval
- Central scheme subcategory retrieval
- Combined State + Central subcategory lists
- Error handling for missing files

### TestSchemeTool
Tests for the `scheme_tool`:
- Filtering by state and subcategory
- Scheme scope filtering (state_only, central_only, all)
- Result limiting to top 10 schemes
- Partial subcategory matching

### TestRAGAgent (if available)
Tests for RAG agent components:
- UserProfile initialization
- QueryParser for extracting user information
- SchemeDataNormalizer for data preprocessing
- Eligibility hints extraction

### TestEdgeCases
Tests for error handling:
- Empty input handling
- Invalid state handling
- Age mention exclusion from number detection

## Running the Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements.txt
```

### Run All Tests

Using pytest directly:
```bash
pytest test_scheme_agent.py -v
```

Using the test runner script:
```bash
python run_tests.py
```

### Run Specific Test Classes

```bash
# Run only helper function tests
pytest test_scheme_agent.py::TestHelperFunctions -v

# Run only scheme agent node tests
pytest test_scheme_agent.py::TestSchemeAgentNode -v

# Run only tool tests
pytest test_scheme_agent.py::TestSubcategoriesTool -v
pytest test_scheme_agent.py::TestSchemeTool -v
```

### Run with Coverage

```bash
pytest test_scheme_agent.py --cov=agents --cov=scheme_rag_agent --cov-report=html
```

This will generate an HTML coverage report in `htmlcov/index.html`.

## Test Coverage

The test suite covers:

- ✅ State extraction (various formats and case sensitivity)
- ✅ Subcategory extraction and matching
- ✅ Number-to-subcategory mapping with different scopes
- ✅ Scheme filtering by state, subcategory, and scope
- ✅ Result limiting and truncation
- ✅ Error handling and edge cases
- ✅ RAG agent components (if available)
- ✅ Eligibility question generation

## Mocking Strategy

The tests use extensive mocking to:
- Avoid dependency on actual API calls (LLM)
- Avoid dependency on actual data files
- Test logic in isolation
- Run tests quickly without external dependencies

Key mocks:
- `AgriMitraLLM.chat()`: Mocked to return predictable JSON responses
- File I/O: Mocked using `unittest.mock.mock_open`
- External tools: Mocked using `unittest.mock.patch`

## Example Test Output

```
test_scheme_agent.py::TestHelperFunctions::test_truncate_text_short PASSED
test_scheme_agent.py::TestHelperFunctions::test_truncate_text_long PASSED
test_scheme_agent.py::TestSchemeAgentNode::test_extract_state_from_input_goa PASSED
test_scheme_agent.py::TestSchemeAgentNode::test_map_number_to_subcategory_all_scope PASSED
...
```

## Notes

- Some tests require the RAG agent to be available. These are marked with `@pytest.mark.skipif(not RAG_AVAILABLE, ...)` and will be skipped if the RAG agent is not installed.
- Tests use mocked data to avoid dependencies on actual scheme files, but the structure matches the real data format.
- The test suite is designed to run quickly and provide fast feedback during development.

## Contributing

When adding new features to the Scheme Agent:
1. Add corresponding unit tests
2. Ensure all tests pass
3. Maintain or improve test coverage
4. Update this README if adding new test categories






