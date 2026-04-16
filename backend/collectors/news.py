import feedparser
import requests
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import RSS_FEEDS, NEWS_API_KEY
from database import insert_news
from datetime import datetime

def collect_rss_news():
    """Fetch news from RSS feeds — no API key needed."""
    print("📰 Fetching RSS News Feeds...")
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries[:10]:  # latest 10 per source
                title     = entry.get("title", "").strip()
                link      = entry.get("link", "")
                published = entry.get("published", datetime.utcnow().isoformat())

                # Categorise by keywords in title
                category = categorise_news(title)

                if title:
                    insert_news(title, source, link, category, published)
                    count += 1

            print(f"  ✅ {source}: {count} articles fetched")

        except Exception as e:
            print(f"  ⚠️  Error fetching {source}: {e}")

def collect_newsapi(query="stock market OR indian economy OR RBI OR Fed Reserve", language="en"):
    """Fetch news from NewsAPI."""
    print("📰 Fetching NewsAPI articles...")
    if not NEWS_API_KEY:
        print("  ⚠️  NEWS_API_KEY not set, skipping.")
        return
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q":        query,
            "language": language,
            "sortBy":   "publishedAt",
            "pageSize": 20,
            "apiKey":   NEWS_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        articles = response.json().get("articles", [])

        for article in articles:
            title     = article.get("title", "").strip()
            source    = article.get("source", {}).get("name", "NewsAPI")
            url_link  = article.get("url", "")
            published = article.get("publishedAt", datetime.utcnow().isoformat())
            category  = categorise_news(title)

            if title and title != "[Removed]":
                insert_news(title, source, url_link, category, published)

        print(f"  ✅ NewsAPI: {len(articles)} articles fetched")

    except Exception as e:
        print(f"  ⚠️  NewsAPI error: {e}")

def categorise_news(title):
    """Simple keyword-based categorisation."""
    title_lower = title.lower()

    if any(w in title_lower for w in ["bitcoin", "crypto", "ethereum", "blockchain", "binance"]):
        return "crypto"
    elif any(w in title_lower for w in ["rbi", "rupee", "sensex", "nifty", "bse", "nse", "india"]):
        return "india"
    elif any(w in title_lower for w in ["fed", "federal reserve", "fomc", "interest rate", "treasury"]):
        return "fed"
    elif any(w in title_lower for w in ["oil", "crude", "gold", "silver", "commodity"]):
        return "commodity"
    elif any(w in title_lower for w in ["nasdaq", "s&p", "dow", "ftse", "dax", "nikkei"]):
        return "global"
    elif any(w in title_lower for w in ["forex", "dollar", "euro", "yen", "currency"]):
        return "forex"
    else:
        return "general"

def collect_all_news():
    """Master function — called by scheduler."""
    collect_rss_news()
    collect_newsapi()
    print("✅ News collection complete.\n")

if __name__ == "__main__":
    collect_all_news()