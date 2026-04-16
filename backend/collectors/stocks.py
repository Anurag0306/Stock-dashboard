import yfinance as yf
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import GLOBAL_INDICES, INDIAN_INDICES, COMMODITIES, BONDS, FOREX_PAIRS
from database import insert_price

def fetch_quote(symbol):
    """Fetch latest price and change % for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        data   = ticker.fast_info
        price  = data.last_price
        prev   = data.previous_close
        change_pct = ((price - prev) / prev) * 100 if prev else 0
        volume = getattr(data, 'three_month_average_volume', None)
        return round(price, 4), round(change_pct, 4), volume
    except Exception as e:
        print(f"  ⚠️  Error fetching {symbol}: {e}")
        return None, None, None

def collect_global_indices():
    print("📊 Fetching Global Indices...")
    for name, symbol in GLOBAL_INDICES.items():
        price, chg, vol = fetch_quote(symbol)
        if price:
            insert_price(name, "global_index", symbol, price, chg, vol)
            print(f"  ✅ {name}: {price} ({chg:+.2f}%)")

def collect_indian_indices():
    print("📊 Fetching Indian Indices...")
    for name, symbol in INDIAN_INDICES.items():
        price, chg, vol = fetch_quote(symbol)
        if price:
            insert_price(name, "indian_index", symbol, price, chg, vol)
            print(f"  ✅ {name}: {price} ({chg:+.2f}%)")

def collect_commodities():
    print("🛢️  Fetching Commodities...")
    for name, symbol in COMMODITIES.items():
        price, chg, vol = fetch_quote(symbol)
        if price:
            insert_price(name, "commodity", symbol, price, chg, vol)
            print(f"  ✅ {name}: {price} ({chg:+.2f}%)")

def collect_bonds():
    print("📈 Fetching Bond Yields...")
    for name, symbol in BONDS.items():
        price, chg, vol = fetch_quote(symbol)
        if price:
            insert_price(name, "bond", symbol, price, chg, vol)
            print(f"  ✅ {name}: {price}% ({chg:+.2f}%)")

def collect_forex():
    print("💱 Fetching Forex Pairs...")
    for name, symbol in FOREX_PAIRS.items():
        price, chg, vol = fetch_quote(symbol)
        if price:
            insert_price(name, "forex", symbol, price, chg, vol)
            print(f"  ✅ {name}: {price} ({chg:+.2f}%)")

def collect_all_market_data():
    """Master function — called by scheduler every 5 min."""
    print("\n🔄 Starting market data collection...")
    collect_global_indices()
    collect_indian_indices()
    collect_commodities()
    collect_bonds()
    collect_forex()
    print("✅ Market data collection complete.\n")

if __name__ == "__main__":
    collect_all_market_data()