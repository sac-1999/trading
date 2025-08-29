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
save_image = True
risk = 1000
rrlist = [1.5, 2, 2.5]
tax_pct = 0.1
changedf_dict = {}


class insidebar_strategy(strategy.BaseStrategy):
    def future(self, orgdf, entry, sl, trade_type, day,  tradetime, bookedrr = [1.5,2,3,4, 100]):
        results = []
        if trade_type == 'buy':
            slpoints = entry - sl
        
            for trail in [True, False]:
                for rr in bookedrr:
                    df = orgdf.copy()
                    bookedprofit = 0
                    prevrow = None
                    exit = -1
                    for i,row in df.iterrows():
                        bookedprofit = (row['high'] - entry)/slpoints
                        
                        if row['low'] < sl:
                            bookedprofit = -1
                            exit = sl
                            break
                        

                        if bookedprofit > rr:
                            bookedprofit = rr
                            exit = row['high']
                            break

                        if trail and prevrow is not None:
                            if row['time'] < pd.to_datetime("12:30").time() and row['close'] < row['ema_21'] and row['close'] < prevrow['low']:
                                bookedprofit = (row['close'] - entry)/slpoints
                                exit = row['close']
                                break
                        
                        if row['time'] >= pd.to_datetime("14:55").time():
                            bookedprofit = (row['close'] - entry)/slpoints
                            exit = row['close']
                            break

                        prevrow = row
                    
                    results.append({'trail':trail, 'bookat':rr, 'profit':round(bookedprofit,1), 'day' : day, 'tradetime' : tradetime,  'entry':entry, 'sl':sl, 'exit' : exit, 'symbol':self.kwargs.get('symbol')})

        if trade_type == 'sell':
            slpoints = sl - entry
        
            for trail in [True, False]:
                for rr in bookedrr:
                    df = orgdf.copy()
                    bookedprofit = 0
                    prevrow = None
                    exit = -1
                    for i,row in df.iterrows():
                        bookedprofit = (entry - row['low'])/slpoints
                        if row['high'] > sl:
                            bookedprofit = -1
                            exit = row['high']
                            break
                        

                        if bookedprofit > rr:
                            bookedprofit = rr
                            exit = row['low']
                            break

                        if trail and prevrow is not None:
                            if row['time'] < pd.to_datetime("12:30").time() and row['close'] > row['ema_21'] and row['close'] > prevrow['high']:
                                bookedprofit = (entry - row['close'])/slpoints
                                exit = row['close']
                                break
                        
                        if row['time'] >= pd.to_datetime("14:55").time():
                            bookedprofit = (entry - row['close'])/slpoints
                            exit = row['close']
                            break

                        prevrow = row
                    
                    results.append({'trail':trail, 'bookat':rr, 'profit':round(bookedprofit,1), 'day' : day, 'tradetime' : tradetime, 'entry':entry, 'sl':sl, 'exit' : exit, 'symbol':self.kwargs.get('symbol')})
        return results
    def create_candles_rule(self, rowlist):
        firstrow = rowlist[-1]
        secondrow = rowlist[-2]
        thirdrow = rowlist[-3]

        if self.trade_type == 'buy':
            rule1 = firstrow['close'] >= thirdrow['high']
            rule2 = (secondrow['close'] > secondrow['open']) != (thirdrow['close'] > thirdrow['open'])
            mid2 = (secondrow['high'] +  secondrow['low'])/2
            rule3 = firstrow['low'] <= mid2
            rule4 = (thirdrow['high'] > secondrow['high']) and (thirdrow['low'] < secondrow['low'])
            rule5 = firstrow['low']<= secondrow['low']
        
            if rule1 and rule2 and rule3 and rule4 and rule5 and (firstrow['volume'] > secondrow['volume']):
                return True
            
        if self.trade_type == 'sell':
            rule1 = firstrow['close'] <= thirdrow['low']
            rule2 = (secondrow['close'] > secondrow['open']) != (thirdrow['close'] > thirdrow['open'])
            mid2 = (secondrow['high'] +  secondrow['low'])/2
            rule3 = firstrow['high'] >= mid2
            rule4 = (thirdrow['high'] > secondrow['high']) and (thirdrow['low'] < secondrow['low'])
            rule5 = firstrow['high']>= secondrow['high']

            if rule1 and rule2 and rule3 and rule4 and rule5 and (firstrow['volume'] > secondrow['volume']):
                return True
            
        return False            
    
    def save_image(self, df, stock, day, entry, sl, exit, tradetime):
        if stock is None:
            raise ValueError("Trades can save as symbol name is missing")
        date = str(day)[:10]
        foldername = f"samplesimages/{stock}"
        os.makedirs(foldername, exist_ok=True)
        filename = f"{foldername}/{'-'.join(date.split(':'))}.jpg"
        df['time'] = pd.to_datetime(df['timestamp'])
        df.set_index('time', inplace=True)
        ema_plots = []

            # Set timestamp as datetime index
        df['time'] = pd.to_datetime(df['timestamp'])
        df.set_index('time', inplace=True)

        entry_line = pd.Series(entry, index=df.index)
        sl_line = pd.Series(sl, index=df.index)
        exit_line = pd.Series(exit, index=df.index)


        # Create EMA overlays
        ema_plots = [
            mpf.make_addplot(entry_line, color='purple', linestyle='-', width=2),
            mpf.make_addplot(sl_line, color='red', linestyle='--', width=2)
           
        ]


        # if 'vwap' in list(df.columns):
        #         ema_plots.append(mpf.make_addplot(df['vwap'], color='red', width=3))
        # col = df.columns
        # col = sorted(col)
        width = 1
        for col in list(df.columns): 
            if 'ema_' in col or 'supertrend' in col:
                ema_plots.append(mpf.make_addplot(df[col], color='blue', width=width))
                width += 1
        
        # ema_plots.append(mpf.make_addplot(df['vwap'], color='red', width=2))

        mpf.plot(df, type='candle', style='charles', title=f"{tradetime}",
                ylabel='Price', addplot=ema_plots,
                figsize=(16, 8),
                savefig=dict(fname=filename, dpi=100),
                volume=True, 
                )


    def day_handle(self,df, stock, day):
        orgdf = df.copy()
        df = df[(df['time'] < pd.to_datetime("12:45").time())].copy()
        df.reset_index(inplace = True, drop = True)
        rowlist = []
        for i, row in df.iterrows():
            rowlist.append(row)
            if row['time'] < pd.to_datetime("10:00").time():
                continue

            if len(rowlist)<3:
                continue

            if self.create_candles_rule(rowlist):
                print(day)
                entry = row['close']
                sl = None

                if self.trade_type == 'buy':
                    sl = row['low']
        
                if self.trade_type == 'sell':
                    sl = row['high']

                df = orgdf[(orgdf['time'] > row['time']) & (orgdf['time'] <= pd.to_datetime("14:55").time())].copy()
                results = self.future(df, entry, sl,self.trade_type, day, row['timestamp'])
                return results
        return None
        # self.save_image(df, stock, day)
        
    
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
            output = self.day_handle(dftmp.copy(), self.kwargs.get('symbol'), x)
            if output is not None:
                for ot in output:
                    if not ot['trail'] and  ot['bookat'] == 3:
                        if self.kwargs.get('save_trade'):
                            # utils.save_plot(dftmp,self.kwargs.get('symbol') + '_' + self.trade_type, ot)
                            self.save_image(dftmp, self.kwargs.get('symbol'), x, ot['entry'], ot['sl'], ot['exit'], ot['tradetime'])
                        # print(ot)
            
for symbol in pd.read_csv('ind_nifty50list.csv')['Symbol']:
    if 'adani' in symbol.lower():
        continue

    try:
        token = utils.get_token(exchange, symbol + '-EQ')
        orgdf = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval)
        mystrategy = insidebar_strategy(orgdf.copy(), 'buy', window = 3, ema_list = [8, 21, 50], symbol = symbol, save_trade = save_image, live = is_live, change_dict = changedf_dict)
        mystrategy.run()

        # orgdf = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval)
        mystrategy = insidebar_strategy(orgdf.copy(), 'sell', window = 3, ema_list = [8, 21, 50], symbol = symbol, save_trade = save_image, live = is_live, change_dict = changedf_dict)
        mystrategy.run()
        
        
    except Exception as e:
        print('Error : ', e)


df = pd.DataFrame(all_results)
df.to_csv("allresults.csv",index=False)