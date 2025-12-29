import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from logger_config import get_logger
logger = get_logger(__name__)

def get_product_id_by_symbol(symbol = None):
    headers = {
    'Accept': 'application/json'
    }

    r = requests.get('https://api.india.delta.exchange/v2/products/', params={}, headers = headers)
    r = r.json()
    try:
        for i in r['result']:
            if i['contract_type'] == 'perpetual_futures' and i['symbol'] == symbol:
                return i['id']
    except Exception as e:
        print(e)
    return None


def load_data(broker, symbol,start_date, end_date, timeframe = '1m'):
    dflist = []
    while(start_date < end_date or start_date.date() == datetime.today().date()):
        logger.info(f"Loading data for {start_date}")
        start_t = datetime(start_date.year, start_date.month, start_date.day, 0, 0)
        start_date = start_date + timedelta(days = 1)
        end_t = datetime(start_date.year, start_date.month, start_date.day, 0, 0) - timedelta(minutes=1)
        while(True):
            df = broker.get_historical_data_by_dates(symbol, timeframe, start_date=start_t, end_date=end_t)
            df['symbol'] = symbol
            df['timeframe'] = timeframe

            if df is  None:
                logger.error(f"No data retrieved from {start_t} to {end_t}")
                time.sleep(5)
                continue
            else:
                dflist.append(df)
                break

    df = pd.concat(dflist)
    return df

