import pandas_ta as ta
import pandas as pd
class Indicators:
    @staticmethod
    def resample(data, interval, offset = '0min'):
        data.index = pd.to_datetime(data['timestamp'])
        data = data.resample(interval, offset = offset).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        data.reset_index(inplace=True)
        return data
    
    @staticmethod
    def ema(data, length, col):
        data[col + '_' + str(length)] = ta.ema(data['close'], length)
        return data
    
    @staticmethod
    def supertrend(data, length, multiplier, col):
        colname = col + '_' + str(length) + '_' + str(multiplier)
        supertrend = ta.supertrend(high=data['high'], low=data['low'], close=data['close'], length=length, multiplier=multiplier)
        data[colname] = supertrend["SUPERT_{}_{}.0".format(length, multiplier)]
        data[colname + '_' + 'direction'] = supertrend["SUPERTd_{}_{}.0".format(length, multiplier)]
        return data
    
    @staticmethod
    def vwap(data, col):
        data.index = pd.to_datetime(data['timestamp'])
        data[col] = ta.vwap(data['high'], data['low'], data['close'], data['volume'])
        data.reset_index(inplace=True, drop=True)
        return data
    
    @staticmethod
    def local_maxima(data, col, window):
        half_window = window // 2
        maxima = data['high'].rolling(window, center=True).apply(lambda x: int(x[half_window] == max(x)), raw=True).astype(bool)

    @staticmethod
    def local_maxima(data, window):
        # Compute rolling windows with the given window size
        rolling_max = data['high'].rolling(window, center=True, min_periods=window).max()
        data['maxima'] = data['high'] == rolling_max
        return data

    @staticmethod
    def local_minima(data, window):
        rolling_min = data['low'].rolling(window, center=True, min_periods=window).min()
        data['minima'] = data['low'] == rolling_min
        return data
    
    