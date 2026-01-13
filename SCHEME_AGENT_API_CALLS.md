# Scheme Agent API Call Analysis

## Problem Identified

The Scheme Agent is making **2 API calls** per query, which contributes to rate limit issues:

### API Call #1: Query Parsing (Line 1000)
```python
response = self.llm.chat(SCHEME_AGENT_SYSTEM_PROMPT, context)
```
- Purpose: Extract state, subcategory, category from user query
- **Always executed** when processing a scheme query

### API Call #2: Eligibility Questions Generation (Line 1284)
```python
eligibility_questions = self.generate_eligibility_questions(...)
response = self.llm.chat(SCHEME_ELIGIBILITY_PROMPT, context)
```
- Purpose: Generate 3-5 eligibility questions based on scheme criteria
- **Always executed** when schemes are found (both RAG and traditional paths)

## Total API Calls Per Scheme Query

1. **Reasoner Node**: 1 API call
2. **Scheme Agent**: 2 API calls (parsing + eligibility questions)
3. **Coordinator Node**: 1 API call

**Total: 4 API calls per scheme query**

## Why This Causes Rate Limits

- Each query = 4 API calls
- Multiple queries in quick succession = rapid token consumption
- Groq limit: 200,000 tokens per day
- No caching or optimization

## Solutions

1. **Make eligibility questions optional** - Only generate if user explicitly asks
2. **Cache eligibility questions** - Same schemes = same questions
3. **Skip eligibility questions when using RAG** - RAG already provides eligibility assessment
4. **Combine prompts** - Merge query parsing and eligibility generation into one call

