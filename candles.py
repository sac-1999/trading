
import numpy as np
from indicators import Indicators

def load_resistance_support(df, window, trade_type):
    if trade_type == 'buy':
        df['peak'] = df['high'] == df['high'].rolling(2*window+1, center = True).max()
        df['resistance'] = np.where(df['peak'], df['high'], np.nan)
        df['resistance'] = df['resistance'].shift(window + 1)
        df.loc[:, 'resistance'] = df['resistance'].ffill()

        

    if trade_type == 'sell':
        df['bottom'] = df['low'] == df['low'].rolling(2*window + 1, center = True).min() 
        df['support'] = np.where(df['bottom'], df['low'], np.nan)
        df['support'] = df['support'].shift(window + 1)
        df.loc[:, 'support'] = df['support'].ffill()

    return df


def breakout_breakdown( df, window, trade_type):
    maincolumns = list(df.columns)
    df = load_resistance_support(df.copy(), window, trade_type)
    if trade_type == 'buy':
        df['last_max'] = df['high'].shift(1).rolling(2*window).max()
        df['breakout'] = (df['close'] > df['resistance']) & (df['last_max'] <= df['resistance'])
        maincolumns.append('breakout')

    if trade_type == 'sell':
        df['last_min'] = df['low'].shift(1).rolling(2*window).min()
        df['breakdown'] = (df['close'] < df['support']) & (df['last_min'] >= df['support'])
        maincolumns.append('breakdown')
    
    return df[maincolumns]

def is_pinbar(rowlist, trade_type, body_ratio=0.33, wick_ratio=0.33):
    row = rowlist[-1]
    open = row['open']
    close = row['close']
    high = row['high']
    low = row['low']

    body = abs(close - open)
    candle_range = high - low
    upper_wick = high - max(open, close)
    lower_wick = min(open, close) - low

    # Avoid division by zero
    if candle_range == 0:
        return False

    small_body = body < (candle_range * body_ratio)
    if trade_type == 'buy':
        return  small_body and lower_wick > (body * wick_ratio) and upper_wick < (lower_wick * wick_ratio)

    if trade_type == 'sell':
        return  small_body and upper_wick > (body * wick_ratio) and lower_wick < (upper_wick * wick_ratio)
       
def is_engulfing(rowlist, trade_type):
    if len(rowlist) < 2:
        print('need atleast two rows')
        return False

    prev = rowlist[-2]
    curr = rowlist[-1]

    # Bullish Engulfing: previous candle is bearish, current is bullish and engulfs previous body
    if trade_type == 'buy':
        return (
            prev['close'] < prev['open'] and  # previous bearish
            curr['close'] > curr['open'] and  # current bullish
            curr['low'] < prev['low'] and
            curr['close'] > prev['high']
        )

    # Bearish Engulfing: previous candle is bullish, current is bearish and engulfs previous body
    elif trade_type == 'sell':
        return (
            prev['close'] > prev['open'] and  # previous bearish
            curr['close'] < curr['open'] and  # current bullish
            curr['high'] > prev['high'] and
            curr['close'] < prev['low']
        )

    return False  # Invalid trade_type
    
def is_inside_bar(rowlist, trade_type = ""):
    if len(rowlist) < 2:
        print("[Error : ] atleast two rows required")
        return False  # Need at least two candles to compare

    prev = rowlist[-2]
    curr = rowlist[-1]
    return curr['high'] < prev['high'] and curr['low'] > prev['low']

def is_star_pattern(rowlist, trade_type):
    if len(rowlist) < 3:
        print("[Error : ] at least three rows required")
        return False

    c1 = rowlist[-3]
    c2 = rowlist[-2]  
    c3 = rowlist[-1]  

    def body(candle):
        return abs(candle['close'] - candle['open'])

    # Helper: candle direction
    def is_bullish(candle):
        return candle['close'] > candle['open']

    def is_bearish(candle):
        return candle['close'] < candle['open']

    small_body = body(c2) < body(c1) * 0.5 and body(c2) < body(c3) * 0.5

    if trade_type == 'buy':
        # Morning Star
        return (
            is_bearish(c1) and
            small_body and
            is_bullish(c3) and
            c3['close'] > (c1['open'] + c1['close']) / 2
        )

    elif trade_type == 'sell':
        # Evening Star
        return (
            is_bullish(c1) and
            small_body and
            is_bearish(c3) and
            c3['close'] < (c1['open'] + c1['close']) / 2
        )

    else:
        print("[Error : ] trade_type must be 'bullish' or 'bearish'")
        return False

def trap_with_3_candle_on_ema(df, trade_type):
    if trade_type == 'buy':
        df['trapbar'] = (df['close'] > df['high'].shift(1)) & (df[['close', 'open']].min(axis=1).shift(2) > df['ema_8'].shift(2)) & ((df['close'].shift(1) < df['ema_8'].shift(1)))
    elif trade_type == 'sell':
        df['trapbar'] = (df['close'] < df['low'].shift(1)) & (df[['close', 'open']].max(axis=1).shift(2) > df['ema_8'].shift(2)) & ((df['close'].shift(1) > df['ema_8'].shift(1)))
    return df

def is_doji(rowlist, threshold=0.1):
    if len(rowlist) < 1:
        print("[Error : ] at least one row required")
        return False

    candle = rowlist[-1]
    body_size = abs(candle['close'] - candle['open'])
    range_size = candle['high'] - candle['low']

    # Avoid division by zero
    if range_size == 0:
        return False

    # If body is less than threshold % of range, it's a Doji
    return body_size / range_size < threshold


def positivecandle(row):
    return row['close'] > row['open']

def negativecandle(row):
    return row['close'] < row['open']

def close_above_previous_high(firstrow, secondrow):
    return secondrow['close'] > firstrow['high']

def close_below_previous_low(firstrow, secondrow):
    return secondrow['close'] < firstrow['low']

def close_above_indictaor(row, indicator):
    return row['close']>row[indicator]

def close_below_indicator(row, indicator):
    return row['close'] < row[indicator]