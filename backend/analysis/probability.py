import numpy as np
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_connection
from datetime import datetime

def get_price_dataframe(symbol, days=30):
    """Get price history as a pandas Series."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT price, timestamp FROM prices
        WHERE symbol = ?
        AND timestamp >= datetime('now', ?)
        ORDER BY timestamp ASC
    """, (symbol, f'-{days} days')).fetchall()
    conn.close()

    if len(rows) < 5:
        return None

    df = pd.DataFrame([dict(r) for r in rows])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    return df['price']

def compute_volatility(prices: pd.Series) -> dict:
    """Compute rolling volatility metrics."""
    if prices is None or len(prices) < 5:
        return {}

    returns = prices.pct_change().dropna()
    if len(returns) < 3:
        return {}

    daily_vol   = float(returns.std())
    annual_vol  = daily_vol * np.sqrt(252) * 100
    weekly_vol  = daily_vol * np.sqrt(5)  * 100

    return {
        "daily_vol":   round(daily_vol  * 100, 4),
        "weekly_vol":  round(weekly_vol,        2),
        "annual_vol":  round(annual_vol,        2),
        "data_points": len(prices),
    }

def compute_expected_move(prices: pd.Series, days_ahead=5) -> dict:
    """
    Compute expected price range using historical volatility.
    Based on: Price ± (Price × Vol × √days)
    """
    if prices is None or len(prices) < 5:
        return {}

    current_price = float(prices.iloc[-1])
    returns       = prices.pct_change().dropna()

    if len(returns) < 3:
        return {}

    daily_vol = float(returns.std())
    move_1d   = current_price * daily_vol
    move_5d   = current_price * daily_vol * np.sqrt(days_ahead)
    move_30d  = current_price * daily_vol * np.sqrt(30)

    return {
        "current_price": round(current_price, 2),
        "expected_move_1d": {
            "points":  round(move_1d, 2),
            "pct":     round(daily_vol * 100, 2),
            "upper":   round(current_price + move_1d, 2),
            "lower":   round(current_price - move_1d, 2),
        },
        "expected_move_5d": {
            "points":  round(move_5d, 2),
            "pct":     round(daily_vol * np.sqrt(5) * 100, 2),
            "upper":   round(current_price + move_5d, 2),
            "lower":   round(current_price - move_5d, 2),
        },
        "expected_move_30d": {
            "points":  round(move_30d, 2),
            "pct":     round(daily_vol * np.sqrt(30) * 100, 2),
            "upper":   round(current_price + move_30d, 2),
            "lower":   round(current_price - move_30d, 2),
        },
    }

def compute_support_resistance(prices: pd.Series) -> dict:
    """Calculate support and resistance levels."""
    if prices is None or len(prices) < 10:
        return {}

    current = float(prices.iloc[-1])
    high    = float(prices.max())
    low     = float(prices.min())
    mean    = float(prices.mean())

    # Pivot points
    pivot = (high + low + current) / 3
    r1    = 2 * pivot - low
    r2    = pivot + (high - low)
    s1    = 2 * pivot - high
    s2    = pivot - (high - low)

    # 52-week high/low (approx from available data)
    high_52w = float(prices.rolling(min(len(prices), 252)).max().iloc[-1])
    low_52w  = float(prices.rolling(min(len(prices), 252)).min().iloc[-1])

    return {
        "current":    round(current, 2),
        "pivot":      round(pivot,   2),
        "resistance": {
            "r1": round(r1, 2),
            "r2": round(r2, 2),
        },
        "support": {
            "s1": round(s1, 2),
            "s2": round(s2, 2),
        },
        "range": {
            "high":     round(high,    2),
            "low":      round(low,     2),
            "mean":     round(mean,    2),
            "high_52w": round(high_52w,2),
            "low_52w":  round(low_52w, 2),
        },
        "distance_from_high_pct": round((current - high) / high * 100, 2),
        "distance_from_low_pct":  round((current - low)  / low  * 100, 2),
    }

def compute_trend(prices: pd.Series) -> dict:
    """Detect trend direction and strength."""
    if prices is None or len(prices) < 5:
        return {}

    current  = float(prices.iloc[-1])
    ma_5     = float(prices.tail(5).mean())  if len(prices) >= 5  else current
    ma_10    = float(prices.tail(10).mean()) if len(prices) >= 10 else current
    ma_20    = float(prices.tail(20).mean()) if len(prices) >= 20 else current

    # Trend signal
    if current > ma_5 > ma_10:
        trend = "STRONG UPTREND"
        trend_score = 85
    elif current > ma_10:
        trend = "UPTREND"
        trend_score = 65
    elif current > ma_20:
        trend = "MILD UPTREND"
        trend_score = 55
    elif current < ma_5 < ma_10:
        trend = "STRONG DOWNTREND"
        trend_score = 15
    elif current < ma_10:
        trend = "DOWNTREND"
        trend_score = 35
    else:
        trend = "SIDEWAYS"
        trend_score = 50

    # RSI approximation
    returns = prices.pct_change().dropna()
    gains   = returns[returns > 0].mean() if len(returns[returns > 0]) > 0 else 0
    losses  = abs(returns[returns < 0].mean()) if len(returns[returns < 0]) > 0 else 0
    rs      = gains / losses if losses != 0 else 1
    rsi     = round(100 - (100 / (1 + rs)), 1)

    return {
        "trend":       trend,
        "trend_score": trend_score,
        "rsi":         rsi,
        "ma_5":        round(ma_5,  2),
        "ma_10":       round(ma_10, 2),
        "ma_20":       round(ma_20, 2),
        "current":     round(current, 2),
        "vs_ma5_pct":  round((current - ma_5)  / ma_5  * 100, 2),
        "vs_ma20_pct": round((current - ma_20) / ma_20 * 100, 2),
    }

def compute_market_breadth(all_prices: list) -> dict:
    """Overall market health indicator."""
    if not all_prices:
        return {}

    total     = len(all_prices)
    advancing = sum(1 for p in all_prices if (p.get('change_pct') or 0) > 0)
    declining = sum(1 for p in all_prices if (p.get('change_pct') or 0) < 0)
    unchanged = total - advancing - declining

    adv_dec_ratio = round(advancing / declining, 2) if declining > 0 else advancing

    # Breadth score 0-100
    breadth_score = round((advancing / total) * 100, 1) if total > 0 else 50

    if breadth_score >= 70:
        breadth_signal = "STRONG BULLISH"
    elif breadth_score >= 55:
        breadth_signal = "BULLISH"
    elif breadth_score >= 45:
        breadth_signal = "NEUTRAL"
    elif breadth_score >= 30:
        breadth_signal = "BEARISH"
    else:
        breadth_signal = "STRONG BEARISH"

    return {
        "total":          total,
        "advancing":      advancing,
        "declining":      declining,
        "unchanged":      unchanged,
        "adv_dec_ratio":  adv_dec_ratio,
        "breadth_score":  breadth_score,
        "breadth_signal": breadth_signal,
        "advancing_pct":  round(advancing / total * 100, 1) if total > 0 else 0,
        "declining_pct":  round(declining / total * 100, 1) if total > 0 else 0,
    }

def compute_vix_proxy(prices_list: list) -> dict:
    """
    Compute a VIX-like fear index from portfolio of assets.
    Uses average realized volatility across all tracked assets.
    """
    conn   = get_connection()
    vols   = []
    assets = []

    for p in prices_list:
        symbol = p.get('symbol')
        if not symbol:
            continue
        rows = conn.execute("""
            SELECT price FROM prices
            WHERE symbol = ?
            AND timestamp >= datetime('now', '-7 days')
            ORDER BY timestamp ASC
        """, (symbol,)).fetchall()

        if len(rows) < 5:
            continue

        px      = pd.Series([r[0] for r in rows])
        returns = px.pct_change().dropna()
        if len(returns) < 3:
            continue

        vol = float(returns.std()) * np.sqrt(252) * 100
        vols.append(vol)
        assets.append({"name": p['asset_name'], "vol": round(vol, 2)})

    conn.close()

    if not vols:
        return {"vix_proxy": 20, "signal": "NEUTRAL", "assets": []}

    avg_vol    = float(np.mean(vols))
    vix_proxy  = round(avg_vol, 1)

    if vix_proxy >= 40:
        signal = "EXTREME FEAR"
        color  = "#ff4560"
    elif vix_proxy >= 25:
        signal = "ELEVATED FEAR"
        color  = "#ff9800"
    elif vix_proxy >= 15:
        signal = "NORMAL"
        color  = "#ffb800"
    else:
        signal = "COMPLACENCY"
        color  = "#00c896"

    assets.sort(key=lambda x: x['vol'], reverse=True)

    return {
        "vix_proxy": vix_proxy,
        "signal":    signal,
        "color":     color,
        "assets":    assets[:8],
    }

# ── Master function ───────────────────────────────────────────────────────────
KEY_ASSETS = {
    "NIFTY 50":      "^NSEI",
    "Sensex":        "^BSESN",
    "S&P 500":       "^GSPC",
    "Gold":          "GC=F",
    "Crude Oil WTI": "CL=F",
    "Bitcoin":       "bitcoin",
    "USD/INR":       "INR=X",
    "US 10Y Yield":  "^TNX",
}

def get_full_probability_report(all_prices: list) -> dict:
    """Master function — compute all probability metrics."""
    results    = {}
    breadth    = compute_market_breadth(all_prices)
    vix        = compute_vix_proxy(all_prices)

    for name, symbol in KEY_ASSETS.items():
        prices = get_price_dataframe(symbol, days=30)
        if prices is None or len(prices) < 5:
            continue

        results[name] = {
            "volatility":          compute_volatility(prices),
            "expected_move":       compute_expected_move(prices),
            "support_resistance":  compute_support_resistance(prices),
            "trend":               compute_trend(prices),
        }

    return {
        "assets":           results,
        "market_breadth":   breadth,
        "vix_proxy":        vix,
        "timestamp":        datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    from database import get_latest_prices
    prices = get_latest_prices()
    print("📊 Computing probability report...")
    report = get_full_probability_report(prices)
    print(f"✅ Computed for {len(report['assets'])} assets")
    print(f"   Breadth: {report['market_breadth'].get('breadth_signal')}")
    print(f"   VIX Proxy: {report['vix_proxy'].get('vix_proxy')}")