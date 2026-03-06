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

supreme_data = {}

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


import json

def store_it_for_training(entry, slpct, df, profit, currdaychange):
    global supreme_data
    hourrsi = df.iloc[0]['hourrsi']
    hour4rsi = df.iloc[0]['hour4rsi']
    atr = df.iloc[0]['atr']/entry * 100

    supreme_data['rsi1'] = supreme_data.get('rsi1', []) + [hourrsi]
    supreme_data['rsi2'] = supreme_data.get('rsi2', []) + [hour4rsi]
    supreme_data['slpct'] = supreme_data.get('slpct', []) + [slpct]
    supreme_data['profit'] = supreme_data.get('profit', []) + [profit]
    supreme_data['currdaychange'] = supreme_data.get('currdaychange', []) + [currdaychange]
    supreme_data['atr'] = supreme_data.get('atr', []) + [atr]
    # print(supreme_data)
    with open("traindata.json", "w") as f:
        json.dump(supreme_data, f, indent=4)

    
def calculate_sell_profit(df, entry, sl, entrytime):
    df = filter_by_time(df, entrytime, pd.to_datetime('15:00:00').time())
    slpoints = entry - sl
    lastprice = None
    for i,row in df.iterrows():
        if row['high'] >= sl:
            return -1
        lastprice = row['close']
    
    return (lastprice - entry) / slpoints if lastprice else 0
    

def sell_strategy(df, lastday_df, day, symbol, supports, resistances):
    copyday_df = df.copy()

    df['min'] = df['low'].cummin()
    df['breakdown1'] = (df['min'].shift(1) == df['min'].shift(5)) & (df['low'] < df['min'].shift(1))
    df['sl'] = df['high'].rolling(window=5).max()
    df = df[df['breakdown1']]
    df = df.head(1)
    if len(df) == 0 or len(supports) == 0 :
        return None
    
    df['breakdown'] = (df['breakdown1']) & (df['time'] < pd.to_datetime('11:30:00').time())

    df = df[df['breakdown']]
    
    if len(df) != 0:
        df = df.head(1)
        entry = df.iloc[0]['close']
        sl = df.iloc[0]['sl']
        tm = df.iloc[0]['time']
        sl = max(sl, entry + entry * 0.005)
        print(f"{symbol}  Entry: {entry}  SL: {sl}  time: {tm} day: {day}")
        # save_image(symbol, copyday_df ,  day, entry, sl, 'sell', tm)
        profit = calculate_sell_profit(copyday_df.copy(), entry, sl, tm)
        slpct = (sl - entry) / entry * 100
        currdaychange = (lastday_df.iloc[-1]['close'] - entry)/entry * 100
        store_it_for_training(entry, slpct, df, profit, currdaychange)




# def buy_strategy(df, lastday_df, day, symbol):
#     copyday_df = df.copy()
#     df['isgoodclose'] = False
#     for i, row in df.iterrows():
#         highs = df.loc[:i, 'high'].tolist()[::-1]
#         if len(highs) < 3:
#             continue
        
#         newhighs = []
#         for i, high in enumerate(highs):
#             if high > row['close'] or high < row['low']:
#                 break
#             newhighs.append(high)


#         if len(newhighs) > 3 and row['close'] > max(newhighs):
#             df.loc[i, 'isgoodclose'] = True

#     df['breakout'] = (df['isgoodclose'])  & (df['time'] > pd.to_datetime('10:00:00').time()) & (df['time'] < pd.to_datetime('13:00:00').time())
#     df['sl'] = df['low'].rolling(window=5).min()
#     df = df[df['breakout']]

#     if len(df) != 0:
#         df = df.head(1)
#         entry = df.iloc[0]['close']
#         sl = df.iloc[0]['sl']
#         tm = df.iloc[0]['time']
#         sl = min(sl, entry - entry * 0.005)
#         print(f"{symbol}  Entry: {entry}  SL: {sl}  time: {tm} day: {day}")
#         save_image(symbol, copyday_df ,  day, entry, sl, 'buy', tm)


def buy_strategy(df, lastday_df, day, symbol):
    copyday_df = df.copy()
    first = df.iloc[0]
    df['failed'] = (df['high'] > first['high']) | (df['close'] < first['low'])
    df['failed'] = df['failed'].cummax()
    df['failed'] = df['failed'].shift(1).fillna(False)
    df['rollingvolume'] = df['volume'].rolling(window=5).mean()

    df['breakout'] = (~df['failed'])  & (df['close']> first['high']) & (df['volume'] > df['rollingvolume'])  & (df['hourrsi'] > 50) & (df['time'] > pd.to_datetime('09:45:00').time()) & (df['time'] < pd.to_datetime('13:00:00').time())
    df['sl'] = df['low'].rolling(window=5).min()
    df = df[df['breakout']]

    if len(df) != 0:
        df = df.head(1)
        entry = df.iloc[0]['close']
        sl = df.iloc[0]['sl']
        tm = df.iloc[0]['time']
        sl = min(sl, entry - entry * 0.005)
        print(f"{symbol}  Entry: {entry}  SL: {sl}  time: {tm} day: {day}")
        save_image(symbol, copyday_df ,  day, entry, sl, 'buy', tm)

def find_bottoms(df, window = 30):
    df['support'] = None
    df['issupport'] = False
    for i in range(len(df)):
        if i < window:
            continue
        left = df.iloc[i-window:i]
        right = df.iloc[i+1:i+window]
        curr = df.iloc[i]

        if left['low'].min() >= curr['low'] and right['low'].min() >= curr['low']:
            df.loc[i, 'support'] = curr['low']
            df.loc[i, 'issupport'] = True

    supports = df[df['issupport']]['support'].tolist()
    supports = supports[::-1]
    finalsupports = []
    for i in range(len(supports)):
        if len(finalsupports) == 0:
            finalsupports.append(supports[i])
            continue

        if supports[i] < finalsupports[-1] * 1.02:
            finalsupports.append(supports[i])

    return finalsupports



def find_peaks(df, window = 30):
    df['resistance'] = None
    df['isresistance'] = False
    for i in range(len(df)):
        if i < window:
            continue
        left = df.iloc[i-window:i]
        right = df.iloc[i+1:i+window]
        curr = df.iloc[i]

        if left['high'].max() <= curr['high'] and right['high'].max() <= curr['high']:
            df.loc[i, 'resistance'] = curr['high']
            df.loc[i, 'isresistance'] = True

    resistances = df[df['isresistance']]['resistance'].tolist()
    resistances = resistances[::-1]
    finalresistances = []
    for i in range(len(resistances)):
        if len(finalresistances) == 0:
            finalresistances.append(resistances[i])
            continue

        if resistances[i] > finalresistances[-1] * 1.02:
            finalresistances.append(resistances[i]) 
    return finalresistances


    
    

TIMEFRAME = '5min'
def track_stock(df, symbol, niftydf):
    df = utils.resample(df, TIMEFRAME)
    df = Indicators.atr(df, 14, col = 'atr')
    df = Indicators.rsi(df, 14, col = 'rsi')
    df = Indicators.ema(df, 9, col = 'ema')
    df = Indicators.ema(df, 15, col = 'ema')
    df_hour = utils.resample(df.copy(), '60min')
    df_hour = Indicators.rsi(df_hour, 14, col = 'hourrsi')
    df_hour['hourrsi'] = df_hour['hourrsi'].shift(1)
    df_hour = df_hour[['timestamp', 'hourrsi']]
    df_4hour = utils.resample(df.copy(), '240min')
    df_4hour = Indicators.rsi(df_4hour, 14, col = 'hour4rsi')
    df_4hour['hour4rsi'] = df_4hour['hour4rsi'].shift(1)
    df_4hour = df_4hour[['timestamp', 'hour4rsi']]

    df = pd.merge(df, df_hour, on='timestamp', how='left')
    df = pd.merge(df, df_4hour, on='timestamp', how='left')
    df = df.fillna(method='ffill')
    df = df.dropna()
    df.reset_index(inplace=True, drop=True)

    df['time'] = df['timestamp'].dt.time
    df['date'] = df['timestamp'].dt.date
    # df = pd.merge(df, niftydf[['timestamp', 'postrend', 'negtrend']], on='timestamp', how='left')

    uniquesday = df['date'].unique()
    lastday = None
    for day in uniquesday[:]:
        if lastday is None:
            lastday = day
            continue
        day_df = filter_by_day(df.copy(), day)
        lastday_df = filter_by_day(df.copy(), lastday)
        pastdata = filter_up_to_day(df.copy(), day)
        supports = find_bottoms(pastdata.copy(), window=30)
        resistances = find_peaks(pastdata.copy(), window=30)
        copyday_df = day_df.copy()
        # buy_strategy(copyday_df.copy(), lastday_df.copy(), day, symbol)
        print(symbol, day, supports, resistances)
        sell_strategy(copyday_df.copy(), lastday_df.copy(), day, symbol, supports, resistances)


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
    startdate = datetime.today() - timedelta(days=30)
    enddate = datetime.today()
    isindex =  False
    # update_redis_data(EXCHANGE, symbol, datetime.today() - timedelta(days=5), datetime.today(), isindex, 'ONE_MINUTE')
    orgdf = load_data_from_redis(symbol, '1m', startdate, enddate)
    # dailydf = load_data_from_redis(symbol, '1d', startdate, enddate)
    if orgdf is None:
        continue
    track_stock(orgdf.copy(), symbol, niftydf.copy())
    print(symbol, 'done')
    # break
    
