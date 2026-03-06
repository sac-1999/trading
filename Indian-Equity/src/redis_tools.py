from redis import Redis
import json
from datetime import datetime, timedelta
from typing import Dict
import pandas as pd

r = Redis(host="localhost", port=6379, decode_responses=True)

def get_last_day_state(db, symbol, last_day):
    last_day = last_day.strftime('%Y-%m-%d')
    key = f"lasttday_state:{last_day}"
    res = r.execute_command("JSON.GET", key, "$")
    if res is None:
        try:
            r.execute_command("JSON.SET", key, "$", "[]", "NX")
        except Exception as e:
            if "ERR" in str(e) and "path" not in str(e):
                pass

        r.execute_command("JSON.ARRAPPEND", key, "$", json.dumps())
        # df = db.get_candles(symbol, '5m')
        # df = filter
    # return 


def reform_date(_date):
    return _date.strftime('%Y-%m-%d')

def load_prev_days_mean_volumes(_day, symbol):
    _day = reform_date(_day)
    key = f"{_day}:{symbol}:prevdaysmeanvolumes"
    return r.get(key)


def set_prev_days_mean_volumes(_day, symbol, volume):
    _day = reform_date(_day)
    key = f"{_day}:{symbol}:prevdaysmeanvolumes"
    r.set(key, volume)


def set_last_day_state(symbol, _date, state):
    _date = reform_date(_date)
    high = f"{_date}:{symbol}:lastdayhigh"
    low = f"{_date}:{symbol}:lastdaylow"
    close = f"{_date}:{symbol}:lastdayclose"
    open = f"{_date}:{symbol}:lastdayopen"
    r.set(high, state['high'])
    r.set(low, state['low'])
    r.set(close, state['close'])
    r.set(open, state['open'])
    
def load_last_day_state(_date, symbol):
    _date = reform_date(_date)
    high = f"{_date}:{symbol}:lastdayhigh"
    low = f"{_date}:{symbol}:lastdaylow"
    close = f"{_date}:{symbol}:lastdayclose"
    open = f"{_date}:{symbol}:lastdayopen"
    open = r.get(open)
    high = r.get(high)
    close = r.get(close)
    low = r.get(low)

    if open is None or high is None or close is None or low is None:
        return None
    return {'open':open ,
            'high': high,
             'close': close,
              'low': low}


def set_curr_day_state(symbol, state):
    _date = datetime.today()
    _date = reform_date(_date)
    high = f"{_date}:{symbol}:dayhigh"
    low = f"{_date}:{symbol}:daylow"
    close = f"{_date}:{symbol}:dayclose"
    open = f"{_date}:{symbol}:dayopen"
    change = f"{_date}:{symbol}:daychange"
    r.set(high, state['high'])
    r.set(low, state['low'])
    r.set(close, state['ltp'])
    r.set(open, state['open'])
    r.set(change, state['change'])

def load_curr_day_state(symbol):
    _date = datetime.today()
    _date = reform_date(_date)
    high = f"{_date}:{symbol}:dayhigh"
    low = f"{_date}:{symbol}:daylow"
    close = f"{_date}:{symbol}:dayclose"
    open = f"{_date}:{symbol}:dayopen"
    change = f"{_date}:{symbol}:daychange"
    high, low, close, open, change = r.get(high),r.get(low) ,r.get(close), r.get(open) , r.get(change)
    if high is None or low is None or open is None or change is None :
        return None

    return {'open':open ,
            'high': high,
             'close': close,
              'low': low,
              'change' : change}


    

def hset_breakouts(symbol: str, breakouts: Dict[int, float]) -> None:
    _date = datetime.today()
    _date = reform_date(_date)
    key = f"{_date}:{symbol}:breakouts"
    mapping = {str(ts): str(level) for ts, level in breakouts.items()}
    r.hset(key, mapping=mapping)


def hget_breakouts(symbol):
    _date = datetime.today()
    _date = reform_date(_date)
    key = f"{_date}:{symbol}:breakouts"
    data = r.hgetall(key)
    if not data:
        return None
    # Convert keys/values
    allbreakouts = [(int(ts.decode()), float(val.decode())) for ts, val in data.items()]
    return allbreakouts


def set_past_resistance(symbol, _date, levels):
    _date = reform_date(_date)
    key = f"{_date}:{symbol}:pastresistance"
    r.set(key, json.dumps(levels))


def get_past_resistance(symbol, _date):
    _date = reform_date(_date)
    key = f"{_date}:{symbol}:pastresistance"
    raw = r.get(key)
    levels = json.loads(raw) if raw else []
    return levels


def set_past_support(symbol, _date, levels):
    _date = reform_date(_date)
    key = f"{_date}:{symbol}:support"
    r.set(key, json.dumps(levels))


def get_past_support(symbol, _date):
    _date = reform_date(_date)
    key = f"{_date}:{symbol}:support"
    raw = r.get(key)
    levels = json.loads(raw) if raw else []
    return levels


def set_day_trades(state : dict):
    _date = datetime.today()
    _date = reform_date(_date)
    trade = {
        "symbol": state['symbol'], 
        "entry": float(state['entry']),
        "sl": float(state['sl']),
        "time": state['tm']
    }
    key = f"{_date}:trades"
    try:
        r.execute_command("JSON.SET", key, "$", "[]", "NX")
    except Exception as e:
        if "ERR" in str(e) and "path" not in str(e):
            pass
    r.execute_command("JSON.ARRAPPEND", key, "$", json.dumps(trade))
    return key


def get_day_trades():
    _date = datetime.today()
    _date = reform_date(_date)
    key = f"{_date}:trades"
    res = r.execute_command("JSON.GET", key, "$")
    if not res:
        return []
   
    data = json.loads(res)
    return data

def set_holiday(holidayflag, _date):
    _date = reform_date(_date)
    key = f"{_date}:holidayflag"
    r.set(key, holidayflag)

def load_holiday(_date):
    _date = reform_date(_date)
    key = f"{_date}:holidayflag"
    return r.get(key)

def set_last_trading_day(_date, last_trading_date):
    last_trading_date = reform_date(last_trading_date)
    _date = reform_date(_date)
    key = f"{_date}:lasttradingday"
    r.set(key, last_trading_date)

def load_last_trading_day(_date):
    _date = reform_date(_date)
    key = f"{_date}:lasttradingday"
    return r.get(key)


def set_top_gainers(gainers):
    _date = datetime.today()
    _date = reform_date(_date)
    key = f"{_date}:gainers"
    r.set(key, json.dumps(gainers))
    print('updating gainers list')
    

def load_top_gainers():
    _date = datetime.today()
    _date = reform_date(_date)
    key = f"{_date}:gainers"
    return r.get(key)

def set_top_losers(gainers):
    _date = datetime.today()
    _date = reform_date(_date)
    key = f"{_date}:losers"
    r.set(key, json.dumps(gainers))
    print('updating losers list')

def load_top_losers():
    _date = datetime.today()
    _date = reform_date(_date)
    key = f"{_date}:losers"
    return r.get(key)

def load_last_median(_date, symbol):
    _date = reform_date(_date)
    key = f"{_date}:{symbol}:lastmedian"
    return r.get(key)


def set_last_median(_date, symbol, median):
    _date = reform_date(_date)
    key = f"{_date}:{symbol}:lastmedian"
    r.set(key, median)

def set_indexlist(listofindex):
    key = f"indian:indices"
    r.set(key, json.dumps(listofindex))

def get_indexlist():
    key = f"indian:indices"
    return r.get(key)