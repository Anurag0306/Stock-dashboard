import asyncio, json, os, sys
from datetime import datetime
from contextlib import asynccontextmanager

sys.path.append(os.path.dirname(__file__))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import (
    init_db, get_latest_prices, get_price_history,
    get_latest_news, get_economic_data,
    add_holding, get_holdings, delete_holding,
    update_holding, save_portfolio_snapshot,
    get_portfolio_history, init_portfolio,
    add_to_watchlist, get_watchlist,
    update_watchlist_alerts, remove_from_watchlist,
    log_alert, get_alert_history, init_watchlist
)
from analysis.correlations import compute_correlation_matrix
from analysis.impact_rules import analyse_current_impacts, get_all_rules
from analysis.ai_brief import (
    generate_daily_brief, generate_impact_analysis,
    generate_sentiment_summary, generate_ai_answer
)
from analysis.probability import get_full_probability_report
from telegram_bot.bot import (
    check_and_send_alerts, send_morning_summary, send_weekly_summary
)
from analysis.quant_signals import (
    get_full_quant_report, compute_zscore,
    compute_kelly, monte_carlo_simulation,
    compute_momentum, compute_drawdown,
    compute_volatility_regime, find_diverged_pairs,
    get_price_series
)
from analysis.technical_scanner import (
    get_full_technical_report, scan_all_assets
)
# ── Pydantic Models ───────────────────────────────────────────────────────────
class HoldingInput(BaseModel):
    symbol:     str
    name:       str
    quantity:   float
    buy_price:  float
    asset_type: str = "stock"

class HoldingUpdate(BaseModel):
    quantity:  float
    buy_price: float

class WatchlistInput(BaseModel):
    symbol:      str
    name:        str
    asset_type:  str   = "stock"
    alert_above: float = None
    alert_below: float = None
    alert_pct:   float = None
    notes:       str   = None

class WatchlistUpdate(BaseModel):
    alert_above: float = None
    alert_below: float = None
    alert_pct:   float = None
    notes:       str   = None

# ── WebSocket Manager ─────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        msg = json.dumps(data)
        for ws in self.active.copy():
            try:
                await ws.send_text(msg)
            except:
                self.active.remove(ws)

manager = ConnectionManager()

# ── Background broadcaster ────────────────────────────────────────────────────
async def broadcast_loop():
    while True:
        try:
            prices = get_latest_prices()
            await manager.broadcast({
                "type":      "prices",
                "data":      prices,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"Broadcast error: {e}")
        await asyncio.sleep(30)

# ── Scheduler ─────────────────────────────────────────────────────────────────
def start_background_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval     import IntervalTrigger
    from apscheduler.triggers.cron         import CronTrigger
    from collectors.stocks   import collect_all_market_data
    from collectors.crypto   import collect_crypto
    from collectors.news     import collect_all_news
    from collectors.economic import collect_economic_indicators

    sched = BackgroundScheduler(timezone="Asia/Kolkata")

    def run_market():
        collect_all_market_data()
        collect_crypto()

    # ── Market jobs ───────────────────────────────────────────────────────────
    sched.add_job(run_market,
                  IntervalTrigger(minutes=5),
                  id="market_data")

    sched.add_job(collect_all_news,
                  IntervalTrigger(minutes=15),
                  id="news")

    sched.add_job(collect_economic_indicators,
                  CronTrigger(hour=8, minute=0),
                  id="economic")

    # ── Telegram jobs ─────────────────────────────────────────────────────────
    
    sched.add_job(
        lambda: asyncio.run(send_morning_summary()),
        CronTrigger(hour=8, minute=0, timezone="Asia/Kolkata"),
        id="morning_summary"
    )
    sched.add_job(
        lambda: asyncio.run(send_weekly_summary()),
        CronTrigger(day_of_week="sun", hour=20, minute=0,
                    timezone="Asia/Kolkata"),
        id="weekly_summary"
    )
# Smart alerts — only HIGH severity impacts
async def smart_alerts():
    try:
        from analysis.impact_rules import analyse_current_impacts
        prices   = get_latest_prices()
        insights = analyse_current_impacts(prices)
        high     = [i for i in insights if i.get('severity') == 'high']
        if high:
            for insight in high:
                await send_impact_alert(insight)
                print(f"🚨 Alert sent: {insight['trigger']}")
    except Exception as e:
        print(f"Smart alert error: {e}")

    sched.add_job(
    lambda: asyncio.run(smart_alerts()),
    IntervalTrigger(minutes=15),  # check every 15 min
    id="smart_alerts"
)

    # ── Watchlist alert job ───────────────────────────────────────────────────
    async def check_wl_alerts():
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                res  = await client.post(
                    "http://localhost:8000/api/watchlist/check-alerts"
                )
                data  = res.json()
                fired = data.get('fired', [])
                if fired:
                    from telegram_bot.bot import send_message
                    for msg in fired:
                        await send_message(msg)
        except Exception as e:
            print(f"Watchlist alert check error: {e}")

    # ── Start scheduler ───────────────────────────────────────────────────────
    sched.start()
    print("✅ Background scheduler started.")
    return sched

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_portfolio()
    init_watchlist()
    sched = start_background_scheduler()
    task  = asyncio.create_task(broadcast_loop())
    yield
    task.cancel()
    sched.shutdown()

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="FinTrack Pro API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Market Data ───────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "FinTrack Pro API running"}

@app.get("/api/prices")
def get_prices(asset_type: str = None):
    return {"data": get_latest_prices(asset_type)}

@app.get("/api/prices/history/{symbol}")
def get_history(symbol: str, days: int = 7):
    return {"data": get_price_history(symbol, days)}

@app.get("/api/news")
def get_news(category: str = None, limit: int = 50):
    return {"data": get_latest_news(category, limit)}

@app.get("/api/economic")
def get_economic():
    return {"data": get_economic_data()}

@app.get("/api/summary")
def get_summary():
    return {
        "prices":    get_latest_prices(),
        "news":      get_latest_news(limit=20),
        "economic":  get_economic_data(),
        "timestamp": datetime.utcnow().isoformat()
    }

# ── Correlation & Impact ──────────────────────────────────────────────────────
@app.get("/api/correlation")
def get_correlation(days: int = 30):
    try:
        import math
        matrix  = compute_correlation_matrix(days)
        cleaned = {}
        for a, row in matrix.items():
            cleaned[a] = {}
            for b, val in row.items():
                if isinstance(val, float) and \
                   (math.isnan(val) or math.isinf(val)):
                    cleaned[a][b] = 0.0
                else:
                    cleaned[a][b] = val
        return {"data": cleaned, "days": days}
    except Exception as e:
        return {"data": {}, "days": days, "error": str(e)}

@app.get("/api/impact")
def get_impact():
    prices   = get_latest_prices()
    insights = analyse_current_impacts(prices)
    return {
        "triggered": insights,
        "count":     len(insights),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/rules")
def get_rules():
    return {"data": get_all_rules()}

# ── Portfolio ─────────────────────────────────────────────────────────────────
@app.get("/api/portfolio/history")
def portfolio_history():
    return {"data": get_portfolio_history()}

@app.get("/api/portfolio")
def get_portfolio():
    import yfinance as yf
    holdings = get_holdings()
    if not holdings:
        return {"holdings": [], "summary": {}}

    total_invested = 0
    total_value    = 0
    results        = []

    for h in holdings:
        symbol = h['symbol']
        if '.' not in symbol and '-' not in symbol \
           and '=' not in symbol and '^' not in symbol:
            symbol = symbol + '.NS'

        live_price = None
        try:
            live_price = yf.Ticker(symbol).fast_info.last_price
            if not live_price or live_price == 0:
                live_price = None
        except:
            pass

        if not live_price:
            try:
                hist = yf.Ticker(symbol).history(period='2d')
                if not hist.empty:
                    live_price = float(hist['Close'].iloc[-1])
            except:
                pass

        if not live_price and symbol.endswith('.NS'):
            try:
                hist = yf.Ticker(
                    symbol.replace('.NS', '.BO')
                ).history(period='2d')
                if not hist.empty:
                    live_price = float(hist['Close'].iloc[-1])
            except:
                pass

        if not live_price or live_price == 0:
            live_price = h['buy_price']
            print(f"⚠️  No live price for {symbol}")
        else:
            print(f"✅ {symbol}: ₹{live_price}")

        invested = h['quantity'] * h['buy_price']
        value    = h['quantity'] * live_price
        pnl      = value - invested
        pnl_pct  = (pnl / invested * 100) if invested else 0

        total_invested += invested
        total_value    += value

        results.append({
            **h,
            "live_price": round(live_price, 2),
            "invested":   round(invested,   2),
            "value":      round(value,       2),
            "pnl":        round(pnl,         2),
            "pnl_pct":    round(pnl_pct,     2),
        })

    total_pnl     = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) \
                    if total_invested else 0
    save_portfolio_snapshot(
        round(total_value, 2), round(total_pnl, 2)
    )

    return {
        "holdings": results,
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_value":    round(total_value,    2),
            "total_pnl":      round(total_pnl,      2),
            "total_pnl_pct":  round(total_pnl_pct,  2),
        }
    }

@app.get("/api/stock-info/{symbol}")
def get_stock_info(symbol: str):
    import yfinance as yf
    try:
        info = yf.Ticker(symbol).info
        name = info.get('shortName') or \
               info.get('longName') or symbol
        name = name.split(' - ')[0]\
                   .split(' Closed')[0].strip()
        return {"symbol": symbol, "name": name}
    except:
        return {"symbol": symbol, "name": symbol}

@app.post("/api/portfolio")
def add_portfolio_holding(data: HoldingInput):
    add_holding(
        data.symbol, data.name,
        data.quantity, data.buy_price, data.asset_type
    )
    return {"status": "ok",
            "message": f"{data.name} added to portfolio"}

@app.delete("/api/portfolio/{holding_id}")
def remove_holding(holding_id: int):
    delete_holding(holding_id)
    return {"status": "ok"}

@app.put("/api/portfolio/{holding_id}")
def edit_holding(holding_id: int, data: HoldingUpdate):
    update_holding(holding_id, data.quantity, data.buy_price)
    return {"status": "ok"}

# ── AI ────────────────────────────────────────────────────────────────────────
@app.get("/api/ai/brief")
def get_ai_brief():
    return generate_daily_brief()

@app.get("/api/ai/sentiment")
def get_ai_sentiment():
    return generate_sentiment_summary()

@app.post("/api/ai/impact")
def get_ai_impact(data: dict):
    event = data.get("event", "")
    if not event:
        return {"error": "No event provided"}
    return generate_impact_analysis(event)

@app.post("/api/ai/ask")
def ask_ai(data: dict):
    question = data.get("question", "")
    if not question:
        return {"error": "No question provided"}
    return generate_ai_answer(question)

# ── Probability ───────────────────────────────────────────────────────────────
@app.get("/api/probability")
def get_probability():
    try:
        prices = get_latest_prices()
        return get_full_probability_report(prices)
    except Exception as e:
        return {"error": str(e), "assets": {}}

# ── Screener ──────────────────────────────────────────────────────────────────
@app.get("/api/screener")
def get_screener():
    import pandas as pd
    from database import get_connection

    prices  = get_latest_prices()
    results = []

    for p in prices:
        symbol = p.get('symbol')
        if not symbol:
            continue

        conn = get_connection()
        rows = conn.execute("""
            SELECT price FROM prices
            WHERE symbol = ?
            AND timestamp >= datetime('now', '-30 days')
            ORDER BY timestamp ASC
        """, (symbol,)).fetchall()
        conn.close()

        price_list = [r[0] for r in rows]
        chg        = p.get('change_pct') or 0
        rsi        = 50
        trend      = "NEUTRAL"
        vol        = 0
        ma5        = p['price']
        ma20       = p['price']

        if len(price_list) >= 5:
            px      = pd.Series(price_list)
            returns = px.pct_change().dropna()

            if len(returns) >= 3:
                gains  = returns[returns > 0].mean() or 0
                losses = abs(returns[returns < 0].mean()) \
                         if len(returns[returns < 0]) > 0 else 0
                rs     = gains / losses if losses != 0 else 1
                rsi    = round(100 - (100 / (1 + rs)), 1)
                vol    = round(float(returns.std()) * 100, 2)

            ma5  = round(float(px.tail(5).mean()), 2)
            ma20 = round(float(px.tail(
                min(20, len(px))).mean()), 2)

            cur = p['price']
            if cur > ma5 > ma20:   trend = "STRONG BULL"
            elif cur > ma20:        trend = "BULLISH"
            elif cur < ma5 < ma20: trend = "STRONG BEAR"
            elif cur < ma20:        trend = "BEARISH"
            else:                   trend = "NEUTRAL"

        if chg > 2 and rsi < 70:    signal = "BUY"
        elif chg > 0.5:             signal = "WATCH"
        elif chg < -2 and rsi > 30: signal = "SELL"
        elif chg < -0.5:            signal = "CAUTION"
        else:                       signal = "HOLD"

        results.append({
            "name":       p['asset_name'],
            "symbol":     symbol,
            "asset_type": p['asset_type'],
            "price":      p['price'],
            "change_pct": round(chg, 2),
            "rsi":        rsi,
            "trend":      trend,
            "signal":     signal,
            "volatility": vol,
            "ma5":        ma5,
            "ma20":       ma20,
            "volume":     p.get('volume') or 0,
        })

    results.sort(
        key=lambda x: abs(x['change_pct']), reverse=True
    )
    return {"data": results, "count": len(results)}

# ── Watchlist ─────────────────────────────────────────────────────────────────

# ⚠️ /alerts MUST come BEFORE /{wid} to avoid conflict
@app.get("/api/watchlist/alerts")
def get_alerts():
    return {"data": get_alert_history()}

@app.post("/api/watchlist/check-alerts")
def check_watchlist_alerts():
    import yfinance as yf
    items = get_watchlist()
    fired = []

    for item in items:
        symbol = item['symbol']
        try:
            live_price = \
                yf.Ticker(symbol).fast_info.last_price or 0
        except:
            live_price = 0

        if not live_price:
            continue

        if item['alert_above'] and \
           live_price >= item['alert_above']:
            msg = (
                f"🔺 PRICE ALERT: {item['name']} hit "
                f"₹{live_price:,.2f} — above target "
                f"₹{item['alert_above']:,.2f}"
            )
            log_alert(symbol, item['name'], "ABOVE",
                      item['alert_above'], live_price, msg)
            fired.append(msg)

        if item['alert_below'] and \
           live_price <= item['alert_below']:
            msg = (
                f"🔻 PRICE ALERT: {item['name']} hit "
                f"₹{live_price:,.2f} — below target "
                f"₹{item['alert_below']:,.2f}"
            )
            log_alert(symbol, item['name'], "BELOW",
                      item['alert_below'], live_price, msg)
            fired.append(msg)

    return {"fired": fired, "count": len(fired)}

@app.get("/api/watchlist")
def get_watchlist_with_prices():
    import yfinance as yf
    items   = get_watchlist()
    results = []

    for item in items:
        symbol = item['symbol']
        if '.' not in symbol and '-' not in symbol \
           and '=' not in symbol and '^' not in symbol:
            symbol = symbol + '.NS'

        live_price = None
        try:
            live_price = yf.Ticker(symbol).fast_info.last_price
        except:
            pass

        if not live_price:
            try:
                hist = yf.Ticker(symbol).history(period='2d')
                if not hist.empty:
                    live_price = float(hist['Close'].iloc[-1])
            except:
                pass

        live_price = live_price or 0

        alerts_triggered = []
        if item['alert_above'] and \
           live_price >= item['alert_above']:
            alerts_triggered.append({
                "type":    "ABOVE",
                "target":  item['alert_above'],
                "current": live_price
            })
        if item['alert_below'] and \
           live_price <= item['alert_below']:
            alerts_triggered.append({
                "type":    "BELOW",
                "target":  item['alert_below'],
                "current": live_price
            })

        dist_above = None
        dist_below = None
        if item['alert_above'] and live_price:
            dist_above = round(
                (item['alert_above'] - live_price)
                / live_price * 100, 2
            )
        if item['alert_below'] and live_price:
            dist_below = round(
                (live_price - item['alert_below'])
                / live_price * 100, 2
            )

        results.append({
            **item,
            "live_price":       round(live_price, 2),
            "alerts_triggered": alerts_triggered,
            "dist_above_pct":   dist_above,
            "dist_below_pct":   dist_below,
        })

    return {"data": results}

@app.post("/api/watchlist")
def add_watchlist_item(data: WatchlistInput):
    added = add_to_watchlist(
        data.symbol, data.name, data.asset_type,
        data.alert_above, data.alert_below,
        data.alert_pct, data.notes
    )
    if not added:
        return {"status": "exists",
                "message": f"{data.name} already in watchlist"}
    return {"status": "ok",
            "message": f"{data.name} added to watchlist"}

@app.put("/api/watchlist/{wid}")
def update_watchlist_item(wid: int, data: WatchlistUpdate):
    update_watchlist_alerts(
        wid, data.alert_above,
        data.alert_below, data.alert_pct, data.notes
    )
    return {"status": "ok"}

@app.delete("/api/watchlist/{wid}")
def delete_watchlist_item(wid: int):
    remove_from_watchlist(wid)
    return {"status": "ok"}
# ── Quant Signals ─────────────────────────────────────────────────────────────

@app.get("/api/quant")
def get_quant_report():
    """Full quantitative analysis for all key assets."""
    try:
        prices = get_latest_prices()
        return get_full_quant_report(prices)
    except Exception as e:
        return {"error": str(e), "assets": {}}

@app.get("/api/quant/{symbol}")
def get_quant_single(symbol: str):
    """Deep quant analysis for a single symbol."""
    try:
        prices = get_price_series(symbol, days=60)
        if prices is None or len(prices) < 5:
            return {"error": "Not enough data for this symbol"}
        return {
            "symbol":     symbol,
            "zscore":     compute_zscore(prices),
            "momentum":   compute_momentum(prices),
            "kelly":      compute_kelly(prices),
            "drawdown":   compute_drawdown(prices),
            "vol_regime": compute_volatility_regime(prices),
            "monte_carlo":monte_carlo_simulation(prices),
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/quant/monte-carlo")
def run_monte_carlo(data: dict):
    """Run Monte Carlo for any symbol."""
    symbol = data.get("symbol")
    days   = data.get("days", 30)
    sims   = data.get("simulations", 500)
    try:
        prices = get_price_series(symbol, days=60)
        if prices is None:
            return {"error": "No data"}
        return monte_carlo_simulation(prices, days=days,
                                      simulations=sims)
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/quant/pairs/scan")
def scan_pairs():
    """Find pairs trading opportunities."""
    try:
        prices = get_latest_prices()
        pairs  = find_diverged_pairs(prices)
        return {"pairs": pairs, "count": len(pairs)}
    except Exception as e:
        return {"pairs": [], "error": str(e)}
# ── Technical Scanner ─────────────────────────────────────────────────────────
@app.get("/api/technical/scan")
def technical_scan():
    """Scan all assets for technical signals."""
    try:
        prices  = get_latest_prices()
        results = scan_all_assets(prices)
        return {"data": results, "count": len(results)}
    except Exception as e:
        return {"data": [], "error": str(e)}

@app.get("/api/technical/{symbol}")
def technical_analysis(symbol: str):
    """Deep technical analysis for one symbol."""
    try:
        return get_full_technical_report(symbol)
    except Exception as e:
        return {"error": str(e)}
# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        prices = get_latest_prices()
        await ws.send_text(json.dumps({
            "type":      "prices",
            "data":      prices,
            "timestamp": datetime.utcnow().isoformat()
        }))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)

# ── Serve Frontend ────────────────────────────────────────────────────────────
frontend_path = os.path.join(
    os.path.dirname(__file__), "..", "frontend"
)
if os.path.exists(frontend_path):
    app.mount(
        "/",
        StaticFiles(directory=frontend_path, html=True),
        name="frontend"
    )