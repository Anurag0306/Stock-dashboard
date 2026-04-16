import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "financial_data.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_name  TEXT    NOT NULL,
            asset_type  TEXT    NOT NULL,
            symbol      TEXT    NOT NULL,
            price       REAL    NOT NULL,
            change_pct  REAL,
            volume      REAL,
            timestamp   TEXT    NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS economic_data (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator    TEXT NOT NULL,
            value        REAL NOT NULL,
            period       TEXT,
            timestamp    TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            source      TEXT,
            url         TEXT,
            category    TEXT,
            published   TEXT,
            timestamp   TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS correlations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_a     TEXT NOT NULL,
            asset_b     TEXT NOT NULL,
            correlation REAL NOT NULL,
            period_days INTEGER NOT NULL,
            timestamp   TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_name  TEXT NOT NULL,
            alert_type  TEXT NOT NULL,
            message     TEXT NOT NULL,
            sent        INTEGER DEFAULT 0,
            timestamp   TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialised at:", DB_PATH)


def insert_price(asset_name, asset_type, symbol, price, change_pct=None, volume=None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO prices (asset_name, asset_type, symbol, price, change_pct, volume, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (asset_name, asset_type, symbol, price, change_pct, volume, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_latest_prices(asset_type=None):
    conn = get_connection()
    if asset_type:
        rows = conn.execute("""
            SELECT * FROM prices WHERE asset_type = ?
            GROUP BY symbol HAVING MAX(timestamp)
            ORDER BY timestamp DESC
        """, (asset_type,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT p.* FROM prices p
            INNER JOIN (
                SELECT symbol, MAX(timestamp) as mt FROM prices GROUP BY symbol
            ) latest ON p.symbol = latest.symbol AND p.timestamp = latest.mt
            ORDER BY asset_type, asset_name
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_price_history(symbol, days=30):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM prices
        WHERE symbol = ?
        AND timestamp >= datetime('now', ?)
        ORDER BY timestamp ASC
    """, (symbol, f'-{days} days')).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def insert_news(title, source, url, category, published):
    conn = get_connection()
    conn.execute("""
        INSERT INTO news (title, source, url, category, published, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, source, url, category, published, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_latest_news(category=None, limit=50):
    conn = get_connection()
    if category:
        rows = conn.execute(
            "SELECT * FROM news WHERE category=? ORDER BY timestamp DESC LIMIT ?",
            (category, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM news ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def insert_alert(asset_name, alert_type, message):
    conn = get_connection()
    conn.execute("""
        INSERT INTO alerts (asset_name, alert_type, message, timestamp)
        VALUES (?, ?, ?, ?)
    """, (asset_name, alert_type, message, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_economic_data():
    conn = get_connection()
    rows = conn.execute("""
        SELECT e.* FROM economic_data e
        INNER JOIN (
            SELECT indicator, MAX(timestamp) as mt FROM economic_data GROUP BY indicator
        ) latest ON e.indicator = latest.indicator AND e.timestamp = latest.mt
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
def init_portfolio():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            name        TEXT    NOT NULL,
            quantity    REAL    NOT NULL,
            buy_price   REAL    NOT NULL,
            asset_type  TEXT    NOT NULL DEFAULT 'stock',
            added_on    TEXT    NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            total_value REAL    NOT NULL,
            total_pnl   REAL    NOT NULL,
            timestamp   TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_holding(symbol, name, quantity, buy_price, asset_type='stock'):
    conn = get_connection()
    conn.execute("""
        INSERT INTO portfolio (symbol, name, quantity, buy_price, asset_type, added_on)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (symbol, name, quantity, buy_price, asset_type, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_holdings():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM portfolio ORDER BY added_on DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_holding(holding_id):
    conn = get_connection()
    conn.execute("DELETE FROM portfolio WHERE id = ?", (holding_id,))
    conn.commit()
    conn.close()

def update_holding(holding_id, quantity, buy_price):
    conn = get_connection()
    conn.execute("""
        UPDATE portfolio SET quantity=?, buy_price=? WHERE id=?
    """, (quantity, buy_price, holding_id))
    conn.commit()
    conn.close()

def save_portfolio_snapshot(total_value, total_pnl):
    conn = get_connection()
    conn.execute("""
        INSERT INTO portfolio_history (total_value, total_pnl, timestamp)
        VALUES (?, ?, ?)
    """, (total_value, total_pnl, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_portfolio_history(days=30):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM portfolio_history
        WHERE timestamp >= datetime('now', ?)
        ORDER BY timestamp ASC
    """, (f'-{days} days',)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def init_watchlist():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol       TEXT    NOT NULL,
            name         TEXT    NOT NULL,
            asset_type   TEXT    NOT NULL,
            alert_above  REAL,
            alert_below  REAL,
            alert_pct    REAL,
            notes        TEXT,
            added_on     TEXT    NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol       TEXT    NOT NULL,
            name         TEXT    NOT NULL,
            alert_type   TEXT    NOT NULL,
            target_price REAL,
            actual_price REAL,
            message      TEXT    NOT NULL,
            triggered_at TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_to_watchlist(symbol, name, asset_type,
                     alert_above=None, alert_below=None,
                     alert_pct=None, notes=None):
    conn = get_connection()
    # Check if already exists
    existing = conn.execute(
        "SELECT id FROM watchlist WHERE symbol=?", (symbol,)
    ).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute("""
        INSERT INTO watchlist
          (symbol, name, asset_type, alert_above,
           alert_below, alert_pct, notes, added_on)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (symbol, name, asset_type, alert_above,
          alert_below, alert_pct, notes,
          datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return True

def get_watchlist():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM watchlist ORDER BY added_on DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_watchlist_alerts(wid, alert_above=None,
                             alert_below=None,
                             alert_pct=None, notes=None):
    conn = get_connection()
    conn.execute("""
        UPDATE watchlist
        SET alert_above=?, alert_below=?,
            alert_pct=?, notes=?
        WHERE id=?
    """, (alert_above, alert_below, alert_pct, notes, wid))
    conn.commit()
    conn.close()

def remove_from_watchlist(wid):
    conn = get_connection()
    conn.execute("DELETE FROM watchlist WHERE id=?", (wid,))
    conn.commit()
    conn.close()

def log_alert(symbol, name, alert_type,
              target_price, actual_price, message):
    conn = get_connection()
    conn.execute("""
        INSERT INTO alert_history
          (symbol, name, alert_type, target_price,
           actual_price, message, triggered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (symbol, name, alert_type, target_price,
          actual_price, message,
          datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_alert_history(limit=50):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM alert_history
        ORDER BY triggered_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]