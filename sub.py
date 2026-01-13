import json
def get_subcategories_for_state(user_state):
    with open("subcategories_by_state.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    result = {}

    # Add state subcategories
    if user_state in data:
        result["State Schemes"] = data[user_state]
    else:
        result["State Schemes"] = {}

    # Add central subcategories
    result["Central Schemes"] = data.get("Central", {})

    return result

print(get_subcategories_for_state("Assam"))