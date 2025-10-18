import requests
import json
import os

ins_code = 6905737326614124
url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ins_code}"
response = requests.get(url)
data = response.json()

os.makedirs("export", exist_ok=True)

save_path = f"export/{ins_code}.json"
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)