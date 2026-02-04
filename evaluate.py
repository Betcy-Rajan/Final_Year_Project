from workflow import AgriMitraWorkflow
import time
import json
from statistics import mean, median
from datetime import datetime
from buyer_connect_storage import storage
from buyer_connect_models import Buyer, CropInterest

# --------------------------------------------------
# Setup: Add more mock buyers for comprehensive testing
# --------------------------------------------------
def setup_mock_buyers():
    """Add additional mock buyers for testing buyer_connect agent"""
    # Get current buyer count
    existing_buyers = storage.get_all_buyers()
    next_id = max([b.id for b in existing_buyers]) + 1 if existing_buyers else 4
    
    # Add more buyers for various crops
    additional_buyers = [
        Buyer(
            id=next_id,
            name="CropMaster Traders",
            phone="+91-9876543213",
            location="Bangalore",
            interested_crops=[
                CropInterest(crop="corn", min_qty=300, max_qty=3000, preferred_price=18),
                CropInterest(crop="wheat", min_qty=400, max_qty=4000, preferred_price=11),
            ],
            verified=True
        ),
        Buyer(
            id=next_id + 1,
            name="AgriVenture Ltd",
            phone="+91-9876543214",
            location="Hyderabad",
            interested_crops=[
                CropInterest(crop="rice", min_qty=600, max_qty=6000, preferred_price=14),
                CropInterest(crop="potato", min_qty=250, max_qty=2500, preferred_price=19),
            ],
            verified=True
        ),
        Buyer(
            id=next_id + 2,
            name="FarmFresh Exports",
            phone="+91-9876543215",
            location="Chennai",
            interested_crops=[
                CropInterest(crop="tomato", min_qty=150, max_qty=1500, preferred_price=31),
                CropInterest(crop="onion", min_qty=200, max_qty=2000, preferred_price=34),
            ],
            verified=True
        ),
        Buyer(
            id=next_id + 3,
            name="RuralConnect Co.",
            phone="+91-9876543216",
            location="Pune",
            interested_crops=[
                CropInterest(crop="wheat", min_qty=350, max_qty=3500, preferred_price=10),
                CropInterest(crop="corn", min_qty=400, max_qty=4000, preferred_price=17),
            ],
            verified=False
        ),
        Buyer(
            id=next_id + 4,
            name="OrganicHarvest Solutions",
            phone="+91-9876543217",
            location="Delhi",
            interested_crops=[
                CropInterest(crop="rice", min_qty=700, max_qty=7000, preferred_price=13),
                CropInterest(crop="potato", min_qty=180, max_qty=1800, preferred_price=21),
            ],
            verified=True
        ),
    ]
    
    for buyer in additional_buyers:
        storage.buyers[buyer.id] = buyer
    
    print(f"Added {len(additional_buyers)} additional mock buyers for testing")

# Initialize mock buyers
setup_mock_buyers()

# --------------------------------------------------
# Helper: Extract per-agent execution times
# --------------------------------------------------
def extract_agent_timings(execution_log):
    """
    Extract execution time spent in each agent
    from LangGraph execution_log timestamps.
    """
    timings = {
        "reasoner_time": 0.0,
        "disease_agent_time": 0.0,
        "price_agent_time": 0.0,
        "buyer_connect_agent_time": 0.0,
        "scheme_agent_time": 0.0
    }

    node_times = []

    for entry in execution_log:
        if "timestamp" in entry:
            node_times.append(
                (entry["node"], datetime.fromisoformat(entry["timestamp"]))
            )

    # Calculate durations between consecutive nodes
    for i in range(len(node_times) - 1):
        node, start = node_times[i]
        _, end = node_times[i + 1]
        duration = (end - start).total_seconds()

        if node == "reasoner":
            timings["reasoner_time"] += duration
        elif node == "disease_agent":
            timings["disease_agent_time"] += duration
        elif node == "price_agent":
            timings["price_agent_time"] += duration
        elif node == "buyer_connect_agent":
            timings["buyer_connect_agent_time"] += duration
        elif node == "scheme_agent":
            timings["scheme_agent_time"] += duration

    return timings


# --------------------------------------------------
# 1. DEFINE 200 TEST QUERIES
# --------------------------------------------------
test_cases = [
    # -------- DISEASE ONLY (40 queries) --------
    ("My tomato leaves have yellow spots", ["disease_agent"]),
    ("White powder appearing on chilli leaves", ["disease_agent"]),
    ("Potato plants are wilting suddenly", ["disease_agent"]),
    ("Brown patches on rice leaves", ["disease_agent"]),
    ("Black spots on mango leaves", ["disease_agent"]),
    ("Leaves of tomato turning curly", ["disease_agent"]),
    ("Stem rot observed in chilli plants", ["disease_agent"]),
    ("Yellowing and drying of leaves in wheat", ["disease_agent"]),
    ("Blight symptoms visible on potato leaves", ["disease_agent"]),
    ("Powdery mildew signs on cucumber", ["disease_agent"]),
    ("Tomato plant looks unhealthy and weak", ["disease_agent"]),
    ("Root rot affecting my plants", ["disease_agent"]),
    ("Spots and discoloration on crop leaves", ["disease_agent"]),
    ("My rice crop has brown leaf spots", ["disease_agent"]),
    ("Tomato fruits are developing black spots", ["disease_agent"]),
    ("Potato tubers showing rot symptoms", ["disease_agent"]),
    ("Wheat leaves have rust colored patches", ["disease_agent"]),
    ("Chilli plants showing leaf curl disease", ["disease_agent"]),
    ("My crops are infected with some disease", ["disease_agent"]),
    ("Tomato leaves turning yellow and falling", ["disease_agent"]),
    ("Black mold on potato leaves", ["disease_agent"]),
    ("Rice plants have stem borer damage", ["disease_agent"]),
    ("White fuzzy growth on plant stems", ["disease_agent"]),
    ("Brown lesions on wheat leaves", ["disease_agent"]),
    ("Tomato plant disease identification needed", ["disease_agent"]),
    ("Potato crop showing wilting symptoms", ["disease_agent"]),
    ("Rice leaves have yellow streaks", ["disease_agent"]),
    ("Fungal infection on my crops", ["disease_agent"]),
    ("Tomato plants with leaf spot disease", ["disease_agent"]),
    ("Potato blight affecting my field", ["disease_agent"]),
    ("Wheat rust disease symptoms", ["disease_agent"]),
    ("Chilli plants infected with viruses", ["disease_agent"]),
    ("My tomato crop is sick", ["disease_agent"]),
    ("Plant disease diagnosis for potato", ["disease_agent"]),
    ("Rice crop showing disease signs", ["disease_agent"]),
    ("Tomato leaves with mosaic pattern", ["disease_agent"]),
    ("Potato plants have bacterial wilt", ["disease_agent"]),
    ("Wheat crop infected with smut", ["disease_agent"]),
    ("My crops need disease treatment", ["disease_agent"]),
    ("Tomato plants showing viral symptoms", ["disease_agent"]),
    ("Potato leaves have late blight", ["disease_agent"]),
    ("Rice plants with blast disease", ["disease_agent"]),
    ("Wheat crop showing powdery mildew", ["disease_agent"]),
    ("Chilli plants have anthracnose", ["disease_agent"]),
    # -------- PRICE ONLY (40 queries) --------
    ("What is the current price of tomato?", ["price_agent"]),
    ("Today's onion market price", ["price_agent"]),
    ("What is the mandi rate for rice?", ["price_agent"]),
    ("Price of wheat today", ["price_agent"]),
    ("How much is corn selling for now?", ["price_agent"]),
    ("Current market value of potato", ["price_agent"]),
    ("Is tomato price increasing today?", ["price_agent"]),
    ("Market rate of chilli", ["price_agent"]),
    ("What is the selling price of rice?", ["price_agent"]),
    ("Price trend for onion this week", ["price_agent"]),
    ("What is the cost of rice in the market?", ["price_agent"]),
    ("Latest price update for wheat", ["price_agent"]),
    ("Should I sell tomato now?", ["price_agent"]),
    ("How much can I get for my potatoes?", ["price_agent"]),
    ("Current crop prices", ["price_agent"]),
    ("Tomato market rate today", ["price_agent"]),
    ("What's the price of wheat per kg?", ["price_agent"]),
    ("Onion price in market", ["price_agent"]),
    ("Rice selling price", ["price_agent"]),
    ("Potato market value", ["price_agent"]),
    ("Tomato price trend", ["price_agent"]),
    ("Current wheat prices", ["price_agent"]),
    ("How much does rice cost?", ["price_agent"]),
    ("Tomato market price today", ["price_agent"]),
    ("Onion rate in mandi", ["price_agent"]),
    ("Wheat price per kilogram", ["price_agent"]),
    ("Rice market rate", ["price_agent"]),
    ("Potato price today", ["price_agent"]),
    ("What is tomato selling for?", ["price_agent"]),
    ("Onion market value", ["price_agent"]),
    ("Wheat current price", ["price_agent"]),
    ("Rice price per kg", ["price_agent"]),
    ("Tomato rate today", ["price_agent"]),
    ("Potato market price", ["price_agent"]),
    ("Onion selling price", ["price_agent"]),
    ("Wheat market rate", ["price_agent"]),
    ("Rice price today", ["price_agent"]),
    ("Tomato cost per kg", ["price_agent"]),
    ("Onion price trend", ["price_agent"]),
    ("Wheat selling rate", ["price_agent"]),
    ("Rice market value", ["price_agent"]),
    ("Potato price per kilogram", ["price_agent"]),
    ("Tomato market value", ["price_agent"]),
    ("Onion current rate", ["price_agent"]),
    ("Wheat price in market", ["price_agent"]),
    ("Rice rate today", ["price_agent"]),
    ("Potato selling price", ["price_agent"]),
    ("Tomato price information", ["price_agent"]),
    ("Onion market price", ["price_agent"]),
    ("Wheat rate per kg", ["price_agent"]),
    ("Rice current market price", ["price_agent"]),

    # -------- BUYER CONNECT (40 queries) --------
    ("I want to sell my tomato crop", ["buyer_connect_agent"]),
    ("Find buyer for my wheat", ["buyer_connect_agent"]),
    ("I need to sell 500 kg of rice", ["buyer_connect_agent"]),
    ("Looking for buyer for potato", ["buyer_connect_agent"]),
    ("Want to sell my onion crop", ["buyer_connect_agent"]),
    ("Find buyer for my corn", ["buyer_connect_agent"]),
    ("I want to sell tomato at good price", ["buyer_connect_agent"]),
    ("Need buyer for wheat crop", ["buyer_connect_agent"]),
    ("Looking for buyer for my rice", ["buyer_connect_agent"]),
    ("Want to sell potatoes", ["buyer_connect_agent"]),
    ("Find buyer for onion", ["buyer_connect_agent"]),
    ("I need a buyer for my tomato", ["buyer_connect_agent"]),
    ("Sell my wheat crop", ["buyer_connect_agent"]),
    ("Looking for buyer to sell rice", ["buyer_connect_agent"]),
    ("Want to find buyer for potato", ["buyer_connect_agent"]),
    ("I have tomato to sell", ["buyer_connect_agent"]),
    ("Find buyer for wheat", ["buyer_connect_agent"]),
    ("Need to sell rice crop", ["buyer_connect_agent"]),
    ("Looking for buyer for onion crop", ["buyer_connect_agent"]),
    ("I want to sell 300 kg tomato", ["buyer_connect_agent"]),
    ("Find buyer for 1000 kg wheat", ["buyer_connect_agent"]),
    ("Sell 500 kg of rice", ["buyer_connect_agent"]),
    ("Want buyer for 400 kg potato", ["buyer_connect_agent"]),
    ("I need buyer for 600 kg onion", ["buyer_connect_agent"]),
    ("Looking to sell tomato at minimum 30 per kg", ["buyer_connect_agent"]),
    ("Find buyer for wheat at 12 per kg", ["buyer_connect_agent"]),
    ("Sell rice for at least 15 per kg", ["buyer_connect_agent"]),
    ("Want buyer for potato minimum 20 per kg", ["buyer_connect_agent"]),
    ("I need buyer for onion at 35 per kg", ["buyer_connect_agent"]),
    ("Looking for buyer to purchase my tomato", ["buyer_connect_agent"]),
    ("Find someone to buy my wheat", ["buyer_connect_agent"]),
    ("Need someone to purchase rice", ["buyer_connect_agent"]),
    ("Want someone to buy potato", ["buyer_connect_agent"]),
    ("I have corn to sell find buyer", ["buyer_connect_agent"]),
    ("Looking for buyer for my crop", ["buyer_connect_agent"]),
    ("I want to sell my produce", ["buyer_connect_agent"]),
    ("Find buyer for agricultural produce", ["buyer_connect_agent"]),
    ("Need buyer for farming produce", ["buyer_connect_agent"]),
    ("Want to sell crops to buyer", ["buyer_connect_agent"]),
    ("I need a buyer for my farm produce", ["buyer_connect_agent"]),
    ("Looking for buyer for harvest", ["buyer_connect_agent"]),
    ("Find buyer to buy my crops", ["buyer_connect_agent"]),
    ("Want to connect with buyers", ["buyer_connect_agent"]),
    ("I need buyers for my crops", ["buyer_connect_agent"]),
    ("Looking for crop buyers", ["buyer_connect_agent"]),
    ("Find agricultural buyers", ["buyer_connect_agent"]),
    ("Want to sell to buyers", ["buyer_connect_agent"]),
    ("I have crops ready to sell", ["buyer_connect_agent"]),
    ("Need to find buyers for my produce", ["buyer_connect_agent"]),
    ("Looking for agricultural product buyers", ["buyer_connect_agent"]),

    # -------- SCHEME AGENT (40 queries) --------
    ("Show me agricultural schemes in Maharashtra", ["scheme_agent"]),
    ("What subsidies are available for dairy farming?", ["scheme_agent"]),
    ("I'm from Goa and want animal husbandry schemes", ["scheme_agent"]),
    ("Agricultural schemes in Karnataka", ["scheme_agent"]),
    ("Show me schemes for fishing in Kerala", ["scheme_agent"]),
    ("What government schemes are available?", ["scheme_agent"]),
    ("Soil health schemes in Gujarat", ["scheme_agent"]),
    ("Financial assistance schemes for farmers", ["scheme_agent"]),
    ("I'm from Himachal Pradesh show me schemes", ["scheme_agent"]),
    ("Animal husbandry schemes in Rajasthan", ["scheme_agent"]),
    ("What schemes are available for organic farming?", ["scheme_agent"]),
    ("Show me irrigation schemes", ["scheme_agent"]),
    ("Agricultural input schemes", ["scheme_agent"]),
    ("Crop insurance schemes", ["scheme_agent"]),
    ("Schemes for farmers in Tamil Nadu", ["scheme_agent"]),
    ("What subsidies for fertilizers?", ["scheme_agent"]),
    ("Show me schemes for seed purchase", ["scheme_agent"]),
    ("Financial assistance programs", ["scheme_agent"]),
    ("I'm from Punjab what schemes available", ["scheme_agent"]),
    ("Livestock schemes in Madhya Pradesh", ["scheme_agent"]),
    ("Dairy farming subsidies", ["scheme_agent"]),
    ("Poultry farming schemes", ["scheme_agent"]),
    ("Fisheries schemes", ["scheme_agent"]),
    ("What schemes for vermicompost?", ["scheme_agent"]),
    ("Entrepreneurship development schemes", ["scheme_agent"]),
    ("Schemes in Uttar Pradesh", ["scheme_agent"]),
    ("Show me all categories of schemes in Goa", ["scheme_agent"]),
    ("What sub-categories are available in Maharashtra?", ["scheme_agent"]),
    ("Animal husbandry schemes", ["scheme_agent"]),
    ("Financial assistance for agriculture", ["scheme_agent"]),
    ("Schemes for small farmers", ["scheme_agent"]),
    ("Organic farming assistance", ["scheme_agent"]),
    ("Irrigation subsidy schemes", ["scheme_agent"]),
    ("Agricultural schemes in West Bengal", ["scheme_agent"]),
    ("What benefits for farmers?", ["scheme_agent"]),
    ("Show me government assistance programs", ["scheme_agent"]),
    ("Schemes for landless farmers", ["scheme_agent"]),
    ("Agricultural development schemes", ["scheme_agent"]),
    ("What schemes for crop production?", ["scheme_agent"]),
    ("Show me subsidy programs", ["scheme_agent"]),
    ("Schemes in Bihar", ["scheme_agent"]),
    ("Financial support for farmers", ["scheme_agent"]),
    ("What schemes available for me?", ["scheme_agent"]),
    ("Agricultural benefits in Odisha", ["scheme_agent"]),
    ("Show me eligible schemes", ["scheme_agent"]),
    ("Government schemes for agriculture", ["scheme_agent"]),
    ("What assistance programs exist?", ["scheme_agent"]),
    ("Schemes for agricultural inputs", ["scheme_agent"]),
    ("Show me farming support schemes", ["scheme_agent"]),
    ("What schemes can I apply for?", ["scheme_agent"]),

    # -------- COMBINED QUERIES (20 queries) --------
    ("My tomato leaves have spots and what is the market price?", ["disease_agent", "price_agent"]),
    ("Chilli plants are infected, should I sell now?", ["disease_agent", "price_agent"]),
    ("Rice crop showing disease, what is the current price?", ["disease_agent", "price_agent"]),
    ("Potato plants have blight, what is the selling rate?", ["disease_agent", "price_agent"]),
    ("Tomato crop affected by disease, is it worth selling?", ["disease_agent", "price_agent"]),
    ("Disease in wheat crop and market value", ["disease_agent", "price_agent"]),
    ("My tomato crop is sick and I want to sell it", ["disease_agent", "buyer_connect_agent"]),
    ("Rice has disease, find buyer for it", ["disease_agent", "buyer_connect_agent"]),
    ("Wheat price and show me schemes", ["price_agent", "scheme_agent"]),
    ("What is rice price and what schemes available?", ["price_agent", "scheme_agent"]),
    ("I want to sell tomato and know the price", ["buyer_connect_agent", "price_agent"]),
    ("Find buyer for wheat and check current price", ["buyer_connect_agent", "price_agent"]),
    ("Show me schemes and tomato price", ["scheme_agent", "price_agent"]),
    ("My potato crop is diseased and price is low", ["disease_agent", "price_agent"]),
    ("Tomato plants infected and I want to sell", ["disease_agent", "buyer_connect_agent"]),
    ("What schemes for farmers and rice price", ["scheme_agent", "price_agent"]),
    ("Find buyer for my crop and show schemes", ["buyer_connect_agent", "scheme_agent"]),
    ("My crops are sick and prices are falling", ["disease_agent", "price_agent"]),
    ("Rice disease and buyer connection needed", ["disease_agent", "buyer_connect_agent"]),
    ("Agricultural schemes and market prices", ["scheme_agent", "price_agent"]),

    # -------- OUT OF SCOPE (20 queries) --------
    ("Who is the president of India?", []),
    ("What is the capital of France?", []),
    ("Tell me about cricket world cup", []),
    ("Who invented the computer?", []),
    ("Weather forecast for tomorrow", []),
    ("Explain artificial intelligence", []),
    ("What is blockchain technology?", []),
    ("Latest movie releases", []),
    ("History of Kerala", []),
    ("Stock market news today", []),
    ("What is quantum computing?", []),
    ("Tell me a joke", []),
    ("What is the weather like?", []),
    ("How to cook biryani?", []),
    ("What is the population of India?", []),
    ("Tell me about space exploration", []),
    ("What is machine learning?", []),
    ("News headlines today", []),
    ("Explain photosynthesis", []),
    ("What is the speed of light?", []),
]


# --------------------------------------------------
# 2. INITIALIZE WORKFLOW
# --------------------------------------------------
workflow = AgriMitraWorkflow()

evaluation_log = {"summary": {}, "queries": []}

latencies = []
reasoner_times = []
disease_times = []
price_times = []
buyer_connect_times = []
scheme_times = []

correct_routing = 0
successful_workflows = 0
error_count = 0
agent_trigger_stats = {}

# --------------------------------------------------
# 3. EVALUATION LOOP
# --------------------------------------------------
print(f"\n{'='*60}")
print(f"Starting evaluation with {len(test_cases)} test queries")
print(f"{'='*60}\n")

for idx, (query, expected_agents) in enumerate(test_cases, 1):
    print(f"[{idx}/{len(test_cases)}] Processing: {query[:60]}...")
    start_time = time.time()

    try:
        result = workflow.run(query)
        end_time = time.time()

        latency = end_time - start_time
        latencies.append(latency)

        predicted_agents = result.get("next_nodes", [])
        final_response = result.get("final_response", None)
        execution_log = result.get("execution_log", [])

        timings = extract_agent_timings(execution_log)

        # Only append timing data for successful queries (filter out zeros to avoid skewing median)
        if timings["reasoner_time"] > 0:
            reasoner_times.append(timings["reasoner_time"])
        if timings["disease_agent_time"] > 0:
            disease_times.append(timings["disease_agent_time"])
        if timings["price_agent_time"] > 0:
            price_times.append(timings["price_agent_time"])
        if timings["buyer_connect_agent_time"] > 0:
            buyer_connect_times.append(timings["buyer_connect_agent_time"])
        if timings["scheme_agent_time"] > 0:
            scheme_times.append(timings["scheme_agent_time"])

        routing_correct = set(predicted_agents) == set(expected_agents)
        if routing_correct:
            correct_routing += 1

        workflow_success = final_response is not None
        if workflow_success:
            successful_workflows += 1

        for agent in predicted_agents:
            agent_trigger_stats[agent] = agent_trigger_stats.get(agent, 0) + 1

        evaluation_log["queries"].append({
            "query": query,
            "expected_agents": expected_agents,
            "predicted_agents": predicted_agents,
            "routing_correct": routing_correct,
            "workflow_success": workflow_success,
            "latency_seconds": round(latency, 4),
            "reasoner_time": round(timings["reasoner_time"], 4),
            "disease_agent_time": round(timings["disease_agent_time"], 4),
            "price_agent_time": round(timings["price_agent_time"], 4),
            "buyer_connect_agent_time": round(timings["buyer_connect_agent_time"], 4),
            "scheme_agent_time": round(timings["scheme_agent_time"], 4),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        error_count += 1
        error_msg = str(e)
        is_rate_limit = "rate limit" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower()
        
        evaluation_log["queries"].append({
            "query": query,
            "expected_agents": expected_agents,
            "error": error_msg,
            "is_rate_limit_error": is_rate_limit,
            "timestamp": datetime.now().isoformat()
        })
        
        if is_rate_limit:
            print(f"  RATE LIMIT ERROR: Waiting 5 seconds before continuing...")
            time.sleep(5)  # Longer wait for rate limit errors
        else:
            print(f"  ERROR: {error_msg[:100]}")
        
        # Don't append to latency lists for failed queries

    # Rate limiting to avoid API throttling (increased from 0.5 to 1.0 seconds)
    if idx < len(test_cases):
        time.sleep(1.0)


# --------------------------------------------------
# 4. SUMMARY METRICS
# --------------------------------------------------
evaluation_log["summary"] = {
    "total_queries": len(test_cases),
    "reasoner_routing_accuracy": round(correct_routing / len(test_cases), 4) if test_cases else 0,
    "workflow_success_rate": round(successful_workflows / len(test_cases), 4) if test_cases else 0,

    "median_latency_seconds": round(median(latencies), 4) if latencies else 0,
    "average_latency_seconds": round(mean(latencies), 4) if latencies else 0,
    "min_latency_seconds": round(min(latencies), 4) if latencies else 0,
    "max_latency_seconds": round(max(latencies), 4) if latencies else 0,

    "median_reasoner_time": round(median(reasoner_times), 4) if reasoner_times else 0,
    "avg_reasoner_time": round(mean(reasoner_times), 4) if reasoner_times else 0,
    "median_disease_agent_time": round(median(disease_times), 4) if disease_times else 0,
    "avg_disease_agent_time": round(mean(disease_times), 4) if disease_times else 0,
    "median_price_agent_time": round(median(price_times), 4) if price_times else 0,
    "avg_price_agent_time": round(mean(price_times), 4) if price_times else 0,
    "median_buyer_connect_agent_time": round(median(buyer_connect_times), 4) if buyer_connect_times else 0,
    "avg_buyer_connect_agent_time": round(mean(buyer_connect_times), 4) if buyer_connect_times else 0,
    "median_scheme_agent_time": round(median(scheme_times), 4) if scheme_times else 0,
    "avg_scheme_agent_time": round(mean(scheme_times), 4) if scheme_times else 0,

    "total_errors": error_count,
    "agent_trigger_distribution": agent_trigger_stats,
    
    "query_distribution": {
        "disease_only": sum(1 for _, agents in test_cases if agents == ["disease_agent"]),
        "price_only": sum(1 for _, agents in test_cases if agents == ["price_agent"]),
        "buyer_connect_only": sum(1 for _, agents in test_cases if agents == ["buyer_connect_agent"]),
        "scheme_only": sum(1 for _, agents in test_cases if agents == ["scheme_agent"]),
        "combined": sum(1 for _, agents in test_cases if len(agents) > 1),
        "out_of_scope": sum(1 for _, agents in test_cases if agents == [])
    }
}


# --------------------------------------------------
# 5. SAVE RESULTS
# --------------------------------------------------
with open("final_results.json", "w", encoding="utf-8") as f:
    json.dump(evaluation_log, f, indent=4, ensure_ascii=False)

# --------------------------------------------------
# 6. PRINT SUMMARY
# --------------------------------------------------
print(f"\n{'='*60}")
print("AGRIMITRA EVALUATION SUMMARY")
print(f"{'='*60}")
for k, v in evaluation_log["summary"].items():
    if isinstance(v, dict):
        print(f"\n{k}:")
        for sub_k, sub_v in v.items():
            print(f"  {sub_k}: {sub_v}")
    else:
        print(f"{k}: {v}")
print(f"{'='*60}\n")
print(f"Results saved to: final_results.json")
