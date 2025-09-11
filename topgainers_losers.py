'''
Use this to get day top gainer and loser
''' 


# %load_ext autoreload
# %autoreload 2

from datetime import datetime, timedelta
from CandleStream import CandleStream 
import pandas as pd
from calender_utils import *
import utils
import dataset
import pandas as pd
import numpy as np
stream = CandleStream()

exchange = 'NSE'
start_date = datetime(2025, 1, 1, 9, 10)
end_date = datetime(2025, 9, 10, 9, 10)
interval = "1min"

maindf = None
for symbol in pd.read_csv('ind_nifty50list.csv')['Symbol'][:]:
    print(symbol)
    try:
        token = utils.get_token(exchange, symbol + '-EQ')
        df = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval)  
        if df is None:
            continue
        df['day'] = df['timestamp'].dt.date  
        daily_summary = df.groupby("day").agg({
            "low": "min",
            "close": "last",
            "high": "max",
            "open": "first"
        }).reset_index()
        daily_summary.rename(columns = {'open':'prevdayopen',
                                        'close':'prevdayclose',
                                        'high':'prevdayhigh',
                                        'low':'prevdaylow'}, inplace = True)
        
        daily_summary['prevdayopen'] = daily_summary['prevdayopen'].shift(1)
        daily_summary['prevdayclose'] = daily_summary['prevdayclose'].shift(1)
        daily_summary['prevdayhigh'] = daily_summary['prevdayhigh'].shift(1)
        daily_summary['prevdaylow'] = daily_summary['prevdaylow'].shift(1)
        df = pd.merge(df, daily_summary, on='day', how='left')
        changecol = 'change_' + symbol
        df[changecol] = round((df['close'] - df['prevdayclose'])/df['prevdayclose'] * 100, 2)
        df = df[['timestamp', changecol]]
        
        if maindf is None:
            maindf = df
        else:
            maindf = pd.merge(maindf, df, on = 'timestamp', how= 'left')

    except Exception as e:
        raise ValueError(e)
    
maindf = maindf.dropna()
maindf.reset_index(inplace=True, drop = True)
change_cols = [col for col in maindf.columns if col.startswith("change_")]
maindf["sorted_changes"] = maindf[change_cols].apply(
    lambda row: sorted(
        [(col.replace("change_", ""), row[col])  for col in change_cols if pd.notna(row[col])],
        key=lambda x: x[1]  # sort by the value
    ), axis=1
)

maindf = maindf[['timestamp', 'sorted_changes']]
print(maindf)
maindf.to_csv('toploser_gainers.csv', index = False)
