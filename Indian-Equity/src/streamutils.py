import numpy as np
import pandas as pd
from objects import *
from datetime import datetime, timedelta
from redis_tools import *
import jsonpickle

_DATE = datetime.today()

def filter_by_day(df, scanday):
    df = df[df['date'] <= pd.to_datetime(scanday).date()]
    df.reset_index(inplace = True, drop = True)
    return df

def filter_by_time(df, starttime, endtime):
    df = df[(df['time'] >= starttime) & (df['time'] <= endtime)]
    df.reset_index(inplace = True, drop = True)
    return df

def sync_daily_past(exchange, symbol, isindex, past_days = 365):
    startdate = _DATE - timedelta(days = past_days)
    startdate = datetime(startdate.year,startdate.month, startdate.day, 0, 0)
    enddate = datetime(_DATE.year, _DATE.month, _DATE.day, 23, 59)
    df = broker.get_candle_stick_data(exchange, symbol, 'ONE_DAY', startdate, enddate, isindex)
    if df is not None and len(df) != 0:
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            df.dropna(subset=["timestamp"], inplace=True)
            df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
            df['symbol'] = symbol
            list_of_jsons = df.to_dict(orient='records')
            print(f"Syncing {symbol}  ", end = " ")
            db.insert_daily_candles(list_of_jsons)
        except Exception as e:
            print(f"Error in syncing : {symbol}", str(e))

def get_candles_from_db(symbol):
    records = db.get_daily_candles(symbol)
    df = pd.DataFrame(records)
    if df.empty:
        print(f"No candle data found. -> {symbol}")
        return None
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df.dropna(subset=["timestamp"], inplace=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    df['date'] = df['timestamp'].dt.date
    df = df.sort_values(by="timestamp")
    df = filter_by_day(df, _DATE - timedelta(1))
    df.reset_index(inplace=True, drop = True)
    return df

def update_last_day_state(exchange, symbol, isindex):
    print(f"Updating Last day state ............. : {symbol}")
    sync_daily_past(exchange, symbol, isindex)
    df = get_candles_from_db(symbol)
    if df is None:
        return None
    lasttradingday = load_last_trading_day(_DATE)
    df = df[df['date'] == pd.to_datetime(lasttradingday).date()]
    if df is None or len(df)==0:
        return None
    state = df.to_dict(orient = 'records')
    set_last_day_state(symbol, _DATE, state[0])

def major_resistance(symbol, window):
    df = get_candles_from_db(symbol)
    if df is None:
        return []
    df['resistance'] = np.nan
    for i in range(len(df)):
        if i == len(df)-window:
            break

        if i == 0:
            right = df.iloc[i+1:i+window+1]
            curr = df.iloc[i]
            if curr['high'] > right['high'].max():
                df.loc[i, 'resistance'] = df.iloc[i]['high']
        
        else:
            left = df.iloc[max(i-window,0) : i+1]
            right = df.iloc[i : i+window+1]
            curr = df.iloc[i]
            if curr['high'] >= left['high'].max() and curr['high'] >= right['high'].max():
                df.loc[i, 'resistance'] = df.iloc[i]['high']
    df = df[['timestamp', 'resistance']]
    df = df.dropna()
    allres = list(df['resistance'])
    if len(allres) == 0:
        return []
    finalres = [allres[-1]]
    for res in allres[::-1]:
        if finalres[-1] < res:
            finalres.append(res)
    return finalres

def major_support(symbol, window):
    df = get_candles_from_db(symbol)
    if df is None:
        return []
    df['support'] = np.nan
    for i in range(len(df)):
        if i == len(df)-window:
            break

        if i == 0:
            right = df.iloc[i+1:i+window+1]
            curr = df.iloc[i]
            if curr['low'] < right['low'].min():
                df.loc[i, 'support'] = df.iloc[i]['low']
        
        else:
            left = df.iloc[max(i-window,0) : i+1]
            right = df.iloc[i : i+window+1]
            curr = df.iloc[i]
            if curr['low'] <= left['low'].min() and curr['low'] <= right['low'].min():
                df.loc[i, 'support'] = df.iloc[i]['low']

    df = df[['timestamp', 'support']]
    df = df.dropna()
    allsupport = list(df['support'])
    if len(allsupport) == 0:
        return []
    finalsupport = [allsupport[-1]]
    for sup in allsupport[::-1]:
        if finalsupport[-1] > sup:
            finalsupport.append(sup)
    return finalsupport

INDEX= 'Nifty 50'
def update_trading_day():
    print(f"Syncing {INDEX}")
    sync_daily_past('NSE', INDEX, True)
    df = get_candles_from_db(INDEX)
    if df is not None:
        lastday = None
        for i, row in df.iterrows():
            set_holiday(0, row['date'])
            if lastday is not None:
                set_last_trading_day(row['date'], lastday)
            lastday = row['date']
        if lastday != _DATE.date():
            set_last_trading_day(_DATE, lastday)
    else:
        print(f"No candle data found for {INDEX}")
    

def get_allstate_for_symbol(exchange, symbol, isindex):
    data = {}
    if load_last_trading_day(_DATE) is None:
        update_trading_day()

    data['symbol'] = symbol
    data['last_trading_day'] =load_last_trading_day(_DATE)
    data['isholiday'] = load_holiday(_DATE)
    data['trades_for_day'] = get_day_trades()

    
    lastdaystate = load_last_day_state(_DATE, symbol)

    if lastdaystate is None or len(lastdaystate) == 0:    
        update_last_day_state(exchange, symbol, isindex)
    data['curr_day_state'] = load_curr_day_state(symbol)
    change = float(data['curr_day_state']['change']) 
    # if abs(change) > 3.5 or abs(change) <1.5: 
    #     return None

    data['last_day_state'] = load_last_day_state(_DATE, symbol)


    supportlevels = get_past_support(symbol, _DATE)
    if supportlevels is None or len(supportlevels) == 0:
        supportlevels = major_support(symbol, 3)
        set_past_support(symbol, _DATE, supportlevels)
    data['past_support'] = get_past_support(symbol, _DATE)[:3]
    
    resistancelevels = get_past_resistance(symbol, _DATE)
    if resistancelevels is None or len(resistancelevels) == 0:
        resistancelevels = major_resistance(symbol, 3)
        set_past_resistance(symbol, _DATE, resistancelevels)
    data['past_resistance'] = get_past_resistance(symbol, _DATE)[:3]

    msg = jsonpickle.encode(data, unpicklable=False)
    return msg


def get_state_for_index(symbol): 
    data = {}
    data['curr_day_state'] = load_curr_day_state(symbol)

    data['symbol'] = symbol + '_index'
    msg = jsonpickle.encode(data, unpicklable=False)
    return msg
