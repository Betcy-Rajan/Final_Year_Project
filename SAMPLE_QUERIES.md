# Sample Queries for RAG Agent Testing

Here are sample queries you can use to test the Government Scheme RAG Agent:

## Basic Queries

### 1. State + Subcategory
```
I am from Goa and need financial assistance schemes
```

### 2. State + Subcategory (Alternative)
```
Show me animal husbandry schemes in Himachal Pradesh
```

### 3. State + Crop
```
I'm a farmer from Rajasthan with 2 acres of land, need schemes for wheat cultivation
```

### 4. State + Activity (Semantic Search)
```
I need schemes for dairy farming in Maharashtra
```

### 5. State + Age + Target Group
```
I'm from Odisha, 35 years old, SC category, need startup schemes
```

### 6. Central Schemes
```
Central schemes for organic farming
```

### 7. State + Land Size + Crop
```
I'm a small farmer from Gujarat with 3 acres, need schemes for rice
```

### 8. State + Multiple Criteria
```
I'm from Kerala, 28 years old, BPL category, need fishing schemes
```

### 9. Entrepreneurship Schemes
```
I am from Sikkim and want entrepreneurship development schemes
```

### 10. State + Subcategory with Scope
```
Show me state schemes for financial assistance in Rajasthan
```

## Advanced Queries (Testing Semantic Search)

### 11. Partial Match
```
I need help with livestock in Himachal Pradesh
```
(Should match "Animal husbandry" schemes)

### 12. Synonym Matching
```
Show me crop insurance schemes in Maharashtra
```
(Should match schemes with "Insurance" subcategory)

### 13. Activity-based
```
I want to start a poultry farm in Goa
```
(Should match "Animal husbandry" and "Entrepreneurship" schemes)

### 14. Multiple Keywords
```
I'm a marginal farmer from Assam, need schemes for seeds and fertilizers
```
(Should match "Agricultural Inputs" schemes)

## Testing Eligibility Assessment

### 15. With Age
```
I'm 45 years old from Himachal Pradesh, need animal husbandry schemes
```

### 16. With Land Size
```
I have 5 acres of land in Rajasthan, need financial assistance
```

### 17. With Income
```
My family income is 1.5 lakhs, I'm from Goa, need startup schemes
```

### 18. With Target Group
```
I'm a woman farmer from Kerala, need dairy schemes
```

## Testing Integration with Existing Flow

### 19. State Only (Should show subcategories)
```
I am from Goa
```

### 20. State + Number Selection
```
I am from Rajasthan and need scheme 3
```

### 21. State + Subcategory + Scope
```
I need both central and state schemes for financial assistance in Gujarat
```

## Usage

Run these queries through the CLI:
```bash
python cli.py
```

Then paste any of the queries above when prompted.




