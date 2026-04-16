import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from groq import Groq
from config import GROQ_API_KEY
from database import get_latest_prices, get_latest_news, get_economic_data
from analysis.impact_rules import analyse_current_impacts
from datetime import datetime

client = Groq(api_key=GROQ_API_KEY)

def build_market_context() -> str:
    """Build a concise market context string for the AI."""
    prices   = get_latest_prices()
    news     = get_latest_news(limit=10)
    economic = get_economic_data()
    impacts  = analyse_current_impacts(prices)

    # Format prices
    price_map = {p['asset_name']: p for p in prices}

    def fmt(name):
        p = price_map.get(name)
        if not p: return f"{name}: N/A"
        c = p.get('change_pct') or 0
        return f"{name}: {p['price']:,.2f} ({c:+.2f}%)"

    sections = []

    # Indian Markets
    sections.append("=== INDIAN MARKETS ===")
    for name in ['NIFTY 50', 'Sensex', 'NIFTY Bank']:
        sections.append(fmt(name))

    # Global Markets
    sections.append("\n=== GLOBAL MARKETS ===")
    for name in ['S&P 500', 'NASDAQ', 'Dow Jones', 'Nikkei 225']:
        sections.append(fmt(name))

    # Commodities & Forex
    sections.append("\n=== COMMODITIES & FOREX ===")
    for name in ['Crude Oil WTI', 'Gold', 'USD/INR', 'Dollar Index']:
        sections.append(fmt(name))

    # Crypto
    sections.append("\n=== CRYPTO ===")
    for name in ['Bitcoin', 'Ethereum']:
        sections.append(fmt(name))

    # Economic Data
    sections.append("\n=== ECONOMIC INDICATORS ===")
    for e in economic[:4]:
        sections.append(f"{e['indicator']}: {e['value']} (as of {e.get('period','')})")

    # Active Impacts
    if impacts:
        sections.append("\n=== ACTIVE MARKET ALERTS ===")
        for i in impacts:
            sections.append(f"{i['trigger']}: {i['change']:+.2f}% — {i['insight'][:80]}")

    # Top News
    if news:
        sections.append("\n=== LATEST NEWS HEADLINES ===")
        for n in news[:6]:
            sections.append(f"• {n['title'][:100]}")

    return "\n".join(sections)


def generate_daily_brief() -> dict:
    """Generate AI market brief using Groq (free)."""
    try:
        context   = build_market_context()
        today     = datetime.now().strftime("%A, %d %B %Y")
        ist_time  = datetime.now().strftime("%H:%M IST")

        prompt = f"""You are a professional financial analyst writing a concise morning market brief for an Indian investor.

Today is {today}, {ist_time}.

Here is the current market data:
{context}

Write a professional morning market brief with these sections:
1. **Market Overview** (2-3 sentences on overall sentiment)
2. **Indian Markets** (NIFTY/Sensex outlook, key levels to watch)
3. **Global Cues** (How US/Asian markets affect India today)
4. **Key Risks** (2-3 bullet points of risks to watch)
5. **Opportunities** (1-2 sectors or assets looking interesting)
6. **One-Line Summary** (single sentence market call for the day)

Keep it concise, professional, and actionable. Focus on Indian market perspective.
Do not use asterisks for bold — use plain text with clear section headers."""

        response = client.chat.completions.create(
            model    = "llama-3.3-70b-versatile",
            messages = [{"role": "user", "content": prompt}],
            max_tokens  = 800,
            temperature = 0.7,
        )

        brief_text = response.choices[0].message.content
        tokens     = response.usage.total_tokens

        return {
            "brief":     brief_text,
            "generated": datetime.now().isoformat(),
            "model":     "llama-3.3-70b-versatile",
            "tokens":    tokens,
            "status":    "ok"
        }

    except Exception as e:
        print(f"❌ AI Brief error: {e}")
        return {
            "brief":     f"AI Brief temporarily unavailable: {str(e)}",
            "generated": datetime.now().isoformat(),
            "status":    "error"
        }


def generate_impact_analysis(event: str) -> dict:
    """Generate AI analysis for a specific market event."""
    try:
        prices  = get_latest_prices()
        context = build_market_context()

        prompt = f"""You are a financial analyst specializing in Indian markets.

Current Market Data:
{context}

Event to analyze: {event}

Provide a brief impact analysis (max 150 words) covering:
1. Immediate impact on Indian markets (NIFTY, Sensex, Rupee)
2. Sectors most affected
3. Short-term outlook (1-2 weeks)

Be specific, concise, and actionable."""

        response = client.chat.completions.create(
            model    = "llama-3.3-70b-versatile",
            messages = [{"role": "user", "content": prompt}],
            max_tokens  = 300,
            temperature = 0.5,
        )

        return {
            "event":    event,
            "analysis": response.choices[0].message.content,
            "status":   "ok"
        }

    except Exception as e:
        return {"event": event, "analysis": str(e), "status": "error"}


def generate_sentiment_summary() -> dict:
    """Generate detailed AI sentiment with probabilities."""
    try:
        news     = get_latest_news(limit=20)
        prices   = get_latest_prices()
        economic = get_economic_data()

        if not news:
            return {"summary": "No news available.", "status": "ok"}

        headlines   = "\n".join([f"• {n['title']}" for n in news[:20]])
        price_map   = {p['asset_name']: p for p in prices}

        # Build quick market snapshot
        nifty  = price_map.get('NIFTY 50',  {})
        sensex = price_map.get('Sensex',    {})
        gold   = price_map.get('Gold',      {})
        oil    = price_map.get('Crude Oil WTI', {})
        usdinr = price_map.get('USD/INR',   {})

        market_snap = f"""
NIFTY 50:  {nifty.get('price','N/A')} ({nifty.get('change_pct',0):+.2f}%)
Sensex:    {sensex.get('price','N/A')} ({sensex.get('change_pct',0):+.2f}%)
Gold:      {gold.get('price','N/A')} ({gold.get('change_pct',0):+.2f}%)
Crude Oil: {oil.get('price','N/A')} ({oil.get('change_pct',0):+.2f}%)
USD/INR:   {usdinr.get('price','N/A')} ({usdinr.get('change_pct',0):+.2f}%)
"""

        prompt = f"""You are a senior financial analyst at a top Indian investment bank.

CURRENT MARKET DATA:
{market_snap}

LATEST NEWS HEADLINES:
{headlines}

Provide a detailed sentiment analysis report with the following sections:

1. OVERALL SENTIMENT SCORE
Give a sentiment score from 0-100 (0=Extreme Fear, 50=Neutral, 100=Extreme Greed)
Format: "Sentiment Score: XX/100 — [Label]"

2. MARKET PROBABILITY MATRIX
Estimate probability of each scenario for NEXT 5 TRADING DAYS:
- NIFTY Bullish (>1% gain): XX%
- NIFTY Bearish (>1% fall): XX%
- NIFTY Sideways (±1%): XX%
- Rupee Appreciation vs USD: XX%
- Gold Rally (>1%): XX%

3. POSITIVE CATALYSTS (top 3)
List with impact rating HIGH/MEDIUM/LOW

4. NEGATIVE RISKS (top 3)
List with probability % and potential NIFTY impact in points

5. SECTOR SENTIMENT
Rate each sector: BULLISH / NEUTRAL / BEARISH
- IT Sector:
- Banking Sector:
- Energy Sector:
- FMCG Sector:
- Auto Sector:

6. KEY LEVELS TO WATCH
- NIFTY Support:
- NIFTY Resistance:
- USD/INR key level:

7. ANALYST VERDICT (2 sentences max)

Keep analysis data-driven and specific to Indian markets.
Do not use asterisks for formatting."""

        response = client.chat.completions.create(
            model       = "llama-3.3-70b-versatile",
            messages    = [{"role": "user", "content": prompt}],
            max_tokens  = 700,
            temperature = 0.4,
        )

        return {
            "summary": response.choices[0].message.content,
            "status":  "ok",
            "tokens":  response.usage.total_tokens
        }

    except Exception as e:
        return {"summary": str(e), "status": "error"}
def generate_ai_answer(question: str) -> dict:
    """Answer any market question using AI."""
    try:
        context = build_market_context()
        prompt  = f"""You are a professional financial advisor specializing in Indian markets.

Current Market Data:
{context}

User Question: {question}

Provide a clear, concise, and professional answer in 100-150 words.
Focus on Indian market perspective where relevant.
Be specific with numbers and levels when possible.
Do not use asterisks for formatting."""

        response = client.chat.completions.create(
            model       = "llama-3.3-70b-versatile",
            messages    = [{"role": "user", "content": prompt}],
            max_tokens  = 250,
            temperature = 0.5,
        )
        return {
            "answer": response.choices[0].message.content,
            "status": "ok"
        }
    except Exception as e:
        return {"answer": str(e), "status": "error"}

if __name__ == "__main__":
    print("🤖 Generating AI Daily Brief...")
    result = generate_daily_brief()
    print(result['brief'])