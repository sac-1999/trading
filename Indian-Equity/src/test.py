
import asyncio
from datetime import datetime
import pandas as pd

# If these are in your project, ensure the imports point to the right modules.
# from sync import historical_sync  # If sync has this function explicitly
from sync import *  # Not ideal, but keeping as you had it
# import db  # Uncomment and fix this import based on your actual package layout

# Load symbols
allstocks = pd.read_csv('./../data/ind_nifty200list.csv')['Symbol'].tolist()
finalstocks = {stock: False for stock in allstocks}
finalstocks['Nifty 50'] = True

async def live_sync():
    """
    Run the historical_sync in a thread so it doesn't block the event loop.
    If historical_sync is already async, call it directly instead of using to_thread.
    """
    # Adjust args if historical_sync expects different types
    await asyncio.to_thread(fast_sync, 'NSE', datetime.today(), datetime.today(), finalstocks)

async def load_candles():
    """
    Load and print the latest candle for ABB, converting timestamp to Asia/Kolkata.
    """
    # records = db.get_candles('ABB', '1m')  # Ensure db is imported correctly
    # If db.get_candles is synchronous, that's fine; otherwise await it.
    records = db.get_candles('ABB', '1m')
    df = pd.DataFrame(records)
    if df.empty:
        print("No candle data found.")
        return
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df.dropna(subset=["timestamp"], inplace=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    print(df.iloc[-1])

async def main():
    """
    Periodically run live_sync and optionally load_candles.
    """
    # Run both as periodic tasks. You can adjust the intervals.
    async def periodic_live_sync(interval_sec: int = 30):
        while True:
            try:
                await live_sync()
            except Exception as e:
                print(f"[live_sync] Error: {e}")
            await asyncio.sleep(interval_sec)

    async def periodic_load_candles(interval_sec: int = 10):
        while True:
            try:
                await load_candles()
            except Exception as e:
                print(f"[load_candles] Error: {e}")
            await asyncio.sleep(interval_sec)

    # Schedule tasks concurrently
    tasks = [
        asyncio.create_task(periodic_live_sync(1)),
        asyncio.create_task(periodic_load_candles(10)),
    ]
    # Let them run forever
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # asyncio.run(main())
    startday = datetime.today() - timedelta(days=10)
    while(startday < datetime.today()):
        fast_sync('NSE', startday, finalstocks)
        startday = startday + timedelta(1)



# 1. maintain stocks with heighest percentage change from last day which are greater than 1.5 percent 
# 2. start syncing these stocks
# 3. 