'''Idea : stochastic divergence is the idea 
''' 


# %load_ext autoreload
# %autoreload 2

from datetime import datetime, timedelta
from CandleStream import CandleStream 
import pandas as pd
from calender_utils import *
import utils
import dataset
import strategy

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
from indicators import Indicators
import mplfinance as mpf
import os

df = pd.DataFrame([])
df.to_csv('allresults.csv', index = False)
print(df)

stream = CandleStream()

exchange = 'NSE'
start_date = datetime(2024, 4, 1, 9, 10)
end_date = datetime(2025, 9, 6, 9, 10)
interval = "15min"
all_results = []

sector = 'Nifty 50'
token = utils.get_token(exchange, sector)
if token is None:
    import sys
    sys.exit()

niftydf = dataset.get_data(stream, 'NSE', sector, token, start_date, end_date, interval)  
niftydf = Indicators.ema(niftydf, 8) 
niftydf = Indicators.ema(niftydf, 21) 
niftydf = Indicators.ema(niftydf, 50) 
niftydf['niftytrend'] = np.where(((niftydf['close'] > niftydf['close'].shift(1)) &
                                    (niftydf['ema_21'] > niftydf['ema_21'].shift(1)) & 
                                    (niftydf['ema_8'] > niftydf['ema_8'].shift(1)) &
                                    (niftydf['ema_50'] > niftydf['ema_50'].shift(10))),
                                    1, 0)

niftydf = (niftydf['niftytrend'] == 1) & (niftydf['timestamp'] > pd.to_datetime('10:00').time()) & (niftydf['timestamp'] < pd.to_datetime('11:00').time())
print(niftydf.tail(50))