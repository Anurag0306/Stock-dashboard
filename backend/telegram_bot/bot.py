import asyncio
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from telegram import Bot
from telegram.error import TelegramError
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from database import get_latest_prices, get_latest_news, get_economic_data
from analysis.impact_rules import analyse_current_impacts
from datetime import datetime
from analysis.ai_brief import generate_daily_brief

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# ── Core send function ────────────────────────────────────────────────────────

async def send_message(text: str):
    """Send a message to the configured Telegram chat."""
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML"
        )
        print(f"✅ Telegram message sent.")
    except TelegramError as e:
        print(f"❌ Telegram error: {e}")

# ── Alert: Price movement ─────────────────────────────────────────────────────

async def send_price_alert(asset_name, price, change_pct, asset_type):
    direction = "🔺" if change_pct > 0 else "🔻"
    emoji_map = {
        "crypto":       "₿",
        "global_index": "📊",
        "indian_index": "🇮🇳",
        "commodity":    "🛢️",
        "forex":        "💱",
        "bond":         "📈",
    }
    emoji = emoji_map.get(asset_type, "📌")
    msg = (
        f"{emoji} <b>PRICE ALERT</b>\n"
        f"Asset : <b>{asset_name}</b>\n"
        f"Price : <b>{price:,.4f}</b>\n"
        f"Change: {direction} <b>{change_pct:+.2f}%</b>\n"
        f"Time  : {datetime.now().strftime('%H:%M:%S IST')}"
    )
    await send_message(msg)

# ── Alert: Impact rule triggered ──────────────────────────────────────────────

async def send_impact_alert(insight: dict):
    severity_emoji = "🚨" if insight['severity'] == "high" else "⚠️"
    affects = ", ".join(insight['affects'])
    msg = (
        f"{severity_emoji} <b>MARKET IMPACT ALERT</b>\n\n"
        f"Trigger : <b>{insight['trigger']}</b> {insight['direction']} {insight['change']:+.2f}%\n"
        f"Affects : {affects}\n\n"
        f"{insight['insight']}"
    )
    await send_message(msg)

# ── Daily Morning Summary ─────────────────────────────────────────────────────

async def send_morning_summary():
    prices   = get_latest_prices()
    economic = get_economic_data()
    news     = get_latest_news(limit=5)
    insights = analyse_current_impacts(prices)

    # Group prices by type
    def get_by_type(asset_type):
        return [p for p in prices if p['asset_type'] == asset_type]

    def format_asset(p):
        chg = p.get('change_pct') or 0
        arr = "🔺" if chg > 0 else "🔻"
        return f"  {arr} {p['asset_name']}: {p['price']:,.2f} ({chg:+.2f}%)"

    # Build message
    lines = [
        f"🌅 <b>MORNING MARKET SUMMARY</b>",
        f"📅 {datetime.now().strftime('%A, %d %B %Y')}",
        "",
        "━━━ 🇮🇳 INDIAN MARKETS ━━━",
    ]
    for p in get_by_type("indian_index"):
        lines.append(format_asset(p))

    lines += ["", "━━━ 🌍 GLOBAL INDICES ━━━"]
    for p in get_by_type("global_index"):
        lines.append(format_asset(p))

    lines += ["", "━━━ 🛢️ COMMODITIES ━━━"]
    for p in get_by_type("commodity"):
        lines.append(format_asset(p))

    lines += ["", "━━━ 💱 FOREX ━━━"]
    for p in get_by_type("forex"):
        lines.append(format_asset(p))

    lines += ["", "━━━ ₿ CRYPTO ━━━"]
    for p in get_by_type("crypto"):
        lines.append(format_asset(p))

    lines += ["", "━━━ 📉 ECONOMIC DATA ━━━"]
    for e in economic:
        lines.append(f"  📌 {e['indicator']}: {e['value']} (as of {e.get('period','')})")

    if insights:
        lines += ["", "━━━ ⚠️ ACTIVE ALERTS ━━━"]
        for i in insights:
            lines.append(f"  {i['direction']} {i['trigger']}: {i['change']:+.2f}%")
            lines.append(f"  → {i['insight'][:100]}...")

    if news:
        lines += ["", "━━━ 📰 TOP NEWS ━━━"]
        for n in news[:5]:
            lines.append(f"  • {n['title'][:80]}")

    lines += ["", f"⏰ Updated: {datetime.now().strftime('%H:%M IST')}"]
    # AI Brief
    try:
        ai = generate_daily_brief()
        if ai['status'] == 'ok':
            lines += ["", "━━━ 🤖 AI BRIEF ━━━"]
            # First 300 chars of brief
            lines.append(ai['brief'][:300] + "...")
    except:
        pass

    await send_message("\n".join(lines))

# ── Weekly Summary ────────────────────────────────────────────────────────────

async def send_weekly_summary():
    prices = get_latest_prices()

    lines = [
        "📊 <b>WEEKLY MARKET WRAP</b>",
        f"📅 Week ending {datetime.now().strftime('%d %B %Y')}",
        "",
        "━━━ KEY MOVERS THIS WEEK ━━━",
    ]

    sorted_prices = sorted(
        [p for p in prices if p.get('change_pct') is not None],
        key=lambda x: abs(x['change_pct']),
        reverse=True
    )

    for p in sorted_prices[:10]:
        chg = p['change_pct']
        arr = "🔺" if chg > 0 else "🔻"
        lines.append(f"  {arr} {p['asset_name']}: {chg:+.2f}%")

    lines += ["", f"⏰ {datetime.now().strftime('%H:%M IST')}"]
    await send_message("\n".join(lines))

# ── Check & fire price alerts ─────────────────────────────────────────────────

async def check_and_send_alerts():
    """
    Only send alerts for major market impact events.
    NO routine price change alerts.
    """
    from analysis.impact_rules import analyse_current_impacts
    prices   = get_latest_prices()
    insights = analyse_current_impacts(prices)

    # Only fire if severity is HIGH (not medium)
    high_alerts = [i for i in insights if i.get('severity') == 'high']

    for insight in high_alerts:
        await send_impact_alert(insight)

# ── Test function ─────────────────────────────────────────────────────────────

async def send_test_message():
    await send_message(
        "🤖 <b>Financial Tracker Bot Online!</b>\n\n"
        "✅ Bot connected successfully\n"
        "✅ Database connected\n"
        "✅ Data collectors running\n\n"
        "You will receive:\n"
        "• 🚨 Real-time price alerts\n"
        "• ⚠️ Market impact insights\n"
        "• 🌅 Daily morning summary (8 AM IST)\n"
        "• 📊 Weekly wrap (Sunday 8 PM IST)\n\n"
        f"⏰ Started: {datetime.now().strftime('%d %b %Y %H:%M IST')}"
    )

if __name__ == "__main__":
    asyncio.run(send_test_message())