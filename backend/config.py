import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID     = os.getenv("TELEGRAM_CHAT_ID", "")

# ── External APIs ─────────────────────────────────────────────────────────────
NEWS_API_KEY         = os.getenv("NEWS_API_KEY", "")
FRED_API_KEY         = os.getenv("FRED_API_KEY", "")

# ── Alert Thresholds ──────────────────────────────────────────────────────────
PRICE_ALERT_THRESHOLD  = float(os.getenv("PRICE_ALERT_THRESHOLD", 2.0))
CRYPTO_ALERT_THRESHOLD = float(os.getenv("CRYPTO_ALERT_THRESHOLD", 5.0))
FOREX_ALERT_THRESHOLD  = float(os.getenv("FOREX_ALERT_THRESHOLD", 1.0))

# ── Scheduler ─────────────────────────────────────────────────────────────────
FETCH_INTERVAL_MINUTES = 5

# ── Assets to Track ───────────────────────────────────────────────────────────

GLOBAL_INDICES = {
    "S&P 500":    "^GSPC",
    "NASDAQ":     "^IXIC",
    "Dow Jones":  "^DJI",
    "FTSE 100":   "^FTSE",
    "DAX":        "^GDAXI",
    "Nikkei 225": "^N225",
}

INDIAN_INDICES = {
    "NIFTY 50":   "^NSEI",
    "Sensex":     "^BSESN",
    "NIFTY Bank": "^NSEBANK",
    "NIFTY IT":   "NIFTYIT.NS",
    "NIFTY Pharma": "^CNXPHARMA",
}

COMMODITIES = {
    "Crude Oil WTI": "CL=F",
    "Brent Crude":   "BZ=F",
    "Gold":          "GC=F",
    "Silver":        "SI=F",
    "Natural Gas":   "NG=F",
}

FOREX_PAIRS = {
    "USD/INR":   "INR=X",
    "EUR/USD":   "EURUSD=X",
    "GBP/USD":   "GBPUSD=X",
    "USD/JPY":   "JPY=X",
    "Dollar Index": "DX-Y.NYB",
}

BONDS = {
    "US 2Y Yield":  "^IRX",
    "US 10Y Yield": "^TNX",
    "US 30Y Yield": "^TYX",
}

CRYPTO = {
    "Bitcoin":  "bitcoin",
    "Ethereum": "ethereum",
    "BNB":      "binancecoin",
    "Solana":   "solana",
    "XRP":      "ripple",
}

# ── FRED Series IDs ───────────────────────────────────────────────────────────
FRED_SERIES = {
    "US CPI":           "CPIAUCSL",
    "US Unemployment":  "UNRATE",
    "Fed Funds Rate":   "FEDFUNDS",
    "US GDP":           "GDP",
    "US PPI":           "PPIACO",
    "Manufacturing PMI":"MANEMP",
}

# ── News RSS Feeds ────────────────────────────────────────────────────────────
RSS_FEEDS = {
    "Economic Times Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Moneycontrol":           "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "Business Standard":      "https://www.business-standard.com/rss/markets-106.rss",
    "CNBC Finance":           "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "Investing.com":          "https://www.investing.com/rss/news.rss",
}
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")