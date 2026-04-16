import sys, os, time
sys.path.append(os.path.dirname(__file__))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval   import IntervalTrigger
from apscheduler.triggers.cron       import CronTrigger
from datetime import datetime

from collectors.stocks   import collect_all_market_data
from collectors.crypto   import collect_crypto
from collectors.news     import collect_all_news
from collectors.economic import collect_economic_indicators
from database            import init_db

scheduler = BlockingScheduler(
    timezone="Asia/Kolkata",
    job_defaults={"misfire_grace_time": 30}
)

def run_market():
    try:
        t = datetime.now().strftime('%H:%M:%S')
        print(f"\n⏰ [{t}] Collecting market data...")
        collect_all_market_data()
        collect_crypto()
        print(f"✅ [{t}] Market data updated.")
    except Exception as e:
        print(f"❌ Market error: {e}")

def run_news():
    try:
        print(f"📰 Fetching news...")
        collect_all_news()
        print(f"✅ News updated.")
    except Exception as e:
        print(f"❌ News error: {e}")

def run_economic():
    try:
        collect_economic_indicators()
        print("✅ Economic data updated.")
    except Exception as e:
        print(f"❌ Economic error: {e}")

def start():
    init_db()

    # ── Market data every 30 seconds ──────────────────────────────────────────
    scheduler.add_job(
        run_market,
        IntervalTrigger(seconds=30),
        id="market_data",
        replace_existing=True
    )

    # ── News every 15 minutes ─────────────────────────────────────────────────
    scheduler.add_job(
        run_news,
        IntervalTrigger(minutes=15),
        id="news",
        replace_existing=True
    )

    # ── Economic data once daily at 8 AM IST ──────────────────────────────────
    scheduler.add_job(
        run_economic,
        CronTrigger(hour=8, minute=0, timezone="Asia/Kolkata"),
        id="economic",
        replace_existing=True
    )

    print("=" * 50)
    print("  FinTrack Pro — Data Scheduler")
    print("=" * 50)
    print("  ⏰ Market data : every 30 seconds")
    print("  📰 News        : every 15 minutes")
    print("  📉 Economic    : daily 8:00 AM IST")
    print("=" * 50)
    print("\n  Running initial collection now...\n")

    # Run once immediately
    run_market()
    run_news()

    print("\n✅ Scheduler running. Press Ctrl+C to stop.\n")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n⛔ Scheduler stopped.")
        scheduler.shutdown()

if __name__ == "__main__":
    start()