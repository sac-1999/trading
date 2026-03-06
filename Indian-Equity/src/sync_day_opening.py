from logging import Logger
import utils
import pandas as pd
from objects import *
from datetime import datetime, timedelta
from indicators import Indicators
from strategy_utils import *
from redis_tools import *

logger = Logger(__name__)
allstocks = pd.read_csv('./../data/ind_nifty200list.csv')['Symbol'].tolist()[:2]
stocks_with_index = {stock: False for stock in allstocks}
INDEX = 'Nifty 50'
EXCHANGE = 'NSE'
WINDOW = 2
stocks_with_index[INDEX] = True

def load_candles(symbol):
    records = db.get_candles(symbol, '5m')
    df = pd.DataFrame(records)
    if df.empty:
        print(f"No candle data found. -> {symbol}")
        return
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df.dropna(subset=["timestamp"], inplace=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    df['time'] = df['timestamp'].dt.time
    df['date'] = df['timestamp'].dt.date
    return df

def load_daily_candles(symbol):
    records = db.get_daily_candles(symbol)
    df = pd.DataFrame(records)
    if df.empty:
        print(f"No candle data found. -> {symbol}")
        return
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df.dropna(subset=["timestamp"], inplace=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    df['date'] = df['timestamp'].dt.date
    return df


def sync_minute_past(past_days = 10):
    global stocks_with_index
    _date = datetime.today() - timedelta(days = 1)
    startdate = _date - timedelta(days = past_days)
    startdate = datetime(startdate.year,startdate.month, startdate.day, 0, 0)
    enddate = datetime(_date.year, _date.month, _date.day, 23, 59)

    for symbol, isindex in stocks_with_index.items():
        try:
            df = broker.get_candle_stick_data(EXCHANGE, symbol, 'ONE_MINUTE', startdate, enddate, isindex)
            if len(df) == 0:
                continue
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            df.dropna(subset=["timestamp"], inplace=True)
            df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
            df['symbol'] = symbol
            df['timeframe'] = '1m'
            list_of_jsons = df.to_dict(orient='records')
            db.insert_candles(list_of_jsons)
        except Exception as e:
            print(f"Error in syncing : {symbol}", str(e))
        

def sync_daily_past(past_days = 365):
    global stocks_with_index
    _date = datetime.today() - timedelta(days = 1)
    startdate = _date - timedelta(days = past_days)
    startdate = datetime(startdate.year,startdate.month, startdate.day, 0, 0)
    enddate = datetime(_date.year, _date.month, _date.day, 23, 59)

    for symbol, isindex in stocks_with_index.items():
        try:
            df = broker.get_candle_stick_data(EXCHANGE, symbol, 'ONE_DAY', startdate, enddate, isindex)
            if len(df) == 0:
                continue
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            df.dropna(subset=["timestamp"], inplace=True)
            df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
            df['symbol'] = symbol
            list_of_jsons = df.to_dict(orient='records')
            print(f"Syncing {symbol}  ", end = " ")
            db.insert_daily_candles(list_of_jsons)
        except Exception as e:
            print(f"Error in syncing : {symbol}", str(e))
            

def Intraday_breakouts(df, window):
    df.reset_index(inplace=True, drop =True)
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

def Intraday_breakdowns(df, window):
    df.reset_index(inplace=True, drop =True)
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

def get_past_levels(symbol, window):
    df = load_daily_candles(symbol)
    if df is None:
        return None, None
    df = df.sort_values(by="timestamp")
    df.reset_index(inplace=True, drop = True)
    allres = Intraday_breakouts(df.copy(), window)
    allsup = Intraday_breakdowns(df.copy(), window)
    return allres, allsup


def update_last_day_state(symbol, date):
    _date = date - timedelta(days = 1)
    while (_date > date - timedelta(5)):
        df = load_daily_candles(symbol)
        df['date'] = df['timestamp'].dt.date
        df = df[df['date'] == _date.date()]
        if len(df) >0:
            state = df.to_dict(orient = 'records')
            print(state)
            set_last_day_state(symbol, date, state[0])
            break
        _date = _date - timedelta(1)
        # set_last_day_state()
        
def filter_by_day(df, scanday):
    df = df[df['date'] == pd.to_datetime(scanday).date()]
    df.reset_index(inplace = True, drop = True)
    return df

def filter_by_time(df, starttime, endtime):
    df = df[(df['time'] >= starttime) & (df['time'] <= endtime)]
    df.reset_index(inplace = True, drop = True)
    return df


def median_volume_in_prev_days(symbol, _date, n_days = 10):
    starttime = datetime(2025, 10, 20, 9, 15).time()
    endtime = datetime(2025, 10, 20, 9, 55).time()
    last_10_days = pd.date_range(end=_date, periods=n_days)[:-1]
    volumes = []
    orgdf = load_candles(symbol)
    print(orgdf)
    if orgdf is None:
        return None
    for last_day in last_10_days:
        df = filter_by_day(orgdf.copy(), last_day)
        df = filter_by_time(df, starttime, endtime)
        if not df.empty: 
            median_vol = df['volume'].median()
            volumes.append(int(median_vol))
    medianvolume = np.quantile(volumes, 0.9)
    return medianvolume

_date = datetime.today()
# sync_daily_past()
# sync_minute_past()


def update_states(_date):
    startdate = datetime(_date.year,_date.month, _date.day, 0, 0)
    enddate = datetime(_date.year, _date.month, _date.day, 23, 59)
    df = broker.get_candle_stick_data(EXCHANGE, INDEX, 'ONE_DAY', startdate, enddate, True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df.dropna(subset=["timestamp"], inplace=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    df['symbol'] = INDEX
    list_of_jsons = df.to_dict(orient='records')
    print(f"Syncing {INDEX}  ", end = " ")
    db.insert_daily_candles(list_of_jsons)

    df = load_daily_candles(INDEX)
    df = df.tail(10)
    df.reset_index(inplace=True)
    lastday = None
    for i, row in df.iterrows():
        set_holiday(0, row['date'])
        if lastday is not None:
            set_last_trading_day(row['date'], lastday)
        lastday = row['date']


update_states(_date)
for symbol, isindex in stocks_with_index.items():
    allres, allsup = get_past_levels(symbol, WINDOW)
    set_past_support(symbol, _date, allsup)
    set_past_resistance(symbol, _date, allres)
    update_last_day_state(symbol, _date)
    medianvolume =  median_volume_in_prev_days(symbol, _date, 5)
    if medianvolume is not None:
        set_prev_days_mean_volumes(_date, symbol, medianvolume)


    open, high, low, close = load_last_day_state( _date, symbol)
    open, high, low, close = float(open), float(high), float(low), float(close)
    print(open, high, low, close)