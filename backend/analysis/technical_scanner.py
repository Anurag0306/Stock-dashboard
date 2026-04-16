import numpy as np
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_connection, get_latest_prices
from datetime import datetime

# ── Helper ────────────────────────────────────────────────────────────────────
def get_price_series(symbol, days=60):
    conn = get_connection()
    rows = conn.execute("""
        SELECT price, timestamp FROM prices
        WHERE symbol = ?
        AND timestamp >= datetime('now', ?)
        ORDER BY timestamp ASC
    """, (symbol, f'-{days} days')).fetchall()
    conn.close()
    if len(rows) < 10:
        return None
    df = pd.DataFrame([dict(r) for r in rows])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.set_index('timestamp')['price']

# ── 1. MACD ───────────────────────────────────────────────────────────────────
def compute_macd(prices: pd.Series,
                 fast=12, slow=26, signal=9) -> dict:
    """
    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal)
    Histogram = MACD - Signal
    """
    if prices is None or len(prices) < slow + signal:
        return {}

    ema_fast   = prices.ewm(span=fast,   adjust=False).mean()
    ema_slow   = prices.ewm(span=slow,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line= macd_line.ewm(span=signal, adjust=False).mean()
    histogram  = macd_line - signal_line

    curr_macd  = float(macd_line.iloc[-1])
    curr_sig   = float(signal_line.iloc[-1])
    curr_hist  = float(histogram.iloc[-1])
    prev_hist  = float(histogram.iloc[-2]) if len(histogram) > 1 else 0

    # Crossover detection
    prev_macd  = float(macd_line.iloc[-2])  if len(macd_line)   > 1 else 0
    prev_sig   = float(signal_line.iloc[-2]) if len(signal_line) > 1 else 0

    bullish_cross = prev_macd < prev_sig and curr_macd > curr_sig
    bearish_cross = prev_macd > prev_sig and curr_macd < curr_sig

    if bullish_cross:
        signal_str = "BULLISH CROSSOVER"
        action     = "BUY signal — MACD crossed above signal line"
        color      = "green"
    elif bearish_cross:
        signal_str = "BEARISH CROSSOVER"
        action     = "SELL signal — MACD crossed below signal line"
        color      = "red"
    elif curr_macd > curr_sig and curr_hist > prev_hist:
        signal_str = "BULLISH MOMENTUM"
        action     = "Uptrend strengthening — hold longs"
        color      = "green"
    elif curr_macd < curr_sig and curr_hist < prev_hist:
        signal_str = "BEARISH MOMENTUM"
        action     = "Downtrend strengthening — hold shorts"
        color      = "red"
    elif curr_macd > 0:
        signal_str = "ABOVE ZERO"
        action     = "Bullish zone — bias long"
        color      = "lightgreen"
    else:
        signal_str = "BELOW ZERO"
        action     = "Bearish zone — bias short"
        color      = "orange"

    return {
        "macd":           round(curr_macd, 4),
        "signal":         round(curr_sig,  4),
        "histogram":      round(curr_hist, 4),
        "signal_str":     signal_str,
        "action":         action,
        "color":          color,
        "bullish_cross":  bullish_cross,
        "bearish_cross":  bearish_cross,
        "macd_history":   [round(v, 4) for v in macd_line.tail(30).tolist()],
        "hist_history":   [round(v, 4) for v in histogram.tail(30).tolist()],
        "above_zero":     curr_macd > 0,
    }

# ── 2. RSI Divergence ─────────────────────────────────────────────────────────
def compute_rsi_series(prices: pd.Series, period=14) -> pd.Series:
    """Compute full RSI series."""
    delta  = prices.diff()
    gain   = delta.clip(lower=0)
    loss   = -delta.clip(upper=0)
    avg_g  = gain.ewm(com=period-1, adjust=False).mean()
    avg_l  = loss.ewm(com=period-1, adjust=False).mean()
    rs     = avg_g / avg_l
    return 100 - (100 / (1 + rs))

def detect_divergence(prices: pd.Series) -> dict:
    """
    Divergence = Price and RSI moving in opposite directions.
    Bullish Divergence: Price makes lower low, RSI makes higher low → BUY
    Bearish Divergence: Price makes higher high, RSI makes lower high → SELL
    """
    if prices is None or len(prices) < 20:
        return {}

    rsi    = compute_rsi_series(prices)
    p_tail = prices.tail(20).reset_index(drop=True)
    r_tail = rsi.tail(20).reset_index(drop=True)

    # Find recent swing points
    p_curr = float(p_tail.iloc[-1])
    p_mid  = float(p_tail.iloc[10])
    p_old  = float(p_tail.iloc[0])

    r_curr = float(r_tail.iloc[-1])
    r_mid  = float(r_tail.iloc[10])
    r_old  = float(r_tail.iloc[0])

    divergences = []

    # Bullish divergence: price lower low, RSI higher low
    if p_curr < p_old and r_curr > r_old:
        strength = abs(r_curr - r_old) / 10
        divergences.append({
            "type":     "BULLISH DIVERGENCE",
            "action":   "High probability LONG setup — price weak but momentum building",
            "strength": "STRONG" if strength > 1 else "MODERATE",
            "color":    "green",
            "prob":     round(min(65 + strength * 5, 85), 1),
        })

    # Bearish divergence: price higher high, RSI lower high
    if p_curr > p_old and r_curr < r_old:
        strength = abs(r_old - r_curr) / 10
        divergences.append({
            "type":     "BEARISH DIVERGENCE",
            "action":   "High probability SHORT setup — price strong but momentum fading",
            "strength": "STRONG" if strength > 1 else "MODERATE",
            "color":    "red",
            "prob":     round(min(65 + strength * 5, 85), 1),
        })

    # Hidden bullish: price higher low, RSI lower low (trend continuation)
    if p_curr > p_mid > p_old and r_curr < r_mid:
        divergences.append({
            "type":     "HIDDEN BULLISH",
            "action":   "Trend continuation LONG — buy the dip in uptrend",
            "strength": "MODERATE",
            "color":    "lightgreen",
            "prob":     60.0,
        })

    # Hidden bearish: price lower high, RSI higher high
    if p_curr < p_mid < p_old and r_curr > r_mid:
        divergences.append({
            "type":     "HIDDEN BEARISH",
            "action":   "Trend continuation SHORT — sell the rally in downtrend",
            "strength": "MODERATE",
            "color":    "orange",
            "prob":     60.0,
        })

    if not divergences:
        divergences.append({
            "type":     "NO DIVERGENCE",
            "action":   "Price and RSI moving together — no divergence signal",
            "strength": "N/A",
            "color":    "gray",
            "prob":     50.0,
        })

    return {
        "divergences":   divergences,
        "current_rsi":   round(r_curr, 1),
        "current_price": round(p_curr,  2),
        "rsi_history":   [round(v, 1) for v in r_tail.tolist()],
        "price_history": [round(v, 2) for v in p_tail.tolist()],
    }

# ── 3. Fibonacci Retracement ──────────────────────────────────────────────────
def compute_fibonacci(prices: pd.Series) -> dict:
    """
    Auto-calculate Fibonacci retracement levels.
    Identifies high-probability support/resistance zones.
    """
    if prices is None or len(prices) < 10:
        return {}

    high  = float(prices.max())
    low   = float(prices.min())
    curr  = float(prices.iloc[-1])
    diff  = high - low

    # Standard Fibonacci levels
    levels = {
        "0.0%":    round(high,               2),
        "23.6%":   round(high - 0.236 * diff, 2),
        "38.2%":   round(high - 0.382 * diff, 2),
        "50.0%":   round(high - 0.500 * diff, 2),
        "61.8%":   round(high - 0.618 * diff, 2),
        "78.6%":   round(high - 0.786 * diff, 2),
        "100.0%":  round(low,                2),
    }

    # Extension levels (targets)
    extensions = {
        "127.2%": round(low  - 0.272 * diff, 2),
        "161.8%": round(low  - 0.618 * diff, 2),
        "261.8%": round(low  - 1.618 * diff, 2),
    }

    # Find nearest support and resistance
    level_vals  = list(levels.values())
    above_curr  = [v for v in level_vals if v > curr]
    below_curr  = [v for v in level_vals if v < curr]

    nearest_res = min(above_curr) if above_curr else None
    nearest_sup = max(below_curr) if below_curr else None

    # Position in range (0-100%)
    position_pct = round((curr - low) / diff * 100, 1) if diff > 0 else 50

    # Which fib zone is price in?
    fib_zone = "Unknown"
    for (name, val), (next_name, next_val) in zip(
        list(levels.items())[:-1], list(levels.items())[1:]
    ):
        if next_val <= curr <= val:
            fib_zone = f"Between {next_name} and {name}"
            break

    return {
        "high":          round(high, 2),
        "low":           round(low,  2),
        "current":       round(curr, 2),
        "levels":        levels,
        "extensions":    extensions,
        "nearest_support":    nearest_sup,
        "nearest_resistance": nearest_res,
        "position_pct":  position_pct,
        "fib_zone":      fib_zone,
        "trend":         "UPTREND" if curr > levels["50.0%"]
                         else "DOWNTREND",
    }

# ── 4. Bollinger Bands ────────────────────────────────────────────────────────
def compute_bollinger(prices: pd.Series,
                      window=20, num_std=2) -> dict:
    """
    Bollinger Bands: MA ± (std × 2)
    Price near upper band → overbought
    Price near lower band → oversold
    Band squeeze → volatility breakout incoming
    """
    if prices is None or len(prices) < window:
        return {}

    ma     = prices.rolling(window).mean()
    std    = prices.rolling(window).std()
    upper  = ma + (std * num_std)
    lower  = ma - (std * num_std)

    curr        = float(prices.iloc[-1])
    curr_upper  = float(upper.iloc[-1])
    curr_lower  = float(lower.iloc[-1])
    curr_ma     = float(ma.iloc[-1])
    band_width  = float((upper - lower).iloc[-1])
    avg_bw      = float((upper - lower).mean())

    # %B indicator: where is price within bands
    pct_b = (curr - curr_lower) / (curr_upper - curr_lower) \
            if (curr_upper - curr_lower) > 0 else 0.5

    # Band squeeze detection
    squeeze = band_width < avg_bw * 0.7

    if pct_b > 0.95:
        signal = "UPPER BAND TOUCH"
        action = "Overbought — potential reversal or continuation if strong"
        color  = "red"
    elif pct_b < 0.05:
        signal = "LOWER BAND TOUCH"
        action = "Oversold — potential bounce setup"
        color  = "green"
    elif squeeze:
        signal = "BAND SQUEEZE"
        action = "Low volatility squeeze — big breakout imminent, watch direction"
        color  = "yellow"
    elif pct_b > 0.8:
        signal = "NEAR UPPER BAND"
        action = "Price strong — in upper zone, trail stops"
        color  = "orange"
    elif pct_b < 0.2:
        signal = "NEAR LOWER BAND"
        action = "Price weak — near support, watch for bounce"
        color  = "lightgreen"
    else:
        signal = "MIDDLE BAND"
        action = "Price near mean — wait for edge"
        color  = "gray"

    return {
        "upper":      round(curr_upper, 2),
        "middle":     round(curr_ma,    2),
        "lower":      round(curr_lower, 2),
        "current":    round(curr,       2),
        "pct_b":      round(pct_b,      3),
        "band_width": round(band_width, 2),
        "squeeze":    squeeze,
        "signal":     signal,
        "action":     action,
        "color":      color,
        "upper_hist": [round(v,2) for v in upper.tail(20).tolist()],
        "lower_hist": [round(v,2) for v in lower.tail(20).tolist()],
        "ma_hist":    [round(v,2) for v in ma.tail(20).tolist()],
    }

# ── 5. Stochastic Oscillator ──────────────────────────────────────────────────
def compute_stochastic(prices: pd.Series,
                        k_period=14, d_period=3) -> dict:
    """
    Stochastic: Compares closing price to high-low range.
    %K > 80 = Overbought, %K < 20 = Oversold
    """
    if prices is None or len(prices) < k_period + d_period:
        return {}

    low_min  = prices.rolling(k_period).min()
    high_max = prices.rolling(k_period).max()
    k_line   = 100 * (prices - low_min) / (high_max - low_min + 1e-10)
    d_line   = k_line.rolling(d_period).mean()

    curr_k   = float(k_line.iloc[-1])
    curr_d   = float(d_line.iloc[-1])
    prev_k   = float(k_line.iloc[-2]) if len(k_line) > 1 else curr_k
    prev_d   = float(d_line.iloc[-2]) if len(d_line) > 1 else curr_d

    bull_cross = prev_k < prev_d and curr_k > curr_d and curr_k < 30
    bear_cross = prev_k > prev_d and curr_k < curr_d and curr_k > 70

    if bull_cross:
        signal = "BULLISH CROSSOVER"
        action = "Strong BUY — Stoch crossed up in oversold zone"
        color  = "green"
    elif bear_cross:
        signal = "BEARISH CROSSOVER"
        action = "Strong SELL — Stoch crossed down in overbought zone"
        color  = "red"
    elif curr_k > 80:
        signal = "OVERBOUGHT"
        action = "Overbought zone — reduce longs, watch for reversal"
        color  = "orange"
    elif curr_k < 20:
        signal = "OVERSOLD"
        action = "Oversold zone — look for long entries on confirmation"
        color  = "lightgreen"
    else:
        signal = "NEUTRAL"
        action = "Stochastic in neutral zone — wait for extremes"
        color  = "gray"

    return {
        "k":           round(curr_k,   1),
        "d":           round(curr_d,   1),
        "signal":      signal,
        "action":      action,
        "color":       color,
        "bull_cross":  bull_cross,
        "bear_cross":  bear_cross,
        "k_history":   [round(v,1) for v in k_line.tail(20).tolist()],
    }

# ── 6. ATR (Average True Range) ───────────────────────────────────────────────
def compute_atr(prices: pd.Series, period=14) -> dict:
    """
    ATR measures volatility. Used for:
    - Stop loss placement (1.5-2x ATR)
    - Position sizing
    - Breakout confirmation
    """
    if prices is None or len(prices) < period + 1:
        return {}

    high  = prices * 1.005  # approximation
    low   = prices * 0.995
    close = prices

    tr_list = []
    for i in range(1, len(prices)):
        hl  = float(high.iloc[i])  - float(low.iloc[i])
        hpc = abs(float(high.iloc[i])  - float(close.iloc[i-1]))
        lpc = abs(float(low.iloc[i])   - float(close.iloc[i-1]))
        tr_list.append(max(hl, hpc, lpc))

    tr_series = pd.Series(tr_list)
    atr       = float(tr_series.ewm(span=period).mean().iloc[-1])
    curr_price= float(prices.iloc[-1])
    atr_pct   = round(atr / curr_price * 100, 3)

    stop_1x  = round(curr_price - atr,       2)
    stop_1_5 = round(curr_price - atr * 1.5, 2)
    stop_2x  = round(curr_price - atr * 2,   2)

    # Target based on 1:2 risk-reward
    target_1_5 = round(curr_price + atr * 1.5, 2)
    target_2x  = round(curr_price + atr * 2,   2)
    target_3x  = round(curr_price + atr * 3,   2)

    return {
        "atr":          round(atr,      2),
        "atr_pct":      atr_pct,
        "current_price":round(curr_price, 2),
        "stop_loss": {
            "1x_atr":   stop_1x,
            "1.5x_atr": stop_1_5,
            "2x_atr":   stop_2x,
        },
        "targets": {
            "1.5x_atr": target_1_5,
            "2x_atr":   target_2x,
            "3x_atr":   target_3x,
        },
        "volatility": "HIGH"   if atr_pct > 2 else
                      "NORMAL" if atr_pct > 0.5 else "LOW",
    }

# ── 7. Supertrend ─────────────────────────────────────────────────────────────
def compute_supertrend(prices: pd.Series,
                        period=10, multiplier=3) -> dict:
    """
    Supertrend: Trend-following indicator using ATR.
    Price above supertrend = BUY
    Price below supertrend = SELL
    """
    if prices is None or len(prices) < period + 5:
        return {}

    high    = prices * 1.005
    low     = prices * 0.995
    hl2     = (high + low) / 2

    # ATR
    tr_list = []
    for i in range(1, len(prices)):
        tr_list.append(max(
            float(high.iloc[i]) - float(low.iloc[i]),
            abs(float(high.iloc[i]) - float(prices.iloc[i-1])),
            abs(float(low.iloc[i])  - float(prices.iloc[i-1]))
        ))
    tr = pd.Series(tr_list, index=prices.index[1:])
    atr = tr.ewm(span=period).mean()

    # Supertrend calculation
    basic_upper = hl2.iloc[1:] + (multiplier * atr)
    basic_lower = hl2.iloc[1:] - (multiplier * atr)

    curr_price  = float(prices.iloc[-1])
    curr_upper  = float(basic_upper.iloc[-1])
    curr_lower  = float(basic_lower.iloc[-1])

    # Trend direction
    if curr_price > curr_lower:
        trend      = "BULLISH"
        supertrend = curr_lower
        action     = "Price above Supertrend — hold/add longs"
        color      = "green"
    else:
        trend      = "BEARISH"
        supertrend = curr_upper
        action     = "Price below Supertrend — hold/add shorts"
        color      = "red"

    distance_pct = round(
        abs(curr_price - supertrend) / curr_price * 100, 2
    )

    return {
        "trend":         trend,
        "supertrend":    round(supertrend, 2),
        "current_price": round(curr_price,  2),
        "distance_pct":  distance_pct,
        "action":        action,
        "color":         color,
        "stop_loss":     round(supertrend, 2),
    }

# ── 8. Candlestick Pattern Scanner ────────────────────────────────────────────
def detect_candlestick_patterns(prices: pd.Series) -> list:
    """
    Detect major candlestick patterns from price data.
    """
    if prices is None or len(prices) < 5:
        return []

    patterns = []
    p   = prices.tolist()
    n   = len(p)

    # Approximate open as previous close
    for i in range(2, min(n, 10)):
        curr  = p[-(i)]
        prev  = p[-(i+1)]
        prev2 = p[-(i+2)] if i+2 <= n else prev

        body   = abs(curr - prev)
        range_ = max(curr, prev) - min(curr, prev)
        if range_ == 0:
            continue

        # Doji (body < 10% of range)
        if body / range_ < 0.1:
            patterns.append({
                "pattern": "DOJI",
                "signal":  "NEUTRAL",
                "desc":    "Indecision — possible trend reversal",
                "color":   "yellow",
                "bars_ago": i,
            })

        # Hammer (bullish reversal)
        lower_wick = min(curr, prev) - min(curr, prev) * 0.99
        if body / range_ < 0.3 and curr > prev:
            patterns.append({
                "pattern": "HAMMER",
                "signal":  "BULLISH",
                "desc":    "Bullish reversal pattern — buy on confirmation",
                "color":   "green",
                "bars_ago": i,
            })

        # Strong bullish candle
        if curr > prev and body / range_ > 0.7:
            patterns.append({
                "pattern": "STRONG BULL CANDLE",
                "signal":  "BULLISH",
                "desc":    "Strong buying pressure — momentum continuation",
                "color":   "green",
                "bars_ago": i,
            })

        # Strong bearish candle
        if curr < prev and body / range_ > 0.7:
            patterns.append({
                "pattern": "STRONG BEAR CANDLE",
                "signal":  "BEARISH",
                "desc":    "Strong selling pressure — momentum continuation",
                "color":   "red",
                "bars_ago": i,
            })

    return patterns[:5]

# ── 9. Overall Technical Score ────────────────────────────────────────────────
def compute_technical_score(macd, divergence,
                             bollinger, stochastic,
                             supertrend) -> dict:
    """
    Aggregate all signals into one technical score (0-100).
    >70 = Strong Buy, 50-70 = Buy, 30-50 = Neutral,
    <30 = Sell
    """
    score  = 50
    signals = []

    # MACD
    if macd:
        if macd.get('bullish_cross'):
            score += 15; signals.append("MACD Bullish Cross (+15)")
        elif macd.get('bearish_cross'):
            score -= 15; signals.append("MACD Bearish Cross (-15)")
        elif macd.get('above_zero'):
            score += 5;  signals.append("MACD Above Zero (+5)")
        else:
            score -= 5;  signals.append("MACD Below Zero (-5)")

    # Divergence
    if divergence and divergence.get('divergences'):
        div = divergence['divergences'][0]
        if 'BULLISH' in div['type']:
            score += 10; signals.append(f"{div['type']} (+10)")
        elif 'BEARISH' in div['type']:
            score -= 10; signals.append(f"{div['type']} (-10)")

    # Bollinger
    if bollinger:
        if bollinger.get('squeeze'):
            signals.append("BB Squeeze — breakout coming")
        if 'LOWER' in bollinger.get('signal', ''):
            score += 8;  signals.append("BB Lower Band (+8)")
        elif 'UPPER' in bollinger.get('signal', ''):
            score -= 8;  signals.append("BB Upper Band (-8)")

    # Stochastic
    if stochastic:
        if stochastic.get('bull_cross'):
            score += 12; signals.append("Stoch Bullish Cross (+12)")
        elif stochastic.get('bear_cross'):
            score -= 12; signals.append("Stoch Bearish Cross (-12)")
        elif stochastic.get('k', 50) < 20:
            score += 6;  signals.append("Stoch Oversold (+6)")
        elif stochastic.get('k', 50) > 80:
            score -= 6;  signals.append("Stoch Overbought (-6)")

    # Supertrend
    if supertrend:
        if supertrend.get('trend') == 'BULLISH':
            score += 10; signals.append("Supertrend Bullish (+10)")
        else:
            score -= 10; signals.append("Supertrend Bearish (-10)")

    score = max(0, min(100, score))

    if score >= 70:
        verdict = "STRONG BUY"
        color   = "green"
    elif score >= 55:
        verdict = "BUY"
        color   = "lightgreen"
    elif score >= 45:
        verdict = "NEUTRAL"
        color   = "yellow"
    elif score >= 30:
        verdict = "SELL"
        color   = "orange"
    else:
        verdict = "STRONG SELL"
        color   = "red"

    return {
        "score":   score,
        "verdict": verdict,
        "color":   color,
        "signals": signals,
    }

# ── Master Function ───────────────────────────────────────────────────────────
KEY_SYMBOLS = {
    "NIFTY 50":      "^NSEI",
    "Sensex":        "^BSESN",
    "S&P 500":       "^GSPC",
    "Gold":          "GC=F",
    "Crude Oil WTI": "CL=F",
    "Bitcoin":       "bitcoin",
    "USD/INR":       "INR=X",
    "US 10Y Yield":  "^TNX",
}

def get_full_technical_report(symbol: str) -> dict:
    """Full technical analysis for one symbol."""
    prices = get_price_series(symbol, days=60)
    if prices is None or len(prices) < 15:
        return {"error": "Not enough data"}

    macd       = compute_macd(prices)
    divergence = detect_divergence(prices)
    fibonacci  = compute_fibonacci(prices)
    bollinger  = compute_bollinger(prices)
    stochastic = compute_stochastic(prices)
    atr        = compute_atr(prices)
    supertrend = compute_supertrend(prices)
    patterns   = detect_candlestick_patterns(prices)
    score      = compute_technical_score(
        macd, divergence, bollinger, stochastic, supertrend
    )

    return {
        "symbol":     symbol,
        "macd":       macd,
        "divergence": divergence,
        "fibonacci":  fibonacci,
        "bollinger":  bollinger,
        "stochastic": stochastic,
        "atr":        atr,
        "supertrend": supertrend,
        "patterns":   patterns,
        "score":      score,
        "timestamp":  datetime.utcnow().isoformat(),
    }

def scan_all_assets(all_prices: list) -> list:
    """Scan all assets and return ranked by technical score."""
    results = []
    for p in all_prices:
        symbol = p.get('symbol')
        if not symbol:
            continue
        prices = get_price_series(symbol, days=60)
        if prices is None or len(prices) < 15:
            continue

        macd       = compute_macd(prices)
        bollinger  = compute_bollinger(prices)
        stochastic = compute_stochastic(prices)
        supertrend = compute_supertrend(prices)
        divergence = detect_divergence(prices)
        score      = compute_technical_score(
            macd, divergence, bollinger, stochastic, supertrend
        )

        results.append({
            "name":       p['asset_name'],
            "symbol":     symbol,
            "asset_type": p['asset_type'],
            "price":      p['price'],
            "score":      score['score'],
            "verdict":    score['verdict'],
            "color":      score['color'],
            "signals":    score['signals'],
            "macd_signal":      macd.get('signal_str', '--'),
            "bb_signal":        bollinger.get('signal', '--'),
            "stoch_signal":     stochastic.get('signal', '--'),
            "supertrend_trend": supertrend.get('trend', '--'),
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results


if __name__ == "__main__":
    print("📊 Running Technical Scanner...")
    prices = get_latest_prices()
    scan   = scan_all_assets(prices)
    print(f"✅ Scanned {len(scan)} assets\n")
    for a in scan[:5]:
        print(f"  {a['name']}: Score={a['score']} | {a['verdict']}")
        print(f"    Signals: {', '.join(a['signals'][:2])}")