import numpy as np
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_connection, get_latest_prices
from datetime import datetime

# ── Helper: Get price series ──────────────────────────────────────────────────
def get_price_series(symbol, days=60):
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
    return df.set_index('timestamp')['price']

# ── 1. Z-Score Mean Reversion ─────────────────────────────────────────────────
def compute_zscore(prices: pd.Series, window=20) -> dict:
    """
    Z-Score = (Current Price - Rolling Mean) / Rolling Std
    >2  = Overbought (mean reversion SHORT signal)
    <-2 = Oversold   (mean reversion LONG signal)
    """
    if prices is None or len(prices) < window:
        return {}

    rolling_mean = prices.rolling(window).mean()
    rolling_std  = prices.rolling(window).std()
    zscore       = (prices - rolling_mean) / rolling_std
    current_z    = float(zscore.iloc[-1])

    if current_z > 2:
        signal    = "STRONG OVERBOUGHT"
        action    = "Mean Reversion SHORT — price statistically high"
        color     = "red"
        prob_mean_revert = min(95, 60 + abs(current_z) * 10)
    elif current_z > 1:
        signal    = "OVERBOUGHT"
        action    = "Caution — price above mean, consider reducing longs"
        color     = "orange"
        prob_mean_revert = min(75, 50 + abs(current_z) * 10)
    elif current_z < -2:
        signal    = "STRONG OVERSOLD"
        action    = "Mean Reversion LONG — price statistically low"
        color     = "green"
        prob_mean_revert = min(95, 60 + abs(current_z) * 10)
    elif current_z < -1:
        signal    = "OVERSOLD"
        action    = "Price below mean — potential bounce setup"
        color     = "lightgreen"
        prob_mean_revert = min(75, 50 + abs(current_z) * 10)
    else:
        signal    = "NEUTRAL"
        action    = "Price near mean — no statistical edge"
        color     = "gray"
        prob_mean_revert = 50

    return {
        "current_z":          round(current_z, 3),
        "signal":             signal,
        "action":             action,
        "color":              color,
        "prob_mean_revert":   round(prob_mean_revert, 1),
        "rolling_mean":       round(float(rolling_mean.iloc[-1]), 2),
        "rolling_std":        round(float(rolling_std.iloc[-1]),  2),
        "current_price":      round(float(prices.iloc[-1]),        2),
        "window":             window,
        "history":            [round(z, 3) for z in zscore.dropna().tail(30).tolist()],
    }

# ── 2. Momentum Factor ────────────────────────────────────────────────────────
def compute_momentum(prices: pd.Series) -> dict:
    """
    Rate of change momentum across multiple timeframes.
    Used in factor investing — buy strength, avoid weakness.
    """
    if prices is None or len(prices) < 5:
        return {}

    current = float(prices.iloc[-1])

    def roc(n):
        if len(prices) > n:
            past = float(prices.iloc[-n])
            return round((current - past) / past * 100, 2)
        return None

    mom_5d  = roc(5)
    mom_10d = roc(10)
    mom_20d = roc(20)
    mom_30d = roc(30)

    # Composite momentum score (-100 to +100)
    scores = [m for m in [mom_5d, mom_10d, mom_20d, mom_30d] if m is not None]
    composite = round(float(np.mean(scores)), 2) if scores else 0

    # Momentum rank signal
    if composite > 3:
        signal = "STRONG MOMENTUM UP"
        action = "Trend following LONG — strong upward momentum"
    elif composite > 1:
        signal = "MOMENTUM UP"
        action = "Positive momentum — hold/add longs on pullbacks"
    elif composite < -3:
        signal = "STRONG MOMENTUM DOWN"
        action = "Trend following SHORT — strong downward momentum"
    elif composite < -1:
        signal = "MOMENTUM DOWN"
        action = "Negative momentum — avoid longs, trail stops"
    else:
        signal = "NO MOMENTUM"
        action = "Choppy/sideways — wait for breakout"

    # Momentum acceleration (is it speeding up or slowing?)
    accel = None
    if mom_5d is not None and mom_20d is not None:
        accel = round(mom_5d - mom_20d, 2)

    return {
        "mom_5d":    mom_5d,
        "mom_10d":   mom_10d,
        "mom_20d":   mom_20d,
        "mom_30d":   mom_30d,
        "composite": composite,
        "signal":    signal,
        "action":    action,
        "acceleration": accel,
        "accel_signal": "ACCELERATING" if accel and accel > 0 else "DECELERATING" if accel and accel < 0 else "STABLE",
    }

# ── 3. Kelly Criterion ────────────────────────────────────────────────────────
def compute_kelly(prices: pd.Series, risk_free_rate=0.065) -> dict:
    """
    Kelly Criterion: Optimal position size based on historical win rate.
    f* = (bp - q) / b
    where b = avg win/avg loss ratio, p = win rate, q = 1-p
    """
    if prices is None or len(prices) < 10:
        return {}

    returns = prices.pct_change().dropna()
    if len(returns) < 5:
        return {}

    wins   = returns[returns > 0]
    losses = returns[returns < 0]

    if len(wins) == 0 or len(losses) == 0:
        return {}

    win_rate  = len(wins) / len(returns)
    loss_rate = 1 - win_rate
    avg_win   = float(wins.mean())
    avg_loss  = abs(float(losses.mean()))
    win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1

    # Kelly formula
    kelly_pct = (win_loss_ratio * win_rate - loss_rate) / win_loss_ratio
    kelly_pct = max(0, min(kelly_pct, 1))  # Cap between 0-100%

    # Half Kelly (safer — recommended for real trading)
    half_kelly = kelly_pct / 2

    # Sharpe Ratio approximation
    excess_returns = returns - (risk_free_rate / 252)
    sharpe = float(excess_returns.mean() / returns.std() * np.sqrt(252)) \
             if returns.std() > 0 else 0

    # Expected Value per trade
    ev = (win_rate * avg_win) - (loss_rate * avg_loss)

    # Risk interpretation
    if half_kelly > 0.15:
        risk_level = "HIGH EDGE"
        advice = f"Strong edge detected. Consider {round(half_kelly*100,1)}% of capital (Half Kelly)"
    elif half_kelly > 0.05:
        risk_level = "MODERATE EDGE"
        advice = f"Moderate edge. Size at {round(half_kelly*100,1)}% of capital"
    elif half_kelly > 0:
        risk_level = "WEAK EDGE"
        advice = f"Weak edge. Keep position small: {round(half_kelly*100,1)}% max"
    else:
        risk_level = "NO EDGE"
        advice = "Negative expectancy — avoid trading this asset currently"

    return {
        "win_rate":        round(win_rate * 100, 1),
        "loss_rate":       round(loss_rate * 100, 1),
        "avg_win_pct":     round(avg_win * 100, 3),
        "avg_loss_pct":    round(avg_loss * 100, 3),
        "win_loss_ratio":  round(win_loss_ratio, 3),
        "kelly_full":      round(kelly_pct * 100, 1),
        "kelly_half":      round(half_kelly * 100, 1),
        "sharpe_ratio":    round(sharpe, 3),
        "expected_value":  round(ev * 100, 4),
        "risk_level":      risk_level,
        "advice":          advice,
        "data_points":     len(returns),
    }

# ── 4. Drawdown Analysis ──────────────────────────────────────────────────────
def compute_drawdown(prices: pd.Series) -> dict:
    """
    Analyze maximum drawdown, recovery time, underwater periods.
    Critical for risk management.
    """
    if prices is None or len(prices) < 5:
        return {}

    # Running maximum (high water mark)
    rolling_max = prices.cummax()
    drawdown    = (prices - rolling_max) / rolling_max * 100

    max_dd      = float(drawdown.min())
    current_dd  = float(drawdown.iloc[-1])

    # Find max drawdown period
    end_idx   = drawdown.idxmin()
    start_idx = prices[:end_idx].idxmax()

    # Recovery analysis
    peak_price    = float(prices.max())
    current_price = float(prices.iloc[-1])
    recovery_needed = ((peak_price - current_price) / current_price * 100) \
                      if current_price < peak_price else 0

    # Drawdown duration
    underwater = drawdown[drawdown < 0]
    avg_dd_duration = len(underwater) if len(underwater) > 0 else 0

    # Risk rating
    if abs(max_dd) > 30:
        risk_rating = "VERY HIGH RISK"
        risk_color  = "red"
    elif abs(max_dd) > 20:
        risk_rating = "HIGH RISK"
        risk_color  = "orange"
    elif abs(max_dd) > 10:
        risk_rating = "MODERATE RISK"
        risk_color  = "yellow"
    else:
        risk_rating  = "LOW RISK"
        risk_color   = "green"

    # Stop loss suggestion (2x avg drawdown)
    avg_dd    = float(drawdown[drawdown < 0].mean()) if len(underwater) > 0 else -5
    stop_loss = round(current_price * (1 + avg_dd / 100 * 1.5), 2)

    return {
        "max_drawdown_pct":    round(max_dd, 2),
        "current_drawdown_pct":round(current_dd, 2),
        "peak_price":          round(peak_price, 2),
        "current_price":       round(current_price, 2),
        "recovery_needed_pct": round(recovery_needed, 2),
        "avg_drawdown_pct":    round(avg_dd, 2),
        "underwater_periods":  avg_dd_duration,
        "risk_rating":         risk_rating,
        "risk_color":          risk_color,
        "suggested_stop_loss": stop_loss,
        "drawdown_history":    [round(d, 2) for d in drawdown.tail(30).tolist()],
    }

# ── 5. Volatility Regime ──────────────────────────────────────────────────────
def compute_volatility_regime(prices: pd.Series) -> dict:
    """
    Detect if market is in Low/Normal/High volatility regime.
    Low vol  → Trend following strategies work
    High vol → Mean reversion strategies work
    """
    if prices is None or len(prices) < 20:
        return {}

    returns  = prices.pct_change().dropna()
    curr_vol = float(returns.tail(5).std()  * np.sqrt(252) * 100)
    hist_vol = float(returns.tail(20).std() * np.sqrt(252) * 100)
    long_vol = float(returns.std()          * np.sqrt(252) * 100)

    vol_ratio = curr_vol / hist_vol if hist_vol > 0 else 1

    if vol_ratio > 1.5:
        regime   = "HIGH VOLATILITY"
        strategy = "Mean Reversion — fade extremes, use wider stops"
        regime_color = "red"
    elif vol_ratio < 0.7:
        regime   = "LOW VOLATILITY"
        strategy = "Trend Following — breakout trades, tight stops"
        regime_color = "green"
    else:
        regime   = "NORMAL VOLATILITY"
        strategy = "Mixed — both trend and mean reversion valid"
        regime_color = "yellow"

    # VIX-like percentile
    all_vols  = [float(returns.iloc[i:i+5].std() * np.sqrt(252) * 100)
                 for i in range(0, len(returns)-5, 1)]
    vol_pctile = round(
        sum(1 for v in all_vols if v < curr_vol) / len(all_vols) * 100, 1
    ) if all_vols else 50

    return {
        "current_vol":   round(curr_vol, 2),
        "historical_vol":round(hist_vol, 2),
        "long_term_vol": round(long_vol, 2),
        "vol_ratio":     round(vol_ratio, 3),
        "vol_percentile":vol_pctile,
        "regime":        regime,
        "regime_color":  regime_color,
        "strategy":      strategy,
        "best_strategy": "MEAN_REVERSION" if vol_ratio > 1.5 else
                         "TREND_FOLLOWING" if vol_ratio < 0.7 else "MIXED",
    }

# ── 6. Multi-Timeframe RSI ────────────────────────────────────────────────────
def compute_multi_rsi(symbol: str) -> dict:
    """
    RSI across multiple timeframes.
    Best signal = when ALL timeframes agree.
    """
    results = {}
    configs = [
        ("short",  7,  14),
        ("medium", 20, 30),
        ("long",   45, 60),
    ]

    for label, window, days in configs:
        prices = get_price_series(symbol, days=days)
        if prices is None or len(prices) < window:
            continue

        returns = prices.pct_change().dropna()
        gains   = returns[returns > 0].mean() if len(returns[returns > 0]) > 0 else 0
        losses  = abs(returns[returns < 0].mean()) if len(returns[returns < 0]) > 0 else 0
        rs      = gains / losses if losses > 0 else 1
        rsi     = round(100 - (100 / (1 + rs)), 1)

        results[label] = {
            "rsi":     rsi,
            "signal":  "OVERBOUGHT" if rsi > 70 else
                       "OVERSOLD"   if rsi < 30 else "NEUTRAL",
            "window":  window,
        }

    # Overall confluence signal
    if len(results) >= 2:
        rsi_vals  = [v['rsi'] for v in results.values()]
        avg_rsi   = round(float(np.mean(rsi_vals)), 1)
        all_over  = all(r['signal'] == 'OVERBOUGHT' for r in results.values())
        all_under = all(r['signal'] == 'OVERSOLD'   for r in results.values())

        if all_over:
            confluence = "STRONG OVERBOUGHT — High probability reversal DOWN"
        elif all_under:
            confluence = "STRONG OVERSOLD — High probability reversal UP"
        else:
            confluence = "MIXED — Wait for timeframe alignment"
    else:
        avg_rsi    = 50
        confluence = "Insufficient data"

    return {
        "timeframes":  results,
        "avg_rsi":     avg_rsi,
        "confluence":  confluence,
    }

# ── 7. Pairs Correlation Scanner ─────────────────────────────────────────────
def find_diverged_pairs(all_prices: list, threshold=0.8) -> list:
    """
    Find pairs that are historically correlated but currently diverging.
    These are pairs trading opportunities.
    """
    conn   = get_connection()
    series = {}

    for p in all_prices:
        symbol = p.get('symbol')
        if not symbol:
            continue
        rows = conn.execute("""
            SELECT price FROM prices
            WHERE symbol = ?
            AND timestamp >= datetime('now', '-30 days')
            ORDER BY timestamp ASC
        """, (symbol,)).fetchall()

        if len(rows) >= 20:
            series[p['asset_name']] = pd.Series([r[0] for r in rows])

    conn.close()

    pairs    = []
    names    = list(series.keys())

    for i in range(len(names)):
        for j in range(i+1, len(names)):
            a, b   = names[i], names[j]
            sa, sb = series[a], series[b]

            min_len = min(len(sa), len(sb))
            if min_len < 20:
                continue

            sa_trim = sa.iloc[-min_len:].reset_index(drop=True)
            sb_trim = sb.iloc[-min_len:].reset_index(drop=True)

            # Historical correlation
            ret_a = sa_trim.pct_change().dropna()
            ret_b = sb_trim.pct_change().dropna()

            min_r = min(len(ret_a), len(ret_b))
            if min_r < 10:
                continue

            corr = float(ret_a.iloc[-min_r:].corr(ret_b.iloc[-min_r:]))
            if abs(corr) < threshold:
                continue

            # Current divergence (ratio z-score)
            ratio   = sa_trim / sb_trim
            z_score = float((ratio.iloc[-1] - ratio.mean()) / ratio.std()) \
                      if ratio.std() > 0 else 0

            if abs(z_score) > 1.5:
                pairs.append({
                    "asset_a":     a,
                    "asset_b":     b,
                    "correlation": round(corr, 3),
                    "z_score":     round(z_score, 3),
                    "signal":      f"LONG {a} / SHORT {b}" if z_score < 0
                                   else f"SHORT {a} / LONG {b}",
                    "strength":    "STRONG" if abs(z_score) > 2 else "MODERATE",
                })

    pairs.sort(key=lambda x: abs(x['z_score']), reverse=True)
    return pairs[:10]

# ── 8. Monte Carlo Simulation ─────────────────────────────────────────────────
def monte_carlo_simulation(prices: pd.Series,
                            days=30, simulations=500) -> dict:
    """
    Run Monte Carlo simulation to estimate future price range
    with probability distribution.
    """
    if prices is None or len(prices) < 10:
        return {}

    returns      = prices.pct_change().dropna()
    mu           = float(returns.mean())
    sigma        = float(returns.std())
    current_price= float(prices.iloc[-1])

    # Run simulations
    np.random.seed(42)
    sim_returns  = np.random.normal(mu, sigma, (simulations, days))
    sim_paths    = current_price * np.cumprod(1 + sim_returns, axis=1)
    final_prices = sim_paths[:, -1]

    # Statistics
    p10  = float(np.percentile(final_prices, 10))
    p25  = float(np.percentile(final_prices, 25))
    p50  = float(np.percentile(final_prices, 50))
    p75  = float(np.percentile(final_prices, 75))
    p90  = float(np.percentile(final_prices, 90))

    prob_up   = float(np.mean(final_prices > current_price) * 100)
    prob_down = 100 - prob_up

    # Expected return
    exp_return = round((p50 - current_price) / current_price * 100, 2)

    return {
        "current_price":   round(current_price, 2),
        "simulations":     simulations,
        "days":            days,
        "percentiles": {
            "p10": round(p10, 2),
            "p25": round(p25, 2),
            "p50": round(p50, 2),
            "p75": round(p75, 2),
            "p90": round(p90, 2),
        },
        "prob_up":         round(prob_up,   1),
        "prob_down":       round(prob_down, 1),
        "expected_return": exp_return,
        "best_case":       round(float(np.percentile(final_prices, 95)), 2),
        "worst_case":      round(float(np.percentile(final_prices, 5)),  2),
    }

# ── Master: Full Quant Report ─────────────────────────────────────────────────
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

def get_full_quant_report(all_prices: list) -> dict:
    """Master function — full quant analysis for all key assets."""
    results = {}

    for name, symbol in KEY_SYMBOLS.items():
        prices = get_price_series(symbol, days=60)
        if prices is None or len(prices) < 10:
            continue

        results[name] = {
            "symbol":     symbol,
            "zscore":     compute_zscore(prices),
            "momentum":   compute_momentum(prices),
            "kelly":      compute_kelly(prices),
            "drawdown":   compute_drawdown(prices),
            "vol_regime": compute_volatility_regime(prices),
            "multi_rsi":  compute_multi_rsi(symbol),
            "monte_carlo":monte_carlo_simulation(prices),
        }

    # Pairs trading
    pairs = find_diverged_pairs(all_prices)

    return {
        "assets":     results,
        "pairs":      pairs,
        "timestamp":  datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    print("🧮 Running Quant Signals Engine...")
    prices = get_latest_prices()
    report = get_full_quant_report(prices)
    print(f"✅ Computed for {len(report['assets'])} assets")
    for name, data in report['assets'].items():
        z  = data['zscore'].get('current_z', 'N/A')
        m  = data['momentum'].get('signal', 'N/A')
        kh = data['kelly'].get('kelly_half', 'N/A')
        print(f"  {name}: Z={z} | {m} | Kelly={kh}%")
    print(f"\n📊 Pairs Trading Opportunities: {len(report['pairs'])}")
    for p in report['pairs'][:3]:
        print(f"  {p['signal']} (Z={p['z_score']})")