# Rate Limit Analysis and Solutions

## Problem Analysis

### API Calls Per Query
Each user query triggers **3 API calls minimum**:
1. **Reasoner Node** - Analyzes intent (1 API call)
2. **Agent Node** (Scheme/Disease/Price) - Processes query (1 API call)  
3. **Coordinator Node** - Synthesizes response (1 API call)

### Example from Terminal:
- Query 1: "govt scheme for kerala" → 3 API calls
- Query 2: "35" → 3 API calls (1 retry due to 429)

**Total: 6 API calls for 2 queries**

### Groq API Limits
- **200,000 tokens per day** (TPD limit)
- **429 errors** occur when limit is exceeded
- System auto-retries (good), but no exponential backoff

## Root Causes

1. **No Response Caching** - Same queries make repeated API calls
2. **RAG Agent Reloads** - Schemes loaded from disk every time (line 122)
3. **No Client-Side Rate Limiting** - No throttling between requests
4. **No Exponential Backoff** - Retries happen immediately
5. **Multiple Sequential Calls** - All calls happen in sequence

## Solutions Needed

1. ✅ Add response caching for repeated queries
2. ✅ Cache RAG agent initialization (don't reload schemes every time)
3. ✅ Add rate limiting/throttling between API calls
4. ✅ Add exponential backoff for retries
5. ✅ Optimize to reduce unnecessary API calls






