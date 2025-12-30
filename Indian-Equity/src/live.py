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

def is_holiday_day(startdate, enddate, listofsymbols):
    failedcount = 0
    for symbol, isindex in listofsymbols.items():
        df = broker.get_candle_stick_data('NSE', symbol, 'ONE_MINUTE', startdate, enddate, isindex)
        if len(df) == 0:
            failedcount += 1
        else:
            return False
        if failedcount == 5:
            return True

def fast_sync(exchange, _date):
    global LISTOFSYMBOLSTOTRADE
    while(True):
        listofsymbols = LISTOFSYMBOLSTOTRADE.copy()
        startdate = datetime(_date.year, _date.month, _date.day, 0, 0)
        enddate = datetime(_date.year, _date.month, _date.day, 23, 59)
        if is_holiday_day(startdate, enddate, listofsymbols):
            print(f"Possibly holiday on {_date}")
            return 
        print("-"*50, listofsymbols)
        for symbol, isindex in listofsymbols.items():
            df = broker.get_candle_stick_data(exchange, symbol, 'ONE_MINUTE', startdate, enddate, isindex)
            if len(df) == 0:
                return 
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            df.dropna(subset=["timestamp"], inplace=True)
            df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
            df['symbol'] = symbol
            df['timeframe'] = '1m'
            list_of_jsons = df.to_dict(orient='records')
            print(symbol, '  ', _date.date(), end= ' ')
            db.insert_candles(list_of_jsons)
        
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
        df = Indicators.ema(df, 9, 'ema')
        df = Indicators.ema(df, 15, 'ema')
        df['bullish'] = (df['close'] > df['ema_9']) & (df['close'] > df['ema_15']) & (df['ema_9'] > df['ema_9'].shift(1)) & (df['ema_15'] > df['ema_15'].shift(1))
        df['bearish'] = (df['close'] < df['ema_9']) & (df['close'] < df['ema_15']) & (df['ema_9'] < df['ema_9'].shift(1)) & (df['ema_15'] < df['ema_15'].shift(1))
        row = df.iloc[-1]
        if row['date'] != _date.date():
            print('Nifty date data is lagging')
            return 
        
        lasttime =  _date - timedelta(minutes=10)
        lasttime = lasttime.time()

        if row['time'] < lasttime:
            print('Nifty time is lagging')
            return 

        if row['bullish']:
            return "bullish"

        if row['bearish']:
            return "bearish"
    return 



def monitor():
    global LISTOFSYMBOLSTOTRADE
    while(True):
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
        if nifty == 'bullish':
            for symbol, state in topgainers:
                df = load_candles(symbol)
                if df is not None:
                    row = df.iloc[-1]
                    if row['date'] != _date.date():
                        print(f"{symbol} date data is lagging")
                        continue
                    
                    lasttime =  _date - timedelta(minutes=10)
                    lasttime = lasttime.time()

                    if row['time'] < lasttime:
                        print(f"{symbol} time is lagging")
                        continue
                    
                    if analyse_move(stock, df.copy(), _date):
                        df = filter_by_day(df, _date)
                        if single_direction_bearish_move(df.copy(), _date):
                            dftmp = Intraday_breakdowns(df.copy(), 3)
                            dftmp = dftmp[dftmp['breakdown']]
                            for i , row in dftmp.iterrows():
                                if row['time'] > datetime(2025, 10, 20, 10, 0).time() and row['time'] < datetime(2025, 10, 20, 11, 30).time():
                                    save_image(stock, df, _date, row['close'], row['close'] + row['close'] * 0.005, row['close'], str(row['time']).replace(':','_'))
                
        if nifty == 'bearish':
            for symbol, state in toplosers:
                df = load_candles(symbol)
                if df is not None:
                    row = df.iloc[-1]
                    if row['date'] != _date.date():
                        print(f"{symbol} date data is lagging")
                        continue
                    
                    lasttime =  _date - timedelta(minutes=10)
                    lasttime = lasttime.time()

                    if row['time'] < lasttime:
                        print(f"{symbol} time is lagging")
                        continue
                    
                    if analyse_move(stock, df.copy(), _date):
                        df = filter_by_day(df, _date)        
                        if single_direction_bearish_move(df.copy(), _date):
                            dftmp = Intraday_breakdowns(df.copy(), 3)
                            dftmp = dftmp[dftmp['breakdown']]
                            for i , row in dftmp.iterrows():
                                if row['time'] > datetime(2025, 10, 20, 10, 0).time() and row['time'] < datetime(2025, 10, 20, 11, 30).time():
                                    save_image(stock, df, _date, row['close'], row['close'] + row['close'] * 0.005, row['close'], str(row['time']).replace(':','_'))
            
            

swsthread = threading.Thread(target=websocket_connect, name="SmartWS", daemon=True)
swsthread.start()
monitorthread = threading.Thread(target=monitor, name="Monitor", daemon=True)
monitorthread.start()
syncthread = threading.Thread(target=fast_sync, name="syncthread", daemon=True, args=(EXCHANGE, datetime.today() - timedelta(1)))
syncthread.start()

print('they will run')
while(1):
    # startday = datetime.today() - timedelta(days=10)
    # while(startday < datetime.today()):
    #     fast_sync('NSE', startday, stocks_with_index)
    #     startday = startday + timedelta(1)
    time.sleep(1000)

