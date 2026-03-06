from broker import Broker_websocket
from logging import Logger
import utils
import pandas as pd
import threading
import time
from objects import *
from datetime import datetime, timedelta
from indicators import Indicators
from strategy_utils import *


logger = Logger(__name__)
allstocks = pd.read_csv('./../data/ind_nifty200list.csv')['Symbol'].tolist()
stocks_with_index = {stock: False for stock in allstocks}
INDEX = 'Nifty 50'
EXCHANGE = 'NSE'
stocks_with_index[INDEX] = True

stocktotoken = {stock: utils.get_token('NSE', stock + '-EQ') for stock in allstocks}
TOPLOSERSGAINERS = 15
THRESHOLDPCT = 1.5
MAXPCT = 3
LISTOFSYMBOLSTOTRADE = {}

stockstate = {}

tokentostock = {
    token: stock
    for stock, token in stocktotoken.items()
    if token is not None
}

subscribelist = [
    {
        "exchangeType": 1,                          
        "tokens": [str(t) for t in tokentostock.keys()]
    }
]

correlation_id = "1234"
def on_open( wsapp):
    logger.info("WebSocket opened")
    broker_socket.sws.subscribe(correlation_id, 2, subscribelist)

def on_data(wsapp, message):
    token = message['token']
    stock = tokentostock[token]
    high = message['high_price_of_the_day']/100
    low = message['low_price_of_the_day']/100
    open = message['open_price_of_the_day']/100
    lastdayclose = message['closed_price']/100
    ltp = message['last_traded_price']/100
    change = (ltp - lastdayclose)/lastdayclose * 100
    stockstate[stock] = {'high' : high,
                         'low' : low,
                         'open' : open,
                         'ltp' : ltp,
                         'lastdayclose': lastdayclose,
                         'change' : change}

def on_error(wsapp, error):
    logger.error(f"WS error: {error}")

def on_close(wsapp):
    logger.warning("WebSocket closed")


broker_socket = Broker_websocket()
broker_socket.sws.on_open = on_open
broker_socket.sws.on_data = on_data
broker_socket.sws.on_error = on_error
broker_socket.sws.on_close = on_close


def websocket_connect():
    broker_socket.sws.connect()


def get_top_movers():
    global stockstate
    data = stockstate.copy()
    data = sorted(data.items(), key=lambda x: x[1]['change'], reverse=True)
    topgainers = data[:TOPLOSERSGAINERS]
    toplosers = data[-TOPLOSERSGAINERS:]
    return toplosers, topgainers

def fast_daily_sync(exchange, _date):
    global LISTOFSYMBOLSTOTRADE
    while(True):
        listofsymbols = LISTOFSYMBOLSTOTRADE.copy()
        startdate = datetime(_date.year, _date.month, _date.day, 0, 0)
        enddate = datetime(_date.year, _date.month, _date.day, 23, 59)
        try:
            for symbol, isindex in listofsymbols.items():
                df = broker.get_candle_stick_data(exchange, symbol, 'ONE_MINUTE', startdate, enddate, isindex)
                if len(df) == 0:
                    continue
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
                df.dropna(subset=["timestamp"], inplace=True)
                df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
                df['symbol'] = symbol
                df['timeframe'] = '1m'
                list_of_jsons = df.to_dict(orient='records')
                print(symbol, '  ', _date.date(), end= ' ')
                db.insert_candles(list_of_jsons)
        except Exception as e:
            print("Error from fast sync thread : ", str(e))
            continue

def islag(symbol, row, _date, thtime = 15):
    if row['date'] != _date.date():
        print(f"{symbol} date data is lagging")
        return True
        
    lasttime =  _date - timedelta(minutes=thtime)
    lasttime = lasttime.time()

    if row['time'] < lasttime:
        print(row['time'], lasttime)
        print(f"{symbol} time is lagging")
        return True

    return False

            
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

def get_nifty_view(_date):
    df = load_candles(INDEX)
    if df is not None:
        df = Indicators.ema(df, 15, 'ema')
        df = Indicators.ema(df, 30, 'ema')
        df['bullish'] = (df['close'] > df['ema_15']) & (df['close'] > df['ema_30']) & (df['ema_15'] > df['ema_15'].shift(1)) & (df['ema_30'] > df['ema_30'].shift(1))
        df['bearish'] = (df['close'] < df['ema_15']) & (df['close'] < df['ema_30']) & (df['ema_15'] < df['ema_15'].shift(1)) & (df['ema_30'] < df['ema_30'].shift(1))
        row = df.iloc[-1]
        if islag(INDEX, row, _date):
            return 
        
        if row['bullish']:
            return "bullish"

        if row['bearish']:
            return "bearish"
    return "sideways"



def monitor():
    global LISTOFSYMBOLSTOTRADE
    while(True):
        try:
            listofsymbols = LISTOFSYMBOLSTOTRADE.copy()
            time.sleep(2)
            listofsymbols = {}
            toplosers, topgainers = get_top_movers()
            topgainers = [(stockstate[0],stockstate[1]) for stockstate in topgainers if abs(stockstate[1]['change']) > THRESHOLDPCT and (abs(stockstate[1]['change'] < MAXPCT))]
            toplosers = [(stockstate[0],stockstate[1]) for stockstate in toplosers if (abs(stockstate[1]['change']) > THRESHOLDPCT) and (abs(stockstate[1]['change'] < MAXPCT))]
        
            for stock, state in topgainers:
                listofsymbols[stock] = False
            for stock, state in toplosers:
                listofsymbols[stock] = False
            listofsymbols[INDEX] = True
            LISTOFSYMBOLSTOTRADE = listofsymbols.copy()
            _date = datetime.today()
            nifty = get_nifty_view(_date)
            print(f"Nifty is {nifty}")
            if nifty == 'bullish':
                for symbol, state in topgainers:
                    df = load_candles(symbol)
                    if df is not None:
                        row = df.iloc[-1]
                        if islag(INDEX, row, _date):
                            continue
        
                        df = Indicators.ema(df, 9, 'ema')
                        df = Indicators.ema(df, 15, 'ema')
                        df = Indicators.ema(df, 30, 'ema')
                        if analyse_move(symbol, df.copy(), _date):
                            print("MOMENTUM IN VOLUME :  BULLISH", symbol)
                            df = filter_by_day(df, _date)
                            if single_direction_bullish_move(df.copy(), _date):
                                print("ONE DIRECTION MOVE HERE :  BULLISH", symbol)
                                dftmp = Intraday_breakouts(df.copy(), 3)
                                dftmp = dftmp[dftmp['breakout']]
                                for i , row in dftmp.iterrows():
                                    print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
                                    if islag(symbol, row, _date, thtime = 10):
                                        continue
                                    if row['time'] > datetime(2025, 10, 20, 10, 0).time() and row['time'] < datetime(2025, 10, 20, 14, 30).time():
                                        save_image(symbol, df, _date, row['close'], row['close'] - row['close'] * 0.005, row['close'], str(row['time']).replace(':','_'))
                                        break
                                    
                    
            if nifty == 'bearish':
                for symbol, state in toplosers:
                    df = load_candles(symbol)
                    if df is not None:
                        row = df.iloc[-1]
                        if islag(INDEX, row, _date):
                            continue
                        
                        df = Indicators.ema(df, 9, 'ema')
                        df = Indicators.ema(df, 15, 'ema')
                        df = Indicators.ema(df, 30, 'ema')

                        if analyse_move(symbol, df.copy(), _date):
                            print("MOMENTUM IN VOLUME :  BEARISH", symbol)
                            df = filter_by_day(df, _date)
                            if single_direction_bearish_move(df.copy(), _date):
                                print("ONE DIRECTION MOVE HERE :  BEARISH", symbol)
                                dftmp = Intraday_breakdowns(df.copy(), 3)
                                dftmp = dftmp[dftmp['breakdown']]
                                for i , row in dftmp.iterrows():
                                    print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
                                    if islag(symbol, row, _date, thtime = 10):
                                        continue
                                    if row['time'] > datetime(2025, 10, 20, 10, 0).time() and row['time'] < datetime(2025, 10, 20, 14, 30).time():
                                        save_image(symbol, df, _date, row['close'], row['close'] - row['close'] * 0.005, row['close'], str(row['time']).replace(':','_'))
                                        break
        except Exception as e:
            print("Error in monitor thread", str(e))
            continue
                

swsthread = threading.Thread(target=websocket_connect, name="SmartWS", daemon=True)
swsthread.start()
monitorthread = threading.Thread(target=monitor, name="Monitor", daemon=True)
monitorthread.start()
syncthread = threading.Thread(target=fast_sync, name="syncthread", daemon=True, args=(EXCHANGE, datetime.today()))
syncthread.start()

while(1):
    time.sleep(1000)

