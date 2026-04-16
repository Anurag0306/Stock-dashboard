import requests
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import CRYPTO
from database import insert_price

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

def collect_crypto():
    print("₿ Fetching Crypto prices...")
    try:
        ids = ",".join(CRYPTO.values())
        params = {
            "ids": ids,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_24hr_vol": "true"
        }
        response = requests.get(COINGECKO_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        for name, coin_id in CRYPTO.items():
            if coin_id in data:
                price      = data[coin_id].get("usd", 0)
                change_pct = data[coin_id].get("usd_24h_change", 0)
                volume     = data[coin_id].get("usd_24h_vol", 0)
                insert_price(name, "crypto", coin_id, price, round(change_pct, 4), volume)
                print(f"  ✅ {name}: ${price:,.2f} ({change_pct:+.2f}%)")
            else:
                print(f"  ⚠️  No data for {name}")

    except Exception as e:
        print(f"  ❌ Crypto fetch error: {e}")

if __name__ == "__main__":
    collect_crypto()