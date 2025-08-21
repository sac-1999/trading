from abc import ABC, abstractmethod
import pandas as pd
import utils
from candles import *
from tradefuture import TradeFuture
from datetime import datetime, timedelta

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, df: pd.DataFrame, trade_type: str, atr_sl_multiplier = 1, **kwargs):
        self.df = df.copy()
        self.trade_type = trade_type.lower()
        self.atr_sl_multiplier = atr_sl_multiplier
        self.kwargs = kwargs

    @abstractmethod
    def apply_strategy(self):
        """Apply the specific strategy logic."""
        pass

    def run(self):
        """Run the full strategy pipeline."""
        return self.apply_strategy()


class CloseOutOfPreviousCandle(BaseStrategy):
    """Implements close-out-of-previous-candle strategy."""
    def apply_strategy(self):
        df = self.df.copy()
        df['time'] = df['timestamp'].dt.time
        df['condition'] = (df['time'] > pd.to_datetime("09:40").time()) & (df['time'] < pd.to_datetime("12:00").time())
        
        if self.trade_type == "buy":
            df['istrade'] = df['condition'] & (df['close'] > df['high'].shift(1)) 
        elif self.trade_type == 'sell':
            df['istrade'] = df['condition'] & (df['close'] < df['low'].shift(1)) 
        else:
            raise ValueError(f"Unknown trade type: {self.trade_type}")
        df.drop(columns = ['time', 'condition'], inplace  = True)
        df.reset_index(drop = True, inplace = True)
        self.df = df
        

class Intraday_trade_on_close(BaseStrategy):
    """Implements close-out-of-previous-candle strategy."""
    def apply_strategy(self):
        df = self.df.copy()
        df['time'] = df['timestamp'].dt.time
        df['condition'] = (df['time'] > pd.to_datetime("09:40").time()) & (df['time'] < pd.to_datetime("12:00").time())
        
        if self.trade_type == "buy":
            df['istrade'] = df['condition'] & (df['close'] > df['high'].shift(1)) 
        elif self.trade_type == 'sell':
            df['istrade'] = df['condition'] & (df['close'] < df['low'].shift(1)) 
        else:
            raise ValueError(f"Unknown trade type: {self.trade_type}")
        df.drop(columns = ['time', 'condition'], inplace  = True)
        df.reset_index(drop = True, inplace = True)
        self.df = df



''' Buy if above previous day low and 15 min candle closes above previous candle
timeframe : 15 min
factors : '''


class strategy15MinPreviousDay(BaseStrategy):
    def apply_strategy(self):
        df = self.df.copy()
        df = Indicators.atr(df)
        # df = Indicators.ema(df, 9)
        # df = Indicators.ema(df, 21)
        df = Indicators.ema(df, 11)
        df = Indicators.ema(df, 30)
        df = Indicators.ema(df, 50)
        df = Indicators.ema(df, 100)
        df = Indicators.supertrend(df, 10, 3)
        df = Indicators.supertrend(df, 10, 2)
        df = Indicators.supertrend(df, 8, 3)
        df = Indicators.supertrend(df, 15, 1)
        df = Indicators.vwap(df)
        df = Indicators.rsi(df)
        df = Indicators.bollinger_bands(df)
        df = Indicators.macd(df)
        df = Indicators.adx(df)
        df['day'] = df['timestamp'].dt.date
        daydf = utils.resample(df.copy(), '1d')
        daydf['day'] = daydf['timestamp'].dt.date
        daydf['day'] = daydf['day'].shift(-1)
        daydf = daydf.drop(['timestamp'], axis = 1)
        daydf.rename(columns  = {'open' : 'previous_day_open',
            'close' : 'previous_day_close',
            'low' : 'previous_day_low',
            'high' : 'previous_day_high',
            'volume' : 'previous_day_volume'}, inplace = True)
        df = pd.merge(df, daydf, on = 'day', how = 'left')
        df['time'] = df['timestamp'].dt.time
        df['condition'] = (df['time'] > pd.to_datetime("09:40").time()) & (df['time'] < pd.to_datetime("12:00").time())

        ## buy side 
        if self.trade_type=='buy':
            df['istrade'] = (df['close'] > df['high'].shift(1))  & (df['close'].shift(1) < df['open'].shift(1)) & (df['condition'])

        ## sell side 
        elif self.trade_type == 'sell':
            df['istrade'] = (df['close'] < df['low'].shift(1)) & (df['close'].shift(1) > df['open'].shift(1)) & (df['condition'])

        else:
            raise ValueError(f"Unknown trade type: {self.trade_type}")
        
        tradefut = TradeFuture(df.copy(), self.trade_type, 'close', self.atr_sl_multiplier)
        df = tradefut.execute()
        self.df = df


class EMA_8_21_50_100_Aligned_by_Ayushi(BaseStrategy):
    def stock_selection(self, rowlist):
        for i in range(0,2):
            row = rowlist[i]
            if i==0:
                if row['close'] < row['open']:
                    return False
            elif i == 1:
                if (row['close'] > rowlist[i-1]['high']) and (row['open'] >= row['previous_day_high']):
                    return True
            else:
                return False
        return False
        

    def create_candles_rule(self,rowlist, trade_type, baseindicator = 'ema_8'):
        # row = rowlist[-1]
        # prevrow = rowlist[-2]
        # if row['low'] < row['ema_8'] and row['close'] > max(prevrow['close'], prevrow['open']):
        #     return True
        # return False

        pinbar = is_pinbar(rowlist, trade_type)
        # engulfing = is_engulfing(rowlist, trade_type)
        inside_bar = is_inside_bar(rowlist[:-1], trade_type)
        star_pattern = is_star_pattern(rowlist, trade_type)
        # doji = is_doji(rowlist[:-1])
        row = rowlist[-1]
        prevrow = rowlist[-2]

        if trade_type == 'buy':
            if  ((inside_bar and row['close'] > prevrow['high']) or (star_pattern) or (pinbar)) and (row['low'] <= row[baseindicator] or  prevrow['low'] <= prevrow[baseindicator]) and row['close'] > row[baseindicator]:
                return True
            
        if trade_type == 'sell':
            if ((inside_bar and row['close'] < prevrow['low']) or (star_pattern) or (pinbar)) and (row['high'] >= row[baseindicator] or prevrow['high'] >= prevrow[baseindicator])  and row['close'] < row[baseindicator]:
                return True            
        return False
    
    def future(self, df, entry, sl):
        maxrr = 0
        for i,row in df.iterrows():
            if self.trade_type == 'buy':
                maxrr = max(maxrr, (row['high'] - entry) / (entry - sl))
                
            if self.trade_type == 'sell':
                maxrr = max(maxrr,(entry - row['low']) / (sl - entry))
            
        return maxrr

    def day_handle(self, df, prevdf):
        orgdf = df.copy()
        df = df[(df['time'] < pd.to_datetime("11:30").time())].copy()
        df.reset_index(inplace = True, drop = True)
        output = {}
        output['trade_type'] = self.trade_type

        
        if self.trade_type == 'buy':
            rowlist = []
            for i, row in df.iterrows():
                rowlist.append(row)                
                if len(rowlist) < 2 :
                    continue

                if len(rowlist) == 2:
                    if self.stock_selection(rowlist) == False:
                        return

                prevrow = rowlist[-2]
                if row['emaaligned'] is False or row['close'] < row['ema_21']:
                    return 
                
                if prevrow is not None:
                    myrule = self.create_candles_rule(rowlist, self.trade_type)
                    if myrule:
                        entry = row['close']
                        sl = min(entry - 1 * row['atr'], row['low'])
                        sl = min(sl, entry - 0.003 * entry)

                        output['entry'] = entry
                        output['sl'] = sl
                        output['tradetime'] = row['timestamp']
                        output['previous_day_low'] = row['previous_day_low']
                        output['previous_day_open'] = row['previous_day_open']
                        output['previous_day_close'] = row['previous_day_close']
                        output['previous_day_high'] = row['previous_day_high']
                        output['supertrend_15_1'] = row['supertrend_15_1']
                        output['adx'] = row['adx']
                        output['atr'] = row['atr']
                        df = orgdf[(orgdf['time'] > row['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
                        output['goodtrade'] = self.future(df, output['entry'], output['sl'])
                        return output
                    
        if self.trade_type == 'sell':
            rowlist = []
            for i, row in df.iterrows():
                rowlist.append(row)
                if len(rowlist) < 2:
                    continue
                
                prevrow = rowlist[-2]
                if (row['emaaligned'] is False):
                    return 
                
                if row['time'] < pd.to_datetime("09:40").time():
                    continue 
                
                if prevrow is not None:
                    myrule =  self.create_candles_rule(rowlist, self.trade_type)
                    if myrule:
                        entry = row['close']
                        sl = max(entry + 1 * row['atr'], row['high'])
                        sl = max(sl, entry + 0.003*entry)
                        output['entry'] = entry
                        output['sl'] = sl
                        output['tradetime'] = row['timestamp']
                        output['previous_day_low'] = row['previous_day_low']
                        output['previous_day_open'] = row['previous_day_open']
                        output['previous_day_close'] = row['previous_day_close']
                        output['previous_day_high'] = row['previous_day_high']
                        output['supertrend_15_1'] = row['supertrend_15_1']
                        output['adx'] = row['adx']
                        output['atr'] = row['atr']
                        df = orgdf[(orgdf['time'] > row['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
                        output['goodtrade'] = self.future(df, output['entry'], output['sl'])
                        return output
        return None
    

    def ema_aligned(self, df, emalist):
        df['emaaligned'] = True
        if self.trade_type == 'buy':
            for i in range(0, len(emalist)-1):
                df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] > df[emalist[i+1]])

        if self.trade_type == 'sell':
            for i in range(0, len(emalist)-1):
                df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] < df[emalist[i+1]])
        return df
    

    def update_sl(self):
        pass
        
    def apply_strategy(self):
        window = self.kwargs.get('window')
        ema_list = self.kwargs.get('ema_list')
        if window  is None:
            raise ValueError("For this strategy we need window to detect breakout and breakdown so pass input like this 'window = 5' in your method ")
        
        if ema_list is None:
            raise ValueError("For this strategy we need window to detect breakout and breakdown so pass input like this 'ema_list = ['ema_8', 'ema_21', 'ema_50', 'ema_100']' in your method ")
            
        df = self.df.copy()
        # df = Indicators.vwap(df)
        
        try :
            for ema in ema_list:
                df = Indicators.ema(df, ema)
            ema_list = ['ema'+'_'+str(ema) for ema in ema_list]
            df = Indicators.atr(df)
            df = self.ema_aligned(df, ema_list)
            df = Indicators.adx(df)
            df = Indicators.vwap(df)
            df = Indicators.supertrend(df, 15,1)
            # print(df.columns)

            df['day'] = df['timestamp'].dt.date
            daydf = utils.resample(df.copy(), '1d')
            daydf['day'] = daydf['timestamp'].dt.date
            daydf['day'] = daydf['day'].shift(-2)
            daydf = daydf.drop(['timestamp'], axis = 1)
            daydf.rename(columns  = {'open' : 'previous_day_open',
                'close' : 'previous_day_close',
                'low' : 'previous_day_low',
                'high' : 'previous_day_high',
                'volume' : 'previous_day_volume'}, inplace = True)
            df = pd.merge(df, daydf, on = 'day', how = 'left')
            df['time'] = df['timestamp'].dt.time
            
            df['day'] = df['timestamp'].dt.date
            df['time'] = df['timestamp'].dt.time
            df = df.dropna()
            df.reset_index(inplace = True, drop = True)
        except Exception as e:
            print("Some error in transforming it", str(e))
            return
        if df is None:
            raise("all Null values")
        
        resultslist = []
        if self.kwargs.get('live'):
            df = df[df['day'] == datetime.today().date()]
            df = df.iloc[:-1].copy()
            df.reset_index(drop=True, inplace=True)
            output = self.day_handle(df.copy())
            if output is not None and self.kwargs.get('save_trade'):
                utils.save_plot(df,self.kwargs.get('symbol') + '_' + self.trade_type, output)
                print(output)
        else:
            prevday = None
            alldays = df['day'].unique()
            for x in alldays:
                dftmp = df[df['day'] == x].copy()
                # prevdf = utils.get_prevous_day_data(df.copy(), x)
                output = self.day_handle(dftmp.copy(), None)
                if output is not None:
                    resultslist.append(output)
                if output is not None and self.kwargs.get('save_trade'):
                    dftmp = utils.filter_data_by_dates(df.copy(), (pd.to_datetime(x) - timedelta(5)).date(), (pd.to_datetime(x) + timedelta(1)).date())
                    utils.save_plot(dftmp,self.kwargs.get('symbol') + '_' + self.trade_type, output)
                    print(output)
                prevday = x
        return resultslist
    

# class EMA_8_21_50_100_Aligned_by_Ayushi(BaseStrategy):
#     def create_candles_rule(self,rowlist, trade_type, baseindicator = 'ema_8'):
#         pinbar = is_pinbar(rowlist, trade_type)
#         # engulfing = is_engulfing(rowlist, trade_type)
#         inside_bar = is_inside_bar(rowlist[:-1], trade_type)
#         star_pattern = is_star_pattern(rowlist, trade_type)
#         # doji = is_doji(rowlist[:-1])
#         row = rowlist[-1]
#         prevrow = rowlist[-2]

#         # if trade_type == 'buy':
#         #     if  ((inside_bar and row['close'] > prevrow['high']) or (star_pattern)) and (row['low'] <= row[baseindicator] or  prevrow['low'] <= prevrow[baseindicator]) and row['close'] > row[baseindicator]:
#         #         return True
            
#         # if trade_type == 'sell':
#         #     if ((inside_bar and row['close'] < prevrow['low']) or (star_pattern) ) and (row['high'] >= row[baseindicator] or prevrow['high'] >= prevrow[baseindicator])  and row['close'] < row[baseindicator]:
#         #         return True

#         if trade_type == 'buy':
#             if  ((row['close'] > row['supertrend_15_1']) and (prevrow['close'] < prevrow['supertrend_15_1']) and (row['close'] > max(prevrow['close'], prevrow['open'])) and (row['emaaligned']) and (row['close'] > row['ema_21'])):
#                 return True
            
#         if trade_type == 'sell':
#             if ((row['close'] < row['supertrend_15_1']) and (prevrow['close'] > prevrow['supertrend_15_1']) and (row['close'] < min(prevrow['close'], prevrow['open'])) and (row['emaaligned']) and (row['close'] < row['ema_21'])):
#                 return True
            
#         return False
    
#     def future(self, df, entry, sl):
#         maxrr = 0
#         for i,row in df.iterrows():
#             if self.trade_type == 'buy':
#                 maxrr = max(maxrr, (row['high'] - entry) / (entry - sl))
                
#             if self.trade_type == 'sell':
#                 maxrr = max(maxrr,(entry - row['low']) / (sl - entry))
            
#         return maxrr

#     def day_handle(self, df):
#         orgdf = df.copy()
#         df = df[(df['time'] < pd.to_datetime("11:30").time())].copy()
#         df.reset_index(inplace = True, drop = True)
#         output = {}
#         output['trade_type'] = self.trade_type
        
#         if self.trade_type == 'buy':
#             rowlist = []
#             for i, row in df.iterrows():
#                 rowlist.append(row)
#                 if i==0 and is_pinbar(rowlist,self.trade_type):
#                     return None
                
#                 if len(rowlist) < 2 :
#                     continue

#                 prevrow = rowlist[-2]
#                 if row['time'] < pd.to_datetime("09:30").time() :
#                     continue 

#                 # if row['emaaligned'] is False :
#                 #     return None
            
#                 if prevrow is not None:
#                     myrule = self.create_candles_rule(rowlist, self.trade_type)
#                     if myrule:
#                         entry = row['close']
#                         sl = min(entry - 1 * row['atr'], row['low'])
#                         sl = min(sl, entry - 0.003 * entry)
        
#                         output['entry'] = entry
#                         output['sl'] = sl
#                         output['tradetime'] = row['timestamp']
#                         output['previous_day_low'] = row['previous_day_low']
#                         output['previous_day_open'] = row['previous_day_open']
#                         output['previous_day_close'] = row['previous_day_close']
#                         output['previous_day_high'] = row['previous_day_high']
#                         output['adx'] = row['adx']
#                         output['atr'] = row['atr']
#                         df = orgdf[(orgdf['time'] > row['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
#                         output['goodtrade'] = self.future(df, output['entry'], output['sl'])
#                         return output
                    
#         if self.trade_type == 'sell':
#             rowlist = []
#             for i, row in df.iterrows():
#                 rowlist.append(row)
#                 if i==0 and is_pinbar(rowlist,self.trade_type):
#                     return None
            
#                 if len(rowlist) < 2:
#                     continue
                
#                 prevrow = rowlist[-2]
#                 if row['time'] < pd.to_datetime("09:20").time():
#                     continue 
                   
#                 # if (row['emaaligned'] is False):
#                 #     return None
                
#                 if prevrow is not None:
#                     myrule =  self.create_candles_rule(rowlist, self.trade_type)
#                     if myrule:
#                         entry = row['close']
#                         sl = max(entry + 1 * row['atr'], row['high'])
#                         sl = max(sl, entry + 0.003*entry)
    
                        
#                         output['entry'] = entry
#                         output['sl'] = sl
#                         output['tradetime'] = row['timestamp']
#                         output['previous_day_low'] = row['previous_day_low']
#                         output['previous_day_open'] = row['previous_day_open']
#                         output['previous_day_close'] = row['previous_day_close']
#                         output['previous_day_high'] = row['previous_day_high']
#                         output['adx'] = row['adx']
#                         output['atr'] = row['atr']
#                         df = orgdf[(orgdf['time'] > row['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
#                         output['goodtrade'] = self.future(df, output['entry'], output['sl'])
#                         return output
#         return None
    

#     def ema_aligned(self, df, emalist):
#         df['emaaligned'] = True
#         if self.trade_type == 'buy':
#             for i in range(0, len(emalist)-1):
#                 df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] > df[emalist[i+1]])

#         if self.trade_type == 'sell':
#             for i in range(0, len(emalist)-1):
#                 df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] < df[emalist[i+1]])
#         return df
    

#     def update_sl(self):
#         pass
        
#     def apply_strategy(self):
#         window = self.kwargs.get('window')
#         ema_list = self.kwargs.get('ema_list')
#         if window  is None:
#             raise ValueError("For this strategy we need window to detect breakout and breakdown so pass input like this 'window = 5' in your method ")
        
#         if ema_list is None:
#             raise ValueError("For this strategy we need window to detect breakout and breakdown so pass input like this 'ema_list = ['ema_8', 'ema_21', 'ema_50', 'ema_100']' in your method ")
            
#         df = self.df.copy()
#         # df = Indicators.vwap(df)
        
#         try :
#             for ema in ema_list:
#                 df = Indicators.ema(df, ema)
#             ema_list = ['ema'+'_'+str(ema) for ema in ema_list]
#             df = Indicators.atr(df)
#             df = self.ema_aligned(df, ema_list)
#             df = Indicators.adx(df)
#             df = Indicators.supertrend(df, 15,1)
#             # print(df.columns)

#             df['day'] = df['timestamp'].dt.date
#             daydf = utils.resample(df.copy(), '1d')
#             daydf['day'] = daydf['timestamp'].dt.date
#             daydf['day'] = daydf['day'].shift(-1)
#             daydf = daydf.drop(['timestamp'], axis = 1)
#             daydf.rename(columns  = {'open' : 'previous_day_open',
#                 'close' : 'previous_day_close',
#                 'low' : 'previous_day_low',
#                 'high' : 'previous_day_high',
#                 'volume' : 'previous_day_volume'}, inplace = True)
#             df = pd.merge(df, daydf, on = 'day', how = 'left')
#             df['time'] = df['timestamp'].dt.time
            
#             df['day'] = df['timestamp'].dt.date
#             df['time'] = df['timestamp'].dt.time
#             df = df.dropna()
#             df.reset_index(inplace = True, drop = True)
#         except Exception as e:
#             print("Some error in transforming it", str(e))
#             return
#         if df is None:
#             raise("all Null values")
        
#         resultslist = []
#         if self.kwargs.get('live'):
#             df = df[df['day'] == datetime.today().date()]
#             df = df.iloc[:-1].copy()
#             df.reset_index(drop=True, inplace=True)
#             output = self.day_handle(df.copy())
#             if output is not None and self.kwargs.get('save_trade'):
#                 utils.save_plot(df,self.kwargs.get('symbol') + '_' + self.trade_type, output)
#                 print(output)
#         else:
#             alldays = df['day'].unique()
#             for x in alldays:
#                 dftmp = df[df['day'] == x].copy()
#                 output = self.day_handle(dftmp.copy())
#                 if output is not None:
#                     resultslist.append(output)
#                 if output is not None and self.kwargs.get('save_trade'):
#                     dftmp = utils.filter_data_by_dates(df.copy(), (pd.to_datetime(x) - timedelta(7)).date(), (pd.to_datetime(x) + timedelta(1)).date())
#                     utils.save_plot(dftmp,self.kwargs.get('symbol') + '_' + self.trade_type, output)
#                     print(output)
#         return resultslist


class VWAP_by_YatinKoodi(BaseStrategy):
    def create_candles_rule(self,rowlist, trade_type, baseindicator = 'ema_8'):
        pinbar = is_pinbar(rowlist, trade_type)
        inside_bar = is_inside_bar(rowlist[:-1], trade_type)
        star_pattern = is_star_pattern(rowlist, trade_type)
        row = rowlist[-1]
        prevrow = rowlist[-2]

        if trade_type == 'buy':
            if  ((inside_bar and row['close'] > prevrow['high']) or (star_pattern) or (pinbar)) and (row['low'] <= row[baseindicator]) and row['close'] > row[baseindicator] and row['high'] > prevrow['high']:
                return True
            
        if trade_type == 'sell':
            if ((inside_bar and row['close'] < prevrow['low']) or (star_pattern) or (pinbar)) and (row['high'] >= row[baseindicator])  and row['close'] < row[baseindicator] and row['low'] < prevrow['low']:
                return True            
        return False
    
    
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
        

        # if trade_type == 'sell':
        #     slpoints = sl - entry
        #     results = []
        #     for trail in [True, False]:
        #         for rr in 
        return results
        
    def reversal_rule(rowlist):
        prevrow = rowlist[-2]
        currow = rowlist[-1]

    def day_handle(self, df, change_dict, day):
        orgdf = df.copy()
        df = df[(df['time'] < pd.to_datetime("12:00").time())].copy()
        df.reset_index(inplace = True, drop = True)
        output = {}
        output['trade_type'] = self.trade_type
        if len(df) <3:
            return None
        
        firstcandle = df.iloc[0]
        secondcandle = df.iloc[1]

        # if self.trade_type == 'buy':
        #     if not ((firstcandle['close'] >= firstcandle['vwap']) and (secondcandle['close'] > firstcandle['high']) and (firstcandle['close'] > firstcandle['open'])):
        #         return None
        
        if self.trade_type == 'buy':
            rowlist = []
            for i, row in df.iterrows():
                rowlist.append(row)
                if i < 3:
                    continue
                prevrow = rowlist[-2]



                if row['time'] > pd.to_datetime("11:30").time() or prevrow['close'] < prevrow['ema_21']:
                    return

                if (self.create_candles_rule(rowlist[:-1], self.trade_type, baseindicator = 'ema_21')) and  row['high'] > prevrow['high']:
                    if row['time'] < pd.to_datetime("09:45").time() or  prevrow['emaaligned'] == False :
                        return 
                    
                    # mt = change_dict.get(prevrow['timestamp'])
                    # if mt is None:
                    #     return 
                    # currentorder = list(mt.keys())[:10]
                    # currentorder = set(currentorder)

                    # if self.kwargs.get('symbol') in currentorder:
                    #     return

                    entry = prevrow['high']
                    sl = prevrow['low']
                    slpct = abs(entry - sl) / entry * 100
                    # if slpct < 0.3:
                    #     sl = entry -  entry*0.003
                    df = orgdf[(orgdf['time'] > prevrow['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
                    results = self.future(df, entry, sl,self.trade_type, day,  row['timestamp'])
                    return results
        if self.trade_type == 'sell':
            rowlist = []
            for i, row in df.iterrows():
                rowlist.append(row)
                if i < 3:
                    continue
                prevrow = rowlist[-2]
                if row['time'] > pd.to_datetime("11:30").time() or prevrow['close'] > prevrow['ema_21']:
                    return

                if (self.create_candles_rule(rowlist[:-1], self.trade_type, baseindicator = 'ema_21')) and  row['low'] < prevrow['low']:
                    if row['time'] < pd.to_datetime("09:45").time() or  prevrow['emaaligned'] == False :
                        return 
                    entry = prevrow['low']
                    sl = prevrow['high'] 
                    slpct = abs(entry - sl) / entry * 100
                    # if slpct < 0.3:
                    #     sl = entry + entry * 0.003
                    df = orgdf[(orgdf['time'] > prevrow['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
                    results = self.future(df, entry, sl,self.trade_type, day, row['timestamp'])
                    return results
        return

    def ema_aligned(self, df, emalist):
        df['emaaligned'] = True
        if self.trade_type == 'buy':
            for i in range(0, len(emalist)-1):
                df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] > df[emalist[i+1]])

        if self.trade_type == 'sell':
            for i in range(0, len(emalist)-1):
                df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] < df[emalist[i+1]])
        return df 

    def update_sl(self):
        pass
        
    def apply_strategy(self):   
        change_dict = self.kwargs.get('change_dict')
        if change_dict  is None:
            raise ValueError("For this strategy we need rank of stocks as dict ")
        
        ema_list = self.kwargs.get('ema_list')
        if ema_list is None:
            raise ValueError("For this strategy we need window to detect breakout and breakdown so pass input like this 'ema_list = ['ema_8', 'ema_21', 'ema_50', 'ema_100']' in your method ")
            
        
        df = self.df.copy()
        for ema in ema_list:
            df = Indicators.ema(df, ema)
        ema_list = ['ema'+'_'+str(ema) for ema in ema_list]
        df = self.ema_aligned(df, ema_list)
        df = Indicators.vwap(df)
        df = Indicators.atr(df)
        df['day'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        df = df.dropna()
        df.reset_index(inplace = True, drop = True)
        alldays = sorted(df['day'].unique(), key=pd.to_datetime)
        resultslist = []

        for x in alldays:
            dftmp = df[df['day'] == x].copy()
            output = self.day_handle(dftmp.copy(), change_dict, x)
            if output is not None:
                resultslist.extend(output)
                for ot in output:
                    if not ot['trail'] and  ot['bookat'] == 3:
                        if self.kwargs.get('save_trade'):
                            utils.save_plot(dftmp,self.kwargs.get('symbol') + '_' + self.trade_type, ot)
                        print(ot)
        return resultslist
    

class Modified_EMA_8_21_50_100_Aligned_by_Ayushi(BaseStrategy):
    def create_candles_rule(self,rowlist, trade_type, baseindicator = 'ema_8'):
        pinbar = is_pinbar(rowlist, trade_type)
        # engulfing = is_engulfing(rowlist, trade_type)
        inside_bar = is_inside_bar(rowlist[:-1], trade_type)
        star_pattern = is_star_pattern(rowlist, trade_type)
        # doji = is_doji(rowlist[:-1])
        row = rowlist[-1]
        prevrow = rowlist[-2]

        if trade_type == 'buy':
            if  ((inside_bar and row['close'] > prevrow['high']) or (star_pattern) or (pinbar)) and (row['low'] <= row[baseindicator] or  prevrow['low'] <= prevrow[baseindicator]) and row['close'] > row[baseindicator]:
                return True
            
        if trade_type == 'sell':
            if ((inside_bar and row['close'] < prevrow['low']) or (star_pattern) or (pinbar)) and (row['high'] >= row[baseindicator] or prevrow['high'] >= prevrow[baseindicator])  and row['close'] < row[baseindicator]:
                return True
        return False
    
    def future(self, df, entry, sl):
        maxrr = 0
        for i,row in df.iterrows():
            if self.trade_type == 'buy':
                maxrr = max(maxrr, (row['high'] - entry) / (entry - sl))
                
            if self.trade_type == 'sell':
                maxrr = max(maxrr,(entry - row['low']) / (sl - entry))
            
        return maxrr

    def day_handle(self, df):
        orgdf = df.copy()
        df = df[(df['time'] < pd.to_datetime("10:30").time())].copy()
        df.reset_index(inplace = True, drop = True)
        output = {}
        output['trade_type'] = self.trade_type

        if self.trade_type == 'buy':
            df['close_below_ema_20'] = np.where(df['close'] < df['ema_21'], 1, 0)
            df['close_below_ema_20'] = df['close_below_ema_20'].cumsum()
            df['failed_emas'] = np.where(df['ema_8'] < df['ema_8'].shift(1), 1, 0)
            df['failed_emas'] = df['failed_emas'].cumsum()

            rowlist = []
            for i, row in df.iterrows():
                if i==0 and (row['close']<row['open']):
                    return None
                rowlist.append(row)
                if len(rowlist) < 2 or row['adx']<20:
                    continue
                prevrow = rowlist[-2]
                if row['time'] < pd.to_datetime("10:30").time():
                    continue 
                #check if hammer at ema_8
                if row['emaaligned'] is False or row['close_below_ema_20']>=1 or row['failed_emas']>=1:
                    return None
            
                if prevrow is not None:
                    
                    myrule = self.create_candles_rule(rowlist, self.trade_type)
                    distance_from_last_close = (row['close'] - row['previous_day_close'])/row['close'] * 100
                    if myrule and  distance_from_last_close< 2.5 and distance_from_last_close>0:
                        output['entry'] = row['close']
                        output['sl'] = min(output['entry'] - 1 * row['atr'], row['low'])
                        output['tradetime'] = row['timestamp']
                        output['previous_day_low'] = row['previous_day_low']
                        output['previous_day_open'] = row['previous_day_open']
                        output['previous_day_close'] = row['previous_day_close']
                        output['previous_day_high'] = row['previous_day_high']
                        output['adx'] = row['adx']
                        df = orgdf[(orgdf['time'] > row['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
                        output['goodtrade'] = self.future(df, output['entry'], output['sl'])
                        return output
                    
        if self.trade_type == 'sell':
            df['close_above_ema_20'] = np.where(df['close'] > df['ema_21'], 1, 0)
            df['close_above_ema_20'] = df['close_above_ema_20'].cumsum()

            df['failed_emas'] = np.where(df['ema_8'] > df['ema_8'].shift(1), 1, 0)
            df['failed_emas'] = df['failed_emas'].cumsum()

    
            rowlist = []
            for i, row in df.iterrows():
                if i==0 and (row['close']>row['open']):
                    return None
                rowlist.append(row)
                if len(rowlist) < 2 or row['adx']<20:
                    continue
                prevrow = rowlist[-2]
                if row['time'] < pd.to_datetime("10:30").time():
                    continue 
                   
                if (row['emaaligned'] is False or row['close_above_ema_20'] >= 1 or row['failed_emas']>=1) :
                    return None
                
                if prevrow is not None:
                    myrule =  self.create_candles_rule(rowlist, self.trade_type)
                    if myrule:
                        output['entry'] = row['close']
                        output['sl'] = max(output['entry'] + 1 * row['atr'], row['high'])
                        output['tradetime'] = row['timestamp']
                        output['previous_day_low'] = row['previous_day_low']
                        output['previous_day_open'] = row['previous_day_open']
                        output['previous_day_close'] = row['previous_day_close']
                        output['previous_day_high'] = row['previous_day_high']
                        output['adx'] = row['adx']
                        df = orgdf[(orgdf['time'] > row['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
                        output['goodtrade'] = self.future(df, output['entry'], output['sl'])
                        return output
        return None
    

    def ema_aligned(self, df, emalist):
        df['emaaligned'] = True
        if self.trade_type == 'buy':
            for i in range(0, len(emalist)-1):
                df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] > df[emalist[i+1]])

        if self.trade_type == 'sell':
            for i in range(0, len(emalist)-1):
                df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] < df[emalist[i+1]])
        return df
    

    def update_sl(self):
        pass

    def was_previous_day_choppy(self, df, prevday,):
        if prevday is None:
            return False
        dftmp = df[df['day'] == prevday].copy()
        dftmp.reset_index(inplace = True, drop =True)
        dftmp['crossover'] = (dftmp['ema_8'] > dftmp['ema_21'])
        dftmp['crossover'] = np.where(dftmp['crossover'] != dftmp['crossover'].shift(1), 1, 0)
        dftmp.loc[0,'crossover'] = 0
        s = dftmp['crossover'].sum()
        print(s, end = " ")
    
        if  s>1:
            return True
        return False
        
    def apply_strategy(self):
        window = self.kwargs.get('window')
        ema_list = self.kwargs.get('ema_list')
        if window  is None:
            raise ValueError("For this strategy we need window to detect breakout and breakdown so pass input like this 'window = 5' in your method ")
        
        if ema_list is None:
            raise ValueError("For this strategy we need window to detect breakout and breakdown so pass input like this 'ema_list = ['ema_8', 'ema_21', 'ema_50', 'ema_100']' in your method ")
            
        df = self.df.copy()
        df = df.sort_values(by='timestamp', ascending= True)

        # df = Indicators.vwap(df)
        
        try :
            for ema in ema_list:
                df = Indicators.ema(df, ema)
            ema_list = ['ema'+'_'+str(ema) for ema in ema_list]
            df = Indicators.atr(df)
            df = self.ema_aligned(df, ema_list)
            df = Indicators.adx(df)

            df['day'] = df['timestamp'].dt.date
            daydf = utils.resample(df.copy(), '1d')
            daydf['day'] = daydf['timestamp'].dt.date
            daydf['day'] = daydf['day'].shift(-1)
            daydf = daydf.drop(['timestamp'], axis = 1)
            daydf.rename(columns  = {'open' : 'previous_day_open',
                'close' : 'previous_day_close',
                'low' : 'previous_day_low',
                'high' : 'previous_day_high',
                'volume' : 'previous_day_volume'}, inplace = True)
            df = pd.merge(df, daydf, on = 'day', how = 'left')
            df['time'] = df['timestamp'].dt.time
            
            df['day'] = df['timestamp'].dt.date
            df['time'] = df['timestamp'].dt.time
            df = df.dropna()
            df.reset_index(inplace = True, drop = True)
            df = df.sort_values(by='timestamp', ascending= True)
        except Exception as e:
            print("Some error in transforming it", str(e))
            return
        if df is None:
            raise("all Null values")
        
        alldays = sorted(df['day'].unique(), key=pd.to_datetime)
        resultslist = []
        if self.kwargs.get('live'):
            df = df[df['day'] == datetime.today().date()]
            df = df.iloc[:-1].copy()
            df.reset_index(drop=True, inplace=True)
            output = self.day_handle(df.copy())
            if output is not None and self.kwargs.get('save_trade'):
                utils.save_plot(df,self.kwargs.get('symbol') + '_' + self.trade_type, output)
                print(output)
        else:
            prevday = None
            for x in alldays:
                if self.was_previous_day_choppy(df.copy(), prevday):
                    dftmp = df[df['day'] == x].copy()
                    output = self.day_handle(dftmp.copy())
                    if output is not None:
                        resultslist.append(output)
                    if output is not None and self.kwargs.get('save_trade'):
                        utils.save_plot(dftmp,self.kwargs.get('symbol') + '_' + self.trade_type, output)
                        print(output)

                prevday = x
        return resultslist





class Yatin_plus_ayushi(BaseStrategy):
    def create_candles_rule(self,rowlist, trade_type, baseindicator = 'vwap'):
        currrow = rowlist[-1]
        prevrow = rowlist[-2]

        if trade_type == 'buy':
            if (prevrow['low'] < prevrow['vwap']) and (prevrow['close'] > prevrow['vwap']) and (prevrow['open'] > prevrow['vwap']):
                if currrow['high'] > prevrow['high']:
                    return True
                
        if trade_type == 'sell':
            if (prevrow['high'] > prevrow['vwap']) and (prevrow['close'] < prevrow['vwap']) and (prevrow['open'] < prevrow['vwap']):
                if currrow['low'] < prevrow['low']:
                    return True
        return False     

    def stock_selection(Self, firstrow, secondrow, tradetype):

        if tradetype == 'buy':
            if close_above_previous_high(firstrow, secondrow) and positivecandle(firstrow) and positivecandle(secondrow) and close_above_indictaor(firstrow, 'vwap') and close_above_indictaor(secondrow, 'vwap'):
                return True
            
        if tradetype == 'sell':
            if close_below_previous_low(firstrow, secondrow) and negativecandle(firstrow) and negativecandle(secondrow) and close_below_indicator(firstrow, 'vwap') and close_below_indicator(secondrow, 'vwap'):
                return True
        return False
    
    def future(self, df, entry, sl):
        maxrr = 0
        for i,row in df.iterrows():
            if self.trade_type == 'buy':
                maxrr = max(maxrr, (row['high'] - entry) / (entry - sl))
                
            if self.trade_type == 'sell':
                maxrr = max(maxrr,(entry - row['low']) / (sl - entry))
            
        return maxrr
    
    def day_trading(self, df):
        df.reset_index(inplace = True, drop = True)
        orgdf = df.copy()
        # df = df[(df['time'] < pd.to_datetime("11:30").time())].copy()
        df = df[(df['time'] < pd.to_datetime("10:30").time())].copy()
        if len(df)==0:
            return None
        output = {}
        if self.trade_type == 'buy':
            df['index'] = df.index
            firstrow = df.iloc[0]
            secondrow = df.iloc[1]
            if not self.stock_selection(firstrow, secondrow, self.trade_type):
                return 
            
            rowlist = []
            for i, row in df.iterrows():
                rowlist.append(row)
                if len(rowlist) <= 2:
                    continue
                
                prevrow = rowlist[-2]
                candlerule = self.create_candles_rule(rowlist, self.trade_type,'vwap')
                if candlerule and prevrow['emaaligned']:
                    output['entry'] = prevrow['high']
                    output['sl'] =  min(prevrow['low'], prevrow['high'] - 0.005 * prevrow['high']) 
                    output['tradetime'] = row['timestamp']
                    df = orgdf[(orgdf['time'] > prevrow['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
                    output['goodtrade'] = self.future(df, output['entry'], output['sl'])
                    
                    return output
                
        if self.trade_type == 'sell':
            df['index'] = df.index

            firstrow = df.iloc[0]
            secondrow = df.iloc[1]
            if (firstrow['open'] - firstrow['close'])/ firstrow['atr'] > 3:
                return

            if not self.stock_selection(firstrow, secondrow, self.trade_type):
                return 
            
            rowlist = []
            for i, row in df.iterrows():
                rowlist.append(row)
                if len(rowlist)<=2:
                    continue
                
                prevrow = rowlist[-2]
                candlerule = self.create_candles_rule(rowlist, self.trade_type,'vwap')
                if candlerule and prevrow['emaaligned']:
                    output['entry'] = prevrow['low']
                    output['sl'] = max(prevrow['high'] , prevrow['low'] + 0.005 * prevrow['low'])
                    output['tradetime'] = row['timestamp']
                    df = orgdf[(orgdf['time'] > prevrow['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
                    output['goodtrade'] = self.future(df, output['entry'], output['sl'])
                    output['first'] = (firstrow['open'] - firstrow['close'])/ firstrow['atr']
                    return output
                
        return 


    def ema_aligned(self, df, emalist):
        df['emaaligned'] = True
        if self.trade_type == 'buy':
            for i in range(1, len(emalist)-1):
                df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] > df[emalist[i+1]])

        if self.trade_type == 'sell':
            for i in range(0, len(emalist)-1):
                df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] < df[emalist[i+1]])
        return df
    
    
    def was_previous_day_choppy(self, df, prevday,):
        if prevday is None:
            return False
        dftmp = df[df['day'] == prevday].copy()
        dftmp.reset_index(inplace = True, drop =True)
        dftmp['crossover'] = (dftmp['ema_8'] > dftmp['ema_21'])
        dftmp['crossover'] = np.where(dftmp['crossover'] != dftmp['crossover'].shift(1), 1, 0)
        dftmp.loc[0,'crossover'] = 0
        s = dftmp['crossover'].sum()

        if  s>1:
            return True
        return False
    
     
    def apply_strategy(self):
        '''rules:
        1. All Ema CO-ordinated
        2. Vwap co-ordinated
        3. Previous day coppy
        4. candles type check'''
        ema_list = self.kwargs.get('ema_list')
        
        if ema_list is None:
            raise ValueError("For this strategy we need window to detect breakout and breakdown so pass input like this 'ema_list = ['ema_8', 'ema_21', 'ema_50', 'ema_100']' in your method ")
            
        df = self.df.copy()
        df = Indicators.vwap(df)
        for ema in ema_list:
            df = Indicators.ema(df, ema)

        ema_list = ['ema'+'_'+str(ema) for ema in ema_list]
        df = Indicators.atr(df)
        df = self.ema_aligned(df, ema_list)
        df = Indicators.adx(df)
        df['day'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        df = df.dropna()
        df.reset_index(inplace = True, drop = True)
        df = df.sort_values(by='timestamp', ascending= True)

        alldays = sorted(df['day'].unique(), key=pd.to_datetime)
        resultslist = []
        if self.kwargs.get('live'):
            df = df[df['day'] == datetime.today().date()]
            df.reset_index(drop=True, inplace=True)
            output = self.day_trading(df.copy())
            if output is not None and self.kwargs.get('save_trade'):
                utils.save_plot(df,self.kwargs.get('symbol') + '_' + self.trade_type, output)
                print(output)
        else:
            prevday = None
            for x in alldays:
                if True:
                    dftmp = df[df['day'] == x].copy()
                    dftmp.reset_index(drop = True, inplace = True)
                    output = self.day_trading(dftmp.copy())
                    if output is not None:
                        resultslist.append(output)
                    if output is not None and self.kwargs.get('save_trade'):
                        utils.save_plot(dftmp,self.kwargs.get('symbol') + '_' + self.trade_type, output)
                        print(output)

                prevday = x
        return resultslist


        


class Reversal(BaseStrategy):    
    def future(self, df, entry, sl):
        maxrr = 0
        for i,row in df.iterrows():
            if self.trade_type == 'buy':
                maxrr = max(maxrr, (row['high'] - entry) / (entry - sl))
                
            if self.trade_type == 'sell':
                maxrr = max(maxrr,(entry - row['low']) / (sl - entry))    
        return maxrr
    
    def is_inside_bar(self, currrow, prevrow):
        return currrow['high'] < prevrow['high'] and currrow['low'] > prevrow['low']
    
    def create_candles_rule(self, rowlist, baseindicator):
        currrow1 = rowlist[-1]
        prevrow2 = rowlist[-2]
        prevrow3 = rowlist[-3]
        prevrow4 = rowlist[-4]
        # print(currrow1, prevrow2, prevrow3, prevrow4)
        if self.trade_type == 'buy':
            if (currrow1['close'] > prevrow2['high']):
                if prevrow2['islowest'] or  prevrow3['islowest'] or prevrow4['islowest']:
                    if self.is_inside_bar(prevrow2, prevrow3) and self.is_inside_bar(prevrow3, prevrow4):
                        return True
        return False
    
    def day_trading(self, df):
        df.reset_index(inplace = True, drop = True)
        orgdf = df.copy()
        df = df[(df['time'] < pd.to_datetime("13:00").time())].copy()
        if len(df)==0:
            return None
        output = {}
        if self.trade_type == 'buy':
            df['islowest'] = df['low'].cummin()
            df['islowest'] = df['islowest'] == df['low']
            df['index'] = df.index
            rowlist = []
            for i, row in df.iterrows():
                rowlist.append(row)
                if len(rowlist) <= 3:
                    continue
                if row['time'] < pd.to_datetime("10:10").time():
                    continue 
                    
                candlerule = self.create_candles_rule(rowlist,'vwap')
                if candlerule and row['emaaligned']:
                    output['entry'] = row['close']
                    output['sl'] =  min(row['low'], row['high'] - 0.005 * row['high']) 
                    output['tradetime'] = row['timestamp']
                    df = orgdf[(orgdf['time'] > row['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
                    output['goodtrade'] = self.future(df, output['entry'], output['sl'])
                    return output
        return 
     
    def ema_aligned(self, df, emalist):
        df['emaaligned'] = True
        if self.trade_type == 'buy':
            for i in range(1, len(emalist)-1):
                df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] > df[emalist[i+1]])

        if self.trade_type == 'sell':
            for i in range(0, len(emalist)-1):
                df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] < df[emalist[i+1]])
        return df

    def apply_strategy(self):
        '''rules:
        1. All Ema CO-ordinated
        2. Vwap co-ordinated
        3. Previous day coppy
        4. candles type check'''
        ema_list = self.kwargs.get('ema_list')
        
        if ema_list is None:
            raise ValueError("For this strategy we need window to detect breakout and breakdown so pass input like this 'ema_list = ['ema_8', 'ema_21', 'ema_50', 'ema_100']' in your method ")
            
        df = self.df.copy()
        df = Indicators.vwap(df)
        for ema in ema_list:
            df = Indicators.ema(df, ema)

        ema_list = ['ema'+'_'+str(ema) for ema in ema_list]
        df = Indicators.atr(df)
        df = self.ema_aligned(df, ema_list)

        df = Indicators.adx(df)
        df['day'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        df = df.dropna()
        df.reset_index(inplace = True, drop = True)
        df = df.sort_values(by='timestamp', ascending= True)

        alldays = sorted(df['day'].unique(), key=pd.to_datetime)
        resultslist = []
        if self.kwargs.get('live'):
            df = df[df['day'] == datetime.today().date()]
            df.reset_index(drop=True, inplace=True)
            output = self.day_trading(df.copy())
            if output is not None and self.kwargs.get('save_trade'):
                utils.save_plot(df,self.kwargs.get('symbol') + '_' + self.trade_type, output)
                print(output)
        else:
            prevday = None
            for x in alldays:
                if True:
                    dftmp = df[df['day'] == x].copy()
                    dftmp.reset_index(drop = True, inplace = True)
                    output = self.day_trading(dftmp.copy())
                    if output is not None:
                        resultslist.append(output)
                    if output is not None and self.kwargs.get('save_trade'):
                        utils.save_plot(dftmp,self.kwargs.get('symbol') + '_' + self.trade_type, output)
                        print(output)

                prevday = x
        return resultslist


        
class breakoutTrading(BaseStrategy):
    def ema_aligned(self, df, emalist):
        df['emaaligned'] = True
        if self.trade_type == 'buy':
            for i in range(1, len(emalist)-1):
                df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] > df[emalist[i+1]])

        if self.trade_type == 'sell':
            for i in range(0, len(emalist)-1):
                df['emaaligned'] = df['emaaligned'] & (df[emalist[i]] < df[emalist[i+1]])
        return df
    def day_handle(self, df, prevdf):
        df['heighest'] = df['high'].cummax()
        df['heighest'] = df['heighest'] == df['high']
        # print(df[df['breakout']])
        orgdf = df.copy()
        df = df[(df['time'] < pd.to_datetime("11:30").time())].copy()
        df.reset_index(inplace = True, drop = True)
        output = {}
        output['trade_type'] = self.trade_type

        if self.trade_type == 'buy':
            rowlist = []
            for i, row in df.iterrows():
                rowlist.append(row) 
                if row['time'] < pd.to_datetime("09:40").time():
                    continue           

                if row['emaaligned'] == False:
                    return      
                
                if row['breakout']:
                    if not row['heighest']:
                        return 
                    entry = row['close']
                    sl = min(entry - 1.5 * row['atr'], row['low'])
                    sl = min(sl, entry - 0.003 * entry)

                    output['entry'] = entry
                    output['sl'] = sl
                    output['tradetime'] = row['timestamp']
                    output['atr'] = row['atr']
                    df = orgdf[(orgdf['time'] > row['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
                    output['goodtrade'] = utils.future(df, output['entry'], output['sl'],self.trade_type)
                    return output
                    
        if self.trade_type == 'sell':
            rowlist = []
            for i, row in df.iterrows():
                rowlist.append(row)
                prevrow = rowlist[-2]
                if row['time'] < pd.to_datetime("09:40").time():
                    continue 
                
                if prevrow is not None:
                    myrule =  self.create_candles_rule(rowlist, self.trade_type)
                    if myrule:
                        entry = row['close']
                        sl = max(entry + 1.5 * row['atr'], row['high'])
                        sl = max(sl, entry + 0.003*entry)
                        output['entry'] = entry
                        output['sl'] = sl
                        output['tradetime'] = row['timestamp']
                        output['atr'] = row['atr']
                        df = orgdf[(orgdf['time'] > row['time']) & (orgdf['time'] <= pd.to_datetime("15:00").time())].copy()
                        output['goodtrade'] = utils.future(df, output['entry'], output['sl'])
                        return output
        return None

    def update_sl(self):
        pass
        
    def apply_strategy(self):
        window = self.kwargs.get('window')
        ema_list = self.kwargs.get('ema_list')
        if window  is None:
            raise ValueError("For this strategy we need window to detect breakout and breakdown so pass input like this 'window = 5' in your method ")
        
        if ema_list is None:
            raise ValueError("For this strategy we need window to detect breakout and breakdown so pass input like this 'ema_list = ['ema_8', 'ema_21', 'ema_50', 'ema_100']' in your method ")
            
        df = self.df.copy()
        
        try :
            for ema in ema_list:
                df = Indicators.ema(df, ema)
            ema_list = ['ema'+'_'+str(ema) for ema in ema_list]
            df = Indicators.atr(df)
            df = self.ema_aligned(df, ema_list)
            df['day'] = df['timestamp'].dt.date
            df['time'] = df['timestamp'].dt.time
            df = df.dropna()
            df.reset_index(inplace = True, drop = True)
        except Exception as e:
            print("Some error in transforming it", str(e))
            return
        if df is None:
            raise("all Null values")
        
        resultslist = []
        if self.kwargs.get('live'):
            df = df[df['day'] == datetime.today().date()]
            df = df.iloc[:-1].copy()
            df.reset_index(drop=True, inplace=True)
            output = self.day_handle(df.copy())
            if output is not None and self.kwargs.get('save_trade'):
                utils.save_plot(df,self.kwargs.get('symbol') + '_' + self.trade_type, output)
                print(output)
        else:
            alldays = df['day'].unique()
            df = breakout_breakdown(df, 4, 'buy')
            for x in alldays:
                dftmp = df[df['day'] == x].copy()
                output = self.day_handle(dftmp.copy(), None)
                if output is not None:
                    resultslist.append(output)
                if output is not None and self.kwargs.get('save_trade'):
                    dftmp = utils.filter_data_by_dates(df.copy(), (pd.to_datetime(x) - timedelta(3)).date(), (pd.to_datetime(x) + timedelta(1)).date())
                    utils.save_plot(dftmp,self.kwargs.get('symbol') + '_' + self.trade_type, output)
                    print(output)
        return resultslist
    