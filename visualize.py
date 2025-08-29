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
from indicators import Indicators

from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
from indicators import Indicators
import mplfinance as mpf
import os


stream = CandleStream()


exchange = 'NSE'
start_date = datetime(2024, 1, 13, 9, 10)
end_date = datetime(2025, 7, 20, 9, 10)
interval = "10min"
bookrr = 2
all_results = []
is_live = False
save_image = False
risk = 1000
rrlist = [1.5, 2, 2.5]
tax_pct = 0.1
changedf_dict = {}


class visualize_stocks(strategy.BaseStrategy):
    def save_image(self, df, stock, day):
        if stock is None:
            raise ValueError("Trades can save as symbol name is missing")
        date = str(day)[:10]
        foldername = f"samplesimages/{stock}"
        os.makedirs(foldername, exist_ok=True)
        filename = f"{foldername}/{'-'.join(date.split(':'))}.jpg"
        df['time'] = pd.to_datetime(df['timestamp'])
        df.set_index('time', inplace=True)
        ema_plots = []

        if 'vwap' in list(df.columns):
                ema_plots.append(mpf.make_addplot(df['vwap'], color='red', width=3))
        col = df.columns
        col = sorted(col)
        width = 1
        for col in list(df.columns): 
            if 'ema_' in col or 'supertrend' in col:
                ema_plots.append(mpf.make_addplot(df[col], color='blue', width=width))
                width += 2
        
        ema_plots.append(mpf.make_addplot(df['vwap'], color='red', width=2))

        mpf.plot(df, type='candle', style='charles', title="",
                ylabel='Price', addplot=ema_plots,
                figsize=(16, 8),
                savefig=dict(fname=filename, dpi=100),
                volume=True, 
                )


    def day_handle(self,df, stock, day):
        self.save_image(df, stock, day)
        
    
    def update_sl(self):
        pass
        
    def apply_strategy(self):   
        ema_list = self.kwargs.get('ema_list')
        if ema_list is None:
            raise ValueError("For this strategy we need window to detect breakout and breakdown so pass input like this 'ema_list = ['ema_8', 'ema_21', 'ema_50', 'ema_100']' in your method ")
            
        df = self.df.copy()
        for ema in ema_list:
            df = Indicators.ema(df, ema)
        ema_list = ['ema'+'_'+str(ema) for ema in ema_list]
        df = Indicators.vwap(df)
        df = Indicators.atr(df)
        df['day'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        df = df.dropna()
        df.reset_index(inplace = True, drop = True)
        alldays = sorted(df['day'].unique(), key=pd.to_datetime)
        for x in alldays:
            dftmp = df[df['day'] == x].copy()
            self.day_handle(dftmp.copy(), self.kwargs.get('symbol'), x)
            
for symbol in pd.read_csv('ind_nifty50list.csv')['Symbol']:
    if 'adani' in symbol.lower():
        continue
    try:
        token = utils.get_token(exchange, symbol + '-EQ')
        orgdf = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval)
        mystrategy = visualize_stocks(orgdf.copy(), 'buy', window = 3, ema_list = [8, 21, 50], symbol = symbol, save_trade = save_image, live = is_live, change_dict = changedf_dict)
        mystrategy.run()
        
    except Exception as e:
        print('Error : ', e)


