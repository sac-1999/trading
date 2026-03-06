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
from redis_tools import *

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
stock_state = {}

tokentostock = {
    token: stock
    for stock, token in stocktotoken.items()
    if token is not None
}

index_to_token, token_to_index = utils.get_index_token_mapping()
allindices = list(index_to_token.keys())
# if get_indexlist() is None:
set_indexlist(list(index_to_token.keys()))
stocktotoken.update(index_to_token)
tokentostock.update(token_to_index)


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
    currstate = {'high' : high,
                    'low' : low,
                    'open' : open,
                    'ltp' : ltp,
                    'lastdayclose': lastdayclose,
                    'change' : round(change, 2)}
    if stock not in allindices:
        stock_state[stock] = currstate
    set_curr_day_state(stock, currstate)
    


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

def sync_candles(exchange, symbol, startdate, enddate):
    isindex = False
    if symbol == 'Nifty 50':
        isindex = True
    print(symbol, isindex)
    df = broker.get_candle_stick_data(exchange, symbol, 'ONE_MINUTE', startdate, enddate, isindex)
    if df is None or len(df) == 0:
        return 
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df.dropna(subset=["timestamp"], inplace=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    df['symbol'] = symbol
    df['timeframe'] = '1m'
    list_of_jsons = df.to_dict(orient='records')
    print(symbol, '  ', enddate.date(), end= ' ')
    db.insert_candles(list_of_jsons)

def fast_daily_sync(exchange, _date):
    while(True):
        listofsymbols = ['Nifty 50']
        losers = load_top_losers()
        gainers = load_top_gainers()
        if losers is not None:
            losers = json.loads(losers)     
            listofsymbols.extend(losers)
        if gainers is not None:
            gainers = json.loads(gainers)
            listofsymbols.extend(gainers)

        startdate = datetime(_date.year, _date.month, _date.day, 0, 0)
        enddate = datetime(_date.year, _date.month, _date.day, 23, 59)
        try:
            for symbol in listofsymbols:
                sync_candles(exchange, symbol, startdate, enddate)
        except Exception as e:
            print("Error from fast sync thread : ", str(e))
            continue


def update_last_median(symbol):
    _date = datetime.today()
    day_10 = _date - timedelta(10)
    startdate = datetime(day_10.year, day_10.month, day_10.day, 0, 0)
    enddate = datetime(_date.year, _date.month, _date.day, 23, 59)
    start_time = datetime(2025, 10, 20, 9, 15).time()
    end_time = datetime(2025, 10, 20, 9, 55).time()
    try:
        sync_candles('NSE', symbol, startdate, enddate)
    except Exception as e:
        print("Error in sync for meadian: ", str(e))
        return 

    
    records = db.get_candles(symbol, '5m')
    df = pd.DataFrame(records)
    if df is not None and  len(df) > 0:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df.dropna(subset=["timestamp"], inplace=True)
        df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
        df['time'] = df['timestamp'].dt.time
        df['date'] = df['timestamp'].dt.date
        df = df.sort_values(by="timestamp")
        last_10_days = pd.date_range(end=_date.date(), periods=10)[:-1]
        volumes = []

        for last_day in last_10_days:
            if last_day.date() == datetime.today().date():
                continue
            dftmp = filter_by_day(df.copy(), last_day)
            dftmp = filter_by_time(dftmp, start_time, end_time)
        
            if not dftmp.empty: 
                median_vol = dftmp['volume'].median()
                volumes.append(int(median_vol))
    
        if len(volumes) > 1:
            set_last_median(_date, symbol, int(np.percentile(volumes, 80)))

        else:
            return 
        
def get_currday_volume(symbol):
    _date = datetime.today()   
    start_time = datetime(2025, 10, 20, 9, 15).time()
    end_time = datetime(2025, 10, 20, 9, 55).time()    
    records = db.get_candles(symbol, '5m')
    df = pd.DataFrame(records)
    if df is not None and  len(df) > 0:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df.dropna(subset=["timestamp"], inplace=True)
        df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
        df['time'] = df['timestamp'].dt.time
        df['date'] = df['timestamp'].dt.date
        df = df.sort_values(by="timestamp")
        dftmp = filter_by_day(df.copy(), _date)
        dftmp = filter_by_time(dftmp, start_time, end_time)
        if dftmp is not None and len(dftmp) > 0:
            return int(dftmp['volume'].median())
    return -1
            

def monitor():
    global stocks_with_index, stock_state
    _date = datetime.today()
    while(True):
        time.sleep(3)
        data = stock_state.copy()
        data = dict(
            sorted(data.items(), key=lambda x: x[1]['change'], reverse=True)
        )
        data = list(data.keys())
        toplosers = data[-TOPLOSERSGAINERS:]
        topgainers = data[:TOPLOSERSGAINERS]
        updatedgainers = []
        for symbol in topgainers:
            lastmedian = load_last_median(_date, symbol) 
            if lastmedian is None:
                update_last_median(symbol)
                continue
            
            lastmedian = int(lastmedian)
            currdayvolume = get_currday_volume(symbol)
            # print(currdayvolume, type(currdayvolume))
            # print(lastmedian, type(lastmedian))
            if currdayvolume > lastmedian:
                updatedgainers.append(symbol)
        
        updatedlosers = []
        for symbol in toplosers:
            lastmedian = load_last_median(_date, symbol) 
            if lastmedian is None:
                update_last_median(symbol)
                continue


            lastmedian = int(lastmedian)
            currdayvolume = get_currday_volume(symbol)
            print(currdayvolume, lastmedian)
            if currdayvolume > lastmedian:
                updatedlosers.append(symbol)
        print(updatedgainers)
        print(updatedlosers)
        set_top_gainers(updatedgainers)
        set_top_losers(updatedlosers)
                

swsthread = threading.Thread(target=websocket_connect, name="SmartWS", daemon=True)
swsthread.start()
monitorthread = threading.Thread(target=monitor, name="Monitor", daemon=True)
monitorthread.start()
syncthread = threading.Thread(target=fast_daily_sync, name="syncthread", daemon=True, args=(EXCHANGE, datetime.today()))
syncthread.start()

while(1):
    time.sleep(100000)

