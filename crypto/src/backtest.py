
from dotenv import load_dotenv
from logger_config import get_logger
import os 
import time
from indicators import Indicators
from dataingestion import  BTCDataLoader
import pandas as pd
import numpy as np
load_dotenv()
logger = get_logger(__name__)
USE_TESTNET = False

logger.info("=" * 60)
WINDOW = 17

SYMBOL = 'BTCUSD'
TIMEFRAME = '5m'
databaseloader = BTCDataLoader()
retrieved_data = databaseloader.get_candles(SYMBOL, TIMEFRAME)
if not retrieved_data:
    os._exit(1)

df = pd.DataFrame(retrieved_data)
df = df.sort_values(by="time")
df["time"] = pd.to_datetime(df["time"], utc=True)
df["time"] = df["time"].dt.tz_convert("Asia/Kolkata")
df['timestamp'] = df['time']
df.to_csv('dataset.csv', index=False)
print(df)