import numpy as np
import pandas as pd
import mplfinance as mpf
import os
from datetime import datetime, timedelta


def filter_by_day(df, scanday):
    df = df[df['date'] == pd.to_datetime(scanday).date()]
    df.reset_index(inplace = True, drop = True)
    return df

def filter_by_time(df, starttime, endtime):
    df = df[(df['time'] >= starttime) & (df['time'] <= endtime)]
    df.reset_index(inplace = True, drop = True)
    return df

def list_of_median_volume(orgdf, _date, starttime, endtime, n_days = 10):
    last_10_days = pd.date_range(end=_date, periods=n_days)[:-1]
    volumes = []
    for last_day in last_10_days:
        df = filter_by_day(orgdf.copy(), last_day)
        df = filter_by_time(df, starttime, endtime)
        if not df.empty: 
            median_vol = df['volume'].median()
            volumes.append(int(median_vol))
    return volumes


def save_image(symbol, df ,  _date, entry, sl, target, tm):
    foldername = "-".join(str(_date).split(':'))
    filename = symbol
    folderpath = f"samplesimages/{foldername}" 
    filepath = f"samplesimages/{foldername}/{tm + filename}.jpg"
    os.makedirs(folderpath, exist_ok=True)
    df['time'] = pd.to_datetime(df['timestamp'])
    df.set_index('time', inplace=True)

    ema_plots = []
    ema_plots.append(mpf.make_addplot(df['ema_9'], color='black', linestyle='-', width=2))
    ema_plots.append(mpf.make_addplot(df['ema_15'], color='black', linestyle='-', width=5))

    entry_m = pd.Series(entry, index=df.index)
    ema_plots.append(mpf.make_addplot(entry_m, color='green', linestyle='-', width=3))
        
    sl_m = pd.Series(sl, index=df.index)
    ema_plots.append(mpf.make_addplot(sl_m, color='red', linestyle='-', width=5))

    mpf.plot(df, type='candle', style='charles', title=symbol,
            ylabel='Price',
            figsize=(32, 16),
            volume=True,
            addplot=ema_plots,
            savefig=dict(fname=filepath, dpi=100))

def Intraday_breakouts(df, window):
    df.reset_index(inplace=True, drop =True)
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
    df['breakout1'] = (df['close'] > df['resistance']) & (df['high'].cummax().shift(1) == df['resistance'].shift(1))
    df['breakout1'] = df['breakout1'].cummax()
    df['breakout'] = df['breakout1'].shift(1) & (df['close'] > df['high'].shift(1)) & ((df['low'] < df['ema_15']) | (df['low'].shift(1) < df['ema_15'].shift(1))) & (df['close'] > df['ema_15'])
    return df 


def Intraday_breakdowns(df, window):
    df.reset_index(inplace=True, drop =True)
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
    df['breakdown1'] = (df['close'] < df['support']) & (df['low'].cummin().shift(1) == df['support'].shift(1))
    df['breakdown1'] = df['breakdown1'].cummax()
    df['breakdown'] = (df['breakdown1'].shift(1)) & (df['close'] < df['low'].shift(1)) & ((df['high'] > df['ema_15']) | (df['high'].shift(1) > df['ema_15'].shift(1))) & (df['close'] < df['ema_15'].shift(1))
    return df 

    

def single_direction_bearish_move(df, _date):
    START_TIME = datetime(2025, 10, 20, 9, 15).time()
    END_TIME = datetime(2025, 10, 20, 9, 55).time()
    df = filter_by_day(df, _date)
    df = filter_by_time(df, START_TIME, END_TIME)
    df['failed_9'] = df['ema_9'] > df['ema_9'].shift(1)
    df['failed_15'] = df['ema_15'] > df['ema_15'].shift(1)
    df.loc[0, 'failed_9'] = False
    df.loc[0, 'failed_15'] = False
    df['failed_9'] = df['failed_9'].cummax()
    df['failed_15'] = df['failed_15'].cummax()
    df['bearish'] = df['failed_9'] | df['failed_15']
    if len(df) > 0:
        return not df.iloc[-1]['bearish']
    

def single_direction_bullish_move(df, _date):
    START_TIME = datetime(2025, 10, 20, 9, 15).time()
    END_TIME = datetime(2025, 10, 20, 9, 55).time()
    df = filter_by_day(df, _date)
    df = filter_by_time(df, START_TIME, END_TIME)
    df['failed_9'] = df['ema_9'] < df['ema_9'].shift(1)
    df['failed_15'] = df['ema_15'] < df['ema_15'].shift(1)
    df.loc[0, 'failed_9'] = False
    df.loc[0, 'failed_15'] = False
    df['failed_9'] = df['failed_9'].cummax()
    df['failed_15'] = df['failed_15'].cummax()
    df['bullish'] = df['failed_9'] | df['failed_15']
    if len(df) > 0:
        return not df.iloc[-1]['bullish']
    
def analyse_move(stock, df, _date):
    START_TIME = datetime(2025, 10, 20, 9, 15).time()
    END_TIME = datetime(2025, 10, 20, 9, 55).time()
    lastdaysvolumes, lastdaysmedians = list_of_median_volume(df.copy(), _date, START_TIME, END_TIME)

    df = filter_by_day(df, _date)
    df = filter_by_time(df, START_TIME, END_TIME)
    median_vol = df['volume'].median()
    if len(lastdaysvolumes) > 0 :
        return median_vol > np.quantile(lastdaysvolumes, 0.9)
    
    return False