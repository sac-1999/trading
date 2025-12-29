import json 

from datetime import datetime, timedelta
from operator import index
from CandleStream import CandleStream 
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
# from calender_utils import *
import equity.utils as utils
import equity.dataset as dataset
# import strategy 
import numpy as np
# from indicators import Indicators
# import mplfinance as mpf
import os

EXCHANGE = 'NSE'
START_DATE = datetime(2025, 12, 1, 9, 10)
END_DATE = datetime(2025, 12, 17, 15, 30)
START_TIME = datetime(2025, 10, 20, 9, 15)
END_TIME = datetime(2025, 10, 20, 15, 30)
INTERVAL = "1min"
INDEX = 'Nifty 50'
TRAIL = False
stream = CandleStream()
ORGINDEXDF = None
SECTORS_DATA = {}
STOCKS_DATA = {}

MAX_NUMBER_OF_STOCKS_PER_DAY = 5
RISK = 0.005
CAPITAL = 200000
RPT = CAPITAL * RISK
DAILYRISK = RPT * MAX_NUMBER_OF_STOCKS_PER_DAY//2
LESSVOLATILESTOCK =  ['TCS', 'HDFCBANK', 'SBIN']

TRADE_HISTORY = {}

###Strategy Params to have a bias
INITIALRANGE_IN_MINUTES = 10
MOMENTUM_IN_LAST_MINUTES = 20
###
ALLSECTORS = None
with open("index_stock.json", "r") as f:
    ALLSECTORS = json.load(f)


class CandleRange:
    def __init__(self, high, low):
        self.high = high
        self.low = low
        

def bias_structure(
    df: pd.DataFrame,
    window: int = 50,
    body_max_frac: float = 0.3,     # body <= 30% of range
    wick_min_frac: float = 0.5,     # long wick >= 50% of range
    top_band_frac: float = 0.2,     # body must close in top 30% (bullish pin)
    bottom_band_frac: float = 0.2,  # body must close in bottom 30% (bearish pin)
    vol_norm_window: int = 10,
    vol_clip: float = 3.0           # cap normalized volume to reduce outlier influence
    ):
    """
    Expects df with columns: open, high, low, close, volume.
    Returns df with pin classifications and a rolling bias score in [-1, +1].
    """
    df = df.copy()

    # Basic geometry
    rng = (df['high'] - df['low']).replace(0, np.nan)
    body = (df['close'] - df['open']).abs()
    upper_wick = df['high'] - np.maximum(df['open'], df['close'])
    lower_wick = np.minimum(df['open'], df['close']) - df['low']

    # Where is close within the range? (0=low, 1=high)
    close_pos = (df['close'] - df['low']) / rng

    # Thresholds
    small_body = (body / rng) <= body_max_frac
    long_upper = (upper_wick / rng) >= wick_min_frac
    long_lower = (lower_wick / rng) >= wick_min_frac

    close_near_top = close_pos >= (1 - top_band_frac)
    close_near_bottom = close_pos <= bottom_band_frac

    # Classifications
    bullish_pin = small_body & long_lower & close_near_top
    bearish_pin = small_body & long_upper & close_near_bottom

    # Percent body move (helps rank strength; sign matters)
    ret_body = (df['close'] - df['open']) / df['open']

    # Volume normalization
    vol_ma = df['volume'].rolling(vol_norm_window, min_periods=1).mean()
    vol_norm = (df['volume'] / vol_ma).clip(lower=0, upper=vol_clip)

    # Assign pressure based on pin and signed return magnitude
    # (You could also use wick/body ratio as weight. Here we combine sign and volume.)
    buy_pressure = np.where(bullish_pin, vol_norm * np.maximum(ret_body, 0), 0.0)
    sell_pressure = np.where(bearish_pin, vol_norm * np.maximum(-ret_body, 0), 0.0)

    df['bullish_pin'] = bullish_pin
    df['bearish_pin'] = bearish_pin
    df['vol_norm'] = vol_norm
    df['buy_p'] = buy_pressure
    df['sell_p'] = sell_pressure

    # Rolling aggregates
    buy_sum = pd.Series(buy_pressure, index=df.index).rolling(window, min_periods=5).sum()
    sell_sum = pd.Series(sell_pressure, index=df.index).rolling(window, min_periods=5).sum()

    # Bias metrics
    spread = buy_sum - sell_sum
    spread_total = (buy_sum + sell_sum).replace(0, np.nan)

    # Final bias score in [-1, +1]
    bias_score = (spread / spread_total).fillna(0).clip(-1, 1)

    df['pin_bias_score'] = bias_score
    df['pin_buy_sum'] = buy_sum
    df['pin_sell_sum'] = sell_sum



def data_bulk_loader():
    global ORGINDEXDF
    ORGINDEXDF = dataset.get_data(stream, 'NSE', INDEX, utils.get_token(EXCHANGE, INDEX), START_DATE, END_DATE, INTERVAL)
    ORGINDEXDF['date'] = ORGINDEXDF['timestamp'].dt.date
    
    for sector, stocks in ALLSECTORS.items():
        sectordf = dataset.get_data(stream, 'NSE', sector, utils.get_token_for_index(EXCHANGE, sector), START_DATE, END_DATE, INTERVAL)
        if sectordf is None:
            print(f"Data not found for sector: {sector}")
        else:
            sectordf['date'] = sectordf['timestamp'].dt.date
            SECTORS_DATA[sector] = sectordf

        for symbol in stocks:
            stockdf = dataset.get_data(stream, 'NSE', symbol, utils.get_token(EXCHANGE, symbol + '-EQ'), START_DATE, END_DATE, INTERVAL)
            if stockdf is None:
                print(f"Data not found for stock: {symbol}")
            else:
                stockdf['date'] = stockdf['timestamp'].dt.date
                STOCKS_DATA[symbol] = stockdf

def filter_data_by_date(df, date):
    filtered_df = df[df['date'] == date.date()]
    return filtered_df

def filter_data_by_time(df, start_time, end_time):
    filtered_df = df[(df['timestamp'].dt.time >= start_time) & (df['timestamp'].dt.time <= end_time)]
    return filtered_df

def get_minor_data(df, date, end_time):
    df = filter_data_by_date(df, date)
    if df.empty:
        return 
    df = filter_data_by_time(df, START_TIME.time(), end_time)
    return df

def fit_strategy(df, side, date, t):
   
    # remainingdf = df.iloc[:-3, :]
    last_3_candles = df.iloc[-3:, :]
    if side == 'bullish':
        dayhigh = df['high'].max()
        if last_3_candles['close'].max() > (dayhigh - dayhigh * 0.03 / 100):
            entry =  df.iloc[-1]['close']
            sl = df.iloc[-25:]['low'].min()
            target = entry + 3 * (entry - sl)

            return {'entry' : entry, 'sl' : sl, 'target' : target, 'date' : date, 'time' : t, 'status' : True}
        
    if side == 'bearish':
        daylow = df['low'].min()
        if last_3_candles['close'].min() < (daylow + daylow * 0.05):
            entry =  df.iloc[-1]['close']
            sl = df.iloc[-25:]['high'].max()
            target = entry - 3 * (sl - entry)
            return {'entry' : entry, 'sl' : sl, 'target' : target, 'date' : date, 'time' : t, 'status' : True}



def manage_trades(stock, is_trade, curr_t):
    update_profit_state(curr_t)
    netrpofit = 0
    totalnumberoftrades = 0
    for stock, trade in TRADE_HISTORY.items():
        netrpofit += trade.get('profit', 0)
        totalnumberoftrades += 1

    print(is_trade)

    if totalnumberoftrades > MAX_NUMBER_OF_STOCKS_PER_DAY:
        return 
    
    if netrpofit < DAILYRISK:
        return 

    print(f"At time {curr_t}, Total trades: {totalnumberoftrades}, Net profit: {netrpofit}")
    if totalnumberoftrades == 1 :
        if netrpofit > RPT//2:
            print(f"Placing {totalnumberoftrades + 1}rd trade at time {curr_t} as net profit {netrpofit} > RPT {RPT//2}")
            TRADE_HISTORY[stock] = is_trade

    elif totalnumberoftrades == 2:
        if netrpofit > RPT:
            print(f"Placing {totalnumberoftrades + 1}rd trade at time {curr_t} as net profit {netrpofit} > RPT {RPT}")
            TRADE_HISTORY[stock] = is_trade

    elif totalnumberoftrades == 3:
        if netrpofit > RPT * 2:
            print(f"Placing {totalnumberoftrades + 1}rd trade at time {curr_t} as net profit {netrpofit} > RPT {RPT * 2}")
            TRADE_HISTORY[stock] = is_trade

    elif totalnumberoftrades >= 4:
        if netrpofit > RPT * 3:
            print(f"Placing {totalnumberoftrades + 1}rd trade at time {curr_t} as net profit {netrpofit} > RPT {RPT * 3}")
            TRADE_HISTORY[stock] = is_trade
    

def update_profit_state(current_time):
    global TRADE_HISTORY
    hisotry_temp = TRADE_HISTORY.copy()
    for stock, trade in TRADE_HISTORY.items():
        stockdf = STOCKS_DATA.get(stock)
        if stockdf is None:
            print(f"This is not Possible as this trade already exists for stock : {stock} with trade \n {trade}")

        else:
            stockdf = get_minor_data(stockdf, trade['date'], current_time)
            currprice = stockdf.iloc[-1]['close']
            if trade['type'] == 'buy' and trade['status'] == True:
                if currprice < trade['sl']:
                    profit = (trade['sl'] - trade['entry']) * trade['quantity']
                    hisotry_temp[stock]['status'] = False
                    hisotry_temp[stock]['exit_price'] = trade['sl']
                    hisotry_temp[stock]['notes'] = 'sl hit'
                    hisotry_temp[stock]['profit'] = profit
                elif currprice > trade['target'] : 
                    profit = (trade['target'] - trade['entry']) * trade['quantity']
                    hisotry_temp[stock]['status'] = False
                    hisotry_temp[stock]['exit_price'] = trade['target']
                    hisotry_temp[stock]['notes'] = 'target achieved'
                    hisotry_temp[stock]['profit'] = profit
                else:
                    profit = (currprice - trade['entry']) * trade['quantity']
                    hisotry_temp[stock]['profit'] = profit
                

                if TRAIL and hisotry_temp[stock]['status'] == True and trade['sl'] != trade['entry']:
                    new_sl = trade['entry']
                    if currprice - trade['entry'] > 2*(trade['entry'] - trade['sl']):
                        hisotry_temp[stock]['sl'] = new_sl


            if trade['type'] == 'sell' and trade['status'] == True:
                if currprice > trade['sl']:
                    profit = (trade['entry'] - trade['sl']) * trade['quantity']
                    hisotry_temp[stock]['status'] = False
                    hisotry_temp[stock]['exit_price'] = trade['sl']
                    hisotry_temp[stock]['notes'] = 'sl hit' 
                    hisotry_temp[stock]['profit'] = profit
                elif currprice < trade['target'] :
                    profit = (trade['entry'] - trade['traget']) * trade['quantity']
                    hisotry_temp[stock]['status'] = False
                    hisotry_temp[stock]['exit_price'] = trade['target']
                    hisotry_temp[stock]['notes'] = 'target achieved'
                    hisotry_temp[stock]['profit'] = profit
                else:
                    profit = (trade['entry'] - currprice) * trade['quantity']
                    hisotry_temp[stock]['profit'] = profit 

                if TRAIL and hisotry_temp[stock]['status'] == True and trade['sl'] != trade['entry']:
                    new_sl = trade['entry']
                    if trade['entry'] - currprice > 2*(trade['sl'] - trade['entry']):
                        hisotry_temp[stock]['sl'] = new_sl

    TRADE_HISTORY = hisotry_temp.copy()

def analyse_momentum(df):
    poschange = []
    negchange = []
    indecisivevolume = []
    for i , row in df.iterrows():
        change = (row['close'] - row['open']) / row['open'] * 100
        bullish = row['close'] > (row['high'] - (row['high'] - row['low'])/3)
        bearish = row['close'] < (row['low'] + (row['high'] - row['low'])/3)
        if bullish:
            poschange.append(change)
        elif bearish:
            negchange.append(change)
        else:
            indecisivevolume.append(change)

    posplayers = len(poschange)
    negplayers = len(negchange)
    if posplayers > negplayers:
        return 'bullish'
    
    if negplayers > posplayers:
        return 'bearish'
    

def strategy_to_create_a_bias(df):
    """
    Docstring for strategy_to_create_a_bias
    1. use 10 min candles high and low 
    2. use volume and price sync for last n candles
    
    :param df: Description
    """
    THRESHOLD_FROM_TOP_BOTTOM = 0.15
    if len(df) < INITIALRANGE_IN_MINUTES or len(df) < MOMENTUM_IN_LAST_MINUTES:
        return None
    candlerange = CandleRange(df.iloc[:INITIALRANGE_IN_MINUTES]['high'].max(), df.iloc[:INITIALRANGE_IN_MINUTES]['low'].min())
    currcandle = df.iloc[-1]
    last_n_candles = df.iloc[-1 * MOMENTUM_IN_LAST_MINUTES : ]
    dayhigh = df.iloc[:-1,:]['high'].max()
    daylow = df.iloc[:-1, :]['low'].min()
    dist_from_top = (dayhigh - currcandle['high'])/currcandle['high']
    dist_from_bottom = (currcandle['low'] - daylow)/daylow 
    momentum = analyse_momentum(last_n_candles.copy())
    if momentum is None:
        return 
    if currcandle['close'] > candlerange.high and momentum == 'bullish' and dist_from_top < THRESHOLD_FROM_TOP_BOTTOM:
        return momentum
    if currcandle['close'] < candlerange.low and momentum == 'bearish'  and dist_from_bottom < THRESHOLD_FROM_TOP_BOTTOM:
        return momentum
    return None
        

def get_market_view(indexdf, date, curr_t):
    indexmomentum = strategy_to_create_a_bias(indexdf)
    # print(f"Seems like index momentum is : {indexmomentum} at {curr_t}")
    # print(currcandle, candlerange.high)
    if indexmomentum is None:
        return None, None
    momentum_sectors = {'bullish' : [], 'bearish' : []}
    for sector, stocks in ALLSECTORS.items():
        sectordf = SECTORS_DATA.get(sector)
        if sectordf is None:
            print(f"No data for sector: {sector} on date: {curr_t}")
            continue    
        sectordf = get_minor_data(sectordf, date, curr_t)
        sectormomentum = strategy_to_create_a_bias(sectordf)
        if sectormomentum:
            momentum_sectors[sectormomentum].append(sector)
    return  indexmomentum, momentum_sectors[indexmomentum]

def get_best_stocks_of_sector(stocks, side, t, date):
    stockchange = {}
    if side == 'bullish':
        for stock in stocks:
            stockdf = STOCKS_DATA.get(stock)
            if stockdf is not None:
                stockdf = get_minor_data(stockdf, date, t)
                daylow = stockdf['low'].min()
                currclose = stockdf.iloc[-1]['close']
                change = (currclose - daylow) / daylow * 100
                stockchange[stock] = change
    
        return sorted(stockchange.items(), key=lambda x: x[1], reverse=True)

    
    if side == 'bearish':
        for stock in stocks:
            stockdf = STOCKS_DATA.get(stock)
            if stockdf is not None:
                stockdf = get_minor_data(stockdf, date, t)
                dayhigh = stockdf['high'].max()
                currclose = stockdf.iloc[-1]['close']
                change = (currclose - dayhigh) / currclose * 100
                stockchange[stock] = change
    
        return sorted(stockchange.items(), key=lambda x: x[1])
   
        



def day_trading(date):
    '''This will do day trading for all stocks in index_stock.json for a given date'''
    print("Starting day trading for date:", date)
    timer = START_TIME
    if ORGINDEXDF is None:
        print(f"XXXXXXXXXXXXXXXXXXXXXXXXXXX           \n No index data for {date}: may be some issue check again")
    indexdf = filter_data_by_date(ORGINDEXDF.copy(), date)
    if indexdf is None or indexdf.empty:
        print(f"XXXXXXXXXXXXXXXXXXXXXXXXXXX           \n No index data for {date}: may be a holiday check again")
        return 
    
    while timer < END_TIME:
        timer = timer + timedelta(minutes=1)
        t = timer.time()
        indexdf = get_minor_data(ORGINDEXDF.copy(), date, t)
        side, sectors = get_market_view(indexdf, date, t)
        if side is None:
            continue
        if side:
            print(f"{date}   {t} -> [{side}]  :  {sectors}")

        for sector in sectors:
            stocks = ALLSECTORS[sector]
            stocks = get_best_stocks_of_sector(stocks, side, t, date)
            # print(stocks)

            for stock, change in stocks:
                if TRADE_HISTORY.get(stock) is None:
                    continue
                if stock in LESSVOLATILESTOCK and abs(change) < 1: 
                    continue 

                if abs(change) < 1.5 and stock not in LESSVOLATILESTOCK:
                    continue

                stockdf = STOCKS_DATA.get(stock)
                if stockdf is None:
                    print(f"No data for stock : {stock} on date : {date}")

                stockdf = get_minor_data(stockdf, date, t)
                is_trade = fit_strategy(stockdf, side, date, t)
                if is_trade is None:
                    continue
                
                else:
                    manage_trades(stock, is_trade, t)
        update_profit_state(t)
    return 
    for sector, stocks in ALLSECTORS.items():
         print("Processing sector:", sector)


    indexdf = filter_data_by_date(ORGINDEXDF, date)
    if indexdf.empty:
        print("No index data for date:", date)
        return
    
    for sector, stocks in ALLSECTORS.items():
        sectordf = SECTORS_DATA.get(sector)
        if sectordf is None:
            print(f"No data for sector: {sector} on date: {date}")
            continue
        sectordf = filter_data_by_date(sectordf, date)
        if sectordf.empty:
            print(f"No sector data for sector: {sector} on date: {date}")
            continue

        for symbol in stocks:
            stockdf = STOCKS_DATA.get(symbol)
            if stockdf is None:
                print(f"No data for stock: {symbol} on date: {date}")
                continue
            stockdf = filter_data_by_date(stockdf, date)
            if stockdf.empty:
                print(f"No stock data for stock: {symbol} on date: {date}")
                continue

            # Here you can implement your trading strategy using indexdf, sectordf, stockdf
            print(f"Processing trading strategy for stock: {symbol} on date: {date}")
            # strategy.execute_trading_strategy(indexdf, sectordf, stockdf)




# for sector, stocks in ALLSECTORS.items(): 
#     print("--"*50, sector)
#     token = utils.get_token_for_index(EXCHANGE, sector)
#     if token is None:
#         continue
#     indexdf = dataset.get_data(stream, 'NSE', sector, token, START_DATE, END_DATE, INTERVAL)
#     indexdf['day'] = indexdf['timestamp'].dt.date
    
#     for symbol in stocks:        
#         token = utils.get_token(EXCHANGE, symbol + '-EQ')
#         orgdf = dataset.get_data(stream, 'NSE', symbol, token, START_DATE, END_DATE, INTERVAL) 
            

data_bulk_loader()
day_trading(END_DATE)
print(TRADE_HISTORY)

#   // "NIFTY OIL & GAS": [
#   //   "IGL",
#   //   "GAIL",
#   //   "GSPL",
#   //   "MGL",
#   //   "RELIANCE",
#   //   "CASTROLIND",
#   //   "OIL",
#   //   "ONGC",
#   //   "ATGL",
#   //   "PETRONET",
#   //   "IOC",
#   //   "BPCL",
#   //   "HINDPETRO",
#   //   "AEGISLOG",
#   //   "GUJGASLTD"
#   // ],