from datetime import datetime, timedelta
import pandas as pd
from objects import *



def fast_sync(exchange, _date, listofsymbols):
    startdate = datetime(_date.year, _date.month, _date.day, 0, 0)
    enddate = datetime(_date.year, _date.month, _date.day, 23, 59)
    for symbol, isindex in listofsymbols.items():
        df = broker.get_candle_stick_data(exchange, symbol, 'ONE_MINUTE', startdate, enddate, isindex)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print(df.head(1))
        

