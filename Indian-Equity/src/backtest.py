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


def sync_candles(exchange, symbol, startdate, enddate):
    isindex = False
    if symbol == 'Nifty 50':
        isindex = True
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

# for symbol,_ in stocktotoken.items():
#     startdate = datetime.now() - timedelta(days=100)
#     enddate = datetime.now()
#     while(startdate < datetime.today()):
#         enddate = startdate + timedelta(days=5)
#         sync_candles(EXCHANGE, symbol, startdate, enddate)
#         startdate = enddate


#get last trading day 
INDEX = 'Nifty 50'
trade_day_mapping = {}

# def load_data(daily = False, isindex = False):
#     records = db.get_candles(symbol, '1m')
#     df = pd.DataFrame(records)
#     if df.empty:
#         print(f"No candle data found. -> {symbol}")
#         continue
#     df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
#     df.dropna(subset=["timestamp"], inplace=True)
#     df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
#     df = df.sort_values(by='timestamp')
#     df['time'] = df['timestamp'].dt.time
#     df['date'] = df['timestamp'].dt.date
#     print(df)
#     break
def update_trading_days():
    startdate = datetime.today() - timedelta(days=100)
    enddate = datetime.today()
    df = broker.get_candle_stick_data(EXCHANGE, INDEX, 'ONE_DAY', startdate, enddate, isindex=True)
    if df is None or len(df) == 0:
        return None
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df.dropna(subset=["timestamp"], inplace=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    df = df.sort_values(by='timestamp')
    df['date'] = df['timestamp'].dt.date
    lastday = None
    for i, row in df.iterrows():
        trade_day_mapping[row['date']] = lastday
        lastday = row['date']

# def _update_state():


# update_trading_days()
# def backtest(df):

    

# for symbol,_ in stocktotoken.items():
#     records = db.get_candles(symbol, '1m')
#     df = pd.DataFrame(records)
#     if df.empty:
#         print(f"No candle data found. -> {symbol}")
#         continue
#     df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
#     df.dropna(subset=["timestamp"], inplace=True)
#     df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
#     df = df.sort_values(by='timestamp')
#     df['time'] = df['timestamp'].dt.time
#     df['date'] = df['timestamp'].dt.date
#     print(df)
#     break



def get_data_from_broker(exchange, symbol, startdate, enddate, isindex, timeframe):
    df = broker.get_candle_stick_data(exchange, symbol, timeframe, startdate, enddate, isindex)
    if df is None or len(df) == 0:
        return 
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df.dropna(subset=["timestamp"], inplace=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    df['symbol'] = symbol
    df['timeframe'] = '1m'
    list_of_jsons = df.to_dict(orient='records')
    print(symbol, '  ', enddate.date(), end= ' ')
    return list_of_jsons

def update_redis_data(exchange, symbol, startdate, enddate, isindex, timeframe):
    if timeframe == 'ONE_DAY' or timeframe == '1d':
        list_of_jsons = get_data_from_broker(exchange, symbol, startdate, enddate, isindex, 'ONE_DAY')
        if list_of_jsons is not None:
            db.insert_daily_candles(list_of_jsons)

    if timeframe == 'ONE_MINUTE' or timeframe == '1m':
        while(startdate < enddate):
            temp_enddate = startdate + timedelta(days=5)
            list_of_jsons = get_data_from_broker(exchange, symbol, startdate, temp_enddate, isindex, 'ONE_MINUTE')
            if list_of_jsons is not None:
                db.insert_candles(list_of_jsons)
            startdate = temp_enddate

def load_data_from_redis(symbol, timeframe, startdate ,enddate):
    records = None
    if timeframe == '1m' or timeframe == 'ONE_MINUTE':
        records = db.get_candles(symbol, '1m')

    if timeframe == '1d' or timeframe == 'ONE_DAY':
        records = db.get_daily_candles(symbol)

    df = pd.DataFrame(records)
    if df.empty:
        print(f"No candle data found. -> {symbol}")
        return 
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df.dropna(subset=["timestamp"], inplace=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    df = df.sort_values(by='timestamp')
    df['time'] = df['timestamp'].dt.time
    df['date'] = df['timestamp'].dt.date
    df = df[(df['date'] >= startdate.date()) & (df['date'] <= enddate.date())]
    df.reset_index(inplace = True, drop = True)
    return df




# for symbol, token in stocktotoken.items():
#     isindex =  False
#     if symbol == 'Nifty 50':
#         isindex = True
#     update_redis_data(EXCHANGE, symbol, datetime.today() - timedelta(days=100), datetime.today(), isindex, 'ONE_MINUTE')
#     update_redis_data(EXCHANGE, symbol, datetime.today() - timedelta(days=100), datetime.today(), isindex, 'ONE_DAY')
#     startdate = datetime.today() - timedelta(days=30)
#     enddate = datetime.today()
#     df = load_data_from_redis(symbol, '1m', startdate, enddate)
#     print(df)
#     break


'''
If stock qualifies this then choice of the day
1. volume better than last day 
2. entry only > 1.5 percent
3. last day change < 1 percent
4. timeframe 10min.
'''

def save_image(symbol, df ,  _date, entry, sl, type, tm):
    tm = str(tm)[:6].replace(':', '-')
    foldername = "-".join(str(_date).split(':'))
    filename = symbol
    folderpath = f"samplesimages/{foldername}" 
 
    filepath = f"samplesimages/{foldername}/{tm + filename + type}.jpg"
    os.makedirs(folderpath, exist_ok=True)
    for f in os.listdir(folderpath):
        if symbol in f:
            return 
    df['time'] = pd.to_datetime(df['timestamp'])
    df.set_index('time', inplace=True)

    ema_plots = []
    ema_plots.append(mpf.make_addplot(df['ema_9'], color='black', linestyle='-', width=2))
    # ema_plots.append(mpf.make_addplot(df['ema_30'], color='black', linestyle='-', width=5))

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


def is_good_volume(df, lastdaydf):
    top20 = lastdaydf.sort_values('volume', ascending=False).head(10)
    lastday_median = top20['volume'].median()
    start_10 = df.iloc[0:2]
    today_volume = start_10['volume'].median()
    if today_volume > lastday_median:
        print(f"Today volume: {today_volume}  Lastday median: {lastday_median}")
        return True
    return False

def buy_strategy(df, lastday_df, day, symbol):
    lastdaychange = (lastday_df.iloc[-1]['close'] - lastday_df.iloc[0]['open']) /  (lastday_df.iloc[0]['open']) * 100
    if abs(lastdaychange) > 1.5:
        return None
    copyday_df = df.copy()
    if is_good_volume(df.copy(), lastday_df.copy()) == False:
        return None
    firsthigh = df.iloc[0]['high']
    lastclose = lastday_df.iloc[-1]['close']
    lasthigh = lastday_df.iloc[-1]['high']
    df['change'] = (df['close'] - lastclose)/lastclose * 100
    df['max'] = df['high'].cummax()
    df['breakout'] = (df['max'].shift(1) == df['max'].shift(3)) & (df['high'] > df['max'].shift(1)) & (df['time'] < pd.to_datetime('11:30:00').time()) & (df['time'] > pd.to_datetime('10:00:00').time())
    df['breakout'] = df['breakout'].cummax()
    df['sl'] = df['low']
    df = df[df['breakout']]
    df['breakout'] = df['breakout'] &  (df['close'] > lasthigh) & (df['change'] < 3) & (df['change'] > 1.5) & (df['postrend']) & (df['time'] < pd.to_datetime('11:30:00').time()) & (df['time'] > pd.to_datetime('09:45:00').time())
    df = df[df['breakout']]
    if len(df) != 0:
        df = df.head(1)
        entry = df.iloc[0]['close']
        sl = df.iloc[0]['sl']
        tm = df.iloc[0]['time']
        sl = min(sl, entry - entry * 0.005)
        print(f"{symbol}  Entry: {entry}  SL: {sl}  time: {tm} day: {day}")
        save_image(symbol, copyday_df ,  day, entry, sl, 'buy', tm)


def is_sellcandle(df):
    df['pinbar1'] = (df['close'] < df['low'].shift(1))
    df['pinbar2'] = np.maximum(df['close'], df['open']) <= (df['low'] + (df['high'] - df['low']) * 0.2)
    df['newlow'] = np.minimum(df['low'], df['low'].shift(1))
    df['newhigh'] = np.maximum(df['high'], df['high'].shift(1))
    df['newopen'] = df['open'].shift(1)
    df['pinbar3'] = np.maximum(df['close'], df['newopen']) <= (df['newlow'] + (df['newhigh'] - df['newlow']) * 0.2)
    df['pinbar'] = df['pinbar1'] | df['pinbar2'] | df['pinbar3']
    return df

def sell_strategy(df, lastday_df, day, symbol):
    copyday_df = df.copy()
    # top20 = lastday_df.sort_values('volume', ascending=False).head(15)

    if is_good_volume(df.copy(), lastday_df.copy()) == False:
        return None
    
    top20 = lastday_df.head(10)
    lastday_median = top20['volume'].median()
    lastclose = lastday_df.iloc[-1]['close']
    lastlow = lastday_df.iloc[-1]['low']
    lasthigh = lastday_df.iloc[-1]['high']

    df['maxchange'] = (df['close'] - lasthigh)/lasthigh * 100

    df['change'] = (df['close'] - lastclose)/lastclose * 100
    df['rolling_median'] = df['volume'].rolling(window=5).median()
    df['rolling_mean'] = df['volume'].rolling(window=5).mean()
    df['rolling_var'] = df['volume'].rolling(window=5).std()
    df['rolling_var'] = df['rolling_var'].fillna(0)/df['rolling_mean'].replace(0, 1)
    df['isgoodstock'] = (df['rolling_median'] > lastday_median) & (df['rolling_var'] < 0.3) & (df['change'] < -1.5) 

    df['ema_above'] = df['ema_9'] > df['ema_9'].shift(1)
    df['ema_above'] = df['ema_above'].cummax()
    df['ema_touch'] = (df['high'] >= df['ema_9']) | (df['high'].shift(1) > df['ema_9'].shift(1))
    df['max'] = df['high'].cummax()

    df['goodclose'] = df['close'] <= (df['low'] + (df['high'] - df['low']) * 0.15)
    # df = is_sellcandle(df)
    # df['breakdown2'] = (df['close'] < df['low'].shift(1)) & (df['high'] > df['high'].shift(1)) & (df['ema_above'] == False) & (df['goodclose']) 
    df['breakdown1'] =  (df['close'].shift(1) > df['low'].shift(2)) & (df['close'] < df['low'].shift(1)) & (df['ema_above'] == False) & (df['ema_touch']) & (df['goodclose']) & (df['high'] >= df['ema_9'])
    df['breakdown'] = (df['breakdown1']) & (df['time'] > pd.to_datetime('09:25:00').time()) &(df['time'] < pd.to_datetime('11:00:00').time())
    df['sl'] = df['ema_9'].rolling(window=3).max()
    df = df[df['breakdown']]
    df = df.head(1)
    df['breakdown'] = df['breakdown'] &  (df['close'] < lastlow)  & (df['rolling_var'] > 0.3) & (df['change'] < -1.2) 
    if len(df) != 0:
        df = df.head(1)
        entry = df.iloc[0]['close']
        sl = df.iloc[0]['sl']
        tm = df.iloc[0]['time']
        sl = max(sl, entry + entry * 0.005)
        print(f"{symbol}  Entry: {entry}  SL: {sl}  time: {tm} day: {day}")
        save_image(symbol, copyday_df ,  day, entry, sl, 'sell', tm)




def buy_strategy(df, lastday_df, day, symbol):
    copyday_df = df.copy()
    if is_good_volume(df.copy(), lastday_df.copy()) == False:
        return None
    
    top20 = lastday_df.head(10)
    lastday_median = top20['volume'].median()
    lastclose = lastday_df.iloc[-1]['close']
    lastlow = lastday_df.iloc[-1]['low']
    lasthigh = lastday_df.iloc[-1]['high']

    df['maxchange'] = (df['close'] - lastlow)/lastlow * 100

    df['change'] = (df['close'] - lastclose)/lastclose * 100
    df['rolling_median'] = df['volume'].rolling(window=5).median()
    df['rolling_mean'] = df['volume'].rolling(window=5).mean()
    df['rolling_var'] = df['volume'].rolling(window=5).std()
    df['rolling_var'] = df['rolling_var'].fillna(0)/df['rolling_mean'].replace(0, 1)
    # df['isgoodstock'] = (df['rolling_median'] > lastday_median) & (df['rolling_var'] < 0.3) & (df['change'] < -1.5) 

    df['ema_below'] = df['ema_9'] < df['ema_9'].shift(1)
    df['ema_below'] = df['ema_below'].cummax()
    df['ema_touch'] = (df['low'] <= df['ema_9'])
    df['max'] = df['high'].cummax()

    df['goodclose'] = df['close'] >= (df['high'] - (df['high'] - df['low']) * 0.15)
    # df = is_sellcandle(df)
    # df['breakdown2'] = (df['close'] < df['low'].shift(1)) & (df['high'] > df['high'].shift(1)) & (df['ema_above'] == False) & (df['goodclose']) 
    df['breakdown1'] =  (df['close'].shift(1) < df['high'].shift(2)) & (df['close'] > df['high'].shift(1)) & (df['ema_below'] == False) & (df['ema_touch']) & (df['goodclose']) 
    df['breakdown'] = (df['breakdown1']) & (df['time'] > pd.to_datetime('09:25:00').time()) &(df['time'] < pd.to_datetime('11:00:00').time())
    df['sl'] = df['ema_9'].rolling(window=3).max()
    df = df[df['breakdown']]
    df = df.head(1)
    df['breakdown'] = df['breakdown'] &  (df['close'] > lasthigh)  & (df['rolling_var'] > 0.3) & (df['change'] > 1.2) 
    if len(df) != 0:
        df = df.head(1)
        entry = df.iloc[0]['close']
        sl = df.iloc[0]['sl']
        tm = df.iloc[0]['time']
        sl = min(sl, entry - entry * 0.005)
        print(f"{symbol}  Entry: {entry}  SL: {sl}  time: {tm} day: {day}")
        save_image(symbol, copyday_df ,  day, entry, sl, 'buy', tm)


TIMEFRAME = '15min'
def track_stock(df, symbol, niftydf):
    df = utils.resample(df, TIMEFRAME)
    df = Indicators.ema(df, 9, col = 'ema')
    df = Indicators.ema(df, 15, col = 'ema')
    df['time'] = df['timestamp'].dt.time
    df['date'] = df['timestamp'].dt.date
    df = pd.merge(df, niftydf[['timestamp', 'postrend', 'negtrend']], on='timestamp', how='left')

    uniquesday = df['date'].unique()
    lastday = None
    for day in uniquesday[:]:
        if lastday is None:
            lastday = day
            continue
        day_df = filter_by_day(df.copy(), day)
        lastday_df = filter_by_day(df.copy(), lastday)
        copyday_df = day_df.copy()
        buy_strategy(day_df.copy(), lastday_df.copy(), day, symbol)
        sell_strategy(copyday_df.copy(), lastday_df.copy(), day, symbol)



isindex =  False
startdate = datetime.today() - timedelta(days=10)
enddate = datetime.today()
isindex =  True
# update_redis_data(EXCHANGE, 'Nifty 50', datetime.today() - timedelta(days=100), datetime.today(), isindex, 'ONE_MINUTE')
niftydf = load_data_from_redis('Nifty 50', '1m', startdate, enddate)
niftydf = utils.resample(niftydf, TIMEFRAME)
niftydf = Indicators.ema(niftydf, 9, col = 'ema')
niftydf = Indicators.ema(niftydf, 15, col = 'ema')
niftydf['postrend'] = (niftydf['ema_9'] > niftydf['ema_9'].shift(2)) & (niftydf['ema_15'] > niftydf['ema_15'].shift(1)) & (niftydf['ema_9'] > niftydf['ema_15']) & (niftydf['low'] > niftydf['ema_15']) & (niftydf['low'] > niftydf['ema_9'].shift(1))
niftydf['negtrend'] = (niftydf['ema_9'] < niftydf['ema_9'].shift(2)) & (niftydf['ema_15'] < niftydf['ema_15'].shift(1)) & (niftydf['ema_9'] < niftydf['ema_15']) & (niftydf['high'] < niftydf['ema_15']) & (niftydf['high'] < niftydf['ema_9'].shift(1))

# print(niftydf[niftydf['postrend'] | niftydf['negtrend']])

for symbol, token in stocktotoken.items():
    isindex =  False
    startdate = datetime.today() - timedelta(days=1)
    enddate = datetime.today()
    isindex =  False
    update_redis_data(EXCHANGE, symbol, datetime.today() - timedelta(days=7), datetime.today(), isindex, 'ONE_MINUTE')
    orgdf = load_data_from_redis(symbol, '1m', startdate, enddate)
    # dailydf = load_data_from_redis(symbol, '1d', startdate, enddate)
    if orgdf is None:
        continue
    track_stock(orgdf.copy(), symbol, niftydf.copy())

    
