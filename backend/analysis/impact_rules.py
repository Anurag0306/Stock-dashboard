"""
Predefined market impact rules based on known financial relationships.
These fire when thresholds are breached to generate actionable insights.
"""

IMPACT_RULES = [
    {
        "id":       "oil_rupee",
        "trigger":  "Crude Oil WTI",
        "affects":  ["USD/INR", "NIFTY 50", "Sensex"],
        "direction": "positive",   # oil up → rupee weakens (USD/INR up)
        "threshold": 2.0,
        "insight":  (
            "🛢️ Crude oil spike detected. "
            "Impact: Indian rupee likely to weaken (higher import costs), "
            "inflation pressure on RBI, NIFTY energy sector may rally, "
            "airline & paint stocks under pressure."
        )
    },
    {
        "id":       "us10y_fii",
        "trigger":  "US 10Y Yield",
        "affects":  ["NIFTY 50", "Sensex", "USD/INR"],
        "direction": "negative",   # yields up → FII outflows from India
        "threshold": 0.1,
        "insight":  (
            "📈 US 10Y yield rising. "
            "Impact: FII outflows from Indian equities likely, "
            "rupee under pressure, NIFTY financials may face selling. "
            "Watch RBI response."
        )
    },
    {
        "id":       "dxy_emerging",
        "trigger":  "Dollar Index",
        "affects":  ["USD/INR", "Gold", "NIFTY 50"],
        "direction": "negative",   # DXY up → gold down, EM equities down
        "threshold": 1.0,
        "insight":  (
            "💵 Dollar Index strengthening. "
            "Impact: Commodity prices under pressure, "
            "emerging market currencies including rupee likely to weaken, "
            "Indian IT sector (USD revenue) may benefit."
        )
    },
    {
        "id":       "gold_risk",
        "trigger":  "Gold",
        "affects":  ["S&P 500", "NIFTY 50"],
        "direction": "negative",   # gold up = risk-off
        "threshold": 1.5,
        "insight":  (
            "🥇 Gold surging — risk-off signal. "
            "Impact: Global equities may face selling pressure, "
            "investors moving to safe havens. "
            "Watch VIX and FII flows into India."
        )
    },
    {
        "id":       "sp500_sensex",
        "trigger":  "S&P 500",
        "affects":  ["NIFTY 50", "Sensex"],
        "direction": "positive",   # SP500 down → India opens lower
        "threshold": 1.5,
        "insight":  (
            "📉 S&P 500 significant move detected. "
            "Impact: Indian markets likely to follow direction at open, "
            "FPI sentiment affected, "
            "check overnight US futures for next-day NIFTY gap."
        )
    },
    {
        "id":       "btc_risk",
        "trigger":  "Bitcoin",
        "affects":  ["Ethereum", "S&P 500"],
        "direction": "positive",
        "threshold": 5.0,
        "insight":  (
            "₿ Bitcoin major move detected. "
            "Impact: Altcoins likely to follow, "
            "crypto-correlated tech stocks may react, "
            "watch for risk appetite signal in broader markets."
        )
    },
    {
        "id":       "eurusd_dxy",
        "trigger":  "EUR/USD",
        "affects":  ["Dollar Index", "Gold", "USD/INR"],
        "direction": "negative",
        "threshold": 0.5,
        "insight":  (
            "💶 EUR/USD major move. "
            "Impact: Dollar Index inversely affected, "
            "commodity prices and rupee will react, "
            "watch ECB policy signals."
        )
    },
]

def analyse_current_impacts(latest_prices: list) -> list:
    """
    Compare latest prices against rules and return triggered insights.
    latest_prices: list of price dicts from get_latest_prices()
    """
    price_map = {p['asset_name']: p for p in latest_prices}
    triggered = []

    for rule in IMPACT_RULES:
        trigger_asset = rule['trigger']
        if trigger_asset not in price_map:
            continue

        asset      = price_map[trigger_asset]
        change_pct = asset.get('change_pct', 0) or 0
        threshold  = rule['threshold']

        if abs(change_pct) >= threshold:
            direction = "🔺 UP" if change_pct > 0 else "🔻 DOWN"
            triggered.append({
                "rule_id":   rule['id'],
                "trigger":   trigger_asset,
                "change":    round(change_pct, 2),
                "direction": direction,
                "affects":   rule['affects'],
                "insight":   rule['insight'],
                "severity":  "high" if abs(change_pct) >= threshold * 2 else "medium"
            })

    return triggered

def get_all_rules():
    return IMPACT_RULES