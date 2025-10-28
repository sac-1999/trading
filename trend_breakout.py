
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
start_date = datetime(2025, 10, 5, 9, 10)
end_date = datetime(2025, 10, 30, 15, 30)
interval = "5min"
all_results = []
save_image_tmp =  True
s_r_timeframe = '15min'
level_window = 10
maxnumber_of_levels = 2
save_by_stock = False
draw_levels = False
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
        
        # df = pd.concat([prevdaydf, df], axis = 0)
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
        if 'ema_30' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['ema_30'], color='blue', width=2))
        if 'ema_50' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['ema_50'], color='blue', width=2))
        if 'ema_100' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['ema_100'], color='black', width=3)) 
        # if 'vwap' in list(df.columns):
        #     ema_plots.append(mpf.make_addplot(df['vwap'], color='black', width=5)) 

        
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
    

    def stock_for_day(self, df, prevdaydf):
        firstcandle = df.iloc[0]
        secondcandle = df.iloc[1]
        green = (firstcandle['close'] - firstcandle['open'])
        secondgreen = (secondcandle['close'] - secondcandle['open'])
        goodclose = (secondcandle['close'] > max(firstcandle['open'], firstcandle['close'])) and (secondcandle['close'] > prevdaydf['high'].max())
        return goodclose and secondgreen
    


    def trade_strategy(self, df, newpeaks, newbottoms, prevdaydf):
        df.reset_index(drop = True, inplace = True)
        df['index'] = df.index
        # print(df)
        lastdayclose = prevdaydf.iloc[-1]['close']
        lastdaychange = (prevdaydf.iloc[-1]['close'] - prevdaydf.iloc[0]['open'])/ prevdaydf.iloc[0]['open'] * 100
        if self.trade_type=='buy':
            if lastdaychange > 1:
                return 
            if len(df) == 0:
                return 
            
            df = self.Intraday_breakouts(df, 3)
            df['max'] = df['high'].cummax()
            df['min'] = df['low'].cummin()
            df['breakout1'] = (df['high'] > df['resistance'].shift(1)) & (df['max'].shift(1) == df['resistance'].shift(1))
            df['failed_ema'] = ((df['ema_9'] < df['ema_9'].shift(1)) | (df['close'] < df['ema_100'])) & (df['index'] >= 2)
            df['failed_ema'] = df['failed_ema'].cummax()

            df['touchedema'] = (df['low'] <= df['ema_9']) & (df['time'] >= pd.to_datetime('09:30').time())
            df['touchedema'] = df['touchedema'].cummax()
            
            df['breakout'] = (df['failed_ema'] == False)  & (df['breakout1']) & (df['time'] < pd.to_datetime('12:30').time()) & (df['time'] >= pd.to_datetime('09:50').time())
            df['entry'] = df['close']

            df['expectsl'] = df['low'].rolling(6).min()
            df['sl'] = df['ema_9']
            
            breakdf = df[df['breakout']] 
            if len(breakdf) == 0:
                return 
            
            traderow = breakdf.iloc[0]
            entry = traderow['entry']
            sl = traderow['sl']
            df['entry'] = entry
            df['sl'] = sl
            
            if traderow['close'] < prevdaydf.iloc[-1]['high']:
                return 

            if traderow['trend'] == False:
                return 

            
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
        
        

    def apply_strategy(self):   
        df = self.df.copy()
        df = Indicators.atr(df)
        df = Indicators.ema(df, 9)
        df = Indicators.ema(df, 21)
        df = Indicators.ema(df, 30)
        df = Indicators.ema(df, 50)
        df = Indicators.ema(df, 100)
        df = Indicators.vwap(df)
  
        df['day'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        df = df.dropna()
        df.reset_index(inplace = True, drop = True)
        alldays = sorted(df['day'].unique(), key=pd.to_datetime)
        if len(alldays) == 0:
            return 
        
        for i,x_day in enumerate(alldays):
            # if x_day != datetime.today().date():
            #     continue
            prevdaydf = None
            if i <= 1:
                continue
            
            prevdaydf = utils.filter_data_by_dates(df.copy(), alldays[max(i-2,0)], alldays[i-1])
            # print(self.kwargs['symbol'], prevdaydf['high'].max())
            if islive and x_day != datetime.today().date():
                continue

            dftmp = utils.filter_data_by_dates(df.copy(), x_day, x_day)
            newpeaks = []
            newbottoms = []

            print((datetime.today() - timedelta(2)).date(),'-----------------')


            print('test for :::: ', x_day, dftmp)
            if islive:
                # dftmp = dftmp.iloc[:-1].copy()
                print(dftmp)
                # print(prevdaydf)
            if draw_levels:
                levels = self.find_relevant_levels(dftmp, x_day)
                if levels is not None:
                    if dftmp is not None:
                        newpeaks , newbottoms = levels
            # print(dftmp)
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

# stocklist = list(pd.read_csv('ind_nifty100list.csv')['Symbol'])
# print(stocklist)

# with open("index_stock.json", "r") as f:
#     sectors = json.load(f)

# for sector, stocks in sectors.items(): 
#     print("--"*50, sector)
#     token = utils.get_token_for_index(exchange, sector)
#     if token is None:
#         continue
#     indexdf = dataset.get_data(stream, 'NSE', sector, token, start_date, end_date, interval)
#     indexdf['day'] = indexdf['timestamp'].dt.date

    
#     daily_group = indexdf.groupby('day')[['high', 'low', 'close']]

#     daily_stats = daily_group.agg({
#         'high': ['max', 'first'],
#         'low': ['min', 'first'],
#         'close': 'last'
#     })

#     daily_stats.columns = ['prev_day_high', 'start_high', 'prev_day_low', 'start_low', 'prev_day_close']
#     daily_stats.reset_index(inplace = True)
#     daily_stats['prev_day_high'] = daily_stats['prev_day_high'].shift(1)
#     daily_stats['prev_day_low'] = daily_stats['prev_day_low'].shift(1)
#     daily_stats['prev_day_close'] = daily_stats['prev_day_close'].shift(1)

#     indexdf = pd.merge(indexdf, daily_stats, on = 'day', how = 'left')
#     indexdf = indexdf.dropna()
    
#     indexdf['sector_trend'] = np.where((indexdf['close'] > indexdf['prev_day_close']) & (indexdf['close'] > indexdf['start_high']),1,
#                                 np.where((indexdf['close'] < indexdf['prev_day_close']) & (indexdf['close'] < indexdf['start_low']),-1,0))
#     indexdf = indexdf[['timestamp', 'sector_trend']]

#     for symbol in stocks:
#         if symbol not in stocklist:
#             continue
#         try:
#             token = utils.get_token(exchange, symbol + '-EQ')
#             orgdf = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval) 
#             levelsdf = None
#             orgdf = pd.merge(orgdf, indexdf, on = 'timestamp', how = 'left')
#             print(orgdf)
#             mystrategy = High_volume_surge_on_day(orgdf.copy(), 'buy', symbol = symbol, save_trade = save_image_tmp,levelsdf = levelsdf)
#             results = mystrategy.run()
#         except Exception as e:
#             print(e)
#             # raise ValueError(e)


stocklist = list(pd.read_csv('ind_nifty100list.csv')['Symbol'])
print(stocklist)


index = 'Nifty 50'
token = utils.get_token(exchange, index)
niftydf = dataset.get_data(stream, 'NSE', index, token, start_date, end_date, interval)
niftydf['day'] = niftydf['timestamp'].dt.date
daily_group = niftydf.groupby('day')[['high', 'low', 'close']]
daily_stats = daily_group.agg({
        'high': 'first',
        'low': 'first',
    })
daily_stats.columns = ['open_high', 'open_low']
daily_stats.reset_index(inplace = True)
niftydf = pd.merge(niftydf, daily_stats, on = 'day', how = 'left')
niftydf = Indicators.ema(niftydf, 8)
niftydf['trend'] = (niftydf['close'] > niftydf['ema_8']) & (niftydf['ema_8'] > niftydf['ema_8'].shift(1)) & (niftydf['close'] > niftydf['open_high'])
niftydf = niftydf[['timestamp', 'trend']].copy()
print(niftydf)

for symbol in stocklist: 
    try:
        token = utils.get_token(exchange, symbol + '-EQ')
        orgdf = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval) 
        levelsdf = None
        orgdf = pd.merge(orgdf, niftydf, on = 'timestamp', how = 'left')
        print(orgdf)
        mystrategy = High_volume_surge_on_day(orgdf.copy(), 'buy', symbol = symbol, save_trade = save_image_tmp,levelsdf = levelsdf)
        results = mystrategy.run()
    except Exception as e:
        print(e)
        # raise ValueError(e)



df = pd.DataFrame(all_results)
df.to_csv('allresults.csv', index = False)
print(df)