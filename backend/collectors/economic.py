import requests
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import FRED_API_KEY, FRED_SERIES
from database import get_connection
from datetime import datetime

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

def fetch_fred_series(series_id):
    """Fetch latest value for a FRED economic series."""
    try:
        params = {
            "series_id":      series_id,
            "api_key":        FRED_API_KEY,
            "file_type":      "json",
            "sort_order":     "desc",
            "limit":          1
        }
        response = requests.get(FRED_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        observations = data.get("observations", [])
        if observations:
            value  = observations[0].get("value", ".")
            period = observations[0].get("date", "")
            if value == ".":
                return None, period
            return float(value), period
        return None, None
    except Exception as e:
        print(f"  ⚠️  FRED error for {series_id}: {e}")
        return None, None

def collect_economic_indicators():
    print("📉 Fetching Economic Indicators (FRED)...")
    conn = get_connection()
    for name, series_id in FRED_SERIES.items():
        value, period = fetch_fred_series(series_id)
        if value is not None:
            conn.execute("""
                INSERT INTO economic_data (indicator, value, period, timestamp)
                VALUES (?, ?, ?, ?)
            """, (name, value, period, datetime.utcnow().isoformat()))
            print(f"  ✅ {name}: {value} (as of {period})")
        else:
            print(f"  ⚠️  No data for {name}")
    conn.commit()
    conn.close()
    print("✅ Economic data collection complete.\n")

if __name__ == "__main__":
    collect_economic_indicators()