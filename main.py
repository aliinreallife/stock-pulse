import requests
import json
import os

ins_code = 6905737326614124

def get_closing_price_info(ins_code):
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ins_code}"
    response = requests.get(url)
    data = response.json()
    return data

def get_best_limits(ins_code):
    url = f"https://cdn.tsetmc.com/api/BestLimits/{ins_code}"
    response = requests.get(url)
    data = response.json()
    return data

data_closing_price_info = get_closing_price_info(ins_code)
data_best_limits = get_best_limits(ins_code)

os.makedirs("export", exist_ok=True)
save_path_closing_price_info = f"export/{ins_code}_closing_price_info.json"
with open(save_path_closing_price_info, "w", encoding="utf-8") as f:
    json.dump(data_closing_price_info, f, indent=4, ensure_ascii=False)

save_path_best_limits = f"export/{ins_code}_best_limits.json"
with open(save_path_best_limits, "w", encoding="utf-8") as f:
    json.dump(data_best_limits, f, indent=4, ensure_ascii=False)