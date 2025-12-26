from broker import DeltaExchange
from dotenv import load_dotenv
from logger_config import get_logger
import os 
import time
from indicators import Indicators
import pandas as pd
logger = get_logger(__name__)
from datetime import datetime, timedelta
from dataingestion import BTCDataLoader
import numpy as np
load_dotenv()

USE_TESTNET = False
broker = DeltaExchange()
logger.info("=" * 60)
WINDOW = 17


def load_data(symbol,start_date, end_date):
    dflist = []
    while(start_date < end_date or start_date.date() == datetime.today().date()):
        logger.info(f"Loading data for {start_date}")
        start_t = datetime(start_date.year, start_date.month, start_date.day, 0, 0)
        start_date = start_date + timedelta(days = 1)
        end_t = datetime(start_date.year, start_date.month, start_date.day, 0, 0) - timedelta(minutes=1)
        while(True):
            df = broker.get_historical_data_by_dates(symbol, "1m", start_date=start_t, end_date=end_t)
            if df is  None:
                logger.error(f"No data retrieved from {start_t} to {end_t}")
                time.sleep(5)
                continue
            else:
                dflist.append(df)
                break

    df = pd.concat(dflist)
    return df



# df = load_data('BTCUSD', datetime(2025,11,1), datetime.today())
# list_of_jsons = df.to_dict(orient='records')
databaseloader = BTCDataLoader()
# databaseloader.insert_candles(list_of_jsons)

retrieved_data = databaseloader.get_candles()
if not retrieved_data:
    os.exit(1)

df = pd.DataFrame(retrieved_data)
df = df.sort_values(by="time")
df["time"] = pd.to_datetime(df["time"], utc=True)
df["time"] = df["time"].dt.tz_convert("Asia/Kolkata")
df['timestamp'] = df['time']
df.to_csv('dataset.csv', index=False)
print(df)