import requests
import json
import time

API_KEY = "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc"
URL = "https://api.myscheme.gov.in/search/v6/schemes"

HEADERS = {
    "x-api-key": API_KEY,
    "accept": "application/json",
}

all_slugs = []
page = 0
size = 10

while True:
    print(f"Fetching page: {page+1}")

    params = {
        "lang": "en",
        "q": '[{"identifier":"schemeCategory","value":"Agriculture,Rural & Environment"}]',
        "keyword": "",
        "sort": "",
        "from": page * size,
        "size": size
    }

    res = requests.get(URL, headers=HEADERS, params=params)

    if res.status_code != 200:
        print("Error:", res.status_code)
        break

    data = res.json()

    items = data["data"]["hits"]["items"]

    if not items:
        break

    for item in items:
        slug = item["fields"]["slug"]
        all_slugs.append(slug)

    page += 1
    total_pages = data["data"]["hits"]["page"]["totalPages"]

    if page >= total_pages:
        break

    time.sleep(0.3)

# SAVE SLUGS
with open("slugs.json", "w") as f:
    json.dump(all_slugs, f, indent=4)

print("\nTotal slugs saved:", len(all_slugs))
