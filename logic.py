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


stream = CandleStream()


exchange = 'NSE'
start_date = datetime(2025, 3, 1, 9, 10)
end_date = datetime(2025, 7, 30, 9, 10)
interval = "1min"
all_results = []
save_image = False
volume_day_window = 2
compare = 'median'
ratio = 5
foler_by_stock = True


class High_volume_surge_on_day(strategy.BaseStrategy):
    def breakout(self, df, window):
        df['peak'] = False
        df['max'] = df['high'].cummax()
        for i in range(len(df)-window):
            curr = df.iloc[i]['high']
            if curr != df.iloc[i]['max']:
                continue
            left = df.iloc[:i]
            right = df.iloc[i+1 : i + window]
            if i==0:
                if curr > right['high'].max():
                    df.loc[i,'peak'] = True
            else:
                if left['high'].max() < curr  and curr > right['high'].max() and curr == df.iloc[i]['max']:
                    df.loc[i,'peak'] = True
        df['peak'] = np.where(df['peak'], df['high'], np.nan)
        df['peak'] = df['peak'].ffill()
        df['breakout'] = (df['close'] > df['peak'].shift(1)) & (df['high'] == df['max']) & (df['max'].shift(1) == df['peak'].shift(1)) & (df['time']<pd.to_datetime("11:30").time())
        df = df[df['breakout']]
        if len(df) == 0:
            return None        
        return df.iloc[0]['close']
                

    def save_image(self, df, day):
        entry = self.breakout(df,3)
        if entry is None:
            return None
        symbol = self.kwargs.get('symbol')
        if symbol is None:
            raise ValueError("Assign symbol = 'name' like as input in class")
        tradeperminute  = df.iloc[:10]['volume'].max() * df.iloc[:10]['close'].mean()
        tradeperminute = round(tradeperminute / 10000000 , 1)

        filename = "-".join(str(day).split(':'))
        foldername = symbol

        if foler_by_stock == False:
            foldername = "-".join(str(day).split(':'))
            filename = symbol

        folderpath = f"samplesimages/{foldername}" 
        filepath = f"samplesimages/{foldername}/{filename}.jpg"
        os.makedirs(folderpath, exist_ok=True)
        title = f"{symbol}.  {tradeperminute} crore"
        df['time'] = pd.to_datetime(df['timestamp'])
        df.set_index('time', inplace=True)
        entry_line = pd.Series(entry, index=df.index)

        ema_plots = [mpf.make_addplot(entry_line, color='purple', linestyle='-', width=2)]

        if 'vwap' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['vwap'], color='red', width=3))
        
        if 'ema_' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['vwap'], color='red', width=3))
        

        mpf.plot(df, type='candle', style='charles', title=title,
                ylabel='Price',
                addplot=ema_plots,
                figsize=(16, 8),
                volume=True,
                savefig=dict(fname=filepath, dpi=100))
        
        
        

    def aggregator(self,df, compare):
        stat_functions = {
                    'mean': df['volume'].mean(),
                    'median': df['volume'].median(),
                    'sum': df['volume'].sum(),
                    'std': df['volume'].std(),
                    'min': df['volume'].min(),
                    'max': df['volume'].max()
                }
        return stat_functions.get(compare)


    def is_volume_fit(self, orgdf, window, x_day, ratio, compare = 'median'):
        if orgdf is None:
            return False
        unique_days = orgdf['day'].unique()
        unique_days = sorted(unique_days)
        if x_day not in unique_days:
            return False 
        day_index = unique_days.index(x_day)
        start_day_index = day_index - window
        if start_day_index < 0:
            return False
        
        end_day = unique_days[day_index]
        start_day = unique_days[start_day_index]
        orgdf = utils.filter_data_by_dates(orgdf, start_day, end_day)
        unique_days = orgdf['day'].unique()
        volume_holder = []
        if len(unique_days) < window:
            return False
        
        current_day_volume = None
        for i, day in enumerate(unique_days):
            df = utils.filter_data_by_dates(orgdf,day, day)
            if df is not None or len(df) > 0:
                if day == x_day:
                    df = df[(df['time'] >= pd.to_datetime("09:15").time()) & (df['time'] < pd.to_datetime("09:25").time())].copy()
                    m = self.aggregator(df, compare)
                    if m is not None:
                        current_day_volume = m
                else:
                    m = self.aggregator(df, compare)
                    if m is not None:
                        volume_holder.append(m)
            else:
                raise ValueError("Error : No reason to get empty data here")
        # print(volume_holder)
        if len(volume_holder)!=window:
            # print("less number of days to compare from current dya")
            return False
        
        for volume in volume_holder:
            if  current_day_volume < volume * ratio:
                return False
        return True


    def update_sl(self):
        pass
        
    def apply_strategy(self):   
        df = self.df.copy()
        df = Indicators.vwap(df)
        # df = Indicators.ema(df, 300)
        df['day'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        df = df.dropna()
        df.reset_index(inplace = True, drop = True)
        alldays = sorted(df['day'].unique(), key=pd.to_datetime)

        for x_day in alldays:
            print(x_day, " is this day good for trade ?? any volume surge on this day ??????")
            if self.is_volume_fit(df.copy(),volume_day_window, x_day, ratio, compare):
                currdaydf = utils.filter_data_by_dates(df.copy(), x_day, x_day)
                if currdaydf is None or len(currdaydf) == 0:
                    raise ValueError("How it is even possible that curr dya does not exist")
                self.save_image(currdaydf, x_day)


for symbol in pd.read_csv('ind_nifty200list.csv')['Symbol']:
    if 'adani' in symbol.lower():
        continue
    try:
        print('I am here Draw some good volume surge graphs')
        token = utils.get_token(exchange, symbol + '-EQ')
        orgdf = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval)
        mystrategy = High_volume_surge_on_day(orgdf.copy(), 'buy', window = 3, ema_list = [8, 21, 50], symbol = symbol, save_trade = save_image,)
        results = mystrategy.run()
        # break
    except Exception as e:
        # raise ValueError(e)
        print(e)

    



