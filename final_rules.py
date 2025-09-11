'''Idea : stochastic divergence is the idea 

universal rule : below previous two days for sell and buy for near top of last 2 days

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
start_date = datetime(2025, 8, 1, 9, 10)
end_date = datetime(2025, 9, 10, 9, 10)
interval = "5min"
all_results = []
save_image_tmp = False
s_r_timeframe = '30min'
level_window = 1
maxnumber_of_levels = 5
save_by_stock = False
draw_levels = True

class High_volume_surge_on_day(strategy.BaseStrategy):
    def save_image(self, df, day, peaks, bottoms, entry, sl, maxrr, dayendrr, prevdaydf):
        if not self.kwargs.get('save_trade'): 
            return 
        
        stock_high = prevdaydf.iloc[-1]['close']
        stock_low = prevdaydf.iloc[-1]['close']
        stock_high = stock_high + stock_high * 0.05
        stock_low = stock_low - stock_low * 0.05
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
            if peak < stock_high:
                line = pd.Series(peak, index=df.index)
                ema_plots.append(mpf.make_addplot(line, color='orange', linestyle='-', width=6))

        entry = pd.Series(entry, index=df.index)
        ema_plots.append(mpf.make_addplot(entry, color='green', linestyle='-', width=3))
        
        sl = pd.Series(sl, index=df.index)
        ema_plots.append(mpf.make_addplot(sl, color='red', linestyle='-', width=5))

        # for bottom in bottoms:
        #     if bottom < stock_high and bottom > stock_low:
        #         line = pd.Series(bottom, index=df.index)
        #         ema_plots.append(mpf.make_addplot(line, color='blue', linestyle='-', width=1))

        if 'ema_9' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['ema_9'], color='blue', width=2))
        if 'ema_21' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['ema_21'], color='black', width=3)) 

        
        # ema_plots.append(mpf.make_addplot(df['stochk_9_3'], panel = 2, color='black', width=2)) 
        # ema_plots.append(mpf.make_addplot(df['stochk_14_3'], panel = 2, color='orange', width=2)) 
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
    
    def morning_star(self, df):
        df['red'] = df['close'] < df['open']
        df['center_candle'] = df['red'].shift(1) & (df['high'] < df['high'].shift(1))
        df['morning_star'] = df['center_candle'].shift(1) & (df['close'] > df['open'].shift(2))
        return df
    

    def indicator_support(self, df, indicator):
        df[indicator + '_sup'] = (df['close'] > df['high'].shift(1)) & ((df['low'] < df[indicator])) & ((df['high'].shift(1) > df[indicator].shift(1)))       
        return df

    def trade_strategy(self, df, newpeaks, newbottoms, prevdaydf):
        df = utils.filter_by_time(df, '9:14', '15:00')
        df.reset_index(inplace = True, drop = True)
        df = self.morning_star(df)
        df['min'] = df['low'].cummin()
        df['islowest'] = df['low'] == df['min']
        df['volume_mean'] = df['volume'].rolling(window=3, min_periods=3).mean()
        df['ema11_failed'] = np.where(df['close'] < df['ema_11'], 1, 0)
        df['eam11_failed'] = df['ema11_failed'].cummax()
        df['ema21_failed'] = np.where(df['close'] < df['ema_21'], 1, 0)
        df['eam21_failed'] = df['ema21_failed'].cummax()
        df = self.indicator_support(df, 'ema_11')
        df = self.indicator_support(df, 'vwap')


        df['breakout'] = ((df['eam11_failed'].shift(1) <= 0) & (df['eam21_failed'].shift(1) <= 0)) & (df['ema_11_sup'] | df['vwap_sup']) & (df['time'] > pd.to_datetime('10:00').time()) & (df['time'] < pd.to_datetime('11:30').time()) 
        df['sl'] = np.minimum(df['low'], df['low'].shift(1))
        breakdf = df[df['breakout']]
        if len(breakdf) == 0:
            return 

        traderow = breakdf.iloc[0]
        if traderow['niftytrend'] !=1:
            return 
        
        entry = traderow['close']
        sl = traderow['sl']                
        # if (entry - sl)/sl * 100 > 0.6:
        #     return

        sl = sl - sl * 0.001
        # sl = min(sl, entry - entry * 0.0025)
        df['sl'] = sl
        df['entry'] = entry
        
        futdf = df[df['time'] > traderow['time']].copy()
        if len(futdf)==0:
            return
        futdf['sl'] = sl
        futdf['entry'] = entry
        futdf['rr'] = round(((futdf['high'] - futdf['entry'])/(futdf['entry'] - futdf['sl'])), 1) 
        futdf['dayendrr'] = round(((futdf['close'] - futdf['entry'])/(futdf['entry'] - futdf['sl'])), 1) 
        futdf['maxrr'] = futdf['rr'].cummax()
        futdf['slhit'] = futdf['low'] < futdf['sl']
        futdf['slhit'] = futdf['slhit'].cummax()
        maxrr = 0
        dayendrr = -1
        if len(futdf[futdf['slhit']]) > 0:
            dayendrr = -1
            futdf = futdf[futdf['slhit'] == False]
            if len(futdf) > 0:
                maxrr = futdf['maxrr'].max()


        else:
            futdf = futdf[futdf['slhit'] == False]
            dayendrr = futdf.iloc[-1]['dayendrr']
            if len(futdf) > 0:
                maxrr = futdf['maxrr'].max()

        data = traderow.to_dict()
        data['maxrr'] = maxrr
        data['rr'] = dayendrr
        all_results.append(data)
        return (entry, sl, maxrr, dayendrr)


    def apply_strategy(self):   
        df = self.df.copy()
        df = Indicators.ema(df, 11)
        df = Indicators.ema(df, 21)
        df = Indicators.stoch(df, 4, 9, 3)
        df = Indicators.stoch(df, 4, 14, 3)
        df = Indicators.vwap(df)

        df['day'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        df = df.dropna()
        df.reset_index(inplace = True, drop = True)
        alldays = sorted(df['day'].unique(), key=pd.to_datetime)
        prevday = None
        for x_day in alldays:
            # if (datetime.today() - timedelta(400)).date() >= pd.to_datetime(x_day).date():
            #     prevday = x_day
            #     continue
            if prevday is None:
                prevday = x_day
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
                self.save_image(dftmp, x_day, newpeaks, newbottoms, entry, sl, maxrr, dayendrr, prevdaydf)
                
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

sector = 'Nifty 50'
token = utils.get_token(exchange, sector)
if token is None:
    import sys
    sys.exit()

niftydf = dataset.get_data(stream, 'NSE', sector, token, start_date, end_date, interval)  
niftydf = Indicators.ema(niftydf, 9) 
niftydf = Indicators.ema(niftydf, 21) 
niftydf = Indicators.ema(niftydf, 50) 
niftydf = Indicators.stoch(niftydf, 4, 14, 3)  
niftydf = Indicators.stoch(niftydf, 4, 9, 3)  
niftydf['stochk_14_3_mean'] = niftydf['stochk_14_3'].rolling(window=5, min_periods=5).mean()

niftydf['niftytrend'] = np.where(((niftydf['ema_21'] > niftydf['ema_21'].shift(1)) & 
                                    (niftydf['ema_9'] > niftydf['ema_9'].shift(1))),
                                    1, 0)

# niftydf['niftytrend'] = np.where(((niftydf['close'] > niftydf['ema_500'].shift(1))),
                                    # 1, 0)
niftydf = niftydf[['timestamp', 'niftytrend']]
for symbol in pd.read_csv('ind_nifty50list.csv')['Symbol']:
    try:
        token = utils.get_token(exchange, symbol + '-EQ')
        orgdf = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval)  
        orgdf = pd.merge(orgdf, niftydf, on = 'timestamp', how = 'left') 
        levelsdf = None
        if draw_levels:    
            levelsdf = find_previous_levels(orgdf.copy())
            levelsdf['day'] = levelsdf['timestamp'].dt.date

        mystrategy = High_volume_surge_on_day(orgdf.copy(), 'buy', symbol = symbol, save_trade = save_image_tmp,levelsdf = levelsdf)
        results = mystrategy.run()

    except Exception as e:
        raise ValueError(e)
    
df = pd.DataFrame(all_results)
df.to_csv('allresults.csv', index = False)
print(df)