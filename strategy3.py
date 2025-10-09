
'''Idea : start trading after 9:45
''' 


# %load_ext autoreload
# %autoreload 2

import ast

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
end_date = datetime(2025, 9, 18, 9, 10)
interval = "5min"
all_results = []
save_image_tmp = True
s_r_timeframe = '30min'
level_window = 5
maxnumber_of_levels = 5
save_by_stock = False
draw_levels = True
islive = True

class High_volume_surge_on_day(strategy.BaseStrategy):         
    def save_image(self, df, day, peaks, bottoms, entry, sl, maxrr, dayendrr, prevdaydf):
        if not self.kwargs.get('save_trade'): 
            return 
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

        entry = pd.Series(entry, index=df.index)
        ema_plots.append(mpf.make_addplot(entry, color='green', linestyle='-', width=3))
        
        sl = pd.Series(sl, index=df.index)
        ema_plots.append(mpf.make_addplot(sl, color='red', linestyle='-', width=5))

        for bottom in bottoms:
            if bottom < stock_high and bottom > stock_low:
                line = pd.Series(bottom, index=df.index)
                ema_plots.append(mpf.make_addplot(line, color='blue', linestyle='-', width=1))

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
    def inside_candle_breakout(self, df):
        df['redcandle'] = df['close'] < df['open']
        df['goodclose'] = (df['close'] > (df['high'] - 0.2 * (df['high'] - df['low'])))
        df['insidecandle'] = (df['high'] < df['high'].shift(1)) & (df['low'] > df['low'].shift(1)) 
        df['insidecandle_breakout'] = (df['close'] > df['high'].shift(2)) & (df['insidecandle'].shift(1)) & (df['goodclose']) & ((df['close'] - df['low']) > 1 * df['atr'])
        return df

    def pinbar_at_support(self, df, ema):
        df['smallbody'] = abs(df['close'] - df['open'])/(df['high'] - df['low'])*100 < 25
        df['goodclose'] = (df['close'] > (df['high'] - 0.1 * (df['high'] - df['low'])))
        df['redcandle'] = df['close'] < df['low']
        df[ema+'_breakout'] = (df['goodclose']) & (df['close'] > df[ema])
        return df
    
    def pinbar_at_bottom(self, df):
        df['smallbody'] = abs(df['close'] - df['open'])/(df['high'] - df['low'])*100 < 25
        df['goodclose'] = (df['close'] > (df['high'] - 0.1 * (df['high'] - df['low'])))
        df['redcandle'] = df['close'] < df['low']
        df['min'] = df['low'].cummin()
        df['islowest'] = df['min'] == df['low']
        df['bottom_pinbar'] = (df['goodclose']) & (df['close'] > np.maximum(df['open'].shift(1), df['close'].shift(1))) & (df['islowest'])
        return df
    
    def Intraday_breakdowns(self, df, window):
        df['support'] = np.nan
        df['min'] = df['low'].cummin()
        df['islowest'] = df['min'] == df['low']

        for i in range(len(df)):
            if i == len(df)-window:
                break

            if i == 0:
                right = df.iloc[i+1:i+window+1]
                curr = df.iloc[i]
                if curr['low'] < right['low'].min() and curr['islowest']:
                    df.loc[i, 'support'] = df.iloc[i]['low']
            
            else:
                left = df.iloc[max(i-window,0) : i+1]
                right = df.iloc[i : i+window+1]
                curr = df.iloc[i]
                if curr['low'] <= left['low'].min() and curr['low'] <= right['low'].min() and curr['islowest']:
                    df.loc[i, 'support'] = df.iloc[i]['low']

        df['support'] = df['support'].ffill()
        df['support'] = df['support'].shift(window)
        df = df.drop(columns = ['islowest'])
        
        return df

    def trade_strategy(self, df, newpeaks, newbottoms, prevdaydf):
        if len(df) == 0:
            return
        if self.trade_type == 'buy':
            df = self.Intraday_breakouts(df, 2)
            df['max'] = df['high'].cummax()
            df['min'] = df['low'].cummin()
            df['goodclose'] = (df['close'] > (df['high'] - 0.2 * (df['high'] - df['low'])))
            df['breakout1'] = (df['high'] > df['resistance']) & (df['resistance'] == df['max'].shift(2))

            df['withoutclosebreakout'] = np.where(df['breakout1'], 1, 0)
            df['withoutclosebreakout'] = df['withoutclosebreakout'].cumsum()
            df['volume_mean'] = df['volume'].rolling(window = 3).mean()
            df['goodvolume'] = (df['volume'] > df['volume_mean'].shift(1))

            df['breakout'] = (df['close'] > (df['high'].shift(1) + df['high'].shift(1) * 0.001)) & (df['breakout1'] | df['breakout1'].shift(1)) 
            df['ema_failed'] = np.where(df['close'] < df['ema_21'], 1, 0)
            df['ema_failed'] = df['ema_failed'].cumsum()
            df['support'] = np.where((df['low'] < df['low'].shift(-1)) & (df['low'] < df['low'].shift(1)) &  (df['low'] < df['low'].shift(1)), df['low'], np.nan)
            df['support'] = df['support'].shift(1)
            df.loc[0,'support'] = df.iloc[0]['low']
            df['support'] = df['support'].ffill()
            df['sl'] = df['support']
            # df['sl'] = np.minimum(df['low'], df['low'].shift(1))
            breakdf = df[df['breakout']]

            if len(breakdf) == 0:
                return

            traderow = breakdf.iloc[0]
            entry = traderow['close']
            sl = traderow['sl']
            slpct = (entry - sl)/sl * 100
            movetillnow = (entry - traderow['min'])/entry * 100
            if not traderow['goodclose'] or traderow['withoutclosebreakout'] >= 2 or not traderow['goodvolume']:
                return 
            if traderow['time'] < pd.to_datetime('09:40').time() or traderow['time'] > pd.to_datetime('11:00').time() or (movetillnow > 3.5) or (movetillnow < 1.5) or (traderow['ema_failed'] >= 4) :
                return      
            
            sl = max(traderow['ema_21'], traderow['support'])
            sl = min(sl, entry - entry * 0.003)
            sl = sl - sl * 0.0005
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
        if self.trade_type == 'sell':
            df = self.Intraday_breakdowns(df, 2)
            df['max'] = df['high'].cummax()
            df['min'] = df['low'].cummin()
            df['ema_failed'] = np.where(df['close'] > df['ema_21'], 1, 0)
            df['ema_failed'] = df['ema_failed'].cumsum()

            df['breakdown1'] = (df['low'] < df['support']) & (df['support'] == df['min'].shift(2))
            
            df['withoutclosebreakdown'] = np.where(df['breakdown1'], 1, 0)
            df['withoutclosebreakdown'] = df['withoutclosebreakdown'].cumsum()
            df['volume_mean'] = df['volume'].rolling(window = 3).mean()
            df['goodvolume'] = (df['volume'] > df['volume_mean'].shift(1))
            df['goodclose'] = (df['close'] < (df['low'] + 0.2 * (df['high'] - df['low'])))

            df['breakdown'] = (df['close'] < (df['low'].shift(1) - df['low'].shift(1) * 0.001)) & (df['breakdown1'] | df['breakdown1'].shift(1))
            df['resistance'] = np.where((df['high'] > df['high'].shift(-1)) & (df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(1)), df['high'], np.nan)
            
            df['resistance'] = df['resistance'].shift(1)
            df.loc[0,'resistance'] = df.iloc[0]['high']
            df['resistance'] = df['resistance'].ffill()
            df['sl'] = df['resistance']
            breakdf = df[df['breakdown']]

            if len(breakdf) == 0:
                return

            traderow = breakdf.iloc[0]
            entry = traderow['close']
            sl = traderow['sl']
            movetillnow = (traderow['max'] - entry)/entry * 100

            if not traderow['goodclose'] or traderow['withoutclosebreakdown'] >= 2 or not traderow['goodvolume']:
                return 

            if traderow['time'] < pd.to_datetime('09:35').time() or traderow['time'] > pd.to_datetime('11:00').time() or (movetillnow > 2.5) or (movetillnow < 1) or (traderow['ema_failed'] >= 4):
                return      
            
            sl = max(traderow['ema_21'], traderow['sl'])
            sl = max(sl, entry + entry * 0.003)
            sl = sl + sl * 0.0005
    
            df['sl'] = sl
            df['entry'] = entry
            futdf = df[df['time'] > traderow['time']].copy()
            if len(futdf)==0:
                return 
            futdf['sl'] = sl
            futdf['entry'] = entry
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
        df = Indicators.ema(df, 8)
        df = Indicators.ema(df, 21)
        df = Indicators.ema(df, 120)
        df = Indicators.vwap(df)
        df = Indicators.atr(df)

        df['day'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        df = df.dropna()
        df.reset_index(inplace = True, drop = True)
        alldays = sorted(df['day'].unique(), key=pd.to_datetime)
        if len(alldays) == 0:
            return 
        prevday = alldays[0]

        for x_day in alldays:
            
            prevdaydf = None
            if prevday != x_day:
                newprevday = pd.to_datetime(prevday) - timedelta(3)
                prevdaydf = utils.filter_data_by_dates(df.copy(), newprevday, prevday)

            if islive and x_day != datetime.today().date():
                prevday = x_day
                continue

    

            dftmp = utils.filter_data_by_dates(df.copy(), x_day, x_day)
            newpeaks = []
            newbottoms = []
            print('test for :::: ', x_day)
            if islive:
                dftmp = dftmp.iloc[:-1].copy()
                print(dftmp)
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


while(True):
    for sector, stocks in sectors.items(): 
        # token = utils.get_token_for_index(exchange, sector)
        # if token is None:
        #     continue
        # indexdf = dataset.get_data(stream, 'NSE', sector, token, start_date, end_date, interval)
        # indexdf = Indicators.ema(indexdf, 11)  
        # indexdf['day'] = indexdf['timestamp'].dt.date
        # indexdf['sectortrend'] = np.where(indexdf['close'] > indexdf['ema_11'], 1, -1) 
        # indexdf = indexdf[['timestamp', 'sectortrend']]
        for symbol in stocks:
            try:
                token = utils.get_token(exchange, symbol + '-EQ')
                orgdf = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval) 
                levelsdf = None
                if draw_levels:    
                    levelsdf = find_previous_levels(orgdf.copy())
                    levelsdf['day'] = levelsdf['timestamp'].dt.date
                # orgdf = pd.merge(orgdf, indexdf, on = 'timestamp', how = 'left')
                mystrategy = High_volume_surge_on_day(orgdf.copy(), 'buy', symbol = symbol, save_trade = save_image_tmp,levelsdf = levelsdf)
                results = mystrategy.run()

                mystrategy = High_volume_surge_on_day(orgdf.copy(), 'sell', symbol = symbol, save_trade = save_image_tmp,levelsdf = levelsdf)
                results = mystrategy.run()
            except Exception as e:
                print(e)
                raise ValueError(e)

    if not islive:
        break

df = pd.DataFrame(all_results)
df.to_csv('allresults.csv', index = False)
print(df)
