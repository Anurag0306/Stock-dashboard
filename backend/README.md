# 📈 Financial Tracker

A live financial asset tracking and analysis system.

## What it tracks
- 🇮🇳 Indian Markets: NIFTY 50, Sensex, NIFTY Bank, NIFTY IT, NIFTY Pharma
- 🌍 Global Indices: S&P 500, NASDAQ, Dow Jones, FTSE, DAX, Nikkei
- 🛢️ Commodities: Crude Oil, Gold, Silver, Natural Gas
- 💱 Forex: USD/INR, EUR/USD, GBP/USD, USD/JPY, Dollar Index
- ₿ Crypto: Bitcoin, Ethereum, BNB, Solana, XRP
- 📉 Economic: Fed Rate, US CPI, GDP, Unemployment, PPI
- 📰 News: Economic Times, Moneycontrol, CNBC, Investing.com, NewsAPI

## How to start
1. Double-click `start.bat`
2. Dashboard opens automatically in browser

## Manual start
```powershell
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```
Then open `frontend/index.html` in browser.

## API Keys needed
- FRED: https://fred.stlouisfed.org/docs/api/api_key.html
- NewsAPI: https://newsapi.org/register
- Telegram: @BotFather on Telegram

## Data refresh rates
- Market prices: every 5 minutes
- News: every 15 minutes
- Economic data: daily at 8 AM IST
- Telegram alerts: every 5 minutes
- Morning summary: daily at 8 AM IST
- Weekly wrap: Sunday 8 PM IST