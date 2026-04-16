import pandas as pd
import numpy as np
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_connection, get_latest_prices
from datetime import datetime

def get_price_series(days=30):
    """Get price history for all assets as a DataFrame."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT asset_name, price, timestamp FROM prices
        WHERE timestamp >= datetime('now', ?)
        ORDER BY timestamp ASC
    """, (f'-{days} days',)).fetchall()
    conn.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(r) for r in rows])
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.floor('5min')
    pivot = df.pivot_table(index='timestamp', columns='asset_name', values='price', aggfunc='last')
    pivot = pivot.ffill().dropna(axis=1, thresh=int(len(pivot)*0.5))
    return pivot

def compute_correlation_matrix(days=30):
    """Compute correlation matrix for all tracked assets."""
    pivot = get_price_series(days)
    if pivot.empty or len(pivot) < 5:
        print("  ⚠️  Not enough data for correlation. Run scheduler first.")
        return {}

    returns = pivot.pct_change().dropna()
    corr    = returns.corr().round(4)
    return corr.to_dict()

def save_correlations(days=30):
    """Compute and save correlations to DB."""
    pivot = get_price_series(days)
    if pivot.empty or len(pivot) < 5:
        return

    returns = pivot.pct_change().dropna()
    corr    = returns.corr().round(4)
    conn    = get_connection()
    ts      = datetime.utcnow().isoformat()

    for asset_a in corr.columns:
        for asset_b in corr.columns:
            if asset_a >= asset_b:
                continue
            val = corr.loc[asset_a, asset_b]
            if pd.isna(val):
                continue
            conn.execute("""
                INSERT INTO correlations (asset_a, asset_b, correlation, period_days, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (asset_a, asset_b, float(val), days, ts))

    conn.commit()
    conn.close()
    print(f"✅ Correlations saved ({len(corr.columns)} assets, {days}d window)")

def get_top_correlations(asset_name, top_n=5, days=30):
    """Get the most correlated assets to a given asset."""
    corr_dict = compute_correlation_matrix(days)
    if not corr_dict or asset_name not in corr_dict:
        return []

    related = corr_dict[asset_name]
    sorted_corr = sorted(
        [(k, v) for k, v in related.items() if k != asset_name],
        key=lambda x: abs(x[1]),
        reverse=True
    )
    return sorted_corr[:top_n]

if __name__ == "__main__":
    print("📊 Computing correlation matrix...")
    matrix = compute_correlation_matrix(days=30)
    if matrix:
        assets = list(matrix.keys())
        print(f"✅ Matrix computed for {len(assets)} assets:")
        for a in assets:
            print(f"   {a}")
        save_correlations()
    else:
        print("⚠️  No data yet — run scheduler.py first to collect data.")