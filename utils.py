import pandas as pd
import requests
import json
import os

from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
from indicators import Indicators
import mplfinance as mpf


master_token_list = None
master_token_file = "masterscrip.json"

def filter_by_day(df, scanday):
    scanday = scanday.strftime('%Y-%m-%d')
    df = df[df['scanday'] == scanday]
    return df

def resample(data, interval, offset = '0min'):
    if interval == '10min' or interval == '1h':
        offset = '15min' 
    data.index = pd.to_datetime(data['timestamp'])
    data = data.resample(interval, offset = offset).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    data = data.dropna()
    data.reset_index( inplace=True)
    return data


def download_scrip_master():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    response = requests.get(url)

    if response.status_code == 200:
        scrips = response.json()
        with open(master_token_file, "w") as file:
            json.dump(scrips, file)
        return scrips
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")

def get_token(exchange, symbol):
    if not os.path.exists(master_token_file):
        download_scrip_master()
    global master_token_list
    if master_token_list is None:
        with open(master_token_file, 'r') as file:
            master_token_list = json.load(file)

    for scrip in master_token_list:
        if scrip.get('symbol') == symbol and scrip.get('exch_seg') == exchange:
            return scrip.get('token')
    return None



def get_dates(startdate, enddate):
    startdate = pd.to_datetime(startdate)
    enddate = pd.to_datetime(enddate)
    list_of_dates = []

    while startdate <= enddate:
        list_of_dates.append(startdate)
        startdate += relativedelta(months=1)

    return list_of_dates


def filter_data_by_dates(df, startdate, enddate):
    df = df[(df['day'] >= pd.to_datetime(startdate).date()) & (df['day'] < pd.to_datetime(enddate).date())]
    df = df.sort_values(by='timestamp')
    df.reset_index(inplace = True, drop = True)
    return df

def get_prevous_day_data(df, day):
    df = df.sort_values(by='timestamp')
    df = df[(df['day'] < pd.to_datetime(day).date())]
    if len(df)==0:
        return None
    lastday = list(df['day'].values)[-1]
    df = df[(df['day'] == pd.to_datetime(lastday).date())]
    df = df.sort_values(by='timestamp')
    df.reset_index(inplace = True, drop = True)
    return df


# def previous_day_ema_crossover_count(df):



# def save_plot(df, stock, text):
#     date = str(text['tradetime'])
#     date = date[:10]

#     filename = "samplesimages/"+stock + '_' + date + ".jpg"
#     title = f"entry :{text['entry']} sl : {text['sl']} time : {text['tradetime']}"
#     df['time'] = df['timestamp']
#     df.set_index('time', inplace=True)

#     mpf.plot(df, type='candle', style='charles', title=title,
#          ylabel='Price', savefig=dict(fname=filename, dpi=100))


# import pandas as pd
# import mplfinance as mpf

def save_plot(df, stock, text):
    if stock is None:
        raise ValueError("Trades can save as symbol name is missing")
    # Format date and filename
    date = str(text['tradetime'])[:10]
    foldername = f"samplesimages/{'-'.join(date.split(':'))}"
    os.makedirs(foldername, exist_ok=True)

    filename = f"{foldername}/{stock}.jpg"
    entry = text['entry']
    sl = text ['sl']
    exit = text['exit']
    title = f"rr : {round(text['profit'],2)} || time : {text['tradetime'].time()}"

    # Set timestamp as datetime index
    df['time'] = pd.to_datetime(df['timestamp'])
    df.set_index('time', inplace=True)

    entry_line = pd.Series(entry, index=df.index)
    sl_line = pd.Series(sl, index=df.index)
    exit_line = pd.Series(exit, index=df.index)


    # Create EMA overlays
    ema_plots = [
        mpf.make_addplot(entry_line, color='purple', linestyle='-', width=2),
        mpf.make_addplot(sl_line, color='red', linestyle='--', width=2),
        mpf.make_addplot(exit_line, color='green', linestyle='--', width=2)
    ]

    if 'vwap' in list(df.columns):
            ema_plots.append(mpf.make_addplot(df['vwap'], color='red', width=3))

    # for col in list(df.columns): 
    #     if 'ema_' in col or 'supertrend' in col:
    #         ema_plots.append(mpf.make_addplot(df[col], color='blue', width=1))
    
    ema_plots.append(mpf.make_addplot(df['ema_8'], color='black', width=1))
    ema_plots.append(mpf.make_addplot(df['ema_21'], color='blue', width=2))
    # ema_plots.append(mpf.make_addplot(df['vwap'], color='red', width=2))

    # Generate candlestick chart with EMAs
    mpf.plot(df, type='candle', style='charles', title=title,
             ylabel='Price', addplot=ema_plots,
             figsize=(16, 8),
             savefig=dict(fname=filename, dpi=100))
    

def future(df, entry, sl, trade_type):
    maxrr = 0
    for i,row in df.iterrows():
        if trade_type == 'buy':
            if row['low'] < sl:
                break
            maxrr = max(maxrr, (row['high'] - entry) / (entry - sl))
            
        if trade_type == 'sell':
            if row['high'] > sl:
                break
            maxrr = max(maxrr,(entry - row['low']) / (sl - entry))
        
    return maxrr