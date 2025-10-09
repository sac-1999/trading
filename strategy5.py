
'''Idea : start trading after 9:45
''' 


# %load_ext autoreload
# %autoreload 2

import ast
import json
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
import mplfinance as mpf
import os
import telegram_services
import asyncio

df = pd.DataFrame([])
df.to_csv('allresults.csv', index = False)
# topgainers_losers = pd.read_csv('toploser_gainers.csv')
# topgainers_losers["sorted_changes"] = topgainers_losers["sorted_changes"].apply(
#     lambda x: ast.literal_eval(x.replace("np.float64", "")) if isinstance(x, str) else x
# )
# print(topgainers_losers)

# topgainers_losers['timestamp'] = pd.to_datetime(topgainers_losers['timestamp'])

topgainers_losers = None


stream = CandleStream()

exchange = 'NSE'
start_date = datetime(2025, 7, 1, 9, 10)
end_date = datetime(2025, 9, 20, 9, 10)
interval = "10min"
all_results = []
save_image_tmp =    True
s_r_timeframe = '30min'
level_window = 20
maxnumber_of_levels = 1
save_by_stock = False
draw_levels = True
islive = False

class High_volume_surge_on_day(strategy.BaseStrategy):         
    def save_image(self, df, day, peaks, bottoms, entry, sl, maxrr, dayendrr, prevdaydf):
        if not self.kwargs.get('save_trade'): 
            return 
        
        lastentrytime = df.iloc[-1]['time']
        currday = df.iloc[-1]['day']

        stock_high, stock_low = df.iloc[0]['low'], df.iloc[0]['high']
        if prevdaydf is not None:
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

        entry_m = pd.Series(entry, index=df.index)
        ema_plots.append(mpf.make_addplot(entry_m, color='green', linestyle='-', width=3))
        
        sl_m = pd.Series(sl, index=df.index)
        ema_plots.append(mpf.make_addplot(sl_m, color='red', linestyle='-', width=5))

        # for bottom in bottoms:
        #     if bottom < stock_high and bottom > stock_low:
        #         line = pd.Series(bottom, index=df.index)
        #         ema_plots.append(mpf.make_addplot(line, color='blue', linestyle='-', width=1))

        if 'ema_9' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['ema_9'], color='blue', width=2))
        if 'ema_21' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['ema_21'], color='black', width=3)) 
        if 'vwap' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['vwap'], color='black', width=5)) 

        
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
        telegram_file_path = 'telegram_msg.json'

        if os.path.exists(telegram_file_path):
            with open(telegram_file_path, "r") as f:
                try:
                    notifieddata = json.load(f)
                except json.JSONDecodeError:
                    notifieddata = {}
        else:
            notifieddata = {}
        print(type(currday))

        currday_str = str(currday)  
        if notifieddata.get(currday_str) is None:
            notifieddata[currday_str] = []
        if symbol+'_'+self.trade_type in notifieddata[currday_str]:
            return 
        if islive and datetime.today().date() == currday:
            print("This should be notified in telegram asap")
            if lastentrytime > (datetime.now() - timedelta(minutes=60)).time():
                text = f"{self.trade_type} - {symbol} \nEntry : {entry} \nSL : {sl}"
                asyncio.run(telegram_services.send_and_refresh_image(filepath, text))
                notifieddata[currday_str].append(symbol+'_'+self.trade_type)
                with open(telegram_file_path, "w") as f:
                    json.dump(notifieddata, f, indent=4)
            else:
                print("We are late to notify it in talegram")

    def update_sl(self):
        pass

        
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
    
    def strategy1_pinbar_buy(self, df):
        df['min'] = df['low'].cummin()
        df['body'] = abs(df['high'] - np.minimum(df['open'], df['close']))
        df['downwick'] = np.minimum(df['open'], df['close']) - df['low']
        df['goodwick'] = df['downwick'] > df['body'] * 1.5
        df['goodsize'] = (df['high'] - df['low']) > df['atr'] 
        df['pinbar'] = df['goodsize'] & (df['goodwick']) & (df['low']!=df['min'])
        df['breakout1'] = (df['pinbar'].shift(1)) & (df['high'] > df['high'].shift(1)) 
        df['entry1'] = df['high'].shift(1)
        df['sl1'] = df['low'].shift(1)
        df['goodvolume1'] = df['volume'].shift(1) > df['volume'].shift(2)

        return df 
    
    def strategy1_pinbar_sell(self, df):
        df['max'] = df['high'].cummax()
        df['body'] = abs(np.maximum(df['open'], df['close']) - df['low'])
        df['upwick'] = df['high'] - np.maximum(df['open'], df['close']) 
        df['goodwick'] = df['upwick'] > df['body'] * 1.5
        df['goodsize'] = (df['high'] - df['low']) >  df['atr'] 
        df['pinbar'] = df['goodsize'] & (df['goodwick']) & (df['high']!=df['max'])
        df['breakdown1'] = (df['pinbar'].shift(1)) & (df['low'] < df['low'].shift(1)) 
        df['entry1'] = df['low'].shift(1)
        df['sl1'] = df['high'].shift(1)
        df['goodvolume1'] = df['volume'].shift(1) > df['volume'].shift(2)
        return df 

        
    def strategy2_morning_buy_vwap(self, df):
        df['min'] = df['low'].cummin()
        df['vwapcandle'] =  (df['close'] > df['high'].shift(1)) & (df['low'] < df['vwap'] - df['vwap']*0.0005) & (df['time'] >= pd.to_datetime('09:25').time()) & (df['time']< pd.to_datetime('09:45').time())
        df['goodclose'] = df['close'] > (df['close'] - (df['high'] - df['low']) * 0.1)
        df['breakout1'] = (df['vwapcandle'].shift(1)) & (df['high'] > df['high'].shift(1)) 
        df['entry1'] = df['high'].shift(1)
        df['sl1'] = df['low'].shift(1)
        df['goodvolume1'] = df['volume'].shift(1) > df['volume'].shift(2)

        return df 
    
    
    def strategy2_pinbar(self, df):
        df['high_m'] = np.maximum(df['high'], df['high'].shift(1))
        df['low_m'] = np.minimum(df['low'], df['low'].shift(1))
        df['open_m'] = df['open'].shift(1)
        df['close_m'] = df['close']
        df['min'] = df['low_m'].cummin()
        df['body'] = abs(df['high_m'] - np.minimum(df['open_m'], df['close_m']))
        df['downwick'] = np.minimum(df['open_m'], df['close_m']) - df['low_m']
        df['goodwick'] = df['downwick'] > df['body'] * 1.5
        df['goodsize'] = (df['high_m'] - df['low_m']) > df['atr'] 
        df['pinbar'] = df['goodsize'] & (df['goodwick']) & (df['low']!=df['min']) & (df['low'] <= df['low'].shift(1))
        df['breakout2'] = (df['pinbar'].shift(1)) & (df['high'] > df['high'].shift(1)) 
        df['entry2'] = df['high'].shift(1)
        df['sl2'] = df['low'].shift(1)
        df['goodvolume2'] = df['volume'].shift(1) > df['volume'].shift(2)
        return df 

    def strategy3_engulf(self, df):
        df['min'] = df['low'].cummin()
        df['goodsize'] = (df['high_m'] - df['low_m']) > df['atr'] 
        df['ema_failed'] = df['ema_9'] < df['ema_9'].shift(1)
        df['ema_failed'] = df['ema_failed'].cummax()
        df['breakout3'] = df['goodsize'] & (df['low'] < df['ema_9']) & (df['close'] > df['open']) & (df['close'] > df['ema_9']) & (df['ema_failed'] == False) & (df['close'] > df['high'].shift(1))
        df['entry3'] = df['close']
        df['sl3'] = df['low']
        df['goodvolume3'] = df['volume'] > df['volume'].shift(1)
        return df 
    
           
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


    def trade_strategy(self, df, newpeaks, newbottoms, prevdaydf):
        change = (prevdaydf.iloc[-1]['close'] - prevdaydf.iloc[0]['open'] ) / prevdaydf.iloc[0]['open'] * 100
        
        if self.trade_type=='buy':
            if len(df) == 0:
                return 
           
            n = 3
            df = self.Intraday_breakouts(df, n)
            df['breakout'] = (df['max'].shift(1) == df['resitance']) & (df['close'] > df['resistance'])
            df['breakout'] = (df['breakout1'] | df['breakout1'] | df['breakout1'])
            breakdf = df[df['breakout']]

            if len(breakdf) == 0:
                return 
            
            traderow = breakdf.iloc[0]
            entry = None
            sl = None
            goodvolume = None

            if traderow['breakout1']:
                entry = traderow['entry1']
                sl = traderow['sl1']
                goodvolume = traderow['goodvolume1']

            if not goodvolume  or entry < prevdaydf['high'].max():
                return 
            
            # sl = sl - sl * 0.001
            df['sl'] = sl
            df['entry'] = entry
            futdf = df[df['time'] > traderow['time']].copy()
            if len(futdf)==0:
                return 
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
        if self.trade_type == 'sell':
            if change <  -2:
                return 
            if len(df) == 0:
                return 
            df = self.strategy1_pinbar_sell(df)
            df['breakdown'] = (df['breakdown1']) & (df['time'] >= pd.to_datetime('11:00').time()) & (df['time']< pd.to_datetime('13:00').time())
            breakdf = df[df['breakdown']]

            if len(breakdf) == 0:
                return 
            
            traderow = breakdf.iloc[0]
            entry = None
            sl = None
            goodvolume = None

            if traderow['breakdown1']:
                entry = traderow['entry1']
                sl = traderow['sl1']
                goodvolume = traderow['goodvolume1']
            
            if not goodvolume  or entry > prevdaydf['low'].min():
                return 
            
            df['sl'] = sl
            df['entry'] = entry
            futdf = df[df['time'] > traderow['time']].copy()
            if len(futdf)==0:
                return 
            futdf['rr'] = round(((futdf['entry'] - futdf['low'])/(futdf['sl'] - futdf['entry'])), 1) 
            futdf['dayendrr'] = round(((futdf['entry'] - futdf['close'])/(futdf['sl'] - futdf['entry'])), 1) 
            futdf['maxrr'] = futdf['rr'].cummax()
            futdf['slhit'] = futdf['high'] > futdf['sl']
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
        df = Indicators.atr(df)
        df = Indicators.ema(df, 9)
        df = Indicators.vwap(df)
        df['day'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        df = df.dropna()
        df.reset_index(inplace = True, drop = True)
        alldays = sorted(df['day'].unique(), key=pd.to_datetime)
        if len(alldays) == 0:
            return 
        
        for i,x_day in enumerate(alldays):
            prevdaydf = None
            if i <= 1:
                continue
            
            prevdaydf = utils.filter_data_by_dates(df.copy(), alldays[max(i-1,0)], alldays[i-1])
            if islive and x_day != datetime.today().date():
                continue

            dftmp = utils.filter_data_by_dates(df.copy(), x_day, x_day)
            newpeaks = []
            newbottoms = []
            print('test for :::: ', x_day)
            if islive:
                dftmp = dftmp.iloc[:-1].copy()
                # print(dftmp)
                # print(prevdaydf)
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

import time
while(True):
    for symbol in pd.read_csv('ind_nifty500list.csv')['Symbol']:
        try:
   
            token = utils.get_token(exchange, symbol + '-EQ')
            orgdf = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval)  
            levelsdf = None
            if draw_levels:    
                levelsdf = find_previous_levels(orgdf.copy())
                levelsdf['day'] = levelsdf['timestamp'].dt.date
            mystrategy = High_volume_surge_on_day(orgdf.copy(), 'buy', symbol = symbol, save_trade = save_image_tmp,levelsdf = levelsdf)
            results = mystrategy.run()
            # mystrategy = High_volume_surge_on_day(orgdf.copy(), 'sell', symbol = symbol, save_trade = save_image_tmp,levelsdf = levelsdf)
            # results = mystrategy.run()

        except Exception as e:
            # raise ValueError(e)
            time.sleep(1)
            print(e)
    break

    
        
df = pd.DataFrame(all_results)
df.to_csv('allresults.csv', index = False)
print(df)