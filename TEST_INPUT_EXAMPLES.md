# Buyer Connect Test Input Examples

## Example 1: Tomato Crop (Good Match Scenario)

### Buyer Requirement (Post as Buyer)
```json
{
  "buyer_id": 1,
  "crop": "tomato",
  "required_quantity": 500,
  "max_price": 35,
  "location": "Pune",
  "valid_till": "2024-12-31"
}
```

### Farmer Listing (Post as Farmer)
**Natural Language Query:**
```
I want to sell 500 kg tomato, minimum price 30 rupees per kg
```

**OR Manual Form:**
```json
{
  "farmer_id": 1,
  "crop": "tomato",
  "quantity": 500,
  "unit": "kg",
  "farmer_threshold_price": 30.0
}
```

**Expected Result:** ✅ Should match! 
- Quantity: 500 kg matches buyer's requirement (500 kg)
- Price: Farmer wants ₹30/kg, buyer offers up to ₹35/kg - within 20% range
- Fair price suggestion: Around ₹31-32/kg (depending on market benchmark)

---

## Example 2: Potato Crop (Close Match Scenario)

### Buyer Requirement
```json
{
  "buyer_id": 1,
  "crop": "potato",
  "required_quantity": 1000,
  "max_price": 25,
  "location": "Mumbai",
  "valid_till": "2024-12-31"
}
```

### Farmer Listing
**Natural Language:**
```
I have 900 kg potato to sell, my minimum price is 22 rupees per kg
```

**OR Manual Form:**
```json
{
  "farmer_id": 1,
  "crop": "potato",
  "quantity": 900,
  "unit": "kg",
  "farmer_threshold_price": 22.0
}
```

**Expected Result:** ✅ Should match!
- Quantity: 900 kg is within 20% of buyer's 1000 kg requirement
- Price: ₹22/kg (farmer) vs ₹25/kg (buyer) - good match
- Fair price: Around ₹23-24/kg

---

## Example 3: Rice Crop (Edge Case - Tight Match)

### Buyer Requirement
```json
{
  "buyer_id": 1,
  "crop": "rice",
  "required_quantity": 2000,
  "max_price": 18,
  "location": "Delhi",
  "valid_till": "2024-12-31"
}
```

### Farmer Listing
**Natural Language:**
```
I want to sell 2100 kg rice, minimum price 16 rupees
```

**OR Manual Form:**
```json
{
  "farmer_id": 1,
  "crop": "rice",
  "quantity": 2100,
  "unit": "kg",
  "farmer_threshold_price": 16.0
}
```

**Expected Result:** ✅ Should match!
- Quantity: 2100 kg is within 20% of 2000 kg
- Price: ₹16/kg (farmer) vs ₹18/kg (buyer) - good range
- Fair price: Around ₹17/kg

---

## Example 4: Onion Crop (No Match - Price Too High)

### Buyer Requirement
```json
{
  "buyer_id": 1,
  "crop": "onion",
  "required_quantity": 800,
  "max_price": 30,
  "location": "Kolkata",
  "valid_till": "2024-12-31"
}
```

### Farmer Listing
**Natural Language:**
```
I want to sell 800 kg onion, minimum price 40 rupees per kg
```

**OR Manual Form:**
```json
{
  "farmer_id": 1,
  "crop": "onion",
  "quantity": 800,
  "unit": "kg",
  "farmer_threshold_price": 40.0
}
```

**Expected Result:** ❌ No fair match
- Quantity: ✅ Matches (800 kg)
- Price: ❌ Farmer wants ₹40/kg, buyer offers max ₹30/kg - more than 20% difference
- System will show: "No fair price match available" with explanation

---

## Example 5: Wheat Crop (Quantity Mismatch)

### Buyer Requirement
```json
{
  "buyer_id": 1,
  "crop": "wheat",
  "required_quantity": 5000,
  "max_price": 15,
  "location": "Punjab",
  "valid_till": "2024-12-31"
}
```

### Farmer Listing
**Natural Language:**
```
I have 200 kg wheat to sell, minimum price 12 rupees
```

**OR Manual Form:**
```json
{
  "farmer_id": 1,
  "crop": "wheat",
  "quantity": 200,
  "unit": "kg",
  "farmer_threshold_price": 12.0
}
```

**Expected Result:** ❌ No match
- Quantity: ❌ 200 kg is less than 20% of buyer's 5000 kg requirement
- Price: ✅ Good match (₹12 vs ₹15)
- System will not show this buyer in matches

---

## Step-by-Step Testing Guide

### As a Buyer:
1. Click "🤝 Buyer Connect" in header
2. Select "Buyer" role
3. Click "+ Add Requirement"
4. Fill in the form:
   - Crop: Select from dropdown (e.g., "tomato")
   - Required Quantity: Enter number (e.g., 500)
   - Maximum Price: Enter price per kg (e.g., 35)
   - Location: Enter city (e.g., "Pune")
   - Validity Period: Select a future date
5. Click "Save Requirement"

### As a Farmer:
1. Click "🤝 Buyer Connect" in header
2. Select "Farmer" role
3. Choose input method:
   
   **Option A: Natural Language**
   - Click "Natural Language" tab
   - Type: "I want to sell 500 kg tomato, minimum price 30 rupees per kg"
   - Click "Find Buyers"
   
   **Option B: Manual Form**
   - Click "Manual Form" tab
   - Fill in:
     - Crop: Select "tomato"
     - Quantity: Enter 500
     - Minimum Price: Enter 30
     - Location: (optional, auto-filled)
   - Click "Find Buyers"

4. View matched buyers
5. Click "🤝 Negotiate" on a buyer card
6. View fair price suggestion and explanation
7. Click "✅ Accept" to finalize

---

## Recommended Test Sequence

1. **Create Buyer Requirement** (Example 1 - Tomato)
2. **Create Farmer Listing** (Example 1 - Tomato)
3. **Verify Match** - Should see buyer in matched list
4. **Click Negotiate** - Should see fair price suggestion
5. **View Explanation** - Should see detailed breakdown
6. **Accept Offer** - Should finalize deal

---

## Notes

- **Price Range**: For best matches, keep farmer's minimum price within 20% of buyer's max price
- **Quantity Range**: For best matches, keep quantities within 20% of each other
- **Market Benchmark**: System fetches current market price from PriceAgent
- **Fair Price Calculation**: Uses rule-based algorithm (not LLM) with α=0.10 and β=0.15 bounds
