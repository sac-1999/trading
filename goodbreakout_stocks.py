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
interval = "5min"
all_results = []
save_image_tmp = True
s_r_timeframe = '30min'
level_window = 5  
maxnumber_of_levels = 5
save_by_stock = True
draw_levels = True


class High_volume_surge_on_day(strategy.BaseStrategy):
    def transform(self, df):
        # Trend Indicators
        df = Indicators.ema(df, 21, True, 1)
        df = Indicators.ema(df, 50, True, 2)
        df = Indicators.ema(df, 100, True, 3)
        df = Indicators.sma(df, 21, True, 4)
        df = Indicators.sma(df, 50, True, 5)
        df = Indicators.sma(df, 100, True, 6)
        df = Indicators.rsi(df, 14, True, 7)
        df = Indicators.atr(df, True, 8)
        return df

        
    def save_image(self, df, day, peaks, bottoms, entry, sl, maxrr, dayendrr):
        if not self.kwargs.get('save_trade'): 
            return 
        currdf = utils.filter_data_by_dates(df.copy(), day, day)
        stock_high = currdf['high'].max()
        stock_low = currdf['low'].min()
        stock_high = stock_high + stock_high * 0.01
        stock_low = stock_low - stock_low * 0.02
        symbol = self.kwargs.get('symbol')
        if symbol is None:
            raise ValueError("Assign symbol = 'name' like as input in class")
        foldername = "-".join(str(day).split(':'))
        filename = symbol
        if save_by_stock:
            foldername, filename = filename , foldername
        folderpath = f"samplesimages/{foldername}" 
        filepath = f"samplesimages/{foldername}/{filename}.jpg"
        os.makedirs(folderpath, exist_ok=True)
        title = f"maxrr : {maxrr}   |    day endrr : {dayendrr}"
        df['time'] = pd.to_datetime(df['timestamp'])
        df.set_index('time', inplace=True)

        ema_plots = []

        for peak in peaks:
            if peak < stock_high and peak > stock_low:
                line = pd.Series(peak, index=df.index)
                ema_plots.append(mpf.make_addplot(line, color='orange', linestyle='-', width=1.5))

        entry = pd.Series(entry, index=df.index)
        ema_plots.append(mpf.make_addplot(entry, color='green', linestyle='-', width=5))
        
        sl = pd.Series(sl, index=df.index)
        ema_plots.append(mpf.make_addplot(sl, color='red', linestyle='-', width=5))

        for bottom in bottoms:
            if bottom < stock_high and bottom > stock_low:
                line = pd.Series(bottom, index=df.index)
                ema_plots.append(mpf.make_addplot(line, color='blue', linestyle='-', width=1))

        if 'ema_11' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['ema_11'], color='black', width=3))
        if 'ema_21' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['ema_21'], color='black', width=3)) 

        
        ema_plots.append(mpf.make_addplot(df['stochk_9_3'], panel = 2, color='black', width=2)) 
        ema_plots.append(mpf.make_addplot(df['stochk_14_3'], panel = 2, color='orange', width=2)) 
        # ema_plots.append(mpf.make_addplot(df['stochk_40_3'], panel = 2, color='orange', width=3)) 
        # ema_plots.append(mpf.make_addplot(df['vwap'], color='red', width=4)) 


        mpf.plot(df, type='candle', style='charles', title=title,
                ylabel='Price',
                figsize=(32, 16),
                volume=True,
                addplot=ema_plots,
                savefig=dict(fname=filepath, dpi=100))

    def update_sl(self):
        pass

    def find_relevant_levels(self, dftmp, x_day):
        levelsdf = self.kwargs.get('levelsdf')
        if levelsdf is None:
            return 

        levelsdf = levelsdf[levelsdf['day'] < pd.to_datetime(x_day).date()]
        lastnrows = levelsdf.iloc[-level_window:]
        
        if len(levelsdf) == 0:
            return 
    
        peaks = levelsdf['peak'].dropna().tolist()
        newpeaks = []
        lastmax = lastnrows['high'].max()
        for i in range(len(peaks)-1, -1, -1):
            if peaks[i] >= lastmax:
                newpeaks.insert(0,peaks[i])
                lastmax = peaks[i]
            if len(newpeaks) == maxnumber_of_levels:
                break

        bottoms = levelsdf['bottom'].dropna().tolist()
        newbottoms = []
        lastmin = lastnrows['low'].min()
        for i in range(len(bottoms)-1, -1, -1):
            if bottoms[i] <= lastmin:
                newbottoms.insert(0,bottoms[i])
                lastmin = bottoms[i]
            if len(newbottoms) == maxnumber_of_levels:
                break
     
        return newpeaks, newbottoms
    
    def Intraday_breakouts(self, df, window):
        df['resistance'] = np.nan
        df['max'] = df['high'].cummax()
        df['isheighest'] = df['max'] == df['high']

        for i in range(len(df)):
            if i == len(df)-window:
                break

            if i == 0:
                right = df.iloc[i+1:i+window+1]
                curr = df.iloc[i]
                if curr['high'] > right['high'].max() and curr['isheighest']:
                    df.loc[i, 'resistance'] = df.iloc[i]['high']
            
            else:
                left = df.iloc[max(i-window,0) : i+1]
                right = df.iloc[i : i+window+1]
                curr = df.iloc[i]
                if curr['high'] >= left['high'].max() and curr['high'] >= right['high'].max() and curr['isheighest']:
                    df.loc[i, 'resistance'] = df.iloc[i]['high']

        df['resistance'] = df['resistance'].ffill()
        df['resistance'] = df['resistance'].shift(window)
        df = df.drop(columns = ['isheighest'])
        
        return df 
    

    def Intraday_support_for_breakouts(self, df, window):
        df['islow'] = False
        for i in range(len(df)):
            left = df.iloc[max(i-window,0) : i]
            right = df.iloc[i+1 : i+window+1]
            currlow = df.iloc[i]['low']
            if i == 0:
                if currlow < right['low'].min():
                    df.loc[i, 'islow'] = True

            elif currlow < left['low'].min() and currlow < right['low'].min():
                df.loc[i, 'islow'] = True
        # df['islow'] = df['islow'].ffill()
        return df 

    def is_valid_previous_day(self,df):
        enddf = utils.filter_by_time(df, '12:10', '15:30')
        startdf = utils.filter_by_time(df, '9:14', '12:05')
        if startdf['high'].max() > enddf['high'].max() :
            return True
        return False

    def trade_strategy(self, df, newpeaks, newbottoms, prevdaydf):
        df = utils.filter_by_time(df, '9:14', '15:00')
        df.reset_index(inplace = True, drop = True)

        prevday = list(prevdaydf['day'].unique())[-1]
        prevdaydf = utils.filter_data_by_dates(prevdaydf, prevday, prevday)
        prevdaylow = prevdaydf['low'].min()
        prevdayhigh = prevdaydf['high'].max()

        df = self.Intraday_breakouts(df, 3)
        df['breakout1'] = (df['high'] > df['resistance'].shift(1)) & (df['max'].shift(1) == df['resistance']) & (df['time'] <= pd.to_datetime('11:00').time())
        df['breakout'] = (df['breakout1'] & (df['close'] > df['resistance'])) | (df['breakout1'].shift(1) & (df['close'].shift(1) < df['resistance'].shift(1)) & (df['close'] > df['high'].shift(1)))

        df['sl'] = np.minimum(df['low'] , df['low'].shift(1))
        breakdf = df[df['breakout']]

        if len(breakdf) == 0:
            return 

        traderow = breakdf.iloc[0]
        entry = traderow['close']

        if entry < prevdayhigh:
            return 
        sl = traderow['sl']                
        sl = sl - sl * 0.001
        sl = min(sl, entry - entry * 0.003)
        df['sl'] = sl
        df['entry'] = entry
        
        return (entry, sl, 0, 0)

    def apply_strategy(self):   
        df = self.df.copy()
        df = Indicators.ema(df, 50)
        df = Indicators.ema(df, 11)
        df = Indicators.ema(df, 21)
        df = Indicators.vwap(df)
        df = Indicators.atr(df)
        df = Indicators.stoch(df, 4, 9, 3)
        df = Indicators.stoch(df, 4, 14, 3)
        df = Indicators.stoch(df, 4, 120, 3)


        df['day'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        df = df.dropna()
        df.reset_index(inplace = True, drop = True)
        alldays = sorted(df['day'].unique(), key=pd.to_datetime)
        prevday = None
        for x_day in alldays:
            if (datetime.today() - timedelta(100)).date() >= pd.to_datetime(x_day).date():
                prevday = x_day
                continue
            if prevday is None:
                continue
            newprevday = pd.to_datetime(prevday) - timedelta(3)
            prevdaydf = utils.filter_data_by_dates(df.copy(), newprevday, prevday)
            dftmp = utils.filter_data_by_dates(df.copy(), x_day, x_day)
            newpeaks = []
            newbottoms = []
            if draw_levels:
                levels = self.find_relevant_levels(dftmp, x_day)
                if levels is not None:
                    if dftmp is not None:
                        newpeaks , newbottoms = levels
            trade = self.trade_strategy(dftmp.copy(), newpeaks, newbottoms, prevdaydf)
            if trade is not None:
                entry, sl, maxrr, dayendrr = trade
                print(entry, sl)
                dflist = [dftmp]
                dftmp = pd.concat(dflist)
                dftmp.reset_index(inplace = True, drop = True)
                self.save_image(dftmp, x_day, newpeaks, newbottoms, entry, sl, maxrr, dayendrr)
                
            prevday = x_day


def find_previous_levels(df):
    df = utils.resample(df, s_r_timeframe)
    df = utils.find_past_peaks(df, level_window)
    df = utils.find_past_bottoms(df, level_window)
    df = df[['timestamp', 'low', 'high', 'peak', 'bottom']]
    return df


import json
sectors = None
with open("index_stock.json", "r") as f:
    sectors = json.load(f)

interval = '5min'
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
niftydf = niftydf[['timestamp', 'niftytrend']]
for symbol in pd.read_csv('ind_nifty50list.csv')['Symbol']:
    try:
        token = utils.get_token(exchange, symbol + '-EQ')
        orgdf = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval)  
        orgdf = pd.merge(orgdf, niftydf, on = 'timestamp', how = 'left') 
        levelsdf = None
        if draw_levels is None:    
            levelsdf = find_previous_levels(orgdf.copy())
            levelsdf['day'] = levelsdf['timestamp'].dt.date

        mystrategy = High_volume_surge_on_day(orgdf.copy(), 'buy', symbol = symbol, save_trade = save_image_tmp,levelsdf = levelsdf)
        results = mystrategy.run()

    except Exception as e:
        raise ValueError(e)


df = pd.DataFrame(all_results)
df.to_csv('allresults.csv', index = False)
print(df)